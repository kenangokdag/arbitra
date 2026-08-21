"""MLA 9th edition formatter."""

from __future__ import annotations

from engine.citation._helpers import joined_mla_authors
from engine.citation.types import PaperMeta


def format_mla(meta: PaperMeta) -> str:
    """MLA: Author, First. "Title." Journal, vol. X, no. Y, Year, pp. Z. https://doi.org/..."""
    authors = joined_mla_authors(meta.get("authors", []))
    title = (meta.get("title") or "").rstrip(".")
    venue = meta.get("venue") or ""
    year = meta.get("year")
    volume = meta.get("volume")
    issue = meta.get("issue")
    pages = meta.get("pages")
    doi = meta.get("doi")

    parts: list[str] = []
    if authors:
        parts.append(f"{authors}")
    if title:
        parts.append(f'"{title}."')
    if venue:
        parts.append(f"{venue},")
    if volume:
        parts.append(f"vol. {volume},")
    if issue:
        parts.append(f"no. {issue},")
    if year:
        parts.append(f"{year},")
    if pages:
        parts.append(f"pp. {pages}.")
    elif parts and parts[-1].endswith(","):
        parts[-1] = parts[-1].rstrip(",") + "."
    if doi:
        parts.append(f"https://doi.org/{doi}")

    return " ".join(parts).strip()


__all__ = ["format_mla"]
