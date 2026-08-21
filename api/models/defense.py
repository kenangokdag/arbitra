"""F13-S7 6.2 Savunma Formatı — Pydantic schemas (defense_session tablosu).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S7
Migration: db/migrations/0028_defense_session.sql
RTF: Page_Design/Sayfa_Plani_v2/6.2_savunma_formati.rtf §Plan-Detayı

Endpoints:
  - POST /api/workshop/defense/session            → oturum upsert
  - POST /api/workshop/defense/generate-questions → Gemini Pro soru havuzu
  - GET  /api/workshop/defense/suggest-jury       → havuzdan otomatik jüri

HK-1: Pydantic ConfigDict(extra="forbid") tüm modellerde.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# 0028_defense_session.sql:48 CHECK constraint
SessionType = Literal["makale", "tez", "yeterlilik", "bildiri"]

# RTF §Plan-Detayı (3) — soru kategorileri
QuestionCategory = Literal[
    "method", "contribution", "limitation", "ethics", "field_specific"
]

# 0028:54 CHECK (preferred_lang IN ('tr','en'))
DefenseLang = Literal["tr", "en"]


class FoundPaper(BaseModel):
    """OpenAlex'ten veya havuzdan bulunan jüri üyesi paper'ı."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str
    year: int | None = None
    cited_by: int | None = None


class JuryMember(BaseModel):
    """Tek jüri üyesi metadata + paper listesi.

    `generic_fallback`: OpenAlex match yok veya isim verilmemiş → True.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=200)
    affiliation: str | None = None
    field: str = Field(..., min_length=1, max_length=200)
    orcid: str | None = None
    openalex_author_id: str | None = None
    found_papers: list[FoundPaper] = Field(default_factory=list, max_length=20)
    generic_fallback: bool = False


class DefenseQuestion(BaseModel):
    """Üretilmiş soru — 2-derinlik zincir Stanford-style."""

    model_config = ConfigDict(extra="forbid")

    jury_member_index: int = Field(..., ge=0, le=6)
    category: QuestionCategory
    question: str = Field(..., min_length=5, max_length=600)
    depth: int = Field(..., ge=1, le=2)
    source_paper_id: str | None = None
    follow_up_questions: list[str] = Field(default_factory=list, max_length=4)


class DefenseSessionUpsert(BaseModel):
    """POST /api/workshop/defense/session body — oturum yarat veya güncelle.

    `session_id` verilmezse yeni satır; verilirse mevcut güncellenir.
    Sahiplik service tarafında doğrulanır (projects.user_id JOIN).
    """

    model_config = ConfigDict(extra="forbid")

    session_id: UUID | None = None
    project_id: UUID
    session_type: SessionType
    scheduled_date: date | None = None
    jury_size: int = Field(..., ge=1, le=7)
    title: str = Field(..., min_length=1, max_length=400)
    field: str = Field(..., min_length=1, max_length=200)
    preferred_lang: DefenseLang = "tr"
    jury_members: list[JuryMember] = Field(default_factory=list, max_length=7)


class DefenseSession(BaseModel):
    """defense_session satırının tam response biçimi."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID
    session_type: SessionType
    scheduled_date: date | None = None
    jury_size: int
    title: str
    field: str
    preferred_lang: DefenseLang
    jury_members: list[JuryMember]
    question_pool: list[DefenseQuestion]
    created_at: datetime
    updated_at: datetime


class GenerateQuestionsRequest(BaseModel):
    """POST /api/workshop/defense/generate-questions body."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    jury_member_index: int = Field(..., ge=0, le=6)


class GenerateQuestionsResponse(BaseModel):
    """Yeni üretilen soru listesi + güncel toplam üretim sayısı."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    jury_member_index: int
    questions: list[DefenseQuestion]
    total_pool_size: int


class JurySuggestion(BaseModel):
    """suggest-jury sonucundan tek yazar önerisi (havuzdan)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    affiliation: str | None = None
    paper_count: int = Field(..., ge=1)
    total_citations: int = Field(..., ge=0)
    top_paper_ids: list[str] = Field(..., min_length=1, max_length=3)


class SuggestJuryResponse(BaseModel):
    """GET /api/workshop/defense/suggest-jury response."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    field: str
    suggestions: list[JurySuggestion] = Field(..., max_length=5)


class DefenseQuestionsLLMOutput(BaseModel):
    """Gemini Pro structured output container — generate-questions."""

    model_config = ConfigDict(extra="forbid")

    questions: list[DefenseQuestion] = Field(..., min_length=8, max_length=12)


__all__ = [
    "DefenseLang",
    "DefenseQuestion",
    "DefenseQuestionsLLMOutput",
    "DefenseSession",
    "DefenseSessionUpsert",
    "FoundPaper",
    "GenerateQuestionsRequest",
    "GenerateQuestionsResponse",
    "JuryMember",
    "JurySuggestion",
    "QuestionCategory",
    "SessionType",
    "SuggestJuryResponse",
]
