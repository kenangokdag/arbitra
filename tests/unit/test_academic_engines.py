"""P03-T04/T05 — akademik değerlendirme motorları (qual/quant/general + dispatcher).

LLM istemcisi GERÇEK import yerinde (engine.academic._engine_base.call) monkeypatch'lenir;
TÜM motorlar bu tek köprüden geçer → ağ ÇAĞRILMAZ. En kritik testler:
  - consent-blocked → LLM hiç çağrılmaz (call sayacı 0) + degraded.
  - Finding sözleşmesi DÜRÜST uygulanır: critical-without-action → crash/fake DEĞİL,
    'moderate'a indirilir + not yazılır.
  - dispatcher doğru motora yönlendirir + bir motor çökse diğerleri yine döner.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from api.models.review import (
    CitationContextFinding,
    CitationIntegritySummary,
    EvidencePack,
    Finding,
    Manuscript,
    ManuscriptMeta,
    ParsedReference,
    StatFinding,
)
from engine.academic import _engine_base as eb
from engine.academic.assessment import (
    _downgrade_design_mismatched_quant_findings,
    _downgrade_ungrounded_citation_findings,
    _has_citation_integrity_evidence,
    assess_manuscript,
)
from engine.academic._engine_base import EngineResult
from engine.academic.dimension_engine import assess_dimension
from engine.academic.qualitative_engine import assess_qualitative
from engine.academic.quantitative_engine import assess_quantitative
from engine.academic.rubric_registry import select_rubric

# --- helpers ----------------------------------------------------------------


def _ms() -> Manuscript:
    return Manuscript(
        meta=ManuscriptMeta(
            title="A grounded theory study of doctoral writing",
            abstract="We interviewed 18 PhD students about their writing practices.",
            section_titles=["Introduction", "Methods", "Findings", "Discussion"],
            word_count=6000,
            reference_count=42,
        ),
        full_text="This qualitative study used semi-structured interviews. "
        "Participants were selected purposively. We analysed transcripts thematically. "
        * 50,
    )


def _resp(parsed) -> SimpleNamespace:
    """_engine_base yalnız resp.parsed_output okur → hafif stub yeterli."""
    return SimpleNamespace(parsed_output=parsed)


def _llm_findings(*findings: dict) -> eb._LLMFindingList:
    return eb._LLMFindingList(findings=[eb._LLMFinding(**f) for f in findings])


def _good_finding(dimension: str, severity: str = "major") -> dict:
    """Sözleşmeyi sağlayan bir LLM finding (anchor + action var)."""
    return {
        "dimension": dimension,
        "severity": severity,
        "confidence": 0.8,
        "title": f"{dimension} sorunu",
        "summary": f"{dimension} yeterince ele alınmamış.",
        "manuscript_anchors": [{"section": "Methods", "quote": "Participants were selected purposively."}],
        "action_items": [
            {"priority": "P0", "instruction": f"{dimension} için gerekçe ekle.",
             "target_section": "Methods", "effort": "medium", "expected_gain": "high"}
        ],
    }


# --- qualitative engine -----------------------------------------------------


@pytest.mark.asyncio
async def test_qualitative_engine_produces_qual_dimensions(monkeypatch):
    async def _fake_call(prompt, **kwargs):
        assert kwargs["mode"] == "qualitative_rigor"
        return _resp(
            _llm_findings(
                _good_finding("reflexivity"),
                _good_finding("saturation"),
                _good_finding("trustworthiness", severity="moderate"),
            )
        )

    monkeypatch.setattr(eb, "call", _fake_call)

    result = await assess_qualitative(_ms(), allow_external_ai=True)
    dims = {f.dimension for f in result.findings}
    assert {"reflexivity", "saturation", "trustworthiness"} <= dims
    assert result.degraded == []
    # major finding'ler sözleşmeyi sağlıyor (anchor + action).
    for f in result.findings:
        if f.severity == "major":
            assert f.action_item_ids
            assert f.manuscript_anchors or f.global_issue


@pytest.mark.asyncio
async def test_quantitative_engine_produces_quant_dimensions(monkeypatch):
    captured = {}

    async def _fake_call(prompt, **kwargs):
        captured["mode"] = kwargs["mode"]
        captured["prompt"] = prompt
        return _resp(
            _llm_findings(
                _good_finding("sample_and_power"),
                _good_finding("effect_size"),
                _good_finding("causal_language_discipline"),
            )
        )

    monkeypatch.setattr(eb, "call", _fake_call)

    evidence = EvidencePack(
        stat_findings=[
            StatFinding(
                test_type="t-test",
                reported_p=0.04,
                computed_p=0.06,
                status="red",
                match_text="t(48)=2.01, p=.04",
            )
        ]
    )
    result = await assess_quantitative(_ms(), evidence, allow_external_ai=True)
    dims = {f.dimension for f in result.findings}
    assert {"sample_and_power", "effect_size", "causal_language_discipline"} <= dims
    assert captured["mode"] == "quantitative_validity"
    # statcheck bağlamı prompt'a girdi mi (yeniden hesap yok, yorum bağlamı).
    assert "t(48)=2.01" in captured["prompt"]


# --- DÜRÜST sözleşme uygulaması ---------------------------------------------


@pytest.mark.asyncio
async def test_critical_without_action_is_downgraded_not_crashed(monkeypatch):
    """critical finding action/anchor'sız gelirse → crash/fake DEĞİL, moderate + not."""

    async def _fake_call(prompt, **kwargs):
        return _resp(
            _llm_findings(
                {
                    "dimension": "data_collection_transparency",
                    "severity": "critical",
                    "confidence": 0.9,
                    "title": "Veri toplama belirsiz",
                    "summary": "Görüşme protokolü yok.",
                    # anchor YOK, action YOK, global_issue YOK → sözleşme ihlali olurdu
                }
            )
        )

    monkeypatch.setattr(eb, "call", _fake_call)

    result = await assess_qualitative(_ms(), allow_external_ai=True)
    assert len(result.findings) == 1
    f = result.findings[0]
    # crash olmadı, uydurma anchor/action yok → dürüstçe moderate'a indi.
    assert f.severity == "moderate"
    assert f.action_item_ids == []
    assert f.manuscript_anchors == []
    assert any("moderate" in lim for lim in f.limitations)
    assert any("UYDURULMADI" in lim for lim in f.limitations)


