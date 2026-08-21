"""FAZ C1 — deterministic report synthesis (PURE, no LLM, no clock, no randomness).

Turns the FAZ-B engine output (Finding[] + ActionItem[]) into the v2 report
building blocks: risk_radar, executive_verdict, action_plan, section_reviews.

CANON/report.md: text is a DETERMINISTIC assembly from rules — not an LLM. Every
number here comes from a transparent, documented formula over the findings'
severity distribution; every threshold/weight is a NAMED, commented constant in
ONE place (v1 defaults, tunable — flagged for Omer's scientific audit). Same
findings in → byte-identical report blocks out (no set/dict iteration order in
outputs: everything is explicitly sorted).

FAZ-B carry-forward closed here: executive_verdict confidence DOWN-WEIGHTS
findings whose anchors are unverified (engine/academic/anchoring.py) and findings
that rely ONLY on global_issue=True with no verified anchor — they are not treated
as full-strength evidence.

Contract reused (api/models/review.py):
  - Finding            :557-593   - ActionItem        :539-551
  - RiskRadarItem      :596-603   - ExecutiveVerdict  :631-640
  - SectionReview      :643-651   - Manuscript/Meta   :135-158
  - SeverityV2         :554       - Verdict           :60
  - ActionPriority     :535
Rubric/RubricDimension: engine/academic/rubric_registry.py:80-102 (id field).
"""

from __future__ import annotations

import re

from api.models.review import (
    ActionItem,
    DimensionScore,
    EvidencePack,
    ExecutiveVerdict,
    Finding,
    Manuscript,
    RiskRadarItem,
    SectionReview,
    SeverityV2,
    Verdict,
)
from engine.academic.anchoring import finding_evidence_is_weak
from engine.academic.assessment import QUANTITATIVE_ENGINE
from engine.academic.rubric_registry import Rubric, missing_sections

SYNTHESIS_VERSION = "report_synthesis.v1"

# ===========================================================================
# v1 DEFAULT CONSTANTS — single source of truth, tunable (flag for Omer)
# ===========================================================================

# The 10 risk dimensions, in spec order (review_report_schema_spec.md:43-54).
RISK_DIMENSIONS: tuple[str, ...] = (
    "contribution",
    "literature",
    "methodology",
    "evidence",
    "citation",
    "statistics",
    "ethics",
    "reproducibility",
    "writing",
    "venue_fit",
)

# Severity ordering (worst → best). Used for "worst severity present" + sorting.
_SEVERITY_RANK: dict[str, int] = {
    "critical": 5,
    "major": 4,
    "moderate": 3,
    "minor": 2,
    "info": 1,
}

# Radar score formula: start at RADAR_BASE_SCORE, subtract a penalty per finding
# by its severity, clamp to [0, 100]. Transparent and additive.
RADAR_BASE_SCORE: float = 100.0
RADAR_SEVERITY_PENALTY: dict[str, float] = {
    "critical": 45.0,
    "major": 25.0,
    "moderate": 12.0,
    "minor": 5.0,
    "info": 0.0,
}

# A dimension with NO findings is honestly reported as a high score + info severity
# ("no issues found" — not fake praise).
RADAR_EMPTY_SCORE: float = RADAR_BASE_SCORE
RADAR_EMPTY_SEVERITY: SeverityV2 = "info"
# Confidence we assign to an empty dimension. We did not deeply probe it, so this
# is deliberately moderate, NOT 1.0 (honest: absence of findings != certainty).
RADAR_EMPTY_CONFIDENCE: float = 0.5

# Executive verdict decision tree (readiness score → recommended_decision).
# v2 — 61 makalelik goldset'e karşı EMPIRİK KALİBRE EDİLDİ (2026-08-08, bkz.
# PDF_PIPELINE_CALISMA_GUNLUGU.md §29). Severity-SAYIM eşikleri (v1) yerine
# risk_radar'ın severity-ağırlıklı overall_readiness_score'u kullanılıyor.
#
# Kalibrasyon yöntemi: 61 goldset makalesinin (overall_readiness_score,
# insan_verdict) çiftleri üzerinde sınıf-dengeli doğruluk (balanced accuracy =
# sınıf başı doğruluğun ortalaması; ham accuracy dağılım-çarpık goldset'te
# — 49 accept / 2 major_revision / 10 reject — yanıltıcı) maksimize eden 2
# boyutlu eşik taraması. Dejenere/ikili çöküşü (t1≈t2) engellemek için
# major_revision bandına min 6 puan genişlik zorunlu kılındı.
#
# Sonuç: t_accept=78.5, t_reject=72.0 → sınıf-dengeli doğruluk %71
# (accept 31/49, major_revision 2/2, reject 5/10 doğru).
#
# BİLİNEN BOŞLUK: goldset'te SIFIR minor_revision ground-truth örneği var
# (0/61) — bu katman kalibre EDİLEMEDİ. accept eşiğinin hemen altına uydurma
# bir minor_revision bandı sokmak, elimdeki TEK 2 gerçek major_revision
# örneğini (readiness=76.0 ve 78.0 — tam o banda düşüyorlar) yanlış
# sınıflandırırdı; bu yüzden minor_revision şema değeri olarak kalıyor ama
# bu skor mantığından ÜRETİLMİYOR. Ömer'e açık TODO: ek goldset örnekleri
# veya ayrı bir sinyal olmadan bu katman güvenilir kalibre edilemez.
ACCEPT_READINESS_THRESHOLD: float = 78.5  # readiness >= bu → accept
REJECT_READINESS_THRESHOLD: float = 72.0  # readiness < bu → reject
# else (REJECT_READINESS_THRESHOLD <= readiness < ACCEPT_READINESS_THRESHOLD)
# → major_revision

