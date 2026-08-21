"""FAZ C1 — deterministic report synthesis tests.

Proves: radar aggregation + clamp + honest-empty; executive decision-tree branches
+ reproducibility + the FAZ-B confidence down-weight; action plan ordering/dedupe;
section review grouping. Pure functions — fixtures built directly, no LLM/network.
"""

from __future__ import annotations

import pytest

from api.models.review import (
    ActionItem,
    CitationIntegritySummary,
    DimensionScore,
    EvidencePack,
    Finding,
    Manuscript,
    ManuscriptAnchor,
    ManuscriptMeta,
)
from engine.academic.anchoring import verify_finding_anchors
from engine.academic.assessment import QUANTITATIVE_ENGINE
from engine.academic.report_synthesis import (
    RISK_DIMENSIONS,
    _map_to_risk_dimension,
    apply_deterministic_dimension_scores,
    build_action_plan,
    build_executive_verdict,
    build_risk_radar,
    build_section_reviews,
)
from engine.academic.rubric_registry import Rubric, RubricDimension

pytestmark = pytest.mark.unit


def _finding(
    fid: str,
    *,
    dimension: str = "methodology_fit",
    severity: str = "moderate",
    confidence: float = 0.8,
    anchors: list[ManuscriptAnchor] | None = None,
    global_issue: bool = False,
    action_item_ids: list[str] | None = None,
    title: str | None = None,
) -> Finding:
    return Finding(
        finding_id=fid,
        dimension=dimension,
        severity=severity,  # type: ignore[arg-type]
        confidence=confidence,
        title=title or f"Finding {fid}",
        manuscript_anchors=anchors or [],
        global_issue=global_issue,
        action_item_ids=action_item_ids or [],
    )


# --- risk radar -------------------------------------------------------------


def test_radar_emits_all_ten_dimensions_in_spec_order() -> None:
    radar = build_risk_radar([], rubric=None)
    assert [r.dimension for r in radar] == list(RISK_DIMENSIONS)


def test_radar_empty_dimension_is_high_score_info_severity() -> None:
    radar = build_risk_radar([], rubric=None)
    for item in radar:
        assert item.score == 100.0
        assert item.severity == "info"
        assert "No issues found" in item.why_it_matters


def test_map_to_risk_dimension_known_ids_no_silent_misrouting() -> None:
    """2026-08-07 guardian bulgusu: substring-anahtar-kelime eşleşmesi sıra-
    bağımlıydı, 4 gerçek rubric_registry ID'sini yanlış yönlendiriyordu —
    şimdi _EXPLICIT_DIMENSION_MAP ile doğrudan/doğru eşleniyorlar."""
    assert _map_to_risk_dimension("problem_significance") == "contribution"  # eskiden statistics
    assert _map_to_risk_dimension("analysis_validity") == "methodology"  # eskiden statistics
    assert _map_to_risk_dimension("analysis_depth") == "methodology"  # eskiden statistics
    assert _map_to_risk_dimension("contribution_clarity") == "contribution"  # eskiden writing
    # sanity: dogru kalanlar da (regresyon degil, dogrulama)
    assert _map_to_risk_dimension("citation_integrity") == "citation"
    assert _map_to_risk_dimension("chapter_coherence") == "writing"  # eskiden default


def test_map_to_risk_dimension_unknown_id_falls_back_to_substring() -> None:
    """Bilinmeyen (gelecekte eklenecek) bir ID hâlâ substring tablosuna düşmeli —
    explicit tablo eskiyi TAMAMLIYOR, TAMAMEN yerine geçmiyor."""
    assert _map_to_risk_dimension("some_future_citation_dimension") == "citation"
    assert _map_to_risk_dimension("totally_unmapped_xyz") == "evidence"


def _rubric(dim_ids: list[str], *, engines: dict[str, str] | None = None) -> Rubric:
    engines = engines or {}
    return Rubric(
        rubric_id="test.rubric.v1",
        version="1",
        document_type="journal_article",
        study_design="quantitative",
        review_mode="author",
        strictness="standard",
        dimensions=[
            RubricDimension(
                id=d, weight=1.0, required=True, engine=engines.get(d, "TestEngine")
            )
            for d in dim_ids
        ],
    )


