"""P03-T01/T02 — belge/çalışma türü sınıflandırıcı testleri.

LLM istemcisi GERÇEK import yerinde (engine.academic.classifier.call) monkeypatch'lenir;
ağ ÇAĞRILMAZ. En kritik test: consent-blocked → LLM hiç çağrılmaz (call sayacı 0).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from api.models.review import Manuscript, ManuscriptMeta
from api.services.llm_service import LLMServiceError
from engine.academic import classifier as ac
from engine.academic.classifier import _ClassifierLLMOutput, classify_document


def _ms() -> Manuscript:
    return Manuscript(
        meta=ManuscriptMeta(
            title="A grounded theory study of doctoral writing",
            abstract="We interviewed 18 PhD students...",
            section_titles=["Introduction", "Methods", "Findings", "Discussion"],
        ),
        full_text="Bu çalışma yarı-yapılandırılmış görüşmelerle...",
    )


def _resp(output: _ClassifierLLMOutput) -> SimpleNamespace:
    """classifier yalnız resp.parsed_output okur → hafif stub yeterli."""
    return SimpleNamespace(parsed_output=output)


@pytest.mark.asyncio
async def test_valid_classification(monkeypatch):
    async def _fake_call(prompt, **kwargs):
        return _resp(
            _ClassifierLLMOutput(
                document_type="thesis",
                document_type_confidence=0.88,
                study_design="qualitative",
                study_design_confidence=0.79,
                rationale="Tez ve nitel görüşme sinyalleri.",
            )
        )

    monkeypatch.setattr(ac, "call", _fake_call)

    result = await classify_document(_ms(), allow_external_ai=True)
    assert result.document_type == "thesis"
    assert result.document_type_confidence == 0.88
    assert result.study_design == "qualitative"
    assert result.study_design_confidence == 0.79
    assert result.effective_document_type == "thesis"


@pytest.mark.asyncio
async def test_off_enum_output_becomes_unknown(monkeypatch):
    async def _fake_call(prompt, **kwargs):
        return _resp(
            _ClassifierLLMOutput(
                document_type="research_paper",  # enum-DIŞI
                document_type_confidence=0.95,
                study_design="qualitative",  # geçerli
                study_design_confidence=0.6,
            )
        )

    monkeypatch.setattr(ac, "call", _fake_call)

    result = await classify_document(_ms(), allow_external_ai=True)
    # enum-dışı → unknown + confidence sıfırlanır (güvenilmez)
    assert result.document_type == "unknown"
    assert result.document_type_confidence == 0.0
    # geçerli alan korunur
    assert result.study_design == "qualitative"
    assert result.study_design_confidence == 0.6
    assert result.rationale is not None
    assert "research_paper" in result.rationale


@pytest.mark.asyncio
async def test_consent_blocked_no_llm_call(monkeypatch):
    """GİZLİ + rıza yok → LLM ASLA çağrılmaz (call sayacı 0), dürüst unknown."""
    calls = {"n": 0}

    async def _spy_call(prompt, **kwargs):
        calls["n"] += 1
        return _resp(_ClassifierLLMOutput(document_type="thesis"))

    monkeypatch.setattr(ac, "call", _spy_call)

    result = await classify_document(_ms(), allow_external_ai=False)
    assert calls["n"] == 0, "GATE İHLALİ: external AI engelliyken classifier LLM çağırdı!"
    assert result.document_type == "unknown"
    assert result.document_type_confidence == 0.0
    assert result.study_design == "unknown"
    assert result.rationale is not None
    assert "external ai" in result.rationale.lower()


@pytest.mark.asyncio
async def test_user_override_wins(monkeypatch):
    async def _fake_call(prompt, **kwargs):
        return _resp(
            _ClassifierLLMOutput(
                document_type="thesis",
                document_type_confidence=0.9,
                study_design="qualitative",
                study_design_confidence=0.8,
            )
        )

    monkeypatch.setattr(ac, "call", _fake_call)

    result = await classify_document(
        _ms(),
        allow_external_ai=True,
        user_document_type_override="grant_proposal",
    )
    # inferred değer korunur ama effective_* override'ı döndürür
    assert result.document_type == "thesis"
    assert result.user_document_type_override == "grant_proposal"
    assert result.effective_document_type == "grant_proposal"
    # study_design override'ı yok → model tahmini geçerli
    assert result.effective_study_design == "qualitative"


@pytest.mark.asyncio
async def test_llm_failure_is_honest_unknown(monkeypatch):
    async def _boom(prompt, **kwargs):
        raise LLMServiceError("gemini timeout")

    monkeypatch.setattr(ac, "call", _boom)

    # crash YOK — dürüst unknown döner
    result = await classify_document(_ms(), allow_external_ai=True)
    assert result.document_type == "unknown"
    assert result.study_design == "unknown"
    assert result.document_type_confidence == 0.0
    assert result.rationale is not None
    assert "gemini timeout" in result.rationale


@pytest.mark.asyncio
async def test_confidence_clamped(monkeypatch):
    async def _fake_call(prompt, **kwargs):
        return _resp(
            _ClassifierLLMOutput(
                document_type="journal_article",
                document_type_confidence=1.7,  # aralık dışı
                study_design="quantitative",
                study_design_confidence=-0.3,  # aralık dışı
            )
        )

    monkeypatch.setattr(ac, "call", _fake_call)

    result = await classify_document(_ms(), allow_external_ai=True)
    assert result.document_type_confidence == 1.0
    assert result.study_design_confidence == 0.0