# ---------------------------------------------------------------------------
# moat-gate (2026-08-08, guardian ile 2 tur danışıldı — bkz.
# PDF_PIPELINE_CALISMA_GUNLUGU.md §30)
# ---------------------------------------------------------------------------
# SORUN: readiness yukarıdaki gibi 10 risk kategorisinin EŞİT AĞIRLIKLI
# ortalaması. Moat'a özgü 2 kategori (atıf bütünlüğü, istatistiksel
# tutarlılık) 7 genel (Stanford tarzı) kategoriyle aynı ağırlıkta — biri
# critical bulgu üretse bile diğer 7'si temizse ortalama yine "accept"
# diyebilir, moat'ın kararda GÖRÜNMEZ kalması riski (guardian §29 bulgusu).
#
# ÇÖZÜM: readiness'e/skora DOKUNULMUYOR (o hâlâ §29'daki kalibrasyonun ürünü,
# "transparent/reproducible" iddiası bozulmasın diye) — ayrı bir TAVAN
# katmanı: bu 2 moat grubundan biri CRITICAL bulgu içeriyorsa nihai karar
# en fazla "reject" olabilir (asla daha iyiye çekmiyor, sadece
# kötüleştirebilir — bkz. aşağıdaki _moat_gate).
#
# NEDEN SADECE "critical", "major" DEĞİL (61 makalelik goldset'e karşı
# empirik ölçüldü, §30): ilk tasarım critical+major'ı birlikte tavanlıyordu,
# ama 61 makalenin 53'ünde (%87) en az 1 major-severity citation/quant moat
# bulgusu çıktı — "major" bu goldset'te ayırt edici bir sinyal DEĞİL,
# neredeyse evrensel. Tavan olarak kullanılınca verdict doğruluğu %62'den
# %18'e çöktü (39/49 gerçek-accept makale major_revision'a düşürüldü).
# "critical" çok daha nadir (3/61) ve ayırt edici kaldı — doğruluk etkisi
# ihmal edilebilir (%62→%61, 1 makale). Kök neden (CitationIntegrityEngine/
# QuantitativeValidityEngine'in "major" severity kalibrasyonu mu abartılı,
# yoksa gerçekten neredeyse her makalede bir atıf/istatistik kusuru mu var)
# araştırılmadı — açık TODO.
#
# KAPSAM (guardian'ın 2. tur bulgusu — risk_radar'ın "literature" KOVASI
# KULLANILMIYOR, çünkü o kova _CLAIM_ENGINE'in genel-amaçlı
# theoretical_framing/theoretical_framework bulgularıyla da kirleniyor,
# moat'a özgü değil): doğrudan Finding kaynağından ayrıştırılıyor.
#   - Atıf/kapsam-bütünlüğü: citation_integrity + literature_positioning —
#     ikisi de DOĞRULANABİLİR/deterministik-kanıtlanabilir iddialar (uydurma
#     referans, çözülemeyen atıf, çelişkili bağlam — EvidencePack'in
#     fabricated/retracted/contradicted alanlarıyla eşleşir; bkz.
#     assessment.py::_has_citation_integrity_evidence, aynı 3 gerekçe).
#     dimension_engine.py'nin force_dimension'ı sayesinde bu Finding'lerin
#     .dimension'ı BİREBİR bu ID'lerden biri — keyword-fallback belirsizliği
#     yok.
#   - 2026-08-10 (§38, guardian bulgusu): `literature_depth` BİLİNÇLİ OLARAK
#     BURADAN ÇIKARILDI (eskiden dahildi — gerçek bir tutarsızlıktı: SS35'te
#     literature_depth'in niyeti derinlik/güncellik/eleştirellik diye
#     ayrıştırılmıştı, fabricated/retracted ile "kanıtlanabilir" değil; ama
#     moat-gate'in kendisi hâlâ onu dahil ediyordu — yani kanıtsız bir
#     "critical" literature_depth bulgusu deterministik downgrade guard'ından
#     (assessment.py) hiç geçmeden buraya ulaşıp TÜM makaleyi "reject"e
#     kilitleyebiliyordu. Guard'ın kapsamıyla (citation_integrity/
#     literature_positioning) BİREBİR eşleşmesi için literature_depth
#     çıkarıldı — "moat-gate = doğrulanabilir bütünlük ihlali" tanımı artık
#     tutarlı.
#   - İstatistiksel tutarlılık: QuantitativeValidityEngine'in bulguları
#     LLM-serbest alt-boyut adları taşıyor (force_dimension yok), bu yüzden
#     ID eşleşmesi güvenilir değil — bunun yerine finding_id ÖNEKİ
#     kullanılıyor (quantitative_engine.py id_prefix="quant", tüm codebase'de
#     zaten bu konvansiyon var, bkz. test fixture'larındaki "cite.f0"/
#     "method.f0" örnekleri).
_CITATION_MOAT_DIMENSION_IDS: frozenset[str] = frozenset(
    {"citation_integrity", "literature_positioning"}
)
_STATISTICS_MOAT_FINDING_ID_PREFIX: str = "quant."

# Verdict sıralaması (kötüden iyiye) — gate'in "sadece kötüleştir" mantığı için.
_VERDICT_RANK: dict[str, int] = {
    "reject": 0,
    "major_revision": 1,
    "minor_revision": 2,
    "accept": 3,
}

