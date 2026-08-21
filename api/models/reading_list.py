"""F3e /api/reading-list Pydantic schemas — skeleton (B-018).

Pinecone bağımsız — Postgres CRUD; concrete impl P035 (asyncpg pool setup
sonrası). HK-1: extra=forbid.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReadingStatus = Literal["want_to_read", "reading", "finished", "skipped"]


class ReadingListAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str = Field(min_length=1, max_length=64)
    status: ReadingStatus = "want_to_read"
    notes: str = Field(default="", max_length=2000)


class ReadingListUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReadingStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ReadingListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    paper_id: str
    status: ReadingStatus
    notes: str = ""
    added_at: datetime
    updated_at: datetime


class ReadingListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ReadingListItem]
    count: int
