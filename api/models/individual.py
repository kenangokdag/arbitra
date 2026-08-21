"""F13-S8 6.3 Bireysel Kontrol — Pydantic schemas.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S8
RTF:  Page_Design/Sayfa_Plani_v2/6.3_bireysel_kontrol.rtf §Plan-Detayı

Endpoints:
  - GET  /api/workshop/checklist?doc_type=&lang=          → static JSON
  - PUT  /api/workshop/individual-check                   → cevap kaydı
  - GET  /api/workshop/journal-suggest                    → V1 placeholder
  - POST /api/workshop/personal-feedback                  → Flash 1 paragraf
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DocType = Literal["makale", "tez"]
ChecklistLang = Literal["tr", "en"]
ChecklistResponse = Literal["evet", "hayir", "yapamadim"]


class ChecklistItem(BaseModel):
    """engine/checklist JSON'larındaki tek madde."""

    model_config = ConfigDict(extra="forbid")

    id: str
    soru: str
    aciklama: str
    evet_metin: str
    hayir_metin: str
    yapamadim_metin: str
    kritik: bool = False
    link: str | None = None


class ChecklistCategory(BaseModel):
    """Bir kategori (örn. Etik Kurul) altında madde grubu."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    items: list[ChecklistItem]


class ChecklistResponseModel(BaseModel):
    """GET /api/workshop/checklist response."""

    model_config = ConfigDict(extra="forbid")

    version: str
    language: ChecklistLang
    doc_type: DocType
    note: str | None = None
    categories: list[ChecklistCategory]


class IndividualCheckEntry(BaseModel):
    """defense_session.individual_check listesindeki tek kayıt."""

    model_config = ConfigDict(extra="forbid")

    checklist_id: str
    item_id: str
    response: ChecklistResponse
    noted_at: datetime


class IndividualCheckUpsert(BaseModel):
    """PUT /api/workshop/individual-check body — tek cevap kaydı."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    checklist_id: str = Field(..., min_length=1, max_length=100)
    item_id: str = Field(..., min_length=1, max_length=100)
    response: ChecklistResponse


class IndividualCheckResponse(BaseModel):
    """PUT response — güncel sayım + skor (kritik kapı dahil)."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    total_items_answered: int = Field(..., ge=0)
    evet_count: int = Field(..., ge=0)
    hayir_count: int = Field(..., ge=0)
    yapamadim_count: int = Field(..., ge=0)
    critical_blocked: bool


class JournalSuggestion(BaseModel):
    """journal-suggest yanıt entry'si — v1 placeholder."""

    model_config = ConfigDict(extra="forbid")

    journal_id: str
    name: str
    indices: list[str] = Field(default_factory=list, max_length=8)
    sjr_quartile: str | None = None
    scope_match: float | None = Field(default=None, ge=0.0, le=1.0)
    source: Literal["dim_journal", "hf_dergitarama", "seed_json"]


class JournalSuggestResponse(BaseModel):
    """GET /api/workshop/journal-suggest yanıtı."""

    model_config = ConfigDict(extra="forbid")

    journals: list[JournalSuggestion] = Field(default_factory=list, max_length=5)
    source_attribution: list[str] = Field(default_factory=list)
    fallback_used: bool


class PersonalFeedbackRequest(BaseModel):
    """POST /api/workshop/personal-feedback body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    session_id: UUID
    doc_type: DocType
    lang: ChecklistLang = "tr"
    manuscript_summary: str | None = Field(default=None, max_length=4000)


class PersonalFeedbackResponse(BaseModel):
    """Flash 1 paragraf yorum."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    feedback_paragraph: str = Field(..., min_length=20, max_length=2000)
    weak_areas: list[str] = Field(default_factory=list, max_length=10)


class PersonalFeedbackLLMOutput(BaseModel):
    """Flash structured output container."""

    model_config = ConfigDict(extra="forbid")

    feedback_paragraph: str = Field(..., min_length=20, max_length=2000)
    weak_areas: list[str] = Field(default_factory=list, max_length=10)


__all__ = [
    "ChecklistCategory",
    "ChecklistItem",
    "ChecklistLang",
    "ChecklistResponse",
    "ChecklistResponseModel",
    "DocType",
    "IndividualCheckEntry",
    "IndividualCheckResponse",
    "IndividualCheckUpsert",
    "JournalSuggestResponse",
    "JournalSuggestion",
    "PersonalFeedbackLLMOutput",
    "PersonalFeedbackRequest",
    "PersonalFeedbackResponse",
]