# Evidence down-weight: a finding with no verified anchor (global_issue-only or
# all-anchors-unverified) counts at this fraction of a verified finding when we
# compute verdict confidence. THIS is the FAZ-B carry-forward enforcement.
WEAK_EVIDENCE_WEIGHT: float = 0.4
STRONG_EVIDENCE_WEIGHT: float = 1.0
# Verdict confidence when there are no findings at all (clean document): we are
# moderately confident, not certain (deterministic checks are not exhaustive).
VERDICT_NO_FINDINGS_CONFIDENCE: float = 0.6

# Cap on how many fatal risks the executive verdict surfaces (spec FE: "Top 5").
TOP_FATAL_RISKS_MAX: int = 5

# Section status from the worst finding severity in that section.
SECTION_STATUS_BY_SEVERITY: dict[str, str] = {
    "critical": "broken",
    "major": "broken",
    "moderate": "weak",
    "minor": "weak",
    "info": "ok",
}

# Free-text finding.dimension → one of the 10 RISK_DIMENSIONS. Ordered: first
# matching substring wins (specific before general). v1 mapping — tunable.
_DIMENSION_KEYWORD_MAP: tuple[tuple[str, str], ...] = (
    ("ethic", "ethics"),
    ("integrity_security", "ethics"),
    ("injection", "ethics"),
    ("reproduc", "reproducibility"),
    ("replicat", "reproducibility"),
    ("artifact", "reproducibility"),
    ("guideline", "reproducibility"),
    ("reporting", "reproducibility"),
    ("compliance", "reproducibility"),
    ("stat", "statistics"),
    ("analysis", "statistics"),
    ("significan", "statistics"),
    ("p_value", "statistics"),
    ("citation", "citation"),
    ("reference", "citation"),
    ("literature", "literature"),
    ("related", "literature"),
    ("background", "literature"),
    ("positioning", "literature"),
    ("coverage", "literature"),
    ("framing", "literature"),
    ("framework", "literature"),
    ("method", "methodology"),
    ("sample", "methodology"),
    ("technical_correct", "methodology"),
    ("soundness", "methodology"),
    ("rigor", "methodology"),
    ("validity", "methodology"),
    ("writ", "writing"),
    ("clarity", "writing"),
    ("clear", "writing"),
    ("presentation", "writing"),
    ("structure", "writing"),
    ("grammar", "writing"),
    ("venue", "venue_fit"),
    ("track", "venue_fit"),
    ("scope", "venue_fit"),
    ("contribution", "contribution"),
    ("original", "contribution"),
    ("novel", "contribution"),
    ("importance", "contribution"),
    ("problem", "contribution"),
    ("hypothes", "contribution"),
    ("question", "contribution"),
    ("claim", "evidence"),
    ("evidence", "evidence"),
    ("support", "evidence"),
    ("alignment", "evidence"),
)
# Fallback when nothing matches (most general bucket). v1 default — flag for Omer.
_DEFAULT_RISK_DIMENSION: str = "evidence"

# 2026-08-07 guardian bulgusu: substring-anahtar-kelime eşleştirmesi ("keyword in d")
# sıra-bağımlı ve sessizce yanlış sınıflandırabiliyor — rubric_registry.py'nin TÜM
# gerçek dimension ID'leri (5 tablo, 44 benzersiz ID) tek tek izlendi, 3 GERÇEK
# yanlış-yönlendirme bulundu: "problem_significance" ("significan" alt-dizgesi
# istatistiksel-anlamlılık kovasına çarpıyordu, oysa bu bir hibe önerisinin problem
# önemi — contribution), "analysis_validity"/"analysis_depth" ("analysis" alt-dizgesi
# "statistics"e çarpıyordu, oysa rubric_registry'de ikisi de _METHODOLOGY motoruna
# yönleniyor), "contribution_clarity" ("clarity" alt-dizgesi listede "contribution"dan
# önce geldiği için "writing"e çarpıyordu, oysa _CLAIM_ENGINE'e yönleniyor — contribution
# ailesi). Bilinen ID'ler artık DOĞRUDAN bu tablodan eşleniyor (substring aramaya hiç
# girmiyor); yalnızca gelecekte eklenecek YENİ/bilinmeyen ID'ler için substring tablosu
# (aşağıda) hâlâ fallback olarak kullanılıyor.
_EXPLICIT_DIMENSION_MAP: dict[str, str] = {
    # journal_article / general_fallback
    "contribution_originality": "contribution",
    "research_question_fit": "contribution",
    "theoretical_framing": "literature",
    "literature_positioning": "literature",
    "methodology_fit": "methodology",
    "data_sample_adequacy": "methodology",
    "analysis_validity": "methodology",  # FIX: eskiden "analysis" -> statistics
    "claim_evidence_alignment": "evidence",
    "citation_integrity": "citation",
    "reporting_guideline_compliance": "reproducibility",
    "ethics_reproducibility": "ethics",
    "writing_structure": "writing",
    "venue_fit": "venue_fit",
    # conference_paper
    "track_fit": "venue_fit",
    "novelty_to_length_ratio": "contribution",
    "technical_correctness": "methodology",
    "reproducibility_artifact": "reproducibility",
    "presentation_clarity": "writing",
    "contribution_clarity": "contribution",  # FIX: eskiden "clarity" -> writing
    "ethics_limitations": "ethics",
    "reviewer_confidence": "evidence",  # net karşılığı yok, dürüst catch-all
    # thesis
    "problem_statement": "contribution",
    "research_questions_hypotheses": "contribution",
    "chapter_coherence": "writing",  # FIX: eskiden hiç eşleşmiyordu -> default
    "literature_depth": "literature",
    "theoretical_framework": "literature",
    "methodological_justification": "methodology",
    "analysis_depth": "methodology",  # FIX: eskiden "analysis" -> statistics
    "original_contribution": "contribution",
    "defense_readiness": "venue_fit",  # net karşılığı yok, en yakın: hazır/uygunluk
    "committee_question_risk": "contribution",
    "publication_potential": "contribution",  # net karşılığı yok, en yakın: katkı/önem
    # grant_proposal
    "problem_significance": "contribution",  # FIX: eskiden "significan" -> statistics
    "objectives": "contribution",  # net karşılığı yok, en yakın: katkı/hedef
    "work_packages": "methodology",
    "feasibility": "methodology",
    "team_competence": "evidence",  # net karşılığı yok, dürüst catch-all
    "timeline_realism": "methodology",
    "budget_coherence": "evidence",  # net karşılığı yok, dürüst catch-all
    "risk_mitigation": "methodology",
    "impact_pathway": "contribution",
    "dissemination": "evidence",  # net karşılığı yok, dürüst catch-all
    "ethics_data_management": "ethics",
    "sustainability": "evidence",  # net karşılığı yok, dürüst catch-all
}

