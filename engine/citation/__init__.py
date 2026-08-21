"""F13-S4 5.4 Atıf Stil — per-stil deterministic citation formatters.

5 stil: apa, vancouver, ieee, chicago, mla. Tüm formatter'lar PaperMeta TypedDict
alır, formatted_citation + bibtex_entry str döner. LLM kullanılmaz (RTF §Felsefe:
"halüsinasyon yasak; SQL deterministic + Python template").
"""

from __future__ import annotations

from typing import Literal

from engine.citation.apa import format_apa
from engine.citation.chicago import format_chicago
from engine.citation.ieee import format_ieee
from engine.citation.mla import format_mla
from engine.citation.types import PaperMeta
from engine.citation.vancouver import format_vancouver

CitationStyle = Literal["apa", "vancouver", "ieee", "chicago", "mla"]

_FORMATTERS = {
    "apa": format_apa,
    "vancouver": format_vancouver,
    "ieee": format_ieee,
    "chicago": format_chicago,
    "mla": format_mla,
}


def format_citation(meta: PaperMeta, style: CitationStyle) -> str:
    return _FORMATTERS[style](meta)


def to_bibtex(meta: PaperMeta) -> str:
    """Stil-bağımsız BibTeX entry — copy-paste için."""
    first_author_surname = "Anon"
    if meta.get("authors"):
        first_author = meta["authors"][0]
        surname = first_author.split(",")[0].split()[-1]
        first_author_surname = "".join(c for c in surname if c.isalnum()) or "Anon"
    year = meta.get("year") or "n.d."
    key = f"{first_author_surname}{year}"

    fields: list[str] = []
    if meta.get("title"):
        fields.append(f'  title = {{{meta["title"]}}}')
    if meta.get("authors"):
        fields.append(f'  author = {{{" and ".join(meta["authors"])}}}')
    if meta.get("year"):
        fields.append(f'  year = {{{meta["year"]}}}')
    if meta.get("venue"):
        fields.append(f'  journal = {{{meta["venue"]}}}')
    if meta.get("doi"):
        fields.append(f'  doi = {{{meta["doi"]}}}')

    body = ",\n".join(fields)
    return f"@article{{{key},\n{body}\n}}"


__all__ = [
    "CitationStyle",
    "PaperMeta",
    "format_citation",
    "to_bibtex",
]
