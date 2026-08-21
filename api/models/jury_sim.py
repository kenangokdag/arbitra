"""F13-S10 6.5 Jüri Simülasyonu — Pydantic schemas.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S10
RTF:  Page_Design/Sayfa_Plani_v2/6.5_juri_simulasyonu.rtf §Plan-Detayı

Endpoints:
  - POST /api/defense/jury-question        → 5 persona paralel Flash
  - POST /api/defense/hyde-fanout-rerank   → HyDE + Pinecone fanout + RRF + rerank
  - POST /api/defense/answer-score         → bge-m3 embed + multi-dim rubric
  - POST /api/defense/consistency-check    → Flash second-pass çelişen cevap çiftleri
  - POST /api/defense/jury-decision-band   → weighted_score → kabul/minor/major/red
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from api.models.journal_sim import Verdict

JuryPersonaKey = Literal[
    "canli", "anti_tez", "yontemci", "dis_disiplin", "pratisyen"
]
JuryReaction = Literal["satisfied", "probing", "dissatisfied"]
JuryLang = Literal["tr", "en"]


# ── 1) jury-question ────────────────────────────────────────────────────────


class JuryQuestion(BaseModel):
    """Tek jüri sorusu (zincir derinlik max 2)."""

    model_config = ConfigDict(extra="forbid")

    persona: JuryPersonaKey
    idx: int = Field(..., ge=0)
    text: str = Field(..., min_length=5, max_length=1000)
    depth: int = Field(..., ge=1, le=2)
    parent_idx: int | None = Field(default=None, ge=0)
    anchor: str | None = Field(default=None, max_length=200)


class JuryPersonaOutput(BaseModel):
    """Tek persona'nın Flash structured output container'ı."""

    model_config = ConfigDict(extra="forbid")

    questions: list[JuryQuestion] = Field(..., min_length=1, max_length=8)


class JuryQuestionRequest(BaseModel):
    """POST /api/defense/jury-question body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    session_id: UUID
    manuscript_text: str = Field(..., min_length=100, max_length=40000)
    lang: JuryLang = "tr"


class JuryQuestionResponse(BaseModel):
    """5 persona soruları + ilk aktif soru bilgisi."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    questions: list[JuryQuestion]
    active_idx: int = Field(..., ge=0)
    timer_seconds: int = Field(default=60, ge=10, le=300)


# ── 2) hyde-fanout-rerank ───────────────────────────────────────────────────


class HydeChunk(BaseModel):
    """Rerank top-N cümle (paper_id + chunk_idx + cümle)."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    chunk_idx: int = Field(..., ge=0)
    sentence: str = Field(..., max_length=2000)
    score: float = Field(..., ge=0.0, le=1.0)


class HydeFanoutRequest(BaseModel):
    """POST /api/defense/hyde-fanout-rerank body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    question_text: str = Field(..., min_length=5, max_length=2000)
    manuscript_text: str | None = Field(default=None, max_length=40000)
    lang: JuryLang = "tr"


class HydeFanoutResponse(BaseModel):
    """HyDE arka plan zinciri çıktısı."""

    model_config = ConfigDict(extra="forbid")

    hyde_hypotheticals: list[str] = Field(default_factory=list, max_length=10)
    rerank_top: list[HydeChunk] = Field(default_factory=list, max_length=10)
    missing_concepts: list[str] = Field(default_factory=list, max_length=20)
    fanout_used: bool
    rerank_used: bool


class HydeHypotheticalsOutput(BaseModel):
    """Flash structured output for HyDE 5-hypothetical answers."""

    model_config = ConfigDict(extra="forbid")

    hypotheticals: list[str] = Field(..., min_length=1, max_length=10)
    key_concepts: list[str] = Field(default_factory=list, max_length=15)


# ── 3) answer-score ─────────────────────────────────────────────────────────


class AnswerScoreRequest(BaseModel):
    """POST /api/defense/answer-score body."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    question_idx: int = Field(..., ge=0)
    user_answer: str = Field(..., min_length=1, max_length=10000)
    answer_seconds: int = Field(..., ge=0, le=600)
    hyde_top: list[HydeChunk] = Field(default_factory=list, max_length=10)
    hyde_hypotheticals: list[str] = Field(default_factory=list, max_length=10)
    key_concepts: list[str] = Field(default_factory=list, max_length=15)


class AnswerScoreResponse(BaseModel):
    """Multi-dim rubric çıktısı + jüri tepkisi."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    question_idx: int
    evidence_coverage: float = Field(..., ge=0.0, le=1.0)
    depth_score: float = Field(..., ge=0.0, le=1.0)
    clarity_score: float = Field(..., ge=0.0, le=1.0)
    weighted_score: float = Field(..., ge=0.0, le=1.0)
    jury_reaction: JuryReaction
    missing_concepts: list[str] = Field(default_factory=list, max_length=20)
    follow_up_triggered: bool


# ── 4) consistency-check ────────────────────────────────────────────────────


class ConsistencyConflict(BaseModel):
    """İki soru-cevap arasındaki çelişki."""

    model_config = ConfigDict(extra="forbid")

    q_idx_a: int = Field(..., ge=0)
    q_idx_b: int = Field(..., ge=0)
    conflict_text: str = Field(..., max_length=1000)


class ConsistencyOutput(BaseModel):
    """Flash structured output container."""

    model_config = ConfigDict(extra="forbid")

    conflicts: list[ConsistencyConflict] = Field(default_factory=list, max_length=20)
    summary: str = Field(..., max_length=2000)


class ConsistencyCheckRequest(BaseModel):
    """POST /api/defense/consistency-check body."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID


class ConsistencyCheckResponse(BaseModel):
    """Tutarlılık taraması yanıtı."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    conflicts: list[ConsistencyConflict] = Field(default_factory=list, max_length=20)
    summary: str = Field(..., max_length=2000)


# ── 5) jury-decision-band ───────────────────────────────────────────────────


class JuryDecisionBandRequest(BaseModel):
    """POST /api/defense/jury-decision-band body."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID


class JuryDecisionBandResponse(BaseModel):
    """Toplu kararı tahmini + güven + skor özeti."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    prediction: Verdict
    confidence: float = Field(..., ge=0.0, le=1.0)
    score_summary: dict[str, float] = Field(default_factory=dict)
    advice: str = Field(..., max_length=2000)


__all__ = [
    "AnswerScoreRequest",
    "AnswerScoreResponse",
    "ConsistencyCheckRequest",
    "ConsistencyCheckResponse",
    "ConsistencyConflict",
    "ConsistencyOutput",
    "HydeChunk",
    "HydeFanoutRequest",
    "HydeFanoutResponse",
    "HydeHypotheticalsOutput",
    "JuryDecisionBandRequest",
    "JuryDecisionBandResponse",
    "JuryLang",
    "JuryPersonaKey",
    "JuryPersonaOutput",
    "JuryQuestion",
    "JuryQuestionRequest",
    "JuryQuestionResponse",
    "JuryReaction",
]