@pytest.mark.asyncio
async def test_major_with_action_but_no_anchor_downgraded(monkeypatch):
    """major + action var ama anchor/global yok → yine dürüstçe moderate'a iner."""

    async def _fake_call(prompt, **kwargs):
        return _resp(
            _llm_findings(
                {
                    "dimension": "sampling_strategy",
                    "severity": "major",
                    "title": "Örnekleme gerekçesiz",
                    "summary": "Strateji belirtilmemiş.",
                    "action_items": [{"priority": "P1", "instruction": "Strateji ekle."}],
                    # anchor yok, global_issue yok
                }
            )
        )

    monkeypatch.setattr(eb, "call", _fake_call)
    result = await assess_qualitative(_ms(), allow_external_ai=True)
    f = result.findings[0]
    assert f.severity == "moderate"
    # action korunur (uydurma değil, gerçek model çıktısı)
    assert len(f.action_item_ids) == 1
    assert len(result.action_items) == 1


@pytest.mark.asyncio
async def test_major_with_global_issue_kept_high(monkeypatch):
    """major + action + global_issue (anchor yerine) → önem KORUNUR (sözleşme tatmin)."""

    async def _fake_call(prompt, **kwargs):
        return _resp(
            _llm_findings(
                {
                    "dimension": "claim_discipline",
                    "severity": "major",
                    "title": "Aşırı genelleme",
                    "summary": "Bulguların ötesinde evrensel iddia.",
                    "global_issue": True,
                    "action_items": [{"priority": "P0", "instruction": "İddiaları sınırla."}],
                }
            )
        )

    monkeypatch.setattr(eb, "call", _fake_call)
    result = await assess_qualitative(_ms(), allow_external_ai=True)
    f = result.findings[0]
    assert f.severity == "major"
    assert f.global_issue is True
    assert f.action_item_ids


