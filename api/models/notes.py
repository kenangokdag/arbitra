"""POST/GET/DELETE /api/notes Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str | None = Field(default=None, max_length=64)
    content: str = Field(..., min_length=1, max_length=5000)
    tags: list[str] = Field(default_factory=list)


class NoteUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str | None = Field(default=None, max_length=5000)
    tags: list[str] | None = None


class NoteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    paper_id: str | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class NotesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[NoteItem]
    count: int
