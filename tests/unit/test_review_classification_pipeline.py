"""P03 — run_pipeline sınıflandırma kablolaması.

Doğrular:
  - normal akış: report.document_classification DOLU (classifier sonucu rapora çıpalı).
  - gizli + rıza yok: classification yine DOLU (unknown) ama external AI classifier
    için ÇAĞRILMAZ (engine.academic.classifier.call sayacı 0) ve orkestrasyon atlanır.

LLM istemcisi gerçek import yerinde (svc.academic_classifier.call) monkeypatch'lenir.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from api.models.review import (
    CitationIntegritySummary,
    Manuscript,
    ManuscriptMeta,
    PrivacyConfig,
    ReviewProvenance,
    ReviewReport,
)
from engine.academic.classifier import _ClassifierLLMOutput


def _minimal_report() -> ReviewReport:
    return ReviewReport(
        mode="author",
        language="tr",
        manuscript_meta=ManuscriptMeta(),
        summary="x",
        overall_assessment="y",
        verdict="minor_revision",
        provenance=ReviewProvenance(
            model_used="spy",
            persona_version="v",
            engine_version="v",
            generated_at=datetime.now(UTC),
        ),
    )


def _patch_common(monkeypatch, svc):
    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(svc, "_set_step", _noop)

    ms = Manuscript(meta=ManuscriptMeta(title="T"), full_text="x")
    import engine.ingestion as ing

    monkeypatch.setattr(ing, "parse_document", lambda *a, **k: ms)

    async def _resolve_all(refs):
        return ([], CitationIntegritySummary())

    async def _empty(*a, **k):
        return []

    monkeypatch.setattr(svc.review_citation_service, "resolve_all", _resolve_all)
    monkeypatch.setattr(svc.review_citation_service, "check_context", _empty)
    monkeypatch.setattr(svc.review_citation_service, "find_coverage_gaps", _empty)
    monkeypatch.setattr(svc, "_stat_findings", lambda t: [])

    # FAZ C2: akademik motor stage'i (LLM) bu sınıflandırma-kablolaması testinin
    # konusu değil → ağ/LLM'siz boş EngineResult ile izole et.
    from engine.academic._engine_base import EngineResult

    async def _assess(*a, **k):
        return EngineResult()

    monkeypatch.setattr(svc, "assess_manuscript", _assess)

    async def _spy_orch(*a, **k):
        return _minimal_report()

    monkeypatch.setattr(svc.review_orchestration, "run_orchestration", _spy_orch)


@pytest.mark.asyncio
async def test_pipeline_populates_classification(monkeypatch):
    from api.services import review_service as svc

    _patch_common(monkeypatch, svc)

    async def _fake_call(prompt, **kwargs):
        return SimpleNamespace(
            parsed_output=_ClassifierLLMOutput(
                document_type="thesis",
                document_type_confidence=0.9,
                study_design="qualitative",
                study_design_confidence=0.8,
            )
        )

    # classifier LLM istemcisini gerçek yerinde patch'le (ağ yok)
    monkeypatch.setattr(svc.academic_classifier, "call", _fake_call)

    captured: dict[str, object] = {}

    async def _capture_update(job_id, **fields):
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    privacy = PrivacyConfig(external_ai_consent="allowed")
    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="author", language="tr", privacy=privacy,
    )

    # hem 'classification' kolonu hem rapor içine yazıldı
    assert "classification" in captured
    assert captured["classification"]["document_type"] == "thesis"
    assert "report" in captured
    assert captured["report"]["document_classification"]["document_type"] == "thesis"
    assert captured["report"]["document_classification"]["study_design"] == "qualitative"


@pytest.mark.asyncio
async def test_pipeline_confidential_classifies_unknown_without_external_ai(monkeypatch):
    """Gizli + rıza yok → classification DOLU (unknown), classifier LLM ÇAĞRILMAZ."""
    from api.services import review_service as svc

    _patch_common(monkeypatch, svc)

    orch_calls = {"n": 0}

    async def _spy_orch(*a, **k):
        orch_calls["n"] += 1
        return _minimal_report()

    monkeypatch.setattr(svc.review_orchestration, "run_orchestration", _spy_orch)

    classifier_calls = {"n": 0}

    async def _spy_call(prompt, **kwargs):
        classifier_calls["n"] += 1
        return SimpleNamespace(parsed_output=_ClassifierLLMOutput(document_type="thesis"))

    monkeypatch.setattr(svc.academic_classifier, "call", _spy_call)

    captured: dict[str, object] = {}

    async def _capture_update(job_id, **fields):
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    privacy = PrivacyConfig(
        confidentiality_mode="reviewer_confidential", external_ai_consent="blocked"
    )
    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="editor", language="tr", privacy=privacy,
    )

    assert classifier_calls["n"] == 0, "GATE İHLALİ: gizli dosyada classifier LLM çağrıldı!"
    assert orch_calls["n"] == 0, "GATE İHLALİ: gizli dosyada orkestrasyon çağrıldı!"
    # classification yine üretildi (dürüst unknown) ve rapora çıpalandı
    assert "classification" in captured
    assert captured["classification"]["document_type"] == "unknown"
    assert "report" in captured
    assert captured["report"]["document_classification"]["document_type"] == "unknown"
    # degraded rapor (external AI blocked) korunur
    assert captured["report"]["disclosure"]["degraded_due_to_consent"] is True