# --- consent gate -----------------------------------------------------------


@pytest.mark.asyncio
async def test_consent_blocked_zero_llm_calls(monkeypatch):
    """external AI engelli → motorlar LLM'i ASLA çağırmaz (sayaç 0) + degraded."""
    calls = {"n": 0}

    async def _spy_call(prompt, **kwargs):
        calls["n"] += 1
        return _resp(_llm_findings(_good_finding("x")))

    monkeypatch.setattr(eb, "call", _spy_call)

    qual = await assess_qualitative(_ms(), allow_external_ai=False)
    quant = await assess_quantitative(_ms(), EvidencePack(), allow_external_ai=False)
    dim = await assess_dimension("contribution_originality", _ms(), allow_external_ai=False)

    assert calls["n"] == 0, "GATE İHLALİ: external AI engelliyken motor LLM çağırdı!"
    assert qual.findings == [] and quant.findings == [] and dim.findings == []
    assert "qualitative_engine:external_ai_blocked" in qual.degraded
    assert "quantitative_engine:external_ai_blocked" in quant.degraded
    assert any("external_ai_blocked" in d for d in dim.degraded)


@pytest.mark.asyncio
async def test_consent_blocked_dispatcher_zero_calls(monkeypatch):
    calls = {"n": 0}

    async def _spy_call(prompt, **kwargs):
        calls["n"] += 1
        return _resp(_llm_findings())

    monkeypatch.setattr(eb, "call", _spy_call)
    rubric = select_rubric(document_type="journal_article", study_design="qualitative")
    result = await assess_manuscript(
        _ms(), rubric, EvidencePack(), allow_external_ai=False
    )
    assert calls["n"] == 0
    assert result.findings == []
    assert result.degraded  # tüm motorlar degraded işaretledi


# --- LLM failure honest empty ----------------------------------------------


@pytest.mark.asyncio
async def test_llm_failure_is_honest_empty(monkeypatch):
    from api.services.llm_service import LLMServiceError

    async def _boom(prompt, **kwargs):
        raise LLMServiceError("gemini timeout")

    monkeypatch.setattr(eb, "call", _boom)
    result = await assess_qualitative(_ms(), allow_external_ai=True)
    assert result.findings == []
    assert "qualitative_engine:llm_unavailable" in result.degraded


# --- dispatcher routing + aggregation --------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_routes_qual_and_general(monkeypatch):
    """qual paper: nitel motor + general motor(lar) AYNI çağrıda bulgu üretir."""
    seen_modes: list[str] = []

    async def _fake_call(prompt, **kwargs):
        mode = kwargs["mode"]
        seen_modes.append(mode)
        if mode == "qualitative_rigor":
            return _resp(_llm_findings(_good_finding("reflexivity")))
        if mode == "academic_dimension":
            # general motor: tek boyut → 1 finding (dimension force edilir)
            return _resp(_llm_findings(_good_finding("from_llm_label")))
        raise AssertionError(f"beklenmeyen mode: {mode}")

    monkeypatch.setattr(eb, "call", _fake_call)
    rubric = select_rubric(document_type="journal_article", study_design="qualitative")
    result = await assess_manuscript(
        _ms(), rubric, EvidencePack(), allow_external_ai=True
    )

    # nitel motor TAM 1 kez çağrıldı (her metodoloji boyutu için tekrar etmez).
    assert seen_modes.count("qualitative_rigor") == 1
    # general motor her metodoloji-dışı boyut için çağrıldı.
    general_dims = [
        d.id
        for d in rubric.dimensions
        if d.engine not in ("QualitativeRigorEngine", "QuantitativeValidityEngine")
    ]
    assert seen_modes.count("academic_dimension") == len(general_dims)
    assert "quantitative_validity" not in seen_modes  # qual paper → quant motor koşmaz

    dims = {f.dimension for f in result.findings}
    # nitel bulgu (LLM alt-boyutu) + general bulgu (rubrik boyutuna force edilmiş) bir arada.
    assert "reflexivity" in dims
    for gd in general_dims:
        assert gd in dims, f"general boyut {gd} bulgu üretmedi (tam kapsam ihlali)"


