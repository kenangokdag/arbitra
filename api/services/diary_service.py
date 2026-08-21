"""F13-S1 Araştırma Defteri — Supabase CRUD service (project_event).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S1-P002 + P004
Pattern: bibliometric_service.py — get_supabase_admin + supabase_call_async.
RLS bypass + Python-level user_id filter (sahiplik garantisi).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.diary import (
    DiaryEvent,
    DiaryEventCreate,
    DiaryEventPatch,
    DiaryPreAdvisorResponse,
    DiaryTimelineResponse,
)
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_TABLE = "project_event"
_TIMELINE_PAGE = 50  # cursor-based pagination, plan §3 P003
_PRE_ADVISOR_LOOKBACK_DAYS = 30  # sayfa felsefesi: "son 30 günü özetle"
_PRE_ADVISOR_MAX_EVENTS = 100  # Gemini Flash 2K input cap (~80 char/event)
_PRE_ADVISOR_EMPTY_SUMMARY = "Son 30 günde proje defterinde kayıt bulunmuyor."


async def insert_event(user_id: UUID, payload: DiaryEventCreate) -> DiaryEvent:
    """POST /api/diary/event — insert + return."""
    db = get_supabase_admin()
    row = {
        "project_id": str(payload.project_id),
        "user_id": str(user_id),
        "page_slug": payload.page_slug,
        "paper_id": payload.paper_id,
        "event_type": payload.event_type,
        "payload": payload.payload,
    }

    def _q() -> Any:
        return db.table(_TABLE).insert(row).execute()

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    if not rows:
        raise RuntimeError(f"{_TABLE} insert returned empty")
    return DiaryEvent.model_validate(rows[0])


async def list_timeline(
    user_id: UUID,
    project_id: UUID | None = None,
    page_slug: str | None = None,
    paper_id: str | None = None,
    cursor: str | None = None,
) -> DiaryTimelineResponse:
    """GET /api/diary/timeline — cursor (created_at <) pagination, 50/sayfa."""
    db = get_supabase_admin()

    def _q() -> Any:
        q = db.table(_TABLE).select("*").eq("user_id", str(user_id))
        if project_id is not None:
            q = q.eq("project_id", str(project_id))
        if page_slug is not None:
            q = q.eq("page_slug", page_slug)
        if paper_id is not None:
            q = q.eq("paper_id", paper_id)
        if cursor is not None:
            q = q.lt("created_at", cursor)
        return q.order("created_at", desc=True).limit(_TIMELINE_PAGE).execute()

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    items = [DiaryEvent.model_validate(r) for r in rows]
    next_cursor = (
        items[-1].created_at.isoformat() if len(items) == _TIMELINE_PAGE else None
    )
    return DiaryTimelineResponse(items=items, next_cursor=next_cursor, count=len(items))


async def patch_event(
    user_id: UUID, event_id: UUID, patch: DiaryEventPatch
) -> DiaryEvent:
    """PATCH /api/diary/event/{id} — sahiplik kontrolü user_id eq filter ile.

    payload: replacement (full overwrite, JSON merge yok).
    resolved_at: model_fields_set'te varsa update (None = "Geri aç").
    """
    db = get_supabase_admin()
    updates: dict[str, Any] = {}
    if "payload" in patch.model_fields_set:
        updates["payload"] = patch.payload
    if "resolved_at" in patch.model_fields_set:
        updates["resolved_at"] = (
            patch.resolved_at.isoformat() if patch.resolved_at is not None else None
        )

    if not updates:
        raise ValueError("PATCH body boş — payload veya resolved_at gerekli")

    def _q() -> Any:
        return (
            db.table(_TABLE)
            .update(updates)
            .eq("id", str(event_id))
            .eq("user_id", str(user_id))
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    if not rows:
        raise LookupError(f"{_TABLE} {event_id} not found or not owned")
    return DiaryEvent.model_validate(rows[0])


def _format_event_line(row: dict[str, Any]) -> str:
    """Tek olayı kompakt tek satıra: '2026-04-15 [page/type] note (açık)'."""
    created = str(row.get("created_at", ""))[:10]  # ISO date kısmı
    page_slug = row.get("page_slug", "?")
    event_type = row.get("event_type", "?")
    payload = row.get("payload") or {}
    note = ""
    if isinstance(payload, dict):
        raw_note = payload.get("note")
        if isinstance(raw_note, str) and raw_note:
            note = raw_note[:120]
    state = "açık" if row.get("resolved_at") is None else "çözüldü"
    return f"- {created} [{page_slug} / {event_type}] {note} ({state})"


async def summarize_pre_advisor(
    user_id: UUID, project_id: UUID
) -> DiaryPreAdvisorResponse:
    """POST /api/diary/pre-advisor-summary — son 30 gün defter olayları
    Gemini Flash ile tek paragraf özet (Sayfa_Plani_v2/S1 §4)."""
    period_end = datetime.now(UTC)
    period_start = period_end - timedelta(days=_PRE_ADVISOR_LOOKBACK_DAYS)
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_TABLE)
            .select("page_slug,event_type,payload,created_at,resolved_at")
            .eq("user_id", str(user_id))
            .eq("project_id", str(project_id))
            .gte("created_at", period_start.isoformat())
            .order("created_at", desc=False)
            .limit(_PRE_ADVISOR_MAX_EVENTS)
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows: list[dict[str, Any]] = resp.data or []

    if not rows:
        return DiaryPreAdvisorResponse(
            summary=_PRE_ADVISOR_EMPTY_SUMMARY,
            event_count=0,
            period_start=period_start,
            period_end=period_end,
        )

    body = "Olaylar (eski → yeni):\n" + "\n".join(_format_event_line(r) for r in rows)
    # max_tokens=1500: Gemini 2.5 Flash "thinking tokens"ı tokens_out'a dahil ediyor;
    # 80-150 kelime hedef metin için thinking budget'i kapsayacak yastık gerek.
    llm_resp = await llm_call(
        prompt=body,
        tier="flash",
        mode="diary_pre_advisor",
        max_tokens=1500,
    )
    return DiaryPreAdvisorResponse(
        summary=llm_resp.text.strip(),
        event_count=len(rows),
        period_start=period_start,
        period_end=period_end,
    )


__all__ = [
    "insert_event",
    "list_timeline",
    "patch_event",
    "summarize_pre_advisor",
]