def test_radar_out_of_scope_dimension_is_none_score() -> None:
    """2026-08-07 guardian bulgusu: rubric bir boyutu hiç kapsamıyorsa (örn.
    bu doküman türünde 'ethics' değerlendirilmiyor), skor artık 100 DEĞİL,
    None — 'değerlendirilmedi' 'mükemmel' sanılmasın."""
    rubric = _rubric(["contribution_originality"])  # sadece "contribution" kapsanıyor
    radar = {r.dimension: r for r in build_risk_radar([], rubric=rubric)}

    assert radar["contribution"].score == 100.0  # kapsamda, bulgu yok → dürüst yüksek skor
    assert radar["contribution"].why_it_matters == "No issues found in this dimension."

    assert radar["ethics"].score is None  # kapsam dışı → değerlendirilmedi
    assert radar["ethics"].confidence == 0.0
    assert radar["ethics"].why_it_matters == "Not assessed for this document type."


def test_verdict_readiness_excludes_none_score_dimensions() -> None:
    """Değerlendirilmemiş (score=None) boyutlar readiness ortalamasına
    KARIŞMAZ — aksi halde 'değerlendirilmedi' sessizce 100 sayılıp
    ortalamayı şişirirdi (2026-08-07 önkoşul fix'i, dimension_scores
    entegrasyonundan önce)."""
    rubric = _rubric(["contribution_originality"])  # sadece 1/10 kapsanıyor
    findings = [
        _finding(
            "f1",
            dimension="contribution_originality",
            severity="critical",
            global_issue=True,
            action_item_ids=["a1"],
        )
    ]
    radar = build_risk_radar(findings, rubric=rubric)

    v = build_executive_verdict(findings, radar)
    # readiness SADECE degerlendirilen "contribution" boyutundan (100-45=55)
    # hesaplanmali, kapsam-disi 9 boyutu (None) 100 sayip ortalamayi sismemeli.
    assert v.overall_readiness_score == 55.0


def test_radar_statistics_assessed_when_quantitative_engine_dispatched() -> None:
    """2026-08-07 guardian bulgusu: QuantitativeValidityEngine'in Finding'leri
    LLM-serbest alt-boyum adları taşır (rubric.dimensions'daki SABİT ID
    listesinde hiç görünmez) — bu yüzden 'statistics' kategorisi bu motor
    gerçekten dispatch edilse bile hep 'değerlendirilmedi' (None) sanılıyordu.
    Artık rubric'te QUANTITATIVE_ENGINE'e yönlenen HERHANGİ bir boyut varsa
    'statistics' assessed kümesine AYRICA ekleniyor."""
    rubric = _rubric(
        ["analysis_validity"], engines={"analysis_validity": QUANTITATIVE_ENGINE}
    )
    radar = {r.dimension: r for r in build_risk_radar([], rubric=rubric)}
    assert radar["statistics"].score == 100.0  # artık None DEĞİL
    assert radar["statistics"].why_it_matters == "No issues found in this dimension."


def test_radar_statistics_none_when_quantitative_engine_not_dispatched() -> None:
    """Sanity: QUANTITATIVE_ENGINE hiç dispatch edilmediyse 'statistics' hâlâ
    dürüstçe None (yanlışlıkla her zaman 100 vermeye başlamadı)."""
    rubric = _rubric(["contribution_originality"])  # TestEngine, quantitative değil
    radar = {r.dimension: r for r in build_risk_radar([], rubric=rubric)}
    assert radar["statistics"].score is None


