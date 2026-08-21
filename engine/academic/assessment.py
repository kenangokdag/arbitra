"""P03 — akademik değerlendirme DISPATCHER (academic_engine_spec.md §Pipeline → Domain Engines).

Tek giriş: assess_manuscript(manuscript, rubric, evidence, allow_external_ai)
  → rubrik boyutlarını DOĞRU motora yönlendirir, tüm Finding[]+ActionItem[]'ı toplar.

Yönlendirme (rubric_registry.py:36-37 motor adlarına göre):
  - QualitativeRigorEngine'e yönlenen boyut(lar) varsa → qualitative_engine BİR KEZ
    koşar (12 nitel boyutu derinlemesine; her metodoloji boyutu için tekrar ETMEZ).
  - QuantitativeValidityEngine → quantitative_engine BİR KEZ (10 nicel boyut + statcheck).
  - Geri kalan (claim/citation/ethics/structure/guideline) HER boyut için general
    dimension_engine → her rubrik boyutu kendi bulgusunu üretir (tam kapsam).

İZOLASYON (FAZ A audit gereği — review_service coverage deseni): her motor çağırısı
try/except ile sarılır. Bir motor ÇÖKERSE GÖRÜNÜR degraded sinyali kaydedilir ve
diğer motorların bulguları yine döner; çökme tüm değerlendirmeyi ÖLDÜRMEZ.

FAZ C bunu run_pipeline'a döndürecek (imza buna göre tasarlandı).

PACING NOTU: motor çağrıları arasına Gemini free-tier dakikalık kota limitini aşmamak
için kısa bir bekleme (asyncio.sleep) eklendi — art arda hızlı istekler 429
RateLimitError'a yol açıyordu.
"""

from __future__ import annotations

import asyncio
import logging

from api.models.review import EvidencePack, Manuscript
from engine.academic._engine_base import EngineResult
from engine.academic.dimension_engine import assess_dimension
from engine.academic.evidence_context import serialize_evidence_pack
from engine.academic.qualitative_engine import assess_qualitative
from engine.academic.quantitative_engine import assess_quantitative
from engine.academic.rubric_registry import Rubric

logger = logging.getLogger(__name__)

ENGINE_VERSION = "academic_assessment.v1"

QUALITATIVE_ENGINE = "QualitativeRigorEngine"
QUANTITATIVE_ENGINE = "QuantitativeValidityEngine"
# 2026-08-08 (bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md §31/§32): rubric_registry.py'nin
# private _CITATION_ENGINE sabitiyle AYNI değer — CitationIntegrityEngine'e yönlenen
# boyutlar (citation_integrity/literature_positioning/literature_depth) EvidencePack'i
# alacak, diğerleri (ethics/writing/venue_fit vb.) almayacak çünkü EvidencePack'in
# onlarla ilgili hiçbir olgusu yok (gereksiz token maliyeti + ilgisiz-bağlam kirliliği).
CITATION_ENGINE = "CitationIntegrityEngine"

_PACING_DELAY_SECONDS = 20

# 2026-08-10 (bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md §38 — guardian önerisi):
# citation_integrity/literature_positioning'de critical/major severity İÇİN
# academic_dimension.py'nin KENDİ KURALI (fabricated/retracted/contradicted kanıt
# GEREKİR, salt yüksek not_found_in_index oranı YETMEZ) prompt-seviyesinde LLM
# tarafından güvenilir uygulanmıyordu — 61 makalelik ölçümde 25 güçlü iddianın
# sadece %16'sı (4/25) gerçek kanıtlıydı, LLM hâlâ salt not_found_in_index oranına
# dayanarak major veriyordu (SS33'ün "ASLA tek başına HAK ETMEZ" talimatına rağmen).
# CLAUDE.md §3.3 ("boundary'de validate et, içeride trust et"): talimatı tekrar
# güçlendirmek (CAPS LOCK) yerine DETERMİNİSTİK kod-seviyesi guard — metin-eşleştirme
# YOK (kırılgan local-hack olurdu), sadece dimension+severity+evidence kontrolü.
# literature_depth BİLİNÇLİ dışarıda (kapsam SS35/§38 ile aynı gerekçe: derinlik/
# güncellik niyeti, fabricated/retracted ile grounding kategori-hatası olurdu).
_GROUNDING_REQUIRED_DIMENSIONS = frozenset({"citation_integrity", "literature_positioning"})
_UNGROUNDED_DOWNGRADE_SEVERITY = "moderate"
_UNGROUNDED_DOWNGRADE_NOTE = (
    "Severity kanıtsızlık nedeniyle 'moderate'e indirildi: citation_integrity/"
    "literature_positioning'de critical/major severity fabricated/retracted/"
    "contradicted kanıtı gerektirir (bu makalede EvidencePack'te yok) — motor "
    "'bulunamayan (not_found_in_index) asla suçlama değil' kuralını (HK-3) "
    "kod-seviyesinde, LLM'in metin-uyumuna bel bağlamadan uyguluyor."
)


