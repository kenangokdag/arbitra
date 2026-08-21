"""F13-S4 5.4 — engine/citation deterministic formatter tests."""

from __future__ import annotations

from typing import cast

import pytest

from engine.citation import format_citation, to_bibtex
from engine.citation.types import PaperMeta

pytestmark = pytest.mark.unit


def _meta() -> PaperMeta:
    return cast(
        PaperMeta,
        {
            "paper_id": "W123",
            "title": "Adaptive Learning Systems",
            "authors": ["Kizilcec, René F.", "Pardos, Zachary A."],
            "year": 2024,
            "venue": "Computers & Education",
            "volume": "200",
            "issue": "3",
            "pages": "104-119",
            "doi": "10.1016/j.compedu.2024.104119",
        },
    )


def test_apa_format_includes_authors_year_doi() -> None:
    out = format_citation(_meta(), "apa")
    assert "Kizilcec" in out
    assert "(2024)" in out
    assert "10.1016/j.compedu" in out


def test_vancouver_year_volume_pages() -> None:
    out = format_citation(_meta(), "vancouver")
    assert "Kizilcec RF" in out
    assert "2024;200(3):104-119" in out


def test_ieee_quoted_title() -> None:
    out = format_citation(_meta(), "ieee")
    assert '"Adaptive Learning Systems,"' in out
    assert "vol. 200" in out


def test_chicago_year_after_authors() -> None:
    out = format_citation(_meta(), "chicago")
    assert "Kizilcec" in out
    assert "2024." in out


def test_mla_quoted_title_year_pages() -> None:
    out = format_citation(_meta(), "mla")
    assert '"Adaptive Learning Systems."' in out
    assert "pp. 104-119." in out


def test_to_bibtex_uses_first_author_year_key() -> None:
    out = to_bibtex(_meta())
    assert "@article{Kizilcec2024" in out
    assert "doi = {10.1016/j.compedu.2024.104119}" in out


def test_apa_no_year_fallback() -> None:
    m = _meta()
    m["year"] = None
    out = format_citation(m, "apa")
    assert "(n.d.)" in out


def test_no_authors_fallback() -> None:
    m = _meta()
    m["authors"] = []
    out = format_citation(m, "apa")
    assert "(2024)" in out