def test_apply_deterministic_dimension_scores_overrides_when_assessed() -> None:
    """apply_deterministic_dimension_scores: risk_radar'da GERÇEKTEN
    değerlendirilmiş (score != None) net-eşleşen boyutlar LLM skorunu
    DEĞİŞTİRİR (0-100 -> 1-10 doğrusal ölçek)."""
    rubric = _rubric(["citation_integrity"])
    findings = [
        _finding(
            "f1",
            dimension="citation_integrity",
            severity="major",
            global_issue=True,
            action_item_ids=["a1"],
        )
    ]
    radar = build_risk_radar(findings, rubric=rubric)  # citation: 100-25=75

    llm_scores = [
        DimensionScore(key="citation_integrity", score=9.5, rationale="LLM kendi görüşü"),
        DimensionScore(key="importance", score=8.0, rationale="net karşılığı yok"),
    ]
    out = apply_deterministic_dimension_scores(llm_scores, radar)

    citation = next(d for d in out if d.key == "citation_integrity")
    assert citation.score == pytest.approx(1.0 + (75.0 / 100.0) * 9.0)  # 7.75
    assert "Deterministik" in citation.rationale
    assert "LLM kendi görüşü" in citation.rationale  # eski gerekçe korunuyor (izlenebilirlik)

    # importance icin risk_radar karsiligi yok -> LLM skoru DOKUNULMADAN kalir
    importance = next(d for d in out if d.key == "importance")
    assert importance.score == 8.0
    assert importance.rationale == "net karşılığı yok"


def test_apply_deterministic_dimension_scores_keeps_llm_when_not_assessed() -> None:
    """risk_radar bir boyutu değerlendirmediyse (score=None) LLM'in kendi
    skoru KORUNUR — düşürülmez/sıfırlanmaz (RADAR_EMPTY_SCORE önkoşulunun
    dimension_scores'a doğru yansıması)."""
    rubric = _rubric(["contribution_originality"])  # "citation" kapsam dışı kalır
    radar = build_risk_radar([], rubric=rubric)

    llm_scores = [DimensionScore(key="citation_integrity", score=6.5, rationale="LLM")]
    out = apply_deterministic_dimension_scores(llm_scores, radar)

    assert out[0].score == 6.5  # değişmedi
    assert out[0].rationale == "LLM"  # değişmedi


def test_radar_severity_aggregation_and_score_formula() -> None:
    findings = [
        _finding("F1", dimension="methodology_fit", severity="major", action_item_ids=["A1"],
                 anchors=[ManuscriptAnchor(anchor_id="x", section="Methods", quote="q")]),
        _finding("F2", dimension="data_sample_adequacy", severity="minor"),
    ]
    radar = {r.dimension: r for r in build_risk_radar(findings, rubric=None)}
    meth = radar["methodology"]
    # 100 - (major 25 + minor 5) = 70 ; worst severity = major
    assert meth.score == 70.0
    assert meth.severity == "major"


def test_radar_score_clamped_to_zero() -> None:
    findings = [
        _finding(f"F{i}", dimension="methodology_fit", severity="critical", action_item_ids=["A1"],
                 anchors=[ManuscriptAnchor(anchor_id="x", section="Methods", quote="q")])
        for i in range(5)  # 5 * 45 = 225 penalty
    ]
    radar = {r.dimension: r for r in build_risk_radar(findings, rubric=None)}
    assert radar["methodology"].score == 0.0  # clamped, not negative


def test_radar_deterministic_called_twice_identical() -> None:
    findings = [
        _finding("F1", dimension="citation_integrity", severity="major", action_item_ids=["A1"],
                 anchors=[ManuscriptAnchor(anchor_id="x", section="Refs", quote="q")]),
        _finding("F2", dimension="ethics_reproducibility", severity="moderate"),
    ]
    r1 = build_risk_radar(findings, rubric=None)
    r2 = build_risk_radar(findings, rubric=None)
    assert [m.model_dump() for m in r1] == [m.model_dump() for m in r2]


# --- executive verdict ------------------------------------------------------


def _anchored(fid: str, severity: str, dimension: str = "methodology_fit") -> Finding:
    return _finding(
        fid, dimension=dimension, severity=severity, action_item_ids=[f"{fid}A"],
        anchors=[ManuscriptAnchor(anchor_id=f"{fid}q", section="Methods", quote="q")],
    )