def _has_citation_integrity_evidence(evidence: EvidencePack) -> bool:
    """academic_dimension.py'nin kendi kuralıyla BİREBİR aynı 3 gerekçe: fabricated,
    retracted, veya doğrulanmış 'contradicted' atıf-bağlam bulgusu."""
    ci = evidence.citation_integrity
    if ci.fabricated > 0 or ci.retracted > 0:
        return True
    return any(cf.support == "contradicted" for cf in evidence.context_findings)


def _downgrade_ungrounded_citation_findings(
    engine_result: EngineResult, evidence: EvidencePack
) -> EngineResult:
    """Bu makalede GERÇEK atıf-bütünlüğü kanıtı yoksa, citation_integrity/
    literature_positioning'deki critical/major bulguları 'moderate'e indir —
    LLM'in kendisi indirmediyse bile (SS33'ün amaçladığı ama LLM'in güvenilir
    uygulamadığı kural)."""
    if _has_citation_integrity_evidence(evidence):
        return engine_result  # gerçek kanıt var, LLM'in kararına dokunma
    new_findings = []
    n_downgraded = 0
    for f in engine_result.findings:
        if f.dimension in _GROUNDING_REQUIRED_DIMENSIONS and f.severity in ("critical", "major"):
            f = f.model_copy(
                update={
                    "severity": _UNGROUNDED_DOWNGRADE_SEVERITY,
                    "limitations": [*f.limitations, _UNGROUNDED_DOWNGRADE_NOTE],
                }
            )
            n_downgraded += 1
        new_findings.append(f)
    degraded = list(engine_result.degraded)
    if n_downgraded:
        logger.info(
            "citation_integrity grounding guard: %d bulgu kanıtsızlık nedeniyle moderate'e indirildi",
            n_downgraded,
        )
        degraded.append(f"citation_integrity_grounding:downgraded_{n_downgraded}")
    return EngineResult(
        findings=new_findings, action_items=engine_result.action_items, degraded=degraded
    )


