"""F13-S1 Araştırma Defteri — Pydantic schemas (project_event tablosu).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S1-P002
Migration: db/migrations/0029_project_event.sql
HK-1 Pydantic gate: extra="forbid" tüm modellerde.
HK-4 Runtime assertion: event_type Literal sınırlaması (CHECK ile birebir).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# kaynak: 0029_project_event.sql:43 CHECK (event_type IN (...))
EventType = Literal["kayit", "danismana_sor", "kutuphane_ekle", "not"]


class DiaryEventCreate(BaseModel):
    """POST /api/diary/event body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    page_slug: str = Field(..., min_length=1, max_length=100)
    paper_id: str | None = Field(default=None, max_length=64)
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)


class DiaryEventPatch(BaseModel):
    """PATCH /api/diary/event/{id} body — partial update.

    `resolved_at`: explicit None = "Geri aç" (resolved → unresolved).
    `resolved_at` field unset = değişiklik yok.
    """

    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any] | None = None
    resolved_at: datetime | None = None


class DiaryEvent(BaseModel):
    """Tek satır project_event."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID
    user_id: UUID
    page_slug: str
    paper_id: str | None = None
    event_type: EventType
    payload: dict[str, Any]
    created_at: datetime
    resolved_at: datetime | None = None


class DiaryTimelineResponse(BaseModel):
    """GET /api/diary/timeline response. Cursor-based pagination."""

    model_config = ConfigDict(extra="forbid")

    items: list[DiaryEvent]
    next_cursor: str | None = None
    count: int


class DiaryPreAdvisorRequest(BaseModel):
    """POST /api/diary/pre-advisor-summary body. Lookback son 30 gün sabit
    (Sayfa_Plani_v2/S1 §4 — danışman öncesi defter özeti felsefesi)."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID


class DiaryPreAdvisorResponse(BaseModel):
    """Tek paragraf özet (Gemini Flash) + meta. event_count=0 ise summary
    LLM'siz default cümle (prompt yasakları gereği)."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    event_count: int
    period_start: datetime
    period_end: datetime


__all__ = [
    "DiaryEvent",
    "DiaryEventCreate",
    "DiaryEventPatch",
    "DiaryPreAdvisorRequest",
    "DiaryPreAdvisorResponse",
    "DiaryTimelineResponse",
    "EventType",
]
