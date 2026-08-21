"""F13-S4 5.4 Atıf Stil — Pydantic schemas (citation search/verify/format/balance).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S4
RTF: Page_Design/Sayfa_Plani_v2/5.4_atif_stil_kilavuzu.rtf §Plan-Detayı
HK-1 Pydantic gate: extra="forbid".
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CitationStyle = Literal["apa", "vancouver", "ieee", "chicago", "mla"]
Lang = Literal["tr", "en", "id"]
SentenceStatus = Literal["ok", "hallucinated", "topic_mismatch", "needs_citation"]


class CitationPaper(BaseModel):
    """Aramadan dönen tek paper kartı (Standart Yayın Kartı Daraltılmış)."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str
    authors: list[str]
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    citations_count: int = 0


class CitationSearchResponse(BaseModel):
    """GET /api/workshop/citation-search."""

    model_config = ConfigDict(extra="forbid")

    papers: list[CitationPaper]
    synonyms_tried: list[str]
    total_results: int


class CitationVerifyRequest(BaseModel):
    """POST /api/workshop/citation-verify body."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    document_text: str = Field(..., min_length=1, max_length=50_000)
    citation_style: CitationStyle = "apa"


class CitationFinding(BaseModel):
    """Çıkarılan tek atıf + havuz eşleşme durumu."""

    model_config = ConfigDict(extra="forbid")

    raw: str
    author_guess: str
    year_guess: int | None = None
    matched_paper_id: str | None = None


class SentenceVerification(BaseModel):
    """Cümle başına 4-sınıf doğrulama (ok/hallucinated/topic_mismatch/needs_citation)."""

    model_config = ConfigDict(extra="forbid")

    index: int
    text: str
    citations: list[CitationFinding]
    status: SentenceStatus


class CitationVerifyResponse(BaseModel):
    """POST /api/workshop/citation-verify response."""

    model_config = ConfigDict(extra="forbid")

    sentences: list[SentenceVerification]
    total_citations: int
    hallucinated_count: int
    topic_mismatch_count: int
    needs_citation_count: int


class FormatCitationResponse(BaseModel):
    """GET /api/workshop/format-citation."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    style: CitationStyle
    formatted_citation: str
    bibtex_entry: str


class CitationBalanceRequest(BaseModel):
    """POST /api/workshop/citation-balance body — atıf listesinin yıl histogramı."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    citation_paper_ids: list[str] = Field(..., min_length=1)


class CitationBalanceResponse(BaseModel):
    """Eski-yeni denge çıktısı."""

    model_config = ConfigDict(extra="forbid")

    total: int
    old_count: int
    recent_count: int
    old_pct: float = Field(..., ge=0.0, le=100.0)
    recent_pct: float = Field(..., ge=0.0, le=100.0)
    suggested_papers: list[CitationPaper]
    balance_advice: str


__all__ = [
    "CitationBalanceRequest",
    "CitationBalanceResponse",
    "CitationFinding",
    "CitationPaper",
    "CitationSearchResponse",
    "CitationStyle",
    "CitationVerifyRequest",
    "CitationVerifyResponse",
    "FormatCitationResponse",
    "Lang",
    "SentenceStatus",
    "SentenceVerification",
]