_WS_RE = re.compile(r"\s+")


# ===========================================================================
# shared helpers
# ===========================================================================


def _severity_rank(severity: str) -> int:
    return _SEVERITY_RANK.get(severity, 0)


def _worst_severity(findings: list[Finding]) -> SeverityV2:
    """Worst (highest-rank) severity among findings; 'info' if none."""
    worst: SeverityV2 = "info"
    worst_rank = _severity_rank(worst)
    for f in findings:
        r = _severity_rank(f.severity)
        if r > worst_rank:
            worst, worst_rank = f.severity, r
    return worst


# 2026-08-10 (§39, guardian ile tasarım netleştirildi): "critical" içindeki
# atıf-bütünlüğü tetiklemesi artık TEK bir kural değil — EvidencePack'in
# GERÇEK fabricated+retracted SAYISINA göre kademelendiriliyor (izole olay vs
# sistemik desen). BU SAYI KALİBRE EDİLMEDİ — goldset'te moat boyutlarının
# insan-skoru karşılığı hiç yok (bkz. §29 madde 4), yani count>=2'nin doğru
# eşik olduğunu doğrulayacak HİÇBİR ground truth yok. Bu bir TASARIM kararı
# (n=2 illüstratif örnekten — 1 ve 4 fabricated — türetildi, "kalibrasyon"
# DEĞİL, §29'un in-sample-overfitting itirafının tekrarı olmasın diye böyle
# etiketlendi). Ömer'e açık TODO: gerçek veri birikince yeniden değerlendir.
_SYSTEMIC_FABRICATION_COUNT_THRESHOLD: int = 2


