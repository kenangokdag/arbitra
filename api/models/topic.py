"""F13-S5 5.2 Yayın Taslağı — Pydantic schemas (topic-proposals + draft-skeleton).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S5
RTF:  Page_Design/Sayfa_Plani_v2/5.2_yayin_taslagi.rtf §Plan-Detayı

POST /api/workshop/topic-proposals  — Gemini Pro: 3 gap-uyumlu konu kartı
POST /api/workshop/draft-skeleton   — Gemini Flash 4 paralel + SQL: IMRaD iskelet

HK-1: Pydantic ConfigDict(extra="forbid") tüm modellerde.
"""

from __future__ import annotations

from typing import Literal, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# RTF §Plan-Detayı (2): (1) Gap-Konu eşleşmesi → fact_gap_matrix.matrix_id
GapMatrixId = Literal["M1", "M7", "M8"]

# RTF §Plan-Detayı (2): (2) RQ stilleri — 3 mod
RQMode = Literal["cautious", "balanced", "bold"]

# RTF Plan Akışı (2): bölüm adları IMRaD
SectionName = Literal["intro", "methods", "findings", "discussion"]

# 5.2'de tek dilli prompt; SynthesisLang ile aynı domain
TopicLang = Literal["tr", "en", "id"]


class TopicSubQuestions(BaseModel):
    """3 mod RQ stili (RTF §Plan-Detayı 2)."""

    model_config = ConfigDict(extra="forbid")

    cautious: str = Field(..., min_length=5, max_length=400)
    balanced: str = Field(..., min_length=5, max_length=400)
    bold: str = Field(..., min_length=5, max_length=400)


class TopicEvidenceChain(BaseModel):
    """Kanıt-bağlı konu önerisi şeffaflığı (RTF §Plan-Detayı 3)."""

    model_config = ConfigDict(extra="forbid")

    gap_summary: str = Field(..., min_length=5, max_length=400)
    method_summary: str = Field(..., min_length=5, max_length=400)
    synthesis_summary: str = Field(..., min_length=5, max_length=600)


class TopicProposal(BaseModel):
    """Tek konu kartı — title + 3 alt-soru + ana referans + metod + kanıt."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=5, max_length=300)
    sub_questions: TopicSubQuestions
    top_3_refs: list[str] = Field(..., min_length=1, max_length=3)
    method_suggestion: str = Field(..., min_length=5, max_length=400)
    evidence_chain: TopicEvidenceChain


class TopicProposalsLLMOutput(BaseModel):
    """Gemini Pro structured output container — 3 kart."""

    model_config = ConfigDict(extra="forbid")

    proposals: list[TopicProposal] = Field(..., min_length=3, max_length=3)


class TopicProposalsRequest(BaseModel):
    """POST /api/workshop/topic-proposals body.

    `synthesis_text` opsiyonel — frontend 3.4 sentez çıktısını şart koşmaz
    (henüz synthesis persistence yok). V1: kullanıcı sentez metnini iletirse
    LLM kanıt zincirine girer.
    """

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    gap_matrix_id: GapMatrixId
    gap_axis_x: str = Field(..., min_length=1, max_length=200)
    gap_axis_y: str = Field(..., min_length=1, max_length=200)
    method_profile: list[str] = Field(default_factory=list, max_length=5)
    synthesis_text: str | None = Field(default=None, max_length=4000)
    lang: TopicLang | None = None


class TopicProposalsResponse(BaseModel):
    """3 kart + günlük kota durumu."""

    model_config = ConfigDict(extra="forbid")

    proposals: list[TopicProposal] = Field(..., min_length=3, max_length=3)
    generation_count: int = Field(..., ge=0)
    daily_quota_remaining: int = Field(..., ge=0)
    lang: TopicLang


class DraftSkeletonRequest(BaseModel):
    """POST /api/workshop/draft-skeleton body.

    `selected_topic` frontend'in topic-proposals'tan seçtiği kartın yankısıdır
    (V1: persistence yok, frontend yankılar). `method_metod_ids` Flash
    promptunda metod-uyum SQL'i için kullanılır.
    """

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    selected_topic: TopicProposal
    method_metod_ids: list[str] = Field(default_factory=list, max_length=5)
    sections: list[SectionName] = Field(
        default_factory=lambda: cast(
            list[SectionName], ["intro", "methods", "findings", "discussion"]
        ),
        min_length=1,
        max_length=4,
    )
    lang: TopicLang | None = None


class SkeletonPaperRef(BaseModel):
    """Bölüm-spesifik kaynak önerisi (Standart Yayın Kartı Daraltılmış)."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str
    year: int | None = None
    authors_short: str
    citations_count: int = Field(..., ge=0)


class DraftSection(BaseModel):
    """Bölüm taslağı — Flash 1 paragraf + neden + top-5 paper."""

    model_config = ConfigDict(extra="forbid")

    name: SectionName
    draft_paragraph: str = Field(..., min_length=20, max_length=2000)
    why_explanation: str = Field(..., min_length=5, max_length=400)
    top_5_papers: list[SkeletonPaperRef] = Field(..., max_length=5)


class DraftSkeletonResponse(BaseModel):
    """IMRaD 4 bölüm yanıtı."""

    model_config = ConfigDict(extra="forbid")

    sections: list[DraftSection]
    lang: TopicLang


class DraftSectionLLMOutput(BaseModel):
    """Flash structured output container — tek bölüm."""

    model_config = ConfigDict(extra="forbid")

    draft_paragraph: str = Field(..., min_length=20, max_length=2000)
    why_explanation: str = Field(..., min_length=5, max_length=400)


__all__ = [
    "DraftSection",
    "DraftSectionLLMOutput",
    "DraftSkeletonRequest",
    "DraftSkeletonResponse",
    "GapMatrixId",
    "RQMode",
    "SectionName",
    "SkeletonPaperRef",
    "TopicEvidenceChain",
    "TopicLang",
    "TopicProposal",
    "TopicProposalsLLMOutput",
    "TopicProposalsRequest",
    "TopicProposalsResponse",
    "TopicSubQuestions",
]
