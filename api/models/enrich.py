"""F3d /api/enrich Pydantic schemas — skeleton (B-018).

HK-1: extra=forbid; HK-2: TODO marker P031 OpenAlex polite pool 100K req/gün
verify (DM-009 + Sercan handoff confirmation).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EnrichSource = Literal["openalex", "semantic_scholar", "crossref"]


def _default_sources() -> list[EnrichSource]:
    return ["openalex"]


class EnrichRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str = Field(min_length=1, max_length=64)
    sources: list[EnrichSource] = Field(default_factory=_default_sources)


class EnrichResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str
    sources_hit: list[EnrichSource] = Field(default_factory=list)
    cache_hit: bool = False
    enriched_fields: dict[str, str] = Field(default_factory=dict)