def _moat_gate(
    findings: list[Finding], evidence: EvidencePack | None = None
) -> tuple[Verdict | None, str]:
    """Moat-gate: atıf-bütünlüğü VE istatistiksel-tutarlılık AYRI kurallarla
    ele alınır (bkz. §39 — bunlar özünde farklı: biri deterministik sayaca
    dayanıyor, diğeri salt LLM yargısı). Bu fonksiyon readiness'e/skora
    dokunmaz — sadece build_executive_verdict'in kararını SONRADAN
    kötüleştirebilir (asla iyileştirmez).

    Atıf-bütünlüğü (citation_integrity/literature_positioning) "critical" ise:
    EvidencePack.citation_integrity.fabricated+retracted SAYISI kademelendirir
    — 2+ ise "reject" (sistemik desen), 1 ise "major_revision" (izole olay,
    ciddi ama tek başına sistemik sahtecilik kanıtı değil). `evidence=None`
    (eski çağrı yeri/testler) → sayı bilinmiyor, en kötü sonuca ATLAMA
    (§38'in ruhu: kanıtsız/bilinmeyen durumda maksimum cezaya varma) →
    "major_revision".

    İstatistiksel-tutarlılık (quant.* — örn. causal_language_discipline)
    "critical" ise: HER ZAMAN en fazla "major_revision" (asla tek başına
    "reject" tetiklemez — §30'un "critical" tavanının istatistik tarafı için
    DARALTILMASI, 3. moat boyutu artık "reject"e TEK BAŞINA ulaşamıyor,
    bilinçli bir kapsam daralması, sessizce değil).

    DÜZELTME (2026-08-10, guardian bulgusu): "EvidencePack'te deterministik
    sayaç YOK" iddiası YANLIŞTI — `EvidencePack.stat_findings` (statcheck/
    Nuijten, status="red"/"yellow"/"green") tam olarak böyle bir sayaç,
    incelenmeden reddedilmişti. Elle kontrol edildi: gerçek 2 moat-gate
    tetikleyicisi (`causal_language_discipline`) için `stat_findings` HER
    İKİSİNDE DE BOŞ (statcheck p-value eşleşmesine bakıyor, nedensel-dil
    kullanımı onun kapsamında değil) — yani bu 2 ÖRNEK için pratik sonuç
    değişmiyor. Ama bu, stat_findings'in HİÇBİR quant.* alt-boyutu için
    kullanılamayacağı anlamına gelmez (örn. dimension="statistical_consistency"
    bir bulgu, stat_findings'teki "red" sayısıyla prensipte ilişkilendirilebilir)
    — bu bağlantı henüz KURULMADI, açık TODO. Şimdilik TÜM quant.* critical
    bulguları (finding'in hangi alt-boyuta ait olduğuna bakmadan) koşulsuz
    major_revision'a tavanlanıyor — konservatif/güvenli varsayılan, ama
    stat_findings'i kullanan daha ince taneli bir tasarım mümkün."""
    citation_findings = [f for f in findings if f.dimension in _CITATION_MOAT_DIMENSION_IDS]
    quant_findings = [
        f for f in findings if f.finding_id.startswith(_STATISTICS_MOAT_FINDING_ID_PREFIX)
    ]

    citation_worst = _worst_severity(citation_findings) if citation_findings else "info"
    quant_worst = _worst_severity(quant_findings) if quant_findings else "info"

    if citation_worst == "critical":
        if evidence is None:
            return (
                "major_revision",
                "a critical citation-integrity finding (evidence pack not provided — "
                "cannot confirm systemic pattern, capped at major_revision)",
            )
        count = evidence.citation_integrity.fabricated + evidence.citation_integrity.retracted
        if count >= _SYSTEMIC_FABRICATION_COUNT_THRESHOLD:
            return (
                "reject",
                f"a systemic citation-integrity violation ({count} fabricated/retracted references)",
            )
        return (
            "major_revision",
            f"an isolated citation-integrity violation ({count} fabricated/retracted reference)",
        )

    if quant_worst == "critical":
        return (
            "major_revision",
            "a critical statistical-consistency finding (methodology critique, no "
            "deterministic counter available — capped at major_revision, never reject)",
        )

    # 2026-08-08 — "major" eşiği goldset'te ölçüldü, kaldırıldı: 61 makalenin
    # 53'ünde (%87) en az 1 major-severity citation/quant moat bulgusu vardı,
    # sadece 3'ünde critical vardı. "major" pratikte ayırt edici bir sinyal
    # DEĞİL — neredeyse evrensel — tavan olarak kullanılınca verdict doğruluğu
    # %62'den %18'e çöktü (39/49 gerçek-accept makale major_revision'a
    # düşürüldü). Kök neden araştırılmadı (CitationIntegrityEngine/
    # QuantitativeValidityEngine'in severity kalibrasyonu mu, yoksa gerçekten
    # neredeyse her makalede bir atıf/istatistik kusuru mu var — ayrı TODO,
    # bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md §30). Sadece "critical" (3/61,
    # nadir/ayırt edici) tavan olarak kaldı.
    return None, ""


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def _map_to_risk_dimension(finding_dimension: str) -> str:
    """Map a free-text finding.dimension onto one of the 10 RISK_DIMENSIONS.

    Önce bilinen rubric_registry ID'leri için DOĞRUDAN eşleme (_EXPLICIT_DIMENSION_MAP,
    sıra-bağımsız, kanıtlı doğru) denenir; bulunamazsa (gelecekte eklenecek yeni/
    bilinmeyen ID) substring-anahtar-kelime tablosuna (_DIMENSION_KEYWORD_MAP)
    düşülür — o da bulamazsa dürüst genel kova (_DEFAULT_RISK_DIMENSION)."""
    d = (finding_dimension or "").strip().lower()
    direct = _EXPLICIT_DIMENSION_MAP.get(d)
    if direct is not None:
        return direct
    for keyword, radar_dim in _DIMENSION_KEYWORD_MAP:
        if keyword in d:
            return radar_dim
    return _DEFAULT_RISK_DIMENSION


def _evidence_weight(finding: Finding) -> float:
    """STRONG if the finding has a verified anchor, else WEAK (FAZ-B carry-forward)."""
    return WEAK_EVIDENCE_WEIGHT if finding_evidence_is_weak(finding) else STRONG_EVIDENCE_WEIGHT


def _norm_section(name: str | None) -> str:
    return _WS_RE.sub(" ", (name or "").strip().lower())


# ===========================================================================
# risk radar
# ===========================================================================


def build_risk_radar(
    findings: list[Finding], rubric: Rubric | None = None
) -> list[RiskRadarItem]:
    """Aggregate findings onto the 10 spec risk dimensions (deterministic).

    Score formula (per dimension): RADAR_BASE_SCORE minus the sum of
    RADAR_SEVERITY_PENALTY[severity] over that dimension's findings, clamped to
    [0, 100]. severity = worst severity present. confidence = mean of the
    dimension's finding confidences (RADAR_EMPTY_CONFIDENCE when empty). An empty
    dimension in rubric scope → RADAR_EMPTY_SCORE (honest "no issues found").
    An empty dimension OUT of rubric scope → score=None (honest "not assessed" —
    2026-08-07: eskiden bu da RADAR_EMPTY_SCORE=100 alıyordu, "değerlendirilmedi"
    "mükemmel" gibi görünüyordu, dimension_scores entegrasyonu öncesi önkoşul
    olarak düzeltildi — bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md).
    """
    by_dim: dict[str, list[Finding]] = {d: [] for d in RISK_DIMENSIONS}
    for f in findings:
        by_dim[_map_to_risk_dimension(f.dimension)].append(f)

    assessed: set[str] = set()
    if rubric is not None:
        assessed = {_map_to_risk_dimension(d.id) for d in rubric.dimensions}
        # 2026-08-07 guardian bulgusu: QuantitativeValidityEngine'in ürettiği
        # Finding'ler rubric_registry'nin SABİT dimension ID'lerini DEĞİL,
        # LLM'in kendi serbest alt-boyut adlarını (örn. "sample_and_power")
        # taşır — bu yüzden "statistics" kategorisi rubric.dimensions ID
        # listesinde YAPISAL OLARAK hiç görünmez, motor gerçekten çalışıp
        # temiz sonuç verse bile "değerlendirilmedi" (None) sanılırdı. Bu
        # motor bu rubric için dispatch edildiyse "statistics"i AYRICA ekle.
        if any(d.engine == QUANTITATIVE_ENGINE for d in rubric.dimensions):
            assessed.add("statistics")

    items: list[RiskRadarItem] = []
    for dim in RISK_DIMENSIONS:  # fixed spec order → deterministic
        dim_findings = by_dim[dim]
        if not dim_findings:
            in_scope = (rubric is None) or (dim in assessed)
            items.append(
                RiskRadarItem(
                    dimension=dim,
                    score=RADAR_EMPTY_SCORE if in_scope else None,
                    severity=RADAR_EMPTY_SEVERITY,
                    confidence=RADAR_EMPTY_CONFIDENCE if in_scope else 0.0,
                    why_it_matters=(
                        "No issues found in this dimension."
                        if in_scope
                        else "Not assessed for this document type."
                    ),
                )
            )
            continue
        penalty = sum(RADAR_SEVERITY_PENALTY.get(f.severity, 0.0) for f in dim_findings)
        score = _clamp_score(RADAR_BASE_SCORE - penalty)
        severity = _worst_severity(dim_findings)
        confidence = _clamp_unit(
            sum(f.confidence for f in dim_findings) / len(dim_findings)
        )
        items.append(
            RiskRadarItem(
                dimension=dim,
                score=score,
                severity=severity,
                confidence=confidence,
                why_it_matters=(
                    f"{len(dim_findings)} finding(s); worst severity {severity}."
                ),
            )
        )
    return items