# 2026-08-13 (bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md §44/§46 — plan: docs/plans/
# SOUNDNESS_SEVERITY_CONTEXT_SENSITIVITY_2026-08-13.md): quantitative_validity.py'nin
# "major = güç analizi/etki büyüklüğü yok" kuralı çalışma tasarımından bağımsız,
# literal bir prompt talimatı — computational_modeling (ML/DL) makalelerinde güç
# analizi/örneklem-büyüklüğü raporlaması ampirik nicel sosyal bilim konvansiyonu,
# standart beklenti DEĞİL. 61 makalelik canlı ölçümde bu tek kural yüzünden 40/61
# (%66) makale TAM AYNI soundness skorunu (7.75) alıyordu — sample_and_power TEK
# BAŞINA bu saturasyonun ~%100'ünü açıklıyordu (v8 verisiyle doğrulandı, plan §3b).
# CLAUDE.md §3.3 disiplini: LLM'in prompt talimatına güvenmek yerine (§41b'nin
# öğrettiği ders: prompt-seviyesi düzeltmenin severity etkisi güvenilir ölçülemiyor)
# DETERMİNİSTİK kod-seviyesi guard — _downgrade_ungrounded_citation_findings ile
# AYNI desen.
_QUANT_DESIGN_SENSITIVE_DIMENSIONS = frozenset({"sample_and_power"})
# effect_size/effect_size_and_uncertainty ailesi BİLİNÇLİ dışarıda (plan §3b) —
# _DIMENSION_KEYWORD_MAP'te hiçbir anahtar kelimeye çarpmıyor, "methodology"/
# soundness DEĞİL "evidence"/claims_supported kovasına gidiyor; bu guard'ın
# kapsamı değil.
#
# "Güç analizi standart konvansiyon DEĞİL" sayılan study_design'lar. Sadece
# computational_modeling PRATİKTE _QUANTITATIVE_ENGINE'e yönleniyor
# (rubric_registry.py:47-64) — diğerleri (design_science/software_tool/
# dataset_resource/theoretical/conceptual) şu an _CLAIM_ENGINE'e gidiyor, yani
# bu guard'da şu an ÖLÜ KOD ama routing tablosu değişirse diye kümede tutuluyor
# (savunmacı/ileri-yönlü — v1 default, tunable).
_QUANT_DESIGN_EXEMPT: frozenset[str] = frozenset(
    {
        "computational_modeling",
        "design_science",
        "software_tool",
        "dataset_resource",
        "theoretical",
        "conceptual",
    }
)
# rubric.study_design kendisi DETERMİNİSTİK değil (bir LLM sınıflandırma çıktısı,
# study_design_confidence taşır, api/models/review.py:482) — confidence-gating
# olmadan bu guard "deterministik kanıta dayalı düzeltme" değil "bir LLM'in
# belirsiz etiketine göre başkasının kararını indirme" olurdu (guardian 2. tur
# bulgusu, plan §4a). Eşik v8 verisiyle gerekçeli: 53 computational_modeling
# sınıflandırmasının TAMAMI 0.7-0.9 aralığında (min=0.7) — bu eşik mevcut
# davranışı bozmuyor, gelecekte düşük-confidence bir sınıflandırma gelirse güvenli
# tarafta kalıyor. YENİ bir v1-default (kod tabanında borç alınan bir emsal yok),
# tunable.
_QUANT_DESIGN_CONFIDENCE_THRESHOLD = 0.7
_DESIGN_MISMATCH_DOWNGRADE_SEVERITY = "minor"
_DESIGN_MISMATCH_DOWNGRADE_NOTE = (
    "Severity 'minor'e indirildi: bu çalışma computational_modeling/ML türünde, "
    "güç analizi/örneklem-büyüklüğü raporlaması bu türde standart akademik "
    "konvansiyon DEĞİL (ampirik nicel sosyal bilim konvansiyonu). Motor bunu "
    "classifier'ın study_design çıktısına göre otomatik ayarladı."
)


def _downgrade_design_mismatched_quant_findings(
    engine_result: EngineResult, study_design: str, study_design_confidence: float
) -> EngineResult:
    """Çalışma türü güç-analizi/örneklem-büyüklüğü raporlamasını beklemiyorsa
    (örn. computational_modeling), sample_and_power'daki major bulguları
    'minor'e indir — LLM'in kendi katı kuralına (quantitative_validity.py)
    rağmen (§41b'nin öğrettiği ders: prompt-düzeltmenin etkisi güvenilmez,
    kod-seviyesi guard gerekir).

    Confidence-gating: study_design_confidence eşiğin altındaysa DOKUNMA —
    belirsiz bir sınıflandırmaya göre severity indirmek yeni bir hata sınıfı
    açar (guardian 2. tur bulgusu)."""
    if study_design not in _QUANT_DESIGN_EXEMPT:
        return engine_result  # bu study_design'da güç analizi hâlâ beklenir
    if study_design_confidence < _QUANT_DESIGN_CONFIDENCE_THRESHOLD:
        return engine_result  # sınıflandırma belirsiz, LLM'in kararına dokunma
    new_findings = []
    n_downgraded = 0
    for f in engine_result.findings:
        if f.dimension in _QUANT_DESIGN_SENSITIVE_DIMENSIONS and f.severity == "major":
            f = f.model_copy(
                update={
                    "severity": _DESIGN_MISMATCH_DOWNGRADE_SEVERITY,
                    "limitations": [*f.limitations, _DESIGN_MISMATCH_DOWNGRADE_NOTE],
                }
            )
            n_downgraded += 1
        new_findings.append(f)
    degraded = list(engine_result.degraded)
    if n_downgraded:
        logger.info(
            "quant design-mismatch guard: %d bulgu (study_design=%s) minor'e indirildi",
            n_downgraded,
            study_design,
        )
        degraded.append(f"quant_design_mismatch:downgraded_{n_downgraded}")
    return EngineResult(
        findings=new_findings, action_items=engine_result.action_items, degraded=degraded
    )


