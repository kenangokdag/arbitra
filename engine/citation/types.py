"""F13-S4 5.4 — paylaşılan PaperMeta TypedDict (citation formatters girdisi)."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class PaperMeta(TypedDict):
    """citation formatter girdisi — papers tablosundan toplanır."""

    paper_id: str
    title: str
    authors: list[str]
    year: NotRequired[int | None]
    venue: NotRequired[str | None]
    volume: NotRequired[str | None]
    issue: NotRequired[str | None]
    pages: NotRequired[str | None]
    doi: NotRequired[str | None]


__all__ = ["PaperMeta"]