# ===========================================================================
# executive verdict (transparent, documented decision tree)
# ===========================================================================


def build_executive_verdict(
    findings: list[Finding],
    radar: list[RiskRadarItem],
    evidence: EvidencePack | None = None,
) -> ExecutiveVerdict:
    """Transparent, reproducible decision tree (cf. consent_gate._deterministic_verdict).

    evidence: §39 moat-gate kademelendirmesi için — atıf-bütünlüğü "critical"
    bulgusunun sistemik mi izole mi olduğunu EvidencePack.citation_integrity'nin
    gerçek fabricated+retracted SAYISIYLA ayırt eder (bkz. _moat_gate).
    None ise (eski çağrı yeri/testler) sayı bilinmiyor demektir — en kötü
    sonuca (reject) ATLANMAZ, "major_revision" ile sınırlı kalır.

    overall_readiness_score = mean of the radar dimension scores (clamped 0-100),
    "not assessed" (score=None) boyutlar ortalamaya DAHİL EDİLMEZ (2026-08-07 —
    değerlendirilmemiş bir boyutu 100 sayıp ortalamayı şişirmek yerine, sadece
    gerçekten değerlendirilen boyutlardan hesaplanır; hiçbiri değerlendirilmediyse
    dürüst RADAR_BASE_SCORE varsayılanına düşer).

    recommended_decision (readiness-score thresholds, empirically calibrated
    against the 61-paper goldset — bkz. ACCEPT_READINESS_THRESHOLD /
    REJECT_READINESS_THRESHOLD yorumları; first matching rule wins):
      readiness >= ACCEPT_READINESS_THRESHOLD          → accept
      readiness <  REJECT_READINESS_THRESHOLD           → reject
      else                                              → major_revision
    (minor_revision şema değeri olarak var ama bu skor mantığından
    üretilmiyor — goldset'te sıfır ground-truth örneği var, bkz. yukarıdaki
    sabit tanımlarındaki TODO notu.)

    SONRA moat-gate uygulanır (bkz. yukarıdaki _CITATION_MOAT_DIMENSION_IDS /
    _STATISTICS_MOAT_FINDING_ID_PREFIX yorumları): atıf-bütünlüğü veya
    istatistiksel-tutarlılık boyutlarından biri CRITICAL bulgu içeriyorsa
    (major DEĞİL — bkz. yukarıdaki §30 empirik notu), yukarıdaki readiness
    kararı SADECE KÖTÜLEŞTİRİLİR (asla iyileştirilmez, en fazla "reject")
    — readiness ortalamasının bu 2 moat boyutunu 7 genel boyutla eritip
    kararda görünmez kılmasını engelliyor. Bu durumda
    overall_readiness_score DEĞİŞMEZ (hâlâ §29'un kalibre edilmiş ortalaması)
    ama recommended_decision ondan daha kötü olabilir — bu tutarsızlık
    bilinçli ve one_sentence_diagnosis'te açıkça belirtilir (guardian
    bulgusu: sessiz kalırsa "readiness yüksekken neden red önerisi var"
    sorusu raporda cevapsız kalırdı).

    confidence = EVIDENCE COMPLETENESS = mean over findings of
      (finding.confidence * evidence_weight(finding)),
    where evidence_weight is STRONG for a verified-anchor finding and WEAK for a
    global_issue-only / all-anchors-unverified finding (FAZ-B carry-forward:
    unverified-quote and global-only findings are NOT full-strength). No findings →
    VERDICT_NO_FINDINGS_CONFIDENCE.

    top_fatal_risks = critical+major finding titles, sorted by severity then
    finding_id (deterministic), capped at TOP_FATAL_RISKS_MAX.
    """
    scored = [r.score for r in radar if r.score is not None]
    if scored:
        readiness = _clamp_score(sum(scored) / len(scored))
    else:
        readiness = RADAR_BASE_SCORE

    n_critical = sum(1 for f in findings if f.severity == "critical")
    n_major = sum(1 for f in findings if f.severity == "major")
    n_moderate = sum(1 for f in findings if f.severity == "moderate")

    decision: Verdict
    if readiness >= ACCEPT_READINESS_THRESHOLD:
        decision = "accept"
    elif readiness < REJECT_READINESS_THRESHOLD:
        decision = "reject"
    else:
        decision = "major_revision"

    gate_decision, gate_reason = _moat_gate(findings, evidence)
    gate_applied = gate_decision is not None and _VERDICT_RANK[gate_decision] < _VERDICT_RANK[decision]
    if gate_applied:
        decision = gate_decision  # type: ignore[assignment]

    if findings:
        confidence = _clamp_unit(
            sum(f.confidence * _evidence_weight(f) for f in findings) / len(findings)
        )
    else:
        confidence = VERDICT_NO_FINDINGS_CONFIDENCE

    fatal = sorted(
        (f for f in findings if f.severity in ("critical", "major")),
        key=lambda f: (-_severity_rank(f.severity), f.finding_id),
    )
    top_fatal_risks = [f.title for f in fatal[:TOP_FATAL_RISKS_MAX]]

    if n_critical or n_major:
        diagnosis = (
            f"{n_critical} critical and {n_major} major issue(s) detected; "
            f"recommended decision: {decision}."
        )
    elif n_moderate:
        diagnosis = (
            f"No critical/major issues, but {n_moderate} moderate issue(s) need "
            f"attention; recommended decision: {decision}."
        )
    else:
        diagnosis = (
            "No critical, major, or moderate issues detected; the document "
            "appears submission-ready pending minor checks."
        )

    if gate_applied:
        diagnosis += (
            f" MOAT-GATE: readiness score ({readiness:.1f}) alone would suggest a "
            f"better decision, but {gate_reason} caps it at '{decision}'."
        )

    return ExecutiveVerdict(
        overall_readiness_score=readiness,
        recommended_decision=decision,
        confidence=confidence,
        top_fatal_risks=top_fatal_risks,
        one_sentence_diagnosis=diagnosis,
    )


# ===========================================================================
# deterministic dimension_scores entegrasyonu (2026-08-07)
# ===========================================================================
#
# KANUN (guardian ile 2 tur danışma sonrası, PDF_PIPELINE_CALISMA_GUNLUGU.md
# bölüm 26-27): goldset'e karşı test edilen dimension_scores/verdict eskiden
# TAMAMEN çapasız serbest LLM yargısıydı (review_writer/review_editor brief'leri
# hiçbir boyut için kriter/çapa taşımıyordu). risk_radar/executive_verdict ZATEN
# deterministik (Finding severity-sayımına dayalı, LLM değil) ama hiç kullanılmıyordu.
# Bu bölüm ikisini birleştirir — SADECE net-eşleşen boyutlarda (aşağıdaki tablo),
# risk_radar bir boyutu GERÇEKTEN değerlendirdiyse (score != None). Değerlendirilmedi
# ise LLM'in kendi skoru KORUNUR (düşürülmez) — RADAR_EMPTY_SCORE önkoşulu (bkz.
# yukarı) bu ayrımı güvenilir kılıyor.
#
# "contribution" SADECE originality'ye uygulanır (rubric_registry'de literal
# "contribution_originality" ID'siyle birebir örtüşüyor) — importance'a da
# uygulamak iki farklı Stanford boyutuna aynı sayıyı vermek olurdu, bu bir
# uydurma-hassasiyet iddiası taşırdı. importance/community_value/contextualization
# için risk_radar'ın 10 kategorisinde net karşılık yok — LLM-yalnız kalıyorlar,
# bu bilinçli bir boşluk (bkz. çalışma günlüğü), gelecekte rubric_registry'ye
# yeni boyut eklenerek kapatılabilir.
_DIMENSION_KEY_TO_RISK: dict[str, str] = {
    "citation_integrity": "citation",
    "statistical_consistency": "statistics",
    "coverage_completeness": "literature",
    "clarity": "writing",
    "soundness": "methodology",
    "claims_supported": "evidence",
    "originality": "contribution",
}


def apply_deterministic_dimension_scores(
    dimension_scores: list[DimensionScore], radar: list[RiskRadarItem]
) -> list[DimensionScore]:
    """LLM'in serbest dimension_scores'unu, risk_radar'da GERÇEKTEN değerlendirilmiş
    (score != None) net-eşleşen 7 boyutta deterministik skorla DEĞİŞTİRİR.
    risk_radar o boyutu değerlendirmediyse (score=None) LLM'in kendi skoru
    KORUNUR. 0-100 → 1-10 doğrusal ölçek (1 + score/100*9). Sıra/adet korunur,
    diğer 3 boyuta (importance/community_value/contextualization) dokunulmaz."""
    radar_by_dim = {r.dimension: r for r in radar}
    out: list[DimensionScore] = []
    for ds in dimension_scores:
        risk_key = _DIMENSION_KEY_TO_RISK.get(ds.key)
        item = radar_by_dim.get(risk_key) if risk_key else None
        if item is not None and item.score is not None:
            scaled = round(1.0 + (item.score / 100.0) * 9.0, 2)
            out.append(
                DimensionScore(
                    key=ds.key,
                    score=scaled,
                    rationale=(
                        f"Deterministik (risk_radar/{risk_key}, kanıta-dayalı Finding "
                        f"severity-sayımı): {item.why_it_matters} "
                        f"[LLM'in kendi gerekçesi: {ds.rationale}]"
                    ),
                )
            )
        else:
            out.append(ds)
    return out


# ===========================================================================
# action plan
# ===========================================================================

_PRIORITY_RANK: dict[str, int] = {"P0": 0, "P1": 1, "P2": 2}