def test_verdict_low_readiness_from_concentrated_critical_finding_is_reject() -> None:
    """v2 karar agaci sayim degil, risk_radar readiness skoru kullanir (2026-08-08,
    61 makalelik goldset'e karsi kalibre edildi — bkz. report_synthesis.py
    ACCEPT/REJECT_READINESS_THRESHOLD yorumlari). Rubric tek boyutu (methodology)
    kapsadigindan digerleri kapsam-disi/None sayilir, readiness = o tek boyutun
    skoru: 100-45(critical penalty)=55, kalibre edilen reject esiginin (72.0)
    altinda."""
    rubric = _rubric(["methodology_fit"])
    findings = [_anchored("F1", "critical")]
    radar = build_risk_radar(findings, rubric=rubric)
    v = build_executive_verdict(findings, radar)
    assert v.overall_readiness_score == 55.0
    assert v.recommended_decision == "reject"


def test_verdict_mid_readiness_from_concentrated_major_finding_is_major_revision() -> None:
    """Tek boyuta yogunlasmis major bulgu -> readiness=100-25=75, kalibre edilen
    [72.0, 78.5) major_revision bandina duser."""
    rubric = _rubric(["methodology_fit"])
    findings = [_anchored("F1", "major")]
    radar = build_risk_radar(findings, rubric=rubric)
    v = build_executive_verdict(findings, radar)
    assert v.overall_readiness_score == 75.0
    assert v.recommended_decision == "major_revision"


def test_verdict_minor_revision_is_unreachable_via_current_score_logic() -> None:
    """BILINEN BOSLUK (bkz. report_synthesis.py sabit tanimlarindaki TODO):
    goldset'te (61 makale) SIFIR minor_revision ground-truth ornegi var, bu
    yuzden skor-tabanli karar agaci minor_revision'i hic uretmiyor — sadece
    accept/major_revision/reject dondurebiliyor. Bu test, biri farkinda
    olmadan araya minor_revision uretecek bir esik eklerse (kalibre
    edilmemis, veri destegi olmayan bir degisiklik) fark edilmesini saglar."""
    for severity, expected_score in (
        ("critical", 55.0),
        ("major", 75.0),
        ("moderate", 88.0),
        ("minor", 95.0),
    ):
        rubric = _rubric(["methodology_fit"])
        findings = [_anchored("F1", severity)]
        radar = build_risk_radar(findings, rubric=rubric)
        v = build_executive_verdict(findings, radar)
        assert v.overall_readiness_score == expected_score
        assert v.recommended_decision != "minor_revision"


# --- moat-gate (2026-08-08, guardian ile 2 tur danisildi + 61 makale uzerinde
# empirik olcum) -------------------------------------------------------------
# readiness ortalamasi 10 kategoriyi esit agirlikta eritiyor: bir moat boyutu
# (atif butunlugu/istatistiksel tutarlilik) critical bulgu uretse bile
# digerleri temizse ortalama "accept" diyebilir. Bu testler moat-gate'in bu
# durumda readiness'e DOKUNMADAN karari SADECE KOTULESTIRDIGINI kanitliyor.
# NOT: gate SADECE "critical" severity'de tetikleniyor, "major" DEGIL -
# ilk tasarim critical+major'i birlikte tavanliyordu ama 61 makalenin
# %87'sinde (53/61) en az 1 major-severity moat bulgusu cikti (ayirt edici
# degil, neredeyse evrensel), tavan olarak kullaninca verdict dogrulugu
# %62'den %18'e coktu - bkz. report_synthesis.py _moat_gate() yorumu.


# 2026-08-10 (SS39, guardian ile tasarim netlestirildi): "critical" atif-
# butunlugu bulgusu artik TEK kural degil - EvidencePack'in GERCEK
# fabricated+retracted SAYISINA gore kademelendiriliyor (izole vs sistemik).
# count>=2 -> reject, count==1 -> major_revision, evidence=None (bilinmiyor)
# -> en kotu sonuca ATLAMADAN major_revision'da kalir.