@pytest.mark.asyncio
async def test_dispatcher_quant_paper_uses_quant_engine(monkeypatch):
    seen_modes: list[str] = []

    async def _fake_call(prompt, **kwargs):
        mode = kwargs["mode"]
        seen_modes.append(mode)
        if mode == "quantitative_validity":
            return _resp(_llm_findings(_good_finding("power")))
        return _resp(_llm_findings(_good_finding("x")))

    monkeypatch.setattr(eb, "call", _fake_call)
    rubric = select_rubric(document_type="journal_article", study_design="quantitative")
    result = await assess_manuscript(
        _ms(), rubric, EvidencePack(), allow_external_ai=True
    )
    assert seen_modes.count("quantitative_validity") == 1
    assert "qualitative_rigor" not in seen_modes
    assert any(f.dimension == "power" for f in result.findings)


# --- EvidencePack → assess_dimension wiring (2026-08-08, §31/§32) -----------


@pytest.mark.asyncio
async def test_citation_integrity_dimension_receives_evidence_context(monkeypatch):
    """citation_integrity/literature_positioning (CitationIntegrityEngine'e
    yönlenen boyutlar) LLM çağrısında KANIT PAKETİ'ni GÖRMELİ — EvidencePack'teki
    uydurma referans metni prompt'ta birebir görünmeli."""
    prompts_by_dim: dict[str, str] = {}

    async def _fake_call(prompt, **kwargs):
        # force_dimension sayesinde criteria_block "BOYUT: <id>" satırını taşır.
        for line in prompt.splitlines():
            if line.startswith("BOYUT: "):
                prompts_by_dim[line.removeprefix("BOYUT: ")] = prompt
                break
        return _resp(_llm_findings(_good_finding("x")))

    monkeypatch.setattr(eb, "call", _fake_call)
    rubric = select_rubric(document_type="journal_article", study_design="quantitative")
    evidence = EvidencePack(
        citation_integrity=CitationIntegritySummary(total=3, resolved=2, fabricated=1),
        references=[
            ParsedReference(
                index=1,
                raw="Uydurma Referans XYZ (2020)",
                title="Uydurma Referans XYZ",
                status="fabricated",
                evidence="DOI başka esere ait",
            )
        ],
    )
    await assess_manuscript(_ms(), rubric, evidence, allow_external_ai=True)

    assert "citation_integrity" in prompts_by_dim
    assert "literature_positioning" in prompts_by_dim
    assert "KANIT PAKETİ" in prompts_by_dim["citation_integrity"]
    assert "Uydurma Referans XYZ" in prompts_by_dim["citation_integrity"]
    assert "uydurma=1" in prompts_by_dim["citation_integrity"]
    assert "KANIT PAKETİ" in prompts_by_dim["literature_positioning"]


