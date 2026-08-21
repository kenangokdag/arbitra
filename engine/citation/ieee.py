"""IEEE formatter."""

from __future__ import annotations

from engine.citation._helpers import joined_ieee_authors
from engine.citation.types import PaperMeta


def format_ieee(meta: PaperMeta) -> str:
    """IEEE: A. A. Author and B. B. Author, "Title," Journal, vol. X, no. Y, pp. Z, Year, doi: ..."""
    authors = joined_ieee_authors(meta.get("authors", []))
    title = (meta.get("title") or "").rstrip(".")
    venue = meta.get("venue") or ""
    year = meta.get("year")
    volume = meta.get("volume")
    issue = meta.get("issue")
    pages = meta.get("pages")
    doi = meta.get("doi")

    parts: list[str] = []
    if authors:
        parts.append(f"{authors},")
    if title:
        parts.append(f'"{title},"')
    if venue:
        parts.append(f"{venue},")
    if volume:
        parts.append(f"vol. {volume},")
    if issue:
        parts.append(f"no. {issue},")
    if pages:
        parts.append(f"pp. {pages},")
    if year:
        parts.append(f"{year}.")
    if doi:
        parts.append(f"doi: {doi}")

    return " ".join(parts).strip()


__all__ = ["format_ieee"]
