"""F3b /api/chat Pydantic schemas — skeleton (B-018, F8 DM-LLM-7/8).

HK-1: extra=forbid; HK-2: TODO marker P020 SSE Cosmos endpoint Sercan handoff.

F8: mode + project_id + page_state alanları AdvisorButton + ROLE_MODULES için eklendi.

DANISMAN_REPORT_GROUNDING_PERSONA_2026-08-16: report_id eklendi — Danışman panelinin
incelenen makalenin hakem raporuna (Finding/verdict/risk_radar/citation_integrity)
bağlanması için. paper_context_ids'ten KASITLI AYRI: o dış-kaynak (OpenAlex) literatür
meta'sı taşır, report_id kullanıcının KENDİ incelettiği makalenin raporunu (sahip-kapsamlı,
review_service.get_report üzerinden) taşır.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

LanguageCode = Literal["tr", "en", "id"]


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1, max_length=64)
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)
    language: LanguageCode = "tr"
    paper_context_ids: list[str] = Field(default_factory=list, max_length=10)
    mode: str = Field(default="default", min_length=1, max_length=80)
    project_id: str | None = Field(default=None, max_length=64)
    page_state: dict[str, Any] | None = None
    report_id: UUID | None = Field(default=None)


class ChatChunk(BaseModel):
    """SSE event payload — F3b stream protokolü."""

    model_config = ConfigDict(extra="forbid")

    delta: str
    finished: bool = False
    citation_paper_ids: list[str] = Field(default_factory=list)