def test_moat_gate_downgrades_to_reject_on_systemic_citation_fabrication() -> None:
    """rubric=None -> 10 boyutun 9'u temiz (skor=100), sadece citation_integrity'de
    1 critical bulgu var -> readiness=(900+55)/10=95.5, TEK BASINA accept esiginin
    (78.5) cok ustunde. EvidencePack GERCEKTEN 2 fabricated/retracted referans
    gosteriyor (sistemik esik >=2) -> moat-gate karari reject'e cekiyor - readiness
    DEGISMIYOR (hala 95.5), sadece decision."""
    findings = [_anchored("F1", "critical", dimension="citation_integrity")]
    radar = build_risk_radar(findings, rubric=None)
    evidence = EvidencePack(citation_integrity=CitationIntegritySummary(fabricated=2, total=5))
    v = build_executive_verdict(findings, radar, evidence)
    assert v.overall_readiness_score == 95.5
    assert v.recommended_decision == "reject"
    assert "MOAT-GATE" in v.one_sentence_diagnosis


def test_moat_gate_caps_at_major_revision_on_isolated_citation_fabrication() -> None:
    """AYNI critical bulgu, ama EvidencePack SADECE 1 fabricated referans
    gosteriyor (izole esik <2) -> reject DEGIL, major_revision'da kaliyor -
    tek bir izole olay sistemik sahtecilik kaniti degil."""
    findings = [_anchored("F1", "critical", dimension="citation_integrity")]
    radar = build_risk_radar(findings, rubric=None)
    evidence = EvidencePack(citation_integrity=CitationIntegritySummary(fabricated=1, total=5))
    v = build_executive_verdict(findings, radar, evidence)
    assert v.recommended_decision == "major_revision"
    assert "MOAT-GATE" in v.one_sentence_diagnosis


def test_moat_gate_caps_at_major_revision_when_evidence_pack_not_provided() -> None:
    """evidence=None (eski cagri yeri/testler) -> sayi bilinmiyor, en kotu
    sonuca (reject) ATLANMAZ - major_revision'da sinirli kalir (SS38'in ruhu:
    kanitsiz/bilinmeyen durumda maksimum cezaya varma)."""
    findings = [_anchored("F1", "critical", dimension="citation_integrity")]
    radar = build_risk_radar(findings, rubric=None)
    v = build_executive_verdict(findings, radar)  # evidence verilmedi
    assert v.recommended_decision == "major_revision"
    assert "MOAT-GATE" in v.one_sentence_diagnosis


def test_moat_gate_does_not_fire_on_major_citation_finding() -> None:
    """Empirik bulgu (61 makale, bkz. yukarisi): "major" moat bulgusu ayirt
    edici degil, neredeyse evrensel - gate SADECE critical'de tetiklenir,
    major'da SESSIZ kalir (readiness'in kendi karari - burada accept -
    gecerliligini korur)."""
    findings = [_anchored("F1", "major", dimension="citation_integrity")]
    radar = build_risk_radar(findings, rubric=None)
    v = build_executive_verdict(findings, radar)
    assert v.overall_readiness_score == 97.5
    assert v.recommended_decision == "accept"
    assert "MOAT-GATE" not in v.one_sentence_diagnosis


def test_moat_gate_catches_quant_engine_finding_via_id_prefix_not_dimension_map() -> None:
    """QuantitativeValidityEngine bulgulari LLM-serbest alt-boyut adlari tasir
    (force_dimension yok) - burada 'sample_and_power' keyword-fallback ile
    'methodology' kovasina duser (moat'a ozgu 'statistics' kovasina DEGIL), ama
    moat-gate finding_id onekinden ('quant.') tanidigi icin yine de tetikleniyor.
    Bu, gate'in risk_radar'in (potansiyel olarak yanlis-yonlendirebilen) kova
    eslemesinden BAGIMSIZ calistigini kanitliyor."""
    f = _finding(
        "quant.f0",
        dimension="sample_and_power",
        severity="critical",
        global_issue=True,
        action_item_ids=["a1"],
    )
    radar = build_risk_radar([f], rubric=None)
    by_dim = {r.dimension: r for r in radar}
    assert by_dim["methodology"].score == 55.0  # keyword-fallback dogrulamasi
    assert by_dim["statistics"].score == 100.0  # "statistics" kovasina DUSMEDI
    v = build_executive_verdict([f], radar)
    # SS39: istatistik-kaynakli critical'in deterministik sayaci YOK (statcheck
    # sadece p-value eslesmesi, causal-dil gibi konulari kapsamiyor) - bu yuzden
    # ASLA tek basina reject tetiklemez, en fazla major_revision (evidence
    # verilse bile degismez, quant tarafi count-tabanli degil).
    assert v.recommended_decision == "major_revision"
    assert "MOAT-GATE" in v.one_sentence_diagnosis


