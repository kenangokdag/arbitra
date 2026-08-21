"""V1-S14 P005 — Bibliometric summary Pydantic schemas.

Plan: docs/plans/V1_S14_mock_to_live.md §3 P005 (REVİZE 2026-05-10, B-029).
Frontend: web/src/components/project/BibliometricSummaryPage.tsx — 6 metrik
warehouse'a hizalı (TOP_VENUES→TOP_AREAS, TOP_AUTHORS+LOTKA→TOP_METHODS,
mostCited.title→pmid placeholder).

Kaynak tablolar:
- fact_paper_id_card (year, language) — `0003_paper_anchor_facts.sql:31-48`
- fact_paper_beauty (total_cites) — `0005_paper_estra_temporal.sql:140-152`
- fact_paper_field (primary_field) + dim_field (name_en) — `0006`/`0011`
- fact_paper_sentence_role (dominant_role) — `0004:21-37`
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MostCited(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paper_id: str
    pmid: str | None = None  # title yok (papers tablosu boş, lazy-fill V2)
    citations: int


class YearCount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year: int
    count: int


class LangCount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str  # 2-char ISO veya "unknown"
    count: int


class NamedCount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    count: int


class BibliometricRequest(BaseModel):
    """KD-V1-S14-03 REVİZE 2026-05-10: paper_ids opsiyonel. Frontend boş gönderirse
    backend `project_seed_papers` (admin client, `project.py:344` pattern) üzerinden
    çeker. Override gerekirse client paper_ids array gönderebilir."""

    model_config = ConfigDict(extra="forbid")
    paper_ids: list[str] = Field(default_factory=list, max_length=500)


class BibliometricConfidence(BaseModel):
    """N-13 (2026-05-27): metrik-bazlı kanıt seviyesi.

    A = warehouse aggregate (live SQL → > 0 satır).
    C = boş/fail (tablo yok, satır gelmedi). B (cache) V2'ye kaldı.
    Frontend DataProvenance pill'i bu alanları confidence prop'una bağlar.
    Audit: AUDIT_REPORT.md §11 N-13.
    """

    model_config = ConfigDict(extra="forbid")
    card_metrics: Literal["A", "C"]    # total / median_year / year_dist / lang_dist
    beauty_metrics: Literal["A", "C"]  # mean_citations / most_cited
    top_areas: Literal["A", "C"]
    top_methods: Literal["A", "C"]


class BibliometricSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_papers: int
    median_year: int | None
    mean_citations: float
    most_cited: MostCited | None

    publications_by_year: list[YearCount]
    language_dist: list[LangCount]
    top_areas: list[NamedCount]
    top_methods: list[NamedCount]
    confidence: BibliometricConfidence