async def _safe(label: str, coro) -> EngineResult:
    """Bir motor çağrısını izole et: çökme → degraded sinyali, asla propagate etme."""
    try:
        return await coro
    except Exception as exc:  # bilinçli izolasyon boundary'si — hata yutulmaz, GÖRÜNÜR kaydedilir
        logger.exception("academic engine crashed (%s)", label)
        return EngineResult(degraded=[f"{label}:engine_crashed:{type(exc).__name__}"])


async def assess_manuscript(
    manuscript: Manuscript,
    rubric: Rubric,
    evidence: EvidencePack,
    *,
    allow_external_ai: bool,
) -> EngineResult:
    """Rubriği motorlara dağıt, tüm bulguları topla → EngineResult.
    Args:
        manuscript: parse edilmiş makale.
        rubric: select_rubric çıktısı (dimensions[].engine yönlendirmeyi belirler).
        evidence: deterministik kanıt paketi (statcheck quant motoruna bağlam olur).
        allow_external_ai: consent_gate.external_ai_allowed sonucu. False → motorlar
            SIFIR LLM çağırır, boş bulgu + degraded döner (içerik dışarı gitmez).
    Returns:
        EngineResult — findings + action_items + degraded (tümü tek listede toplanmış).
    """
    result = EngineResult()
    engines_used = {d.engine for d in rubric.dimensions}
    qual_dims = [d.id for d in rubric.dimensions if d.engine == QUALITATIVE_ENGINE]
    quant_dims = [d.id for d in rubric.dimensions if d.engine == QUANTITATIVE_ENGINE]
    # 1) nitel motor — yönlenen boyut varsa BİR KEZ (12 nitel boyut).
    if QUALITATIVE_ENGINE in engines_used:
        logger.info("dispatch: qualitative engine (rubric dims=%s)", qual_dims)
        result.extend(
            await _safe(
                "qualitative_engine",
                assess_qualitative(manuscript, allow_external_ai=allow_external_ai),
            )
        )
        await asyncio.sleep(_PACING_DELAY_SECONDS)
    # 2) nicel motor — yönlenen boyut varsa BİR KEZ (10 nicel boyut + statcheck).
    if QUANTITATIVE_ENGINE in engines_used:
        logger.info("dispatch: quantitative engine (rubric dims=%s)", quant_dims)
        quant_result = await _safe(
            "quantitative_engine",
            assess_quantitative(manuscript, evidence, allow_external_ai=allow_external_ai),
        )
        quant_result = _downgrade_design_mismatched_quant_findings(
            quant_result, rubric.study_design, rubric.study_design_confidence
        )
        result.extend(quant_result)
        await asyncio.sleep(_PACING_DELAY_SECONDS)
    # 3) general motor — metodoloji-DIŞI her boyut için ayrı (tam kapsam).
    # citation_evidence_block döngü DIŞINDA bir kez hesaplanır (saf/deterministik,
    # dim'e bağlı değil) — sadece CitationIntegrityEngine'e yönlenen boyutlara geçilir.
    citation_evidence_block = serialize_evidence_pack(evidence)
    for dim in rubric.dimensions:
        if dim.engine in (QUALITATIVE_ENGINE, QUANTITATIVE_ENGINE):
            continue
        dim_result = await _safe(
            f"dimension_engine:{dim.id}",
            assess_dimension(
                dim.id,
                manuscript,
                allow_external_ai=allow_external_ai,
                evidence_context=(
                    citation_evidence_block if dim.engine == CITATION_ENGINE else None
                ),
            ),
        )
        if dim.engine == CITATION_ENGINE:
            dim_result = _downgrade_ungrounded_citation_findings(dim_result, evidence)
        result.extend(dim_result)
        await asyncio.sleep(_PACING_DELAY_SECONDS)

    logger.info(
        "assessment done: %d findings, %d actions, %d degraded",
        len(result.findings),
        len(result.action_items),
        len(result.degraded),
    )
    return result


__all__ = ["ENGINE_VERSION", "assess_manuscript"]