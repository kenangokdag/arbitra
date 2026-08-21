"""APA 7th edition formatter."""

from __future__ import annotations

from engine.citation._helpers import joined_apa_authors
from engine.citation.types import PaperMeta


def format_apa(meta: PaperMeta) -> str:
    """APA: Author, A. A., & Author, B. B. (Year). Title. Journal, Volume(Issue), Pages. https://doi.org/..."""
    authors = joined_apa_authors(meta.get("authors", []))
    year = meta.get("year")
    year_str = f"({year})" if year else "(n.d.)"
    title = (meta.get("title") or "").rstrip(".")
    venue = meta.get("venue") or ""
    volume = meta.get("volume")
    issue = meta.get("issue")
    pages = meta.get("pages")
    doi = meta.get("doi")

    parts: list[str] = []
    if authors:
        parts.append(f"{authors}")
    parts.append(year_str)
    parts.append(f"{title}.")
    venue_part = venue
    if volume:
        venue_part = f"{venue}, {volume}" if venue else f"{volume}"
        if issue:
            venue_part = f"{venue_part}({issue})"
    elif venue:
        venue_part = venue
    if pages:
        venue_part = f"{venue_part}, {pages}" if venue_part else pages
    if venue_part:
        parts.append(f"{venue_part}.")
    if doi:
        parts.append(f"https://doi.org/{doi}")

    return " ".join(parts).strip()


__all__ = ["format_apa"]
