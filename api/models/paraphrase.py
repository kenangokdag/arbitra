"""F13-S3 5.3 Akademik Dil — Pydantic schemas (paraphrase + silent learning).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S3-P002
Migration: db/migrations/0026_silent_learning.sql
HK-1 Pydantic gate: extra="forbid".
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# kaynak: 0026_silent_learning.sql:23 + RTF §Felsefe (3 dil)
Lang = Literal["tr", "en", "id"]
LangAuto = Literal["auto", "tr", "en", "id"]
SectionContext = Literal["intro", "methods", "findings", "discussion"]
Decision = Literal["accept", "reject", "edit"]
ChangeType = Literal[
    "hedge_added",
    "passive_voice",
    "definitive_removed",
    "shortened",
    "extended",
    "reorder",
    "other",
]


class ParaphraseRequest(BaseModel):
    """POST /api/workshop/paraphrase body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    document_text: str = Field(..., min_length=1, max_length=50_000)
    lang: LangAuto = "auto"
    section_context: SectionContext | None = None


class ParaphraseSentence(BaseModel):
    """Tek cümle çıktısı: orijinal + önerilen + değişim tipi + anlam-kaymasi flag."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(..., ge=0)
    original: str
    proposed: str
    change_type: ChangeType
    confidence: float = Field(..., ge=0.0, le=1.0)
    meaning_drift_risk: bool = False
    similarity: float = Field(..., ge=0.0, le=1.0)


class ParaphraseResponse(BaseModel):
    """POST /api/workshop/paraphrase response — 1 oturumun cümle listesi."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    lang: Lang
    sentences: list[ParaphraseSentence]
    total_sentences: int = Field(..., ge=0)
    meaning_drift_count: int = Field(..., ge=0)
    profile_applied: bool


class ParaphraseDecisionRequest(BaseModel):
    """POST /api/workshop/paraphrase-decision body — sessiz öğrenme log."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    sentence_index: int = Field(..., ge=0)
    sentence_original: str = Field(..., min_length=1)
    sentence_proposed: str = Field(..., min_length=1)
    decision: Decision
    edited_text: str | None = None
    lang: Lang
    section_context: SectionContext | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ParaphraseDecisionResponse(BaseModel):
    """Log INSERT teyidi."""

    model_config = ConfigDict(extra="forbid")

    logged: bool
    log_id: UUID


class StyleProfile(BaseModel):
    """Tek satır user_style_profile."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    lang: Lang
    profile: dict[str, Any]
    sample_size: int = Field(..., ge=0)
    updated_at: datetime


__all__ = [
    "ChangeType",
    "Decision",
    "Lang",
    "LangAuto",
    "ParaphraseDecisionRequest",
    "ParaphraseDecisionResponse",
    "ParaphraseRequest",
    "ParaphraseResponse",
    "ParaphraseSentence",
    "SectionContext",
    "StyleProfile",
]
