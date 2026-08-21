"""G4 — per-stage emit: run_pipeline ReviewStageState[] yazar, get_status döndürür.

Kanıt: FE StageTimeline'ın çıplak çark yerine gerçek aşama listesi alması.
  - _StageTracker birim: stage'ler sırayla queued→running→completed dolar.
  - run_pipeline (consent-allowed) → her aşama sırayla persist edilir (history).
  - consent-blocked → run_reviewer_council 'skipped' (external AI yok).
  - get_status → row.stages'i ReviewStageState[] olarak döndürür.

Tüm ağır aşamalar monkeypatch'lenir (ağ/LLM YOK) — test_review_pipeline_v2 deseni.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from api.models.review import (
    CitationIntegritySummary,
    DocumentClassification,
    Finding,
    Manuscript,
    ManuscriptAnchor,
    ManuscriptMeta,
    PrivacyConfig,
    ReviewProvenance,
    ReviewReport,
)
from engine.academic._engine_base import EngineResult

pytestmark = pytest.mark.unit

_FULL_TEXT = (
    "We used a randomized controlled trial design to evaluate the intervention. "
    "Methods and results are reported below."
)


def _manuscript() -> Manuscript:
    return Manuscript(
        meta=ManuscriptMeta(
            title="A Study",
            section_titles=["Introduction", "Methods", "Results", "Discussion"],
            word_count=2000,
            reference_count=10,
        ),
        full_text=_FULL_TEXT,
    )


def _engine_findings() -> EngineResult:
    f = Finding(
        finding_id="method.f0",
        dimension="methodology_fit",
        severity="major",
        confidence=0.8,
        title="Methodology under-justified",
        manuscript_anchors=[
            ManuscriptAnchor(
                anchor_id="raw.q0",
                section="Methods",
                quote="randomized controlled trial design",
            )
        ],
        action_item_ids=["method.f0.a0"],
    )
    from api.models.review import ActionItem

    return EngineResult(
        findings=[f],
        action_items=[
            ActionItem(
                action_id="method.f0.a0",
                priority="P0",
                instruction="Add a justification.",
                linked_finding_ids=["method.f0"],
            )
        ],
    )


def _orch_report() -> ReviewReport:
    return ReviewReport(
        mode="author",
        language="en",
        manuscript_meta=_manuscript().meta,
        summary="s",
        overall_assessment="o",
        verdict="major_revision",
        provenance=ReviewProvenance(
            model_used="spy",
            persona_version="v",
            engine_version="f14-s4",
            generated_at=datetime.now(UTC),
        ),
    )


def _patch_pipeline(monkeypatch, svc, *, stage_history: list[list[dict]]):
    """Ağ/LLM yok; stages yazımlarının HER snapshot'ını history'e kaydet."""

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(svc, "_set_step", _noop)

    import engine.ingestion as ing

    monkeypatch.setattr(ing, "parse_document", lambda *a, **k: _manuscript())

    async def _resolve_all(refs):
        return ([], CitationIntegritySummary())

    async def _empty(*a, **k):
        return []

    monkeypatch.setattr(svc.review_citation_service, "resolve_all", _resolve_all)
    monkeypatch.setattr(svc.review_citation_service, "check_context", _empty)
    monkeypatch.setattr(svc.review_citation_service, "find_coverage_gaps", _empty)
    monkeypatch.setattr(svc, "_stat_findings", lambda t: [])

    async def _classify(*a, **k):
        return DocumentClassification(
            document_type="journal_article",
            study_design="quantitative",
        )

    monkeypatch.setattr(svc.academic_classifier, "classify_document", _classify)

    async def _assess(*a, **k):
        return _engine_findings()

    monkeypatch.setattr(svc, "assess_manuscript", _assess)

    async def _orch(*a, **k):
        return _orch_report()

    monkeypatch.setattr(svc.review_orchestration, "run_orchestration", _orch)

    async def _capture_update(job_id, **fields):
        if "stages" in fields:
            stage_history.append(fields["stages"])

    monkeypatch.setattr(svc, "_update", _capture_update)


# --- _StageTracker birim -----------------------------------------------------


def test_stage_tracker_fills_in_order() -> None:
    from api.services.review_service import _PIPELINE_STAGES, _StageTracker

    t = _StageTracker()
    dumped = t.dump()
    assert [s["stage"] for s in dumped] == list(_PIPELINE_STAGES)
    assert all(s["status"] == "queued" for s in dumped)

    for stage in _PIPELINE_STAGES:
        t.start(stage)
        running = {s["stage"]: s["status"] for s in t.dump()}
        assert running[stage] == "running"
        t.complete(stage)
        done = {s["stage"]: s["status"] for s in t.dump()}
        assert done[stage] == "completed"

    final = t.dump()
    assert all(s["status"] == "completed" for s in final)
    # sıralama korunur
    assert [s["stage"] for s in final] == list(_PIPELINE_STAGES)


def test_stage_tracker_degrade_and_skip_and_fail() -> None:
    from api.services.review_service import _StageTracker

    t = _StageTracker()
    t.start("retrieve_evidence")
    t.degrade("retrieve_evidence", reason="coverage:openalex_unavailable")
    by = {s["stage"]: s for s in t.dump()}
    assert by["retrieve_evidence"]["status"] == "degraded"
    assert by["retrieve_evidence"]["degraded_reason"] == "coverage:openalex_unavailable"

    t.skip("run_reviewer_council", reason="external_ai_blocked")
    by = {s["stage"]: s for s in t.dump()}
    assert by["run_reviewer_council"]["status"] == "skipped"

    t.start("build_report")
    t.fail_running("RuntimeError")
    by = {s["stage"]: s for s in t.dump()}
    assert by["build_report"]["status"] == "failed"
    assert by["build_report"]["error_code"] == "RuntimeError"


# --- run_pipeline E2E (stages sırayla dolar) --------------------------------


@pytest.mark.asyncio
async def test_pipeline_emits_stages_in_order(monkeypatch) -> None:
    from api.services import review_service as svc

    history: list[list[dict]] = []
    _patch_pipeline(monkeypatch, svc, stage_history=history)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="author", language="en",
        privacy=PrivacyConfig(external_ai_consent="allowed"),
    )

    assert history, "hiç stages yazılmadı"
    final = history[-1]
    assert [s["stage"] for s in final] == list(svc._PIPELINE_STAGES)
    # tüm aşamalar tamamlandı (consent allowed → council da koştu)
    assert all(s["status"] == "completed" for s in final), final

    # Her aşamanın 'running' snapshot'ı, 'completed' snapshot'ından ÖNCE gelir
    # (sırayla doldu). İlk 'running' index < ilk 'completed' index.
    def first_idx(stage: str, status: str) -> int:
        for i, snap in enumerate(history):
            by = {s["stage"]: s["status"] for s in snap}
            if by.get(stage) == status:
                return i
        return -1

    prev_completed = -1
    for stage in svc._PIPELINE_STAGES:
        r = first_idx(stage, "running")
        c = first_idx(stage, "completed")
        assert r != -1 and c != -1, f"{stage} running/completed yazılmadı"
        assert r < c, f"{stage}: running, completed'den sonra"
        assert c > prev_completed, f"{stage} sıra dışı tamamlandı"
        prev_completed = c


@pytest.mark.asyncio
async def test_blocked_path_skips_council_stage(monkeypatch) -> None:
    from api.services import review_service as svc

    history: list[list[dict]] = []
    _patch_pipeline(monkeypatch, svc, stage_history=history)

    # consent blocked → assess external AI'sız, council ATLANIR
    async def _assess_blocked(*a, **k):
        return EngineResult(degraded=["qualitative_engine:external_ai_blocked"])

    monkeypatch.setattr(svc, "assess_manuscript", _assess_blocked)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="editor", language="tr",
        privacy=PrivacyConfig(
            confidentiality_mode="reviewer_confidential",
            external_ai_consent="blocked",
        ),
    )

    final = history[-1]
    by = {s["stage"]: s for s in final}
    assert by["run_reviewer_council"]["status"] == "skipped"
    assert by["run_reviewer_council"]["degraded_reason"]
    # akademik motor degraded sinyaliyle → 'degraded'
    assert by["run_academic_engines"]["status"] == "degraded"
    assert by["build_report"]["status"] == "completed"


# --- get_status stages döndürür ---------------------------------------------


@pytest.mark.asyncio
async def test_get_status_returns_stages(monkeypatch) -> None:
    from api.services import review_service as svc

    job_id = uuid4()
    stages_blob = [
        {"stage": "parse_document", "status": "completed", "progress": 1.0,
         "started_at": None, "completed_at": None, "error_code": None,
         "degraded_reason": None, "summary": None},
        {"stage": "classify", "status": "running", "progress": 0.0,
         "started_at": None, "completed_at": None, "error_code": None,
         "degraded_reason": None, "summary": None},
    ]

    async def _row(jid):
        return {"job_id": str(job_id), "user_id": "u", "status": "parsing",
                "progress": 0.1, "step_label": "x", "stages": stages_blob}

    monkeypatch.setattr(svc, "_fetch_job", _row)

    res = await svc.get_status("u", job_id)
    assert [s.stage for s in res.stages] == ["parse_document", "classify"]
    assert res.stages[0].status == "completed"
    assert res.stages[1].status == "running"


@pytest.mark.asyncio
async def test_get_status_empty_stages_when_absent(monkeypatch) -> None:
    """Eski/boş satır (stages kolonu yok) → [] (additive, kırılmaz)."""
    from api.services import review_service as svc

    job_id = uuid4()

    async def _row(jid):
        return {"job_id": str(job_id), "user_id": "u", "status": "done",
                "progress": 1.0, "step_label": "ok"}

    monkeypatch.setattr(svc, "_fetch_job", _row)

    res = await svc.get_status("u", job_id)
    assert res.stages == []