def test_moat_gate_does_not_fire_below_critical_severity() -> None:
    findings = [_anchored("F1", "moderate", dimension="citation_integrity")]
    radar = build_risk_radar(findings, rubric=None)
    v = build_executive_verdict(findings, radar)
    assert v.recommended_decision == "accept"  # readiness=98.8 -> accept, gate sessiz
    assert "MOAT-GATE" not in v.one_sentence_diagnosis


def test_moat_gate_does_not_fire_for_non_moat_dimension() -> None:
    """writing_structure critical bulgusu moat kumesinde DEGIL - gate'in
    kapsami sadece atif/istatistik, genel boyutlara tasmiyor."""
    findings = [_anchored("F1", "critical", dimension="writing_structure")]
    radar = build_risk_radar(findings, rubric=None)
    v = build_executive_verdict(findings, radar)
    assert v.recommended_decision == "accept"  # readiness=95.5 ama gate tetiklenmiyor
    assert "MOAT-GATE" not in v.one_sentence_diagnosis


def test_moat_gate_does_not_fire_for_literature_depth() -> None:
    """2026-08-10 (SS38, guardian bulgusu): literature_depth ESKIDEN moat-gate
    kapsamindaydi ama assessment.py'nin kanitsizlik-guard'i (SS38) onu
    KAPSAMIYOR - bu tutarsizlik, kanitsiz bir 'critical' literature_depth
    bulgusunun guard'dan gecmeden moat-gate'e ulasip makaleyi 'reject'e
    kilitlemesine izin veriyordu. literature_depth artik _CITATION_MOAT_
    DIMENSION_IDS'ten CIKARILDI - bu test bunu koruyor."""
    findings = [_anchored("F1", "critical", dimension="literature_depth")]
    radar = build_risk_radar(findings, rubric=None)
    v = build_executive_verdict(findings, radar)
    assert v.recommended_decision == "accept"  # readiness yuksek, gate tetiklenmiyor
    assert "MOAT-GATE" not in v.one_sentence_diagnosis


def test_moat_gate_never_upgrades_a_decision() -> None:
    """readiness zaten reject bandindayken (kirli moat-disi boyutlar), moat
    boyutlari TEMIZSE gate hicbir sey yapmaz - sadece kotulestirir, asla
    iyilestirmez."""
    rubric = _rubric(["methodology_fit"])
    findings = [_anchored("F1", "critical", dimension="methodology_fit")]
    radar = build_risk_radar(findings, rubric=rubric)
    v = build_executive_verdict(findings, radar)
    assert v.recommended_decision == "reject"  # readiness=55 zaten reject
    assert "MOAT-GATE" not in v.one_sentence_diagnosis  # moat boyutlari temiz, gate sessiz


def test_verdict_clean_branch_is_accept() -> None:
    radar = build_risk_radar([], rubric=None)
    v = build_executive_verdict([], radar)
    assert v.recommended_decision == "accept"
    assert v.overall_readiness_score == 100.0


def test_verdict_top_fatal_risks_are_critical_and_major_titles() -> None:
    findings = [
        _anchored("F1", "major"),
        _anchored("F2", "critical"),
        _finding("F3", severity="moderate"),
    ]
    radar = build_risk_radar(findings, rubric=None)
    v = build_executive_verdict(findings, radar)
    # critical sorts before major; moderate excluded
    assert v.top_fatal_risks == ["Finding F2", "Finding F1"]


