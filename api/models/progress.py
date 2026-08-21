"""F13-S2 5.1 Yayın Formatı — Pydantic schemas (project_progress tablosu).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S2-P002
Migration: db/migrations/0025_project_progress.sql
HK-1 Pydantic gate: extra="forbid" tüm modellerde.
HK-4 Runtime assertion: status + publication_type Literal sınırlaması.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# kaynak: 0025_project_progress.sql:48 CHECK (status IN (...))
ProgressStatus = Literal["not_started", "in_progress", "completed"]

# kaynak: 5.1_yayin_formati.rtf §Plan-Detayı (4) — 3 yayın türü
PublicationType = Literal["tez", "makale", "bildiri"]


class ProgressUpsert(BaseModel):
    """PUT /api/workshop/progress body — adım durumu yaz."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    step_id: str = Field(..., min_length=1, max_length=60)
    status: ProgressStatus
    meta: dict[str, Any] = Field(default_factory=dict)


class ProgressStep(BaseModel):
    """Tek satır project_progress."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    step_id: str
    status: ProgressStatus
    completed_at: datetime | None = None
    meta: dict[str, Any]
    updated_at: datetime


class MaturityStep(BaseModel):
    """Maturity response içindeki tek satır — UI checklist için zenginleştirilmiş."""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    status: ProgressStatus
    required: bool
    completed_at: datetime | None = None


class MaturityResponse(BaseModel):
    """GET /api/workshop/maturity response.

    `maturity_pct`: ağırlıklı yüzde (zorunlu %70, opsiyonel %30 — RTF §Plan (2d)).
    `button_active`: tüm zorunlu COMPLETED ise True → "Danışmana Gitmeden Evvel".
    """

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    publication_type: PublicationType
    steps: list[MaturityStep]
    maturity_pct: float = Field(..., ge=0.0, le=100.0)
    button_active: bool
    required_total: int
    required_completed: int


class AdvisorSummaryRequest(BaseModel):
    """POST /api/workshop/advisor-summary body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    publication_type: PublicationType


class AdvisorSummaryResponse(BaseModel):
    """4-5 paragraf akademik özet (Gemini Flash + prompt mühendisliği).

    `cache_hit`: 24h cache'ten geldi mi (idempotent).
    """

    model_config = ConfigDict(extra="forbid")

    summary: str
    publication_type: PublicationType
    step_count_used: int
    cache_hit: bool


__all__ = [
    "AdvisorSummaryRequest",
    "AdvisorSummaryResponse",
    "MaturityResponse",
    "MaturityStep",
    "ProgressStatus",
    "ProgressStep",
    "ProgressUpsert",
    "PublicationType",
]
