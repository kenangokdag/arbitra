"""SEC-2 / P01-T03 — external-AI consent gate.

En kritik test: gizli dosya + rıza yok → review_orchestration.run_orchestration
(external LLM) ASLA çağrılmaz. Gizlilik vaadinin backend kanıtı.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from api.models.review import (
    CitationIntegritySummary,
    EvidencePack,
    Manuscript,
    ManuscriptMeta,
    PrivacyConfig,
    ReviewProvenance,
    ReviewReport,
)
from api.services import consent_gate

# --- resolve_privacy (güvenli default) -------------------------------------


def test_editor_mode_defaults_external_ai_blocked():
    p = consent_gate.resolve_privacy(mode="editor")
    assert p.confidentiality_mode == "reviewer_confidential"
    assert p.external_ai_consent == "blocked"


def test_confidential_without_consent_blocks():
    p = consent_gate.resolve_privacy(
        mode="author", confidentiality_mode="reviewer_confidential"
    )
    assert p.external_ai_consent == "blocked"


def test_confidential_explicit_allowed_passes():
    p = consent_gate.resolve_privacy(
        mode="author",
        confidentiality_mode="reviewer_confidential",
        external_ai_consent="allowed",
    )
    assert p.external_ai_consent == "allowed"


def test_author_mode_default_allowed():
    p = consent_gate.resolve_privacy(mode="author")
    assert p.confidentiality_mode == "author_owned"
    assert p.external_ai_consent == "allowed"


def test_external_ai_allowed_logic():
    assert consent_gate.external_ai_allowed(None) is True  # eski akış geri uyum
    assert consent_gate.external_ai_allowed(
        PrivacyConfig(external_ai_consent="allowed")
    ) is True
    assert consent_gate.external_ai_allowed(
        PrivacyConfig(external_ai_consent="blocked")
    ) is False


def test_degraded_report_is_honest():
    ev = EvidencePack(citation_integrity=CitationIntegritySummary(total=5, resolved=4))
    ms = Manuscript(meta=ManuscriptMeta(title="X"), full_text="x")
    p = PrivacyConfig(confidentiality_mode="reviewer_confidential", external_ai_consent="blocked")
    rep = consent_gate.degraded_report(ms, ev, "editor", "tr", p)
    assert rep.disclosure is not None
    assert rep.disclosure.degraded_due_to_consent is True
    assert rep.disclosure.external_ai_used is False
    assert rep.provenance.model_used == "none (external AI blocked)"
    assert "External AI" in rep.summary


# --- GATE: run_pipeline external LLM'i çağırmamalı --------------------------


def _minimal_report() -> ReviewReport:
    return ReviewReport(
        mode="editor",
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


@pytest.mark.asyncio
async def test_run_pipeline_confidential_blocks_external_llm(monkeypatch):
    """GİZLİ + rıza yok → run_orchestration ÇAĞRILMAZ; degraded rapor üretilir."""
    from api.services import review_service as svc

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(svc, "_set_step", _noop)
    monkeypatch.setattr(svc, "_update", _noop)

    ms = Manuscript(meta=ManuscriptMeta(), full_text="x")
    import engine.ingestion as ing

    monkeypatch.setattr(ing, "parse_document", lambda *a, **k: ms)

    async def _resolve_all(refs):
        return ([], CitationIntegritySummary())

    async def _check_context(c, r):
        return []

    async def _find_cov(m, r):
        return []

    monkeypatch.setattr(svc.review_citation_service, "resolve_all", _resolve_all)
    monkeypatch.setattr(svc.review_citation_service, "check_context", _check_context)
    monkeypatch.setattr(svc.review_citation_service, "find_coverage_gaps", _find_cov)
    monkeypatch.setattr(svc, "_stat_findings", lambda t: [])

    called = {"n": 0}

    async def _spy_orch(*a, **k):
        called["n"] += 1
        return _minimal_report()

    monkeypatch.setattr(svc.review_orchestration, "run_orchestration", _spy_orch)

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

    assert called["n"] == 0, "GATE İHLALİ: external LLM gizli dosyada çağrıldı!"
    # degraded rapor persist edildi mi
    assert "report" in captured
    assert captured["report"]["disclosure"]["degraded_due_to_consent"] is True


@pytest.mark.asyncio
async def test_run_pipeline_consent_allowed_runs_orchestration(monkeypatch):
    """Rıza varsa normal orkestrasyon ÇALIŞIR + disclosure external_ai_used=True."""
    from api.services import review_service as svc

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(svc, "_set_step", _noop)

    ms = Manuscript(meta=ManuscriptMeta(), full_text="x")
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

    # FAZ C2: akademik motor stage'i bu testin konusu değil (orkestrasyon gate'i
    # test ediliyor) → ağ/LLM'siz boş EngineResult ile izole et.
    from engine.academic._engine_base import EngineResult

    async def _assess(*a, **k):
        return EngineResult()

    monkeypatch.setattr(svc, "assess_manuscript", _assess)

    called = {"n": 0}

    async def _spy_orch(*a, **k):
        called["n"] += 1
        return _minimal_report()

    monkeypatch.setattr(svc.review_orchestration, "run_orchestration", _spy_orch)

    captured: dict[str, object] = {}

    async def _capture_update(job_id, **fields):
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    privacy = PrivacyConfig(external_ai_consent="allowed")
    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="author", language="tr", privacy=privacy,
    )

    assert called["n"] == 1
    assert captured["report"]["disclosure"]["external_ai_used"] is True
