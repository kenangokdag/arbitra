"""BE-2 / P02-T05 — sağlayıcı arızası GÖRÜNÜR degraded, sessiz değil.

CANON/observability: hata kaybolmaz. find_coverage_gaps OpenAlexError fırlatırsa
run_pipeline bunu yutmaz — EvidencePack.degraded_features'a yazar, boru hattı
düşmez (kapsama eksik ama rapor üretilir + eksiklik raporda görünür).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.models.review import (
    CitationIntegritySummary,
    Manuscript,
    ManuscriptMeta,
)
from api.services.openalex_polite import OpenAlexError


def _patch_pipeline_common(monkeypatch, svc):
    """parse/resolve/context/stat'ı no-op'la; sadece coverage davranışı test edilir."""
    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(svc, "_set_step", _noop)

    ms = Manuscript(meta=ManuscriptMeta(), full_text="x")
    import engine.ingestion as ing

    monkeypatch.setattr(ing, "parse_document", lambda *a, **k: ms)

    async def _resolve_all(refs):
        return ([], CitationIntegritySummary())

    async def _check_context(c, r):
        return []

    monkeypatch.setattr(svc.review_citation_service, "resolve_all", _resolve_all)
    monkeypatch.setattr(svc.review_citation_service, "check_context", _check_context)
    monkeypatch.setattr(svc, "_stat_findings", lambda t: [])

    # FAZ C2: akademik motor stage'i bu testin konusu DEĞİL (coverage degraded
    # davranışı test ediliyor) → ağ/LLM'siz boş EngineResult ile izole et; aksi
    # halde gerçek motor LLM'i tetikler ve degraded_features'ı kirletir.
    from engine.academic._engine_base import EngineResult

    async def _assess(*a, **k):
        return EngineResult()

    monkeypatch.setattr(svc, "assess_manuscript", _assess)

    async def _spy_orch(*a, **k):
        from api.services.consent_gate import build_disclosure

        rep = _minimal_report()
        rep.disclosure = build_disclosure(None, external_ai_used=True, providers=["llm"])
        return rep

    monkeypatch.setattr(svc.review_orchestration, "run_orchestration", _spy_orch)


def _minimal_report():
    from datetime import UTC, datetime

    from api.models.review import ReviewProvenance, ReviewReport

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
async def test_coverage_provider_failure_is_visible_not_silent(monkeypatch):
    """OpenAlex düşerse degraded_features'a yazılır; pipeline failed OLMAZ."""
    from api.services import review_service as svc

    _patch_pipeline_common(monkeypatch, svc)

    async def _boom(meta, refs):
        raise OpenAlexError("OpenAlex 503")

    monkeypatch.setattr(svc.review_citation_service, "find_coverage_gaps", _boom)

    captured: dict[str, object] = {}

    async def _capture_update(job_id, **fields):
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="editor", language="tr",
    )

    # evidence_pack persist edildi ve degraded_features sağlayıcı arızasını taşıyor
    assert "evidence_pack" in captured
    degraded = captured["evidence_pack"]["degraded_features"]
    assert "coverage:openalex_unavailable" in degraded, (
        "SESSİZ ARIZA: OpenAlex düştü ama degraded_features boş — hata yutuldu!"
    )
    # boru hattı düşmedi: rapor üretildi (failed değil)
    assert "report" in captured


@pytest.mark.asyncio
async def test_citation_resolution_provider_failure_is_visible_not_silent(monkeypatch):
    """§41: resolve_all'ın provider_errors>0 döndürmesi SESSİZ kalmamalı —
    review_service.py bunu degraded_features'a + resolve_references stage'ine
    GÖRÜNÜR yazmalı (önceden bu görünmezdi — guardian bulgusu §40)."""
    from api.services import review_service as svc

    _patch_pipeline_common(monkeypatch, svc)

    async def _resolve_all_with_provider_error(refs):
        return ([], CitationIntegritySummary(total=3, not_found_in_index=1, provider_errors=1))

    monkeypatch.setattr(
        svc.review_citation_service, "resolve_all", _resolve_all_with_provider_error
    )

    stage_snapshots: list[list[dict]] = []

    async def _capture_stages(job_id, tracker):
        stage_snapshots.append(tracker.dump())

    monkeypatch.setattr(svc, "_save_stages", _capture_stages)

    captured: dict[str, object] = {}

    async def _capture_update(job_id, **fields):
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="editor", language="tr",
    )

    degraded = captured["evidence_pack"]["degraded_features"]
    assert "citations:openalex_resolution_failed:1" in degraded, (
        "SESSİZ ARIZA: per-referans OpenAlex hatası oldu ama degraded_features "
        "boş — hata yutuldu!"
    )
    # resolve_references stage'i degraded görünmeli (completed DEĞİL).
    final_stages = {s["stage"]: s for s in stage_snapshots[-1]}
    assert final_stages["resolve_references"]["status"] == "degraded"
    assert (
        final_stages["resolve_references"]["degraded_reason"]
        == "citations:openalex_resolution_failed:1"
    )


@pytest.mark.asyncio
async def test_coverage_success_has_no_degraded_feature(monkeypatch):
    """Sağlayıcı çalışıyorsa degraded_features BOŞ kalır (yanlış-pozitif yok)."""
    from api.services import review_service as svc

    _patch_pipeline_common(monkeypatch, svc)

    async def _ok(meta, refs):
        return []

    monkeypatch.setattr(svc.review_citation_service, "find_coverage_gaps", _ok)

    captured: dict[str, object] = {}

    async def _capture_update(job_id, **fields):
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="editor", language="tr",
    )

    assert captured["evidence_pack"]["degraded_features"] == []
