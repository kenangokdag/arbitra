"""F13-S2-P002 — progress_service unit tests.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3
Strateji: supabase_call_async monkeypatch override → Supabase çağrısı bypass;
maturity hesabı pure-function olarak test edilir.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.models.llm import LLMResponse
from api.models.progress import ProgressStep, ProgressUpsert
from api.services import progress_service

pytestmark = pytest.mark.unit


def _step(
    step_id: str = "discovery-1",
    status: str = "completed",
    **overrides: Any,
) -> dict[str, Any]:
    base = {
        "project_id": str(uuid4()),
        "step_id": step_id,
        "status": status,
        "completed_at": datetime.now(UTC).isoformat() if status == "completed" else None,
        "meta": {},
        "updated_at": datetime.now(UTC).isoformat(),
    }
    base.update(overrides)
    return base


def _patch_supabase(
    monkeypatch: pytest.MonkeyPatch,
    *,
    project_owner_data: list[dict[str, Any]] | None = None,
    progress_data: list[dict[str, Any]] | None = None,
    progress_upsert_data: list[dict[str, Any]] | None = None,
) -> None:
    """Sırayla iki çağrı dönecek (assert_owner + table op)."""
    call_count = {"n": 0}

    async def _fake_call(
        _fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        call_count["n"] += 1
        n = call_count["n"]
        # 1. çağrı = _assert_project_owner; 2. çağrı = list/upsert
        if n == 1:
            return SimpleNamespace(
                data=project_owner_data if project_owner_data is not None else [{"id": "x"}]
            )
        if progress_upsert_data is not None:
            return SimpleNamespace(data=progress_upsert_data)
        return SimpleNamespace(data=progress_data or [])

    monkeypatch.setattr(progress_service, "supabase_call_async", _fake_call)
    monkeypatch.setattr(
        progress_service, "get_supabase_admin", lambda: SimpleNamespace()
    )


# ── Test 1: ownership fail → LookupError ────────────────────────────────────
@pytest.mark.asyncio
async def test_assert_owner_fail_raises_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase(monkeypatch, project_owner_data=[])

    with pytest.raises(LookupError):
        await progress_service.list_steps(uuid4(), uuid4())


# ── Test 2: upsert_step status=completed → completed_at otomatik set ────────
@pytest.mark.asyncio
async def test_upsert_completed_sets_completed_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    inserted = _step(step_id="discovery-1", status="completed", project_id=str(pid))
    _patch_supabase(
        monkeypatch,
        progress_upsert_data=[inserted],
    )

    res = await progress_service.upsert_step(
        uuid4(),
        ProgressUpsert(
            project_id=pid, step_id="discovery-1", status="completed", meta={}
        ),
    )
    assert res.status == "completed"
    assert res.completed_at is not None


# ── Test 3: maturity tez tüm zorunlu → 100% + button_active ─────────────────
def test_maturity_tez_all_required_complete() -> None:
    pid = uuid4()
    rows: list[ProgressStep] = []
    for sid in progress_service._REQUIRED_STEPS["tez"]:
        rows.append(
            ProgressStep(
                project_id=pid,
                step_id=sid,
                status="completed",
                completed_at=datetime.now(UTC),
                meta={},
                updated_at=datetime.now(UTC),
            )
        )

    ui, pct, btn, req_total, req_done = progress_service._compute_maturity(rows, "tez")
    assert btn is True
    assert req_total == req_done == len(progress_service._REQUIRED_STEPS["tez"])
    # Tez zorunlu = 19 (tüm step), opsiyonel = 0 → required_pct=1.0, optional_pct=0
    # maturity = 1.0 * 0.70 + 0 * 0.30 = 70.0
    # Yalnız tez için _ALL_STEPS = 19, REQUIRED = 19 → optional_total = 0 → optional_pct = 0
    # → 70%
    assert pct == 70.0


# ── Test 4: maturity makale 6 zorunlu/13 opsiyonel — ağırlık doğru ──────────
def test_maturity_makale_partial() -> None:
    pid = uuid4()
    # 6 zorunlu hepsi tamam, opsiyonelden 0
    rows = [
        ProgressStep(
            project_id=pid,
            step_id=sid,
            status="completed",
            completed_at=datetime.now(UTC),
            meta={},
            updated_at=datetime.now(UTC),
        )
        for sid in progress_service._REQUIRED_STEPS["makale"]
    ]
    ui, pct, btn, req_total, req_done = progress_service._compute_maturity(
        rows, "makale"
    )
    assert btn is True
    assert req_total == 6
    assert req_done == 6
    # required_pct=1.0, optional_pct=0 → 1.0*70 + 0*30 = 70%
    assert pct == 70.0


# ── Test 5: maturity bildiri zorunlu eksik → button_active False ────────────
def test_maturity_bildiri_missing_required_button_inactive() -> None:
    pid = uuid4()
    # 3 zorunlu var (discovery-1, gapatlas-1, curation-4); sadece 2'sini tamamla
    rows = [
        ProgressStep(
            project_id=pid,
            step_id="discovery-1",
            status="completed",
            completed_at=datetime.now(UTC),
            meta={},
            updated_at=datetime.now(UTC),
        ),
        ProgressStep(
            project_id=pid,
            step_id="gapatlas-1",
            status="completed",
            completed_at=datetime.now(UTC),
            meta={},
            updated_at=datetime.now(UTC),
        ),
    ]
    ui, pct, btn, req_total, req_done = progress_service._compute_maturity(
        rows, "bildiri"
    )
    assert btn is False
    assert req_total == 3
    assert req_done == 2
    # ui satırlarında required True olanlar 3 olmalı
    required_ui = [s for s in ui if s.required]
    assert len(required_ui) == 3


# ── Test 6: bilinmeyen step DB'de yoksa not_started döner ───────────────────
def test_maturity_missing_db_rows_default_not_started() -> None:
    ui, pct, btn, _, _ = progress_service._compute_maturity([], "tez")
    # Tüm 19 step not_started
    assert all(s.status == "not_started" for s in ui)
    assert pct == 0.0
    assert btn is False
    # ui satır sayısı = _ALL_STEPS = 19
    assert len(ui) == len(progress_service._ALL_STEPS)


# ── Test 7: advisor-summary 0 completed → LLM çağırılmaz, default mesaj ─────
@pytest.mark.asyncio
async def test_summarize_advisor_empty_skips_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase(monkeypatch, progress_data=[])

    async def _spy_llm(*_a: Any, **_kw: Any) -> LLMResponse:
        raise AssertionError("LLM çağrılmamalıydı (tamamlanmış adım yok)")

    monkeypatch.setattr(progress_service, "llm_call", _spy_llm)

    resp = await progress_service.summarize_advisor(uuid4(), uuid4(), "tez")

    assert resp.step_count_used == 0
    assert "tamamlanmış adım bulunmadığı" in resp.summary
    assert resp.publication_type == "tez"
    assert resp.cache_hit is False


# ── Test 8: advisor-summary completed step varsa LLM çağrılır ──────────────
@pytest.mark.asyncio
async def test_summarize_advisor_calls_llm_with_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    rows = [
        _step("discovery-1", project_id=str(pid), meta={"anchor": "Eğitim teknolojisi"}),
        _step("curation-4", project_id=str(pid), meta={"note": "12 makale sentezi"}),
    ]
    _patch_supabase(monkeypatch, progress_data=rows)

    captured: dict[str, Any] = {}

    async def _fake_llm(prompt: str, **kwargs: Any) -> LLMResponse:
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return LLMResponse(
            text="Bu çalışma eğitim teknolojisi alanında konumlanmaktadır...",
            parsed_output=None,
            model_used="gemini-flash-tr",
            tokens_in=400,
            tokens_out=320,
            latency_ms=1200,
        )

    monkeypatch.setattr(progress_service, "llm_call", _fake_llm)

    resp = await progress_service.summarize_advisor(uuid4(), pid, "makale")

    assert resp.step_count_used == 2
    assert "eğitim teknolojisi" in resp.summary
    assert resp.publication_type == "makale"
    assert captured["kwargs"]["mode"] == "advisor_summary"
    assert captured["kwargs"]["tier"] == "flash"
    # body içerikleri
    assert "Yayın türü: makale" in captured["prompt"]
    assert "discovery-1" in captured["prompt"]
    assert "curation-4" in captured["prompt"]
    assert "anchor=Eğitim teknolojisi" in captured["prompt"]
