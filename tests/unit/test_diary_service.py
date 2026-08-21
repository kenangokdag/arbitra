"""F13-S1-P002+P004 — diary_service unit tests.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3
Strateji: supabase_call_async monkeypatch override → Supabase çağrısı bypass;
servisin kendi mantığı (model_validate, cursor, sahiplik filtresi, pre-advisor
LLM çağrısı) test edilir.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.models.diary import DiaryEventCreate, DiaryEventPatch
from api.models.llm import LLMResponse
from api.services import diary_service

pytestmark = pytest.mark.unit


def _row(**overrides: Any) -> dict[str, Any]:
    """Tam bir project_event satırı — override'lara açık fixture."""
    base = {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "user_id": str(uuid4()),
        "page_slug": "S1_arastirma_defteri",
        "paper_id": None,
        "event_type": "kayit",
        "payload": {"note": "test"},
        "created_at": datetime.now(UTC).isoformat(),
        "resolved_at": None,
    }
    base.update(overrides)
    return base


def _patch_supabase(
    monkeypatch: pytest.MonkeyPatch, *, data: list[dict[str, Any]]
) -> None:
    """Servis Supabase çağrısını sabit response ile değiştir."""

    async def _fake_call(
        _fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        return SimpleNamespace(data=data)

    monkeypatch.setattr(diary_service, "supabase_call_async", _fake_call)
    monkeypatch.setattr(diary_service, "get_supabase_admin", lambda: SimpleNamespace())


# ── Test 1: insert_event happy path ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_insert_event_happy(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    inserted = _row(user_id=str(user_id), event_type="kayit")
    _patch_supabase(monkeypatch, data=[inserted])

    payload = DiaryEventCreate(
        project_id=uuid4(),
        page_slug="5.1_yayin_formati",
        event_type="kayit",
        payload={"note": "format kararı"},
    )
    event = await diary_service.insert_event(user_id, payload)

    assert str(event.user_id) == str(user_id)
    assert event.event_type == "kayit"


# ── Test 2: invalid event_type → Pydantic ValidationError ────────────────────
def test_event_type_literal_rejects_unknown() -> None:
    with pytest.raises(Exception) as exc:
        DiaryEventCreate(
            project_id=uuid4(),
            page_slug="x",
            event_type="bogus",  # type: ignore[arg-type]
            payload={},
        )
    assert "event_type" in str(exc.value).lower() or "literal" in str(exc.value).lower()


# ── Test 3: list_timeline kısa sayfa → next_cursor None ──────────────────────
@pytest.mark.asyncio
async def test_list_timeline_short_page_no_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    rows = [_row(user_id=str(user_id)) for _ in range(3)]
    _patch_supabase(monkeypatch, data=rows)

    resp = await diary_service.list_timeline(user_id, project_id=uuid4())

    assert resp.count == 3
    assert resp.next_cursor is None


# ── Test 4: list_timeline tam sayfa → next_cursor son created_at ─────────────
@pytest.mark.asyncio
async def test_list_timeline_full_page_emits_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    base = datetime.now(UTC)
    rows = [
        _row(user_id=str(user_id), created_at=(base - timedelta(minutes=i)).isoformat())
        for i in range(50)
    ]
    _patch_supabase(monkeypatch, data=rows)

    resp = await diary_service.list_timeline(user_id)

    assert resp.count == 50
    assert resp.next_cursor is not None
    assert resp.next_cursor == resp.items[-1].created_at.isoformat()


# ── Test 5: patch_event ownership fail → LookupError ─────────────────────────
@pytest.mark.asyncio
async def test_patch_event_not_owned_raises_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase(monkeypatch, data=[])  # update returned 0 rows

    with pytest.raises(LookupError):
        await diary_service.patch_event(
            uuid4(), uuid4(), DiaryEventPatch(payload={"new": "x"})
        )


# ── Test 6: patch_event boş body → ValueError ────────────────────────────────
@pytest.mark.asyncio
async def test_patch_event_empty_body_raises_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase(monkeypatch, data=[_row()])

    with pytest.raises(ValueError, match="boş"):
        await diary_service.patch_event(uuid4(), uuid4(), DiaryEventPatch())


# ── Test 7: pre-advisor 0 olay → LLM çağırılmaz, default mesaj ───────────────
@pytest.mark.asyncio
async def test_summarize_pre_advisor_empty_skips_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase(monkeypatch, data=[])
    llm_called = {"count": 0}

    async def _spy_llm(*_a: Any, **_kw: Any) -> LLMResponse:
        llm_called["count"] += 1
        raise AssertionError("LLM 0 olayda çağrılmamalı")

    monkeypatch.setattr(diary_service, "llm_call", _spy_llm)

    resp = await diary_service.summarize_pre_advisor(uuid4(), uuid4())

    assert resp.event_count == 0
    assert "kayıt bulunmuyor" in resp.summary
    assert llm_called["count"] == 0
    # period_end > period_start ve aralık ≈ 30 gün
    delta_days = (resp.period_end - resp.period_start).days
    assert 29 <= delta_days <= 30


# ── Test 8: pre-advisor olay varsa LLM çağrılır, summary text döner ──────────
@pytest.mark.asyncio
async def test_summarize_pre_advisor_calls_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        _row(
            page_slug="4.2_bosluk_profili",
            event_type="kayit",
            payload={"note": "M5 boşluğunu işaretledim"},
            created_at=(datetime.now(UTC) - timedelta(days=10)).isoformat(),
        ),
        _row(
            page_slug="5.2_yayin_taslagi",
            event_type="not",
            payload={"note": "3 RQ taslağı"},
            created_at=(datetime.now(UTC) - timedelta(days=2)).isoformat(),
        ),
    ]
    _patch_supabase(monkeypatch, data=rows)

    captured: dict[str, Any] = {}

    async def _fake_llm(prompt: str, **kwargs: Any) -> LLMResponse:
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return LLMResponse(
            text="Bu ay 4.2 boşluk profilinde M5'i işaretledin, 5.2'de 3 RQ kurdun. "
            "Danışmanına gitmeden bu 2 noktayı netleştirmek isteyebilirsin.",
            parsed_output=None,
            model_used="gemini-flash-tr",
            tokens_in=120,
            tokens_out=60,
            latency_ms=540,
        )

    monkeypatch.setattr(diary_service, "llm_call", _fake_llm)

    resp = await diary_service.summarize_pre_advisor(uuid4(), uuid4())

    assert resp.event_count == 2
    assert "M5" in resp.summary
    assert captured["kwargs"]["mode"] == "diary_pre_advisor"
    assert captured["kwargs"]["tier"] == "flash"
    # event satırları prompt'a girdi mi (page_slug + event_type)
    assert "4.2_bosluk_profili" in captured["prompt"]
    assert "5.2_yayin_taslagi" in captured["prompt"]