def test_verdict_confidence_lower_for_unverified_anchor_findings() -> None:
    """FAZ-B carry-forward: same finding, verified anchor vs unverified anchor."""
    m = Manuscript(
        meta=ManuscriptMeta(section_titles=["Methods"]),
        full_text="Methods. the sampling strategy was named but not justified here.",
    )
    verified = _finding(
        "F1", severity="major", confidence=0.9, action_item_ids=["A1"],
        anchors=[ManuscriptAnchor(anchor_id="o", section="Methods",
                                  quote="sampling strategy was named but not justified")],
    )
    unverified = _finding(
        "F1", severity="major", confidence=0.9, action_item_ids=["A1"],
        anchors=[ManuscriptAnchor(anchor_id="o", section="Methods",
                                  quote="this quote does not exist in the paper at all")],
    )
    vf = verify_finding_anchors([verified], m).findings
    uf = verify_finding_anchors([unverified], m).findings
    radar = build_risk_radar(vf, rubric=None)
    conf_verified = build_executive_verdict(vf, radar).confidence
    conf_unverified = build_executive_verdict(uf, radar).confidence
    assert conf_verified > conf_unverified  # unverified is down-weighted


def test_verdict_confidence_lower_for_global_issue_only() -> None:
    """global_issue-only finding is not full-strength evidence."""
    anchored = _anchored("F1", "major")
    global_only = _finding(
        "F1", severity="major", confidence=0.9, global_issue=True, action_item_ids=["A1"],
    )
    radar = build_risk_radar([anchored], rubric=None)
    c_anchored = build_executive_verdict([anchored], radar).confidence
    c_global = build_executive_verdict([global_only], radar).confidence
    assert c_anchored > c_global


def test_verdict_reproducible_same_in_same_out() -> None:
    findings = [_anchored("F2", "major"), _anchored("F1", "critical")]
    radar = build_risk_radar(findings, rubric=None)
    v1 = build_executive_verdict(findings, radar)
    v2 = build_executive_verdict(findings, radar)
    assert v1.model_dump() == v2.model_dump()


# --- action plan ------------------------------------------------------------


def test_action_plan_orders_p0_before_p1_before_p2() -> None:
    findings = [_finding("F1", action_item_ids=["A2", "A1", "A0"])]
    actions = [
        ActionItem(action_id="A2", priority="P2", instruction="do c", linked_finding_ids=["F1"]),
        ActionItem(action_id="A1", priority="P1", instruction="do b", linked_finding_ids=["F1"]),
        ActionItem(action_id="A0", priority="P0", instruction="do a", linked_finding_ids=["F1"]),
    ]
    plan = build_action_plan(findings, actions)
    assert [a.priority for a in plan] == ["P0", "P1", "P2"]


def test_action_plan_dedupes_identical_actions() -> None:
    findings = [
        _finding("F1", action_item_ids=["A1"]),
        _finding("F2", action_item_ids=["A2"]),
    ]
    actions = [
        ActionItem(action_id="A1", priority="P0", instruction="same instruction",
                   target_section="Methods", linked_finding_ids=["F1"]),
        ActionItem(action_id="A2", priority="P0", instruction="same instruction",
                   target_section="Methods", linked_finding_ids=["F2"]),
    ]
    plan = build_action_plan(findings, actions)
    assert len(plan) == 1
    assert plan[0].action_id == "A1"  # smallest id kept
    assert plan[0].linked_finding_ids == ["F1", "F2"]  # merged + sorted


def test_action_plan_only_includes_linked_actions_deterministic() -> None:
    findings = [_finding("F1", action_item_ids=["A1"])]
    actions = [
        ActionItem(action_id="A1", priority="P1", instruction="linked", linked_finding_ids=["F1"]),
        ActionItem(action_id="A9", priority="P0", instruction="orphan not linked", linked_finding_ids=[]),
    ]
    plan = build_action_plan(findings, actions)
    assert [a.action_id for a in plan] == ["A1"]
    assert build_action_plan(findings, actions)[0].model_dump() == plan[0].model_dump()


