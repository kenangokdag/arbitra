"""F13-S11 3.4 Literatür Sentezi — Pydantic schemas.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTF: Page_Design/Sayfa_Plani_v2/3.4_literatur_sentezi.rtf §Plan-Detayı

POST /api/workshop/synthesize
- 1..25 paper_ids → akademik literatür sentezi (Gemini Pro)
- 3 mode: neutral / critical / short
- Cümle-bazlı faithfulness rozeti (green/yellow/red)
- Tema dağılımı %80 üzeri ise theme_warning
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SynthesizeMode = Literal["neutral", "critical", "short"]
SynthesisFlag = Literal["green", "yellow", "red"]
SynthesisLang = Literal["tr", "en", "id"]


class SynthesizeRequest(BaseModel):
    """POST /api/workshop/synthesize body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    paper_ids: list[str] = Field(..., min_length=1, max_length=25)
    mode: SynthesizeMode = "neutral"
    lang: SynthesisLang | None = None


class SynthesisSentence(BaseModel):
    """Tek cümle + faithfulness değerlendirmesi."""

    model_config = ConfigDict(extra="forbid")

    text: str
    citations: list[str]
    faithfulness_score: float = Field(..., ge=0.0, le=1.0)
    flag: SynthesisFlag


class SynthesisReference(BaseModel):
    """Numaralı kaynak listesi entry."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(..., ge=1)
    paper_id: str
    citation: str


class SynthesizeResponse(BaseModel):
    """POST /api/workshop/synthesize response."""

    model_config = ConfigDict(extra="forbid")

    synthesis_text: str
    sentences: list[SynthesisSentence]
    references: list[SynthesisReference]
    total_faithfulness: float = Field(..., ge=0.0, le=1.0)
    theme_warning: str | None = None
    mode: SynthesizeMode
    lang: SynthesisLang


class SynthesisLLMSentence(BaseModel):
    """LLM structured output cümle entry — citation_indices 1-tabanlı."""

    model_config = ConfigDict(extra="forbid")

    text: str
    citation_indices: list[int] = Field(..., min_length=1)


class SynthesisLLMOutput(BaseModel):
    """LLM structured output container."""

    model_config = ConfigDict(extra="forbid")

    sentences: list[SynthesisLLMSentence]


__all__ = [
    "SynthesisFlag",
    "SynthesisLLMOutput",
    "SynthesisLLMSentence",
    "SynthesisLang",
    "SynthesisReference",
    "SynthesisSentence",
    "SynthesizeMode",
    "SynthesizeRequest",
    "SynthesizeResponse",
]