@pytest.mark.asyncio
async def test_non_citation_dimension_does_not_receive_evidence_context(monkeypatch):
    """ethics_reproducibility (EthicsTransparencyEngine) EvidencePack'in atıf
    kanıtıyla İLGİSİZ — prompt'ta KANIT PAKETİ/uydurma referans metni GÖRÜNMEMELİ
    (ilgisiz-bağlam kirliliği + gereksiz token maliyeti önlenir)."""
    prompts_by_dim: dict[str, str] = {}

    async def _fake_call(prompt, **kwargs):
        for line in prompt.splitlines():
            if line.startswith("BOYUT: "):
                prompts_by_dim[line.removeprefix("BOYUT: ")] = prompt
                break
        return _resp(_llm_findings(_good_finding("x")))

    monkeypatch.setattr(eb, "call", _fake_call)
    rubric = select_rubric(document_type="journal_article", study_design="quantitative")
    evidence = EvidencePack(
        references=[
            ParsedReference(
                index=1,
                raw="Uydurma Referans XYZ (2020)",
                title="Uydurma Referans XYZ",
                status="fabricated",
            )
        ],
    )
    await assess_manuscript(_ms(), rubric, evidence, allow_external_ai=True)

    assert "ethics_reproducibility" in prompts_by_dim
    assert "KANIT PAKETİ" not in prompts_by_dim["ethics_reproducibility"]
    assert "Uydurma Referans XYZ" not in prompts_by_dim["ethics_reproducibility"]


# --- kanıtsızlık guard'ı (2026-08-10, §38) -----------------------------------
# citation_integrity/literature_positioning'de critical/major severity İÇİN
# fabricated/retracted/contradicted kanıt GEREKİR - LLM bunu güvenilir uygulamadığı
# için (61 makalede %16 kanıtlı) deterministik kod-seviyesi guard eklendi.


def _citation_finding(fid: str, dimension: str, severity: str) -> Finding:
    return Finding(
        finding_id=fid,
        dimension=dimension,
        severity=severity,  # type: ignore[arg-type]
        confidence=0.8,
        title="x",
        global_issue=True,
        action_item_ids=[f"{fid}.a0"],
    )


def test_has_citation_integrity_evidence_true_for_fabricated() -> None:
    ev = EvidencePack(citation_integrity=CitationIntegritySummary(fabricated=1))
    assert _has_citation_integrity_evidence(ev) is True


def test_has_citation_integrity_evidence_true_for_retracted() -> None:
    ev = EvidencePack(citation_integrity=CitationIntegritySummary(retracted=1))
    assert _has_citation_integrity_evidence(ev) is True


def test_has_citation_integrity_evidence_true_for_contradicted_context_finding() -> None:
    ev = EvidencePack(
        context_findings=[CitationContextFinding(ref_index=1, claim="x", support="contradicted")]
    )
    assert _has_citation_integrity_evidence(ev) is True


def test_has_citation_integrity_evidence_false_when_only_not_found() -> None:
    """SADECE not_found_in_index -> kanıt SAYILMAZ (HK-3: asla suçlama değil)."""
    ev = EvidencePack(citation_integrity=CitationIntegritySummary(not_found_in_index=50, total=50))
    assert _has_citation_integrity_evidence(ev) is False


def test_downgrade_lowers_ungrounded_critical_citation_finding_to_moderate() -> None:
    ev = EvidencePack(citation_integrity=CitationIntegritySummary(not_found_in_index=10, total=10))
    result = EngineResult(
        findings=[_citation_finding("f0", "citation_integrity", "critical")]
    )
    out = _downgrade_ungrounded_citation_findings(result, ev)
    assert out.findings[0].severity == "moderate"
    assert any("kanıtsızlık" in lim for lim in out.findings[0].limitations)
    assert any("downgraded_1" in d for d in out.degraded)


def test_downgrade_leaves_grounded_finding_untouched() -> None:
    ev = EvidencePack(citation_integrity=CitationIntegritySummary(fabricated=1, total=1))
    result = EngineResult(
        findings=[_citation_finding("f0", "citation_integrity", "critical")]
    )
    out = _downgrade_ungrounded_citation_findings(result, ev)
    assert out.findings[0].severity == "critical"  # dokunulmadı
    assert out.degraded == []


def test_downgrade_ignores_non_citation_dimension() -> None:
    """literature_depth BİLİNÇLİ dışarıda - kapsam sınırı korunuyor."""
    ev = EvidencePack(citation_integrity=CitationIntegritySummary(not_found_in_index=5, total=5))
    result = EngineResult(
        findings=[_citation_finding("f0", "literature_depth", "critical")]
    )
    out = _downgrade_ungrounded_citation_findings(result, ev)
    assert out.findings[0].severity == "critical"  # dokunulmadı


