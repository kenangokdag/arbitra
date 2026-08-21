"""F13-S13 S2 Proje Tamamlama — Pydantic schemas.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S13
RTF:  Page_Design/Sayfa_Plani_v2/S2_proje_tamamlama.rtf

Endpoints:
  - POST /api/completion/snapshot           → snapshot oluştur + LLM özet
  - POST /api/feedback/project-completion   → 5-soru feedback yaz
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

StepStatus = Literal["basarili", "gelistirilmeli"]


class StepReview(BaseModel):
    """Tek adımın değerlendirilmesi (rozet + skor + LLM yorum)."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(..., max_length=80)
    label: str = Field(..., max_length=120)
    status: StepStatus
    score: float = Field(..., ge=0.0, le=1.0)
    comment: str = Field(..., max_length=600)


class CompletionBadges(BaseModel):
    """Rozet sayaçları."""

    model_config = ConfigDict(extra="forbid")

    basarili: int = Field(..., ge=0)
    gelistirilmeli: int = Field(..., ge=0)


class CompletionSnapshot(BaseModel):
    """Tamamlama anlık çıktısı — DB'de jsonb olarak yaşar."""

    model_config = ConfigDict(extra="forbid")

    step_reviews: list[StepReview]
    badges: CompletionBadges
    graduate_advice: list[str] = Field(default_factory=list, max_length=10)
    summary_paragraph: str = Field(..., max_length=2000)


class StepReviewLLMItem(BaseModel):
    """Flash structured output — tek adım yorumu."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(..., max_length=80)
    comment: str = Field(..., max_length=600)


class StepReviewLLMOutput(BaseModel):
    """Flash structured output container."""

    model_config = ConfigDict(extra="forbid")

    reviews: list[StepReviewLLMItem] = Field(..., min_length=1, max_length=15)
    summary_paragraph: str = Field(..., max_length=2000)


# ── HTTP I/O ────────────────────────────────────────────────────────────────


class SnapshotRequest(BaseModel):
    """POST /api/completion/snapshot body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID


class SnapshotResponse(BaseModel):
    """Snapshot persist + return."""

    model_config = ConfigDict(extra="forbid")

    completion_id: UUID
    project_id: UUID
    completed_at: datetime
    snapshot: CompletionSnapshot
    delete_after: datetime


class CompletionFeedback(BaseModel):
    """5-soru kullanıcı geri-bildirimi (RTF: konu önerisi, süreç, eksiklikler,
    genel tatmin, NPS)."""

    model_config = ConfigDict(extra="forbid")

    topic_suggestion_rating: int = Field(..., ge=1, le=5)
    process_rating: int = Field(..., ge=1, le=5)
    missing_features: str = Field(..., max_length=2000)
    overall_satisfaction: int = Field(..., ge=1, le=5)
    nps: int = Field(..., ge=0, le=10)


class FeedbackRequest(BaseModel):
    """POST /api/feedback/project-completion body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    feedback: CompletionFeedback


class FeedbackResponse(BaseModel):
    """Feedback persist + return."""

    model_config = ConfigDict(extra="forbid")

    completion_id: UUID
    project_id: UUID
    feedback: CompletionFeedback
    updated_at: datetime


__all__ = [
    "CompletionBadges",
    "CompletionFeedback",
    "CompletionSnapshot",
    "FeedbackRequest",
    "FeedbackResponse",
    "SnapshotRequest",
    "SnapshotResponse",
    "StepReview",
    "StepReviewLLMItem",
    "StepReviewLLMOutput",
    "StepStatus",
]
