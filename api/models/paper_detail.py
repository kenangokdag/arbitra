"""GET /api/paper/{paper_id} Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from api.models.search import Citation, DecisionBand, GateWarning


class PaperDetail(BaseModel):
    """Full paper detail — superset of PaperCard with enriched fields."""

    model_config = ConfigDict(extra="allow")

    paper_id: str
    pmid: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    year_verified: bool = False
    doi: str | None = None
    abstract: str | None = None
    abstract_excerpt: str | None = None
    journal: str | None = None
    n_cited: int = 0
    signals_13: dict[str, float] = Field(default_factory=dict)
    citations_lvr: list[Citation] = Field(default_factory=list)
    decision_band: DecisionBand = DecisionBand.FRONTIER
    gate_warnings: list[GateWarning] = Field(default_factory=list)
    is_ghost: bool = False
    language: str | None = None
    is_open_access: bool | None = None
    keywords: list[str] = Field(default_factory=list)
    references_count: int = 0
    cited_by_count: int = 0
    url: str | None = None
