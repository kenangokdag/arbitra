"""F5 /api/top5 Pydantic schemas — skeleton (B-018).

Top-5 onay margin filtresi (OPEN-005 default 0.7 onay bekliyor); chat clarify
branch sonrası onaya çıkar. HK-1: extra=forbid.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from api.models.search import PaperCard


class Top5Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=512)
    session_id: str = Field(min_length=1, max_length=64)
    margin: float = Field(default=0.7, ge=0.0, le=1.0)
    k: int = Field(default=5, ge=1, le=10)


class Top5Response(BaseModel):
    model_config = ConfigDict(extra="forbid")

    papers: list[PaperCard] = Field(max_length=10)
    needs_clarify: bool = False
    margin_used: float
