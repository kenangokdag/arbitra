"""V1 Vitrin Pydantic models — Q (25 makale) + Q literature-review.

kaynak: docs/plans/V1_S5_backend_tier_canon.md §1 (3-tier canon)
        docs/plans/V1_S10_vitrin_tek_sayfa.md §5 (KD-V1-S10-04 akademik makale formatı)
HK-1: extra="forbid" tüm dış-yüz modellerde.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PaperPreview(BaseModel):
    """OpenAlex'ten dönen makale kartı — Q ve literature-review ortak."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    openalex_id: str
    doi: str | None = None
    title: str
    abstract: str | None = None
    year: int | None = None
    venue: str | None = None
    authors: list[str] = Field(default_factory=list)
    cited_by_count: int = 0
    mini_summary: str | None = None  # legacy alan; literature-review kullanmaz


# ───── Q (anon/authed — 25 makale preview, no LLM) ─────


class QRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    query: str = Field(min_length=2, max_length=500)
    year_from: int | None = Field(default=None, ge=1900, le=2100)
    year_to: int | None = Field(default=None, ge=1900, le=2100)
    lang: str | None = Field(default=None, pattern=r"^[a-z]{2}$")


class QueryTranslation(BaseModel):
    """V1-S11 — kullanıcı sorgusu → İngilizce çeviri + dil tespiti.

    KD-V1-S11-02: çift dil paralel arama için. detected_lang == "en" ise
    english_query == original (2. arama atlar).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    original: str = Field(min_length=1, max_length=500)
    detected_lang: Literal["tr", "en", "id", "other"]
    english_query: str = Field(min_length=1, max_length=500)


class QueryTranslationLLM(BaseModel):
    """LLM structured output — translate_query mode parsed_output."""

    model_config = ConfigDict(extra="forbid")
    detected_lang: Literal["tr", "en", "id", "other"]
    english_query: str = Field(min_length=1, max_length=500)


class QResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    # KD-V1-S10-01: 25 makale sabit (anon/authed aynı listing).
    papers: list[PaperPreview] = Field(max_length=25)
    # KD-V1-S11-04: translate skip/fail → None; aksi halde original+detected+english.
    translation: QueryTranslation | None = None
    quota_remaining: int
    quota_reset: str  # ISO-8601


# ───── /api/q/literature-review (KD-V1-S10-04 akademik makale formatı) ─────


class LiteratureReviewRequest(BaseModel):
    """Kullanıcının seçtiği makale ID'leri ile literatür özeti üretir.

    Anon: max 3 paper_ids (endpoint'te tier-aware validate).
    Authed: max 25 paper_ids.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    paper_ids: list[str] = Field(min_length=1, max_length=25)
    lang: Literal["tr", "en", "id"] = "tr"


class Reference(BaseModel):
    """Numaralı kaynak — akademik makale Kaynaklar bölümü."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    index: int = Field(ge=1, le=25)
    citation: str = Field(min_length=10, max_length=500)


class LiteratureReviewLLM(BaseModel):
    """LLM structured output — vitrin_literature mode parsed_output.

    KD-V1-S10-04 (revize 2026-05-09): tek blok akademik literatür inceleme
    metni + numaralı kaynaklar. Per-paper scale: kaynak başına ~30-40 kelime
    (~2 satır). N=1 → ~30 kelime, N=25 → ~750 kelime (~1-1.5 sayfa).
    Başlık + 4-alt-bölüm yapısı kaldırıldı (komple makale değil, sadece
    inceleme bölümü).
    """

    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=50, max_length=5000)
    references: list[Reference] = Field(min_length=1, max_length=25)


class LiteratureReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    review: LiteratureReviewLLM
    quota_remaining: int
    quota_reset: str


__all__ = [
    "LiteratureReviewLLM",
    "LiteratureReviewRequest",
    "LiteratureReviewResponse",
    "PaperPreview",
    "QRequest",
    "QResponse",
    "QueryTranslation",
    "QueryTranslationLLM",
    "Reference",
]
