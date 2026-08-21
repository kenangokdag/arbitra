"""Vancouver formatter (NLM/AMA style)."""

from __future__ import annotations

from engine.citation._helpers import joined_vancouver_authors
from engine.citation.types import PaperMeta


def format_vancouver(meta: PaperMeta) -> str:
    """Vancouver: Author AA, Author BB. Title. Journal. Year;Vol(Issue):Pages. doi:..."""
    authors = joined_vancouver_authors(meta.get("authors", []))
    title = (meta.get("title") or "").rstrip(".")
    venue = meta.get("venue") or ""
    year = meta.get("year")
    volume = meta.get("volume")
    issue = meta.get("issue")
    pages = meta.get("pages")
    doi = meta.get("doi")

    parts: list[str] = []
    if authors:
        parts.append(f"{authors}.")
    if title:
        parts.append(f"{title}.")
    if venue:
        parts.append(f"{venue}.")
    end = ""
    if year:
        end = str(year)
        if volume:
            end += f";{volume}"
            if issue:
                end += f"({issue})"
        if pages:
            end += f":{pages}"
        end += "."
    if end:
        parts.append(end)
    if doi:
        parts.append(f"doi:{doi}")

    return " ".join(parts).strip()


__all__ = ["format_vancouver"]