@pytest.mark.asyncio
async def test_dispatcher_downgrades_ungrounded_citation_severity_end_to_end(monkeypatch):
    """Uçtan uca: LLM citation_integrity'e 'critical' verir ama EvidencePack'te
    fabricated/retracted/contradicted YOK -> nihai Finding 'moderate' olmalı."""

    async def _fake_call(prompt, **kwargs):
        # SADECE genel motor (academic_dimension) 'critical' dönsün - quant/qual
        # motorlarının mock'u da aynı sabit yanıtı döndürüp (force_dimension'ları
        # olmadığı için) sahte bir "citation_integrity" bulgusu SIZDIRMASIN
        # (bu, gerçek pipeline'da asla olmaz - quant/qual motorlarının kendi
        # brief'i onlara kendi alt-boyut adlarını kullanmalarını söyler).
        if kwargs.get("mode") == "academic_dimension":
            return _resp(
                _llm_findings(_good_finding("citation_integrity", severity="critical"))
            )
        return _resp(_llm_findings())

    monkeypatch.setattr(eb, "call", _fake_call)
    rubric = select_rubric(document_type="journal_article", study_design="quantitative")
    evidence = EvidencePack(
        citation_integrity=CitationIntegritySummary(not_found_in_index=20, total=20),
    )
    result = await assess_manuscript(_ms(), rubric, evidence, allow_external_ai=True)

    ci_findings = [f for f in result.findings if f.dimension == "citation_integrity"]
    assert ci_findings, "citation_integrity bulgusu üretilmedi"
    assert all(f.severity == "moderate" for f in ci_findings)
    assert any("citation_integrity_grounding" in d for d in result.degraded)


# --- quant design-mismatch guard'ı (2026-08-13, §46) -------------------------
# quantitative_validity.py'nin "major = güç analizi/etki büyüklüğü yok" kuralı
# çalışma tasarımından bağımsız - computational_modeling (ML/DL) makalelerinde
# güç analizi standart konvansiyon DEĞİL. 61 makalede bu tek kural yüzünden
# 40/61 makale AYNI soundness skorunu (7.75) alıyordu (sample_and_power tek
# başına saturasyonun ~%100'ünü açıklıyordu). Plan: docs/plans/
# SOUNDNESS_SEVERITY_CONTEXT_SENSITIVITY_2026-08-13.md


def _quant_finding(fid: str, dimension: str, severity: str) -> Finding:
    return Finding(
        finding_id=fid,
        dimension=dimension,
        severity=severity,  # type: ignore[arg-type]
        confidence=0.8,
        title="x",
        global_issue=True,
        action_item_ids=[f"{fid}.a0"],
    )


def test_downgrade_lowers_sample_and_power_major_to_minor_for_computational_modeling() -> None:
    result = EngineResult(
        findings=[_quant_finding("quant.f0", "sample_and_power", "major")]
    )
    out = _downgrade_design_mismatched_quant_findings(
        result, "computational_modeling", 0.8
    )
    assert out.findings[0].severity == "minor"
    assert any("konvansiyon" in lim for lim in out.findings[0].limitations)
    assert any("downgraded_1" in d for d in out.degraded)


def test_downgrade_leaves_finding_untouched_for_quantitative_study_design() -> None:
    """quantitative (ampirik nicel sosyal bilim) - güç analizi hâlâ standart
    konvansiyon, dokunulmamalı."""
    result = EngineResult(
        findings=[_quant_finding("quant.f0", "sample_and_power", "major")]
    )
    out = _downgrade_design_mismatched_quant_findings(result, "quantitative", 0.9)
    assert out.findings[0].severity == "major"  # dokunulmadı
    assert out.degraded == []