def test_engine_actions_always_bridged_to_finding_no_orphan() -> None:
    """ORPHAN-ACTION GUARD (FAZ 4A ikincil doğrulama).

    Proves the academic engine (_engine_base._to_findings — the ONLY ActionItem
    producer outside tests, grep-confirmed) can NOT emit an orphan action:
      (a) every produced ActionItem has non-empty linked_finding_ids (=[fid]),
      (b) its finding references it back (action_id in finding.action_item_ids),
      (c) build_action_plan over the engine output yields only finding-linked actions.
    Empty-instruction actions are dropped (not orphaned). Combined with the
    build_action_plan link-filter (test above), the cockpit — bridged to findings —
    can never surface an action unreachable from a finding."""
    from engine.academic._engine_base import (
        _LLMActionItem,
        _LLMFinding,
        _LLMFindingList,
        _to_findings,
    )

    parsed = _LLMFindingList(
        findings=[
            _LLMFinding(
                severity="major",
                title="Underpowered design",
                global_issue=True,  # satisfies high-severity anchor/global contract
                action_items=[
                    _LLMActionItem(priority="P0", instruction="Add a power analysis"),
                    _LLMActionItem(priority="P1", instruction=""),  # empty → dropped
                ],
            ),
            _LLMFinding(severity="moderate", title="Minor wording", action_items=[]),
        ]
    )
    result = _to_findings(parsed, id_prefix="orph", force_dimension="soundness")

    # (a) no orphan: every action bridged
    assert result.action_items, "expected at least one produced action"
    for a in result.action_items:
        assert a.linked_finding_ids, f"orphan action {a.action_id} (empty links)"

    # (b) bidirectional link: finding exists and references the action back
    fids = {f.finding_id for f in result.findings}
    for a in result.action_items:
        assert set(a.linked_finding_ids) <= fids
        owner = next(f for f in result.findings if f.finding_id in a.linked_finding_ids)
        assert a.action_id in owner.action_item_ids

    # empty-instruction action was dropped, not emitted as orphan
    assert len(result.action_items) == 1

    # (c) full assembly: no orphan reaches the report action_plan
    plan = build_action_plan(result.findings, result.action_items)
    assert all(a.linked_finding_ids for a in plan)


# --- section reviews --------------------------------------------------------


def _manuscript(sections: list[str]) -> Manuscript:
    return Manuscript(meta=ManuscriptMeta(section_titles=sections), full_text="body")


def test_section_with_critical_finding_is_broken() -> None:
    m = _manuscript(["Methods", "Results"])
    findings = [
        _finding("F1", severity="critical", action_item_ids=["A1"],
                 anchors=[ManuscriptAnchor(anchor_id="x", section="Methods", quote="q")]),
    ]
    reviews = {r.section: r for r in build_section_reviews(findings, m)}
    assert reviews["Methods"].status == "broken"
    assert reviews["Results"].status == "ok"


def test_section_with_moderate_finding_is_weak() -> None:
    m = _manuscript(["Methods"])
    findings = [_finding("F1", severity="moderate",
                         anchors=[ManuscriptAnchor(anchor_id="x", section="Methods", quote="q")])]
    reviews = {r.section: r for r in build_section_reviews(findings, m)}
    assert reviews["Methods"].status == "weak"


def test_section_clean_is_ok() -> None:
    m = _manuscript(["Methods", "Results"])
    reviews = build_section_reviews([], m)
    assert [r.section for r in reviews] == ["Methods", "Results"]
    assert all(r.status == "ok" for r in reviews)


def test_finding_in_unknown_section_is_surfaced() -> None:
    m = _manuscript(["Methods"])
    findings = [
        _finding("F1", severity="major", action_item_ids=["A1"],
                 anchors=[ManuscriptAnchor(anchor_id="x", section="Appendix", quote="q")]),
    ]
    reviews = {r.section: r for r in build_section_reviews(findings, m)}
    assert "Methods" in reviews  # known section still present (ok)
    assert "Appendix" in reviews  # unknown section surfaced, not lost
    assert reviews["Appendix"].status == "broken"


def test_section_reviews_deterministic() -> None:
    m = _manuscript(["Methods", "Results"])
    findings = [
        _finding("F1", severity="major", action_item_ids=["A1"],
                 anchors=[ManuscriptAnchor(anchor_id="x", section="Methods", quote="q")]),
    ]
    r1 = build_section_reviews(findings, m)
    r2 = build_section_reviews(findings, m)
    assert [r.model_dump() for r in r1] == [r.model_dump() for r in r2]
