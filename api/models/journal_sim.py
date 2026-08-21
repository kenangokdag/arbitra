"""F13-S9 6.4 Dergi Simülasyonu — Pydantic schemas.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S9
RTF:  Page_Design/Sayfa_Plani_v2/6.4_dergi_simulasyonu.rtf §Plan-Detayı

Endpoints:
  - POST /api/defense/reviewer-3persona   → 3 persona paralel hakem
  - POST /api/defense/statcheck           → Nuijten p-değer tutarlılık
  - GET  /api/defense/journal-calibration → review distribution + verdict tahmini
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PersonaKey = Literal["skeptik", "sempatik", "yontemci"]
Verdict = Literal["accept", "minor", "major", "reject"]
StatcheckStatus = Literal["green", "yellow", "red"]
ReviewerLang = Literal["tr", "en"]


# ── 3-persona ───────────────────────────────────────────────────────────────


class ReviewerQuestion(BaseModel):
    """Tek hakem maddesi (zincir derinlik max 2)."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=5, max_length=1000)
    depth: int = Field(..., ge=1, le=2)
    follow_up: str | None = Field(default=None, max_length=1000)
    anchor: str | None = Field(default=None, max_length=200)


class ReviewerPersonaOutput(BaseModel):
    """Bir persona'nın LLM çıktı container'ı (structured output)."""

    model_config = ConfigDict(extra="forbid")

    questions: list[ReviewerQuestion] = Field(..., min_length=1, max_length=10)


class Reviewer3PersonaRequest(BaseModel):
    """POST /api/defense/reviewer-3persona body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    session_id: UUID
    manuscript_text: str = Field(..., min_length=100, max_length=40000)
    target_journal_id: str | None = Field(default=None, max_length=200)
    lang: ReviewerLang = "tr"


class Reviewer3PersonaResponse(BaseModel):
    """3 persona paralel sonucu."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    skeptik: ReviewerPersonaOutput
    sempatik: ReviewerPersonaOutput
    yontemci: ReviewerPersonaOutput


# ── statcheck ───────────────────────────────────────────────────────────────


class StatcheckResult(BaseModel):
    """Tek p-değer çıkarımı + yeniden hesap kıyaslaması."""

    model_config = ConfigDict(extra="forbid")

    test_type: Literal["t", "F", "chi2", "r"]
    reported: dict[str, float | str] = Field(default_factory=dict)
    reported_p: float = Field(..., ge=0.0, le=1.0)
    computed_p: float = Field(..., ge=0.0, le=1.0)
    diff: float = Field(..., ge=0.0, le=1.0)
    status: StatcheckStatus
    match_text: str = Field(..., max_length=400)


class StatcheckSummary(BaseModel):
    """Sayaç şeridi."""

    model_config = ConfigDict(extra="forbid")

    total: int = Field(..., ge=0)
    green: int = Field(..., ge=0)
    yellow: int = Field(..., ge=0)
    red: int = Field(..., ge=0)


class StatcheckRequest(BaseModel):
    """POST /api/defense/statcheck body."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    manuscript_text: str = Field(..., min_length=20, max_length=80000)


class StatcheckResponse(BaseModel):
    """statcheck endpoint yanıtı."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    results: list[StatcheckResult] = Field(default_factory=list)
    summary: StatcheckSummary


# ── journal-calibration ─────────────────────────────────────────────────────


class JournalDistribution(BaseModel):
    """Dergi son N makale verdict dağılımı (yüzde, 0..1)."""

    model_config = ConfigDict(extra="forbid")

    window_size: int = Field(..., ge=1)
    accept_pct: float = Field(..., ge=0.0, le=1.0)
    major_pct: float = Field(..., ge=0.0, le=1.0)
    minor_pct: float = Field(..., ge=0.0, le=1.0)
    reject_pct: float = Field(..., ge=0.0, le=1.0)
    source: Literal["manual", "kmkarakaya_hf", "field_average_placeholder"]


class JournalCalibrationResponse(BaseModel):
    """Dergi kalibrasyon endpoint yanıtı."""

    model_config = ConfigDict(extra="forbid")

    journal_id: str | None
    journal_name: str | None
    distribution: JournalDistribution
    prediction: Verdict
    confidence: float = Field(..., ge=0.0, le=1.0)
    fallback_used: bool


__all__ = [
    "JournalCalibrationResponse",
    "JournalDistribution",
    "PersonaKey",
    "Reviewer3PersonaRequest",
    "Reviewer3PersonaResponse",
    "ReviewerLang",
    "ReviewerPersonaOutput",
    "ReviewerQuestion",
    "StatcheckRequest",
    "StatcheckResponse",
    "StatcheckResult",
    "StatcheckStatus",
    "StatcheckSummary",
    "Verdict",
]