def test_downgrade_ignores_low_confidence_classification() -> None:
    """study_design_confidence eşiğin (0.7) altında -> guard ÇALIŞMAZ, belirsiz
    sınıflandırmaya göre severity indirilmez (guardian 2. tur bulgusu)."""
    result = EngineResult(
        findings=[_quant_finding("quant.f0", "sample_and_power", "major")]
    )
    out = _downgrade_design_mismatched_quant_findings(
        result, "computational_modeling", 0.5
    )
    assert out.findings[0].severity == "major"  # dokunulmadı
    assert out.degraded == []


def test_downgrade_ignores_non_sample_and_power_dimension() -> None:
    """effect_size ailesi BİLİNÇLİ dışarıda (plan §3b) - yanlış risk_radar
    kovasına gidiyor (evidence/claims_supported, methodology/soundness DEĞİL)."""
    result = EngineResult(
        findings=[_quant_finding("quant.f0", "effect_size_and_uncertainty", "major")]
    )
    out = _downgrade_design_mismatched_quant_findings(
        result, "computational_modeling", 0.9
    )
    assert out.findings[0].severity == "major"  # dokunulmadı


def test_downgrade_ignores_critical_severity() -> None:
    """Sadece 'major' hedefleniyor - critical'a hiç dokunulmaz (moat-gate
    kapsamı bilinçli korunuyor, plan §4b)."""
    result = EngineResult(
        findings=[_quant_finding("quant.f0", "sample_and_power", "critical")]
    )
    out = _downgrade_design_mismatched_quant_findings(
        result, "computational_modeling", 0.9
    )
    assert out.findings[0].severity == "critical"  # dokunulmadı
    assert out.degraded == []


@pytest.mark.asyncio
async def test_dispatcher_downgrades_design_mismatched_quant_severity_end_to_end(
    monkeypatch,
):
    """Uçtan uca: LLM sample_and_power'a 'major' verir, rubric study_design
    computational_modeling + yüksek confidence -> nihai Finding 'minor' olmalı."""

    async def _fake_call(prompt, **kwargs):
        if kwargs.get("mode") == "quantitative_validity":
            return _resp(_llm_findings(_good_finding("sample_and_power", severity="major")))
        return _resp(_llm_findings())

    monkeypatch.setattr(eb, "call", _fake_call)
    rubric = select_rubric(
        document_type="journal_article",
        study_design="computational_modeling",
        study_design_confidence=0.85,
    )
    result = await assess_manuscript(_ms(), rubric, EvidencePack(), allow_external_ai=True)

    sp_findings = [f for f in result.findings if f.dimension == "sample_and_power"]
    assert sp_findings, "sample_and_power bulgusu üretilmedi"
    assert all(f.severity == "minor" for f in sp_findings)
    assert any("quant_design_mismatch" in d for d in result.degraded)


# --- engine isolation -------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_engine_crash_isolated(monkeypatch):
    """Bir motor (qual) çökse → degraded kaydedilir, diğer motorların bulguları yine döner."""

    async def _fake_call(prompt, **kwargs):
        mode = kwargs["mode"]
        if mode == "qualitative_rigor":
            raise RuntimeError("kasıtlı çökme")
        return _resp(_llm_findings(_good_finding("ok_dim")))

    monkeypatch.setattr(eb, "call", _fake_call)
    rubric = select_rubric(document_type="journal_article", study_design="qualitative")
    result = await assess_manuscript(
        _ms(), rubric, EvidencePack(), allow_external_ai=True
    )

    # çökme propagate ETMEDİ → çağrı tamamlandı.
    assert any("qualitative_engine:engine_crashed" in d for d in result.degraded)
    # general motorların bulguları yine geldi (general motor dimension'ı rubrik
    # boyutuna force eder → "ok_dim" LLM etiketi değil, rubrik boyut id'leri görünür).
    assert result.findings, "izolasyon: diğer motor bulguları kayboldu"
    general_dims = {
        d.id
        for d in rubric.dimensions
        if d.engine not in ("QualitativeRigorEngine", "QuantitativeValidityEngine")
    }
    assert {f.dimension for f in result.findings} == general_dims
