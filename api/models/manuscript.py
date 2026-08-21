"""F13-S6 6.1 Yayın İçeriği — Pydantic schemas (manuscript_section tablosu).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S6
Migration: db/migrations/0027_manuscript_section.sql
RTF: Page_Design/Sayfa_Plani_v2/6.1_yayin_icerigi_doldurma.rtf §Plan-Detayı

Endpoints:
  - GET  /api/workshop/manuscript                         → tüm 5 bölüm + gate
  - PUT  /api/workshop/manuscript/{section_type}          → içerik yaz
  - POST /api/workshop/manuscript/quality-check           → Flash ok/sahte
  - POST /api/workshop/manuscript/auto-draft              → Flash 1 paragraf

HK-1: Pydantic ConfigDict(extra="forbid") tüm modellerde.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# 0027_manuscript_section.sql:38 CHECK constraint
SectionType = Literal["intro", "methods", "findings", "discussion", "conclusion"]

# 0027_manuscript_section.sql:42 CHECK constraint (NULL = değerlendirilmedi)
QualityFlag = Literal["ok", "sahte"]


class ManuscriptSection(BaseModel):
    """Tek bölüm satırı (manuscript_section row → response)."""

    model_config = ConfigDict(extra="forbid")

    section_type: SectionType
    content: str
    word_count: int = Field(..., ge=0)
    ai_quality_flag: QualityFlag | None = None
    ai_quality_reason: str | None = None
    updated_at: datetime


class GateStatus(BaseModel):
    """Doluluk gate (3+ bölüm × 50+ kelime × ai_quality_flag != sahte)."""

    model_config = ConfigDict(extra="forbid")

    filled_count: int = Field(..., ge=0, le=5)
    gate_open: bool
    quality_blocked: bool = Field(
        ...,
        description="Doluluk yeterli ama bir bölümde 'sahte' rozeti varsa True.",
    )


class ManuscriptResponse(BaseModel):
    """GET /api/workshop/manuscript?project_id=... response."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    sections: list[ManuscriptSection]
    gate_status: GateStatus


class ManuscriptUpsert(BaseModel):
    """PUT /api/workshop/manuscript/{section_type} body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    content: str = Field(..., max_length=20_000)


class QualityCheckRequest(BaseModel):
    """POST /api/workshop/manuscript/quality-check body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    section_type: SectionType


class QualityCheckResponse(BaseModel):
    """Quality check yanıtı (flag + 1 cümle gerekçe + cache durumu)."""

    model_config = ConfigDict(extra="forbid")

    section_type: SectionType
    flag: QualityFlag
    reason: str
    cache_hit: bool


class QualityLLMOutput(BaseModel):
    """Gemini Flash structured output (1 kelime + 1 cümle)."""

    model_config = ConfigDict(extra="forbid")

    flag: QualityFlag
    reason: str = Field(..., min_length=3, max_length=300)


class AutoDraftRequest(BaseModel):
    """POST /api/workshop/manuscript/auto-draft body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    section_type: SectionType


class AutoDraftResponse(BaseModel):
    """1 paragraf taslak + hangi step çıktıları kullanıldı.

    `draft_content`: kullanıcı kabul edene kadar manuscript_section'a YAZILMAZ.
    """

    model_config = ConfigDict(extra="forbid")

    section_type: SectionType
    draft_content: str
    source_steps: list[str]


__all__ = [
    "AutoDraftRequest",
    "AutoDraftResponse",
    "GateStatus",
    "ManuscriptResponse",
    "ManuscriptSection",
    "ManuscriptUpsert",
    "QualityCheckRequest",
    "QualityCheckResponse",
    "QualityFlag",
    "QualityLLMOutput",
    "SectionType",
]
