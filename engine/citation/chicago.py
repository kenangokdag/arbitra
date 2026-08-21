"""Chicago (Author-Date) formatter."""

from __future__ import annotations

from engine.citation._helpers import joined_chicago_authors
from engine.citation.types import PaperMeta


def format_chicago(meta: PaperMeta) -> str:
    """Chicago Author-Date: Author, First, and First Author2. Year. "Title." Journal Vol(Issue): Pages. https://doi.org/..."""
    authors = joined_chicago_authors(meta.get("authors", []))
    year = meta.get("year")
    title = (meta.get("title") or "").rstrip(".")
    venue = meta.get("venue") or ""
    volume = meta.get("volume")
    issue = meta.get("issue")
    pages = meta.get("pages")
    doi = meta.get("doi")

    parts: list[str] = []
    if authors:
        parts.append(f"{authors}.")
    if year:
        parts.append(f"{year}.")
    if title:
        parts.append(f'"{title}."')
    venue_part = venue
    if volume:
        venue_part = f"{venue} {volume}".strip()
        if issue:
            venue_part = f"{venue_part}({issue})"
    if pages:
        venue_part = f"{venue_part}: {pages}" if venue_part else pages
    if venue_part:
        parts.append(f"{venue_part}.")
    if doi:
        parts.append(f"https://doi.org/{doi}")

    return " ".join(parts).strip()


__all__ = ["format_chicago"]