def build_action_plan(
    findings: list[Finding], action_items: list[ActionItem]
) -> list[ActionItem]:
    """Collect findings' linked actions, order P0→P1→P2, de-duplicate (deterministic).

    Only actions referenced by some finding.action_item_ids are included. Identical
    actions (same priority + instruction + target_section + effort + expected_gain)
    are merged into one, keeping the lexicographically smallest action_id and the
    sorted union of linked_finding_ids. Ordering: priority rank, then action_id.
    """
    linked_ids: set[str] = set()
    for f in findings:
        linked_ids.update(f.action_item_ids)

    selected = [a for a in action_items if a.action_id in linked_ids]
    # Stable base order so dedupe keeps a deterministic representative.
    selected.sort(key=lambda a: (_PRIORITY_RANK.get(a.priority, 99), a.action_id))

    merged: dict[tuple[str, str, str | None, str, str], ActionItem] = {}
    for a in selected:
        key = (a.priority, a.instruction, a.target_section, a.effort, a.expected_gain)
        if key not in merged:
            merged[key] = a
        else:
            existing = merged[key]
            union = sorted(set(existing.linked_finding_ids) | set(a.linked_finding_ids))
            merged[key] = existing.model_copy(update={"linked_finding_ids": union})

    result = list(merged.values())
    result.sort(key=lambda a: (_PRIORITY_RANK.get(a.priority, 99), a.action_id))
    return result


# ===========================================================================
# section reviews
# ===========================================================================


def build_section_reviews(
    findings: list[Finding],
    manuscript: Manuscript,
    rubric: Rubric | None = None,
) -> list[SectionReview]:
    """Group findings by manuscript section → per-section SectionReview (deterministic).

    Sections come from manuscript.meta.section_titles (kept in their given order); a
    finding is attached to a section if any of its anchors' section matches
    (whitespace-normalized, case-insensitive). Findings whose anchor section is not
    a known title are surfaced as extra SectionReviews (sorted alphabetically) so
    they are not lost ("unknown section handled"). global_issue / anchorless findings
    are not section-scoped and are intentionally excluded here.

    status = SECTION_STATUS_BY_SEVERITY[worst finding severity]; a section with no
    findings → ok.

    G3 'missing': when a `rubric` with expected_sections is given, any expected core
    section absent from manuscript.meta.section_titles (synonym-tolerant match in
    rubric_registry.missing_sections) is appended as a status='missing' SectionReview.
    Expected-section data is the rubric's (doc-type + empirical design); a rubric
    without expected_sections (theoretical/unknown) yields NO 'missing' (honest — we
    do not invent an expectation).
    """
    known_titles = list(manuscript.meta.section_titles)
    norm_to_title: dict[str, str] = {}
    order: list[str] = []
    for t in known_titles:
        nt = _norm_section(t)
        if nt and nt not in norm_to_title:
            norm_to_title[nt] = t
            order.append(nt)

    by_section: dict[str, list[Finding]] = {}
    anchor_ids_by_section: dict[str, list[str]] = {}
    for f in findings:
        seen_here: set[str] = set()  # a finding counts once per section
        for anchor in f.manuscript_anchors:
            nt = _norm_section(anchor.section)
            if not nt:
                continue
            if nt not in norm_to_title:  # unknown section → keep its own bucket
                norm_to_title[nt] = anchor.section or nt
            anchor_ids_by_section.setdefault(nt, []).append(anchor.anchor_id)
            if nt not in seen_here:
                by_section.setdefault(nt, []).append(f)
                seen_here.add(nt)

    extra = sorted(nt for nt in norm_to_title if nt not in order)
    ordered_sections = order + extra

    reviews: list[SectionReview] = []
    for nt in ordered_sections:
        title = norm_to_title[nt]
        sec_findings = by_section.get(nt, [])
        if not sec_findings:
            reviews.append(
                SectionReview(
                    section=title,
                    status="ok",
                    what_works="No issues detected in this section.",
                )
            )
            continue
        worst = _worst_severity(sec_findings)
        status = SECTION_STATUS_BY_SEVERITY.get(worst, "ok")
        ordered_findings = sorted(
            sec_findings, key=lambda f: (-_severity_rank(f.severity), f.finding_id)
        )
        breaks = [
            f.title
            for f in ordered_findings
            if f.severity in ("critical", "major", "moderate")
        ]
        action_ids = sorted(
            {aid for f in sec_findings for aid in f.action_item_ids}
        )
        reviews.append(
            SectionReview(
                section=title,
                status=status,  # type: ignore[arg-type]
                what_works=None,
                what_breaks="; ".join(breaks) if breaks else None,
                anchor_ids=sorted(set(anchor_ids_by_section.get(nt, []))),
                action_item_ids=action_ids,
            )
        )

    # G3: rubric beklenen-bölümlerinden manuscript'te BULUNMAYANLAR → 'missing'.
    # rubric yoksa veya expected_sections boşsa hiçbir 'missing' üretilmez (dürüst).
    if rubric is not None and rubric.expected_sections:
        for label in missing_sections(
            rubric.expected_sections, manuscript.meta.section_titles
        ):
            reviews.append(
                SectionReview(
                    section=label,
                    status="missing",
                    what_breaks=(
                        f"Expected '{label}' section is missing or unrecognized in the "
                        f"manuscript for this document/study type."
                    ),
                )
            )
    return reviews


__all__ = [
    "RISK_DIMENSIONS",
    "SYNTHESIS_VERSION",
    "apply_deterministic_dimension_scores",
    "build_action_plan",
    "build_executive_verdict",
    "build_risk_radar",
    "build_section_reviews",
]
