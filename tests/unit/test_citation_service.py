"""F13-S4 5.4 — citation_service unit tests (regex extract + verify + balance)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.services import citation_service

pytestmark = pytest.mark.unit


def test_extract_citations_simple() -> None:
    out = citation_service._extract_citations("Smith (2020) showed that X.")
    assert out == [("Smith", 2020)]


def test_extract_citations_et_al() -> None:
    out = citation_service._extract_citations("Yıldız et al., 2023 reported.")
    assert out and out[0] == ("Yıldız", 2023)


def test_extract_citations_ignores_numbers() -> None:
    out = citation_service._extract_citations("123 papers cited 99 times.")
    assert out == []


def test_split_sentences_punct() -> None:
    out = citation_service._split_sentences("Cümle bir. Cümle iki! Üç?")
    assert len(out) == 3


def test_looks_like_claim_percent() -> None:
    assert citation_service._looks_like_claim("%23 artış gözlendi.")
    assert citation_service._looks_like_claim("This study showed X.")


def test_looks_like_claim_neutral() -> None:
    assert not citation_service._looks_like_claim("Bu giriş paragrafıdır.")


def test_paper_to_meta_authors_jsonb() -> None:
    row = {
        "paper_id": "W1",
        "title": "T",
        "authors": [{"name": "A One"}, {"name": "B Two"}],
        "year": 2024,
        "venue": "V",
        "doi": "10.x/y",
        "metadata": {"volume": "10", "issue": "2", "pages": "1-5"},
    }
    meta = citation_service._paper_to_meta(row)
    assert meta["authors"] == ["A One", "B Two"]
    assert meta["year"] == 2024
    assert meta["volume"] == "10"


@pytest.mark.asyncio
async def test_search_citations_uses_synonym_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_log: list[str] = []

    async def _fake_supa(fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        call_log.append("call")
        # 1. çağrı = empty (orijinal); 2. = bir paper döner (synonym hit)
        if len(call_log) == 1:
            return SimpleNamespace(data=[])
        return SimpleNamespace(
            data=[
                {
                    "paper_id": "W2",
                    "title": "Synonym hit",
                    "authors": [{"name": "Z. A."}],
                    "year": 2022,
                    "venue": "Journal",
                    "doi": None,
                    "citations_count": 5,
                    "metadata": {},
                }
            ]
        )

    monkeypatch.setattr(citation_service, "supabase_call_async", _fake_supa)
    monkeypatch.setattr(
        citation_service, "get_supabase_admin", lambda: SimpleNamespace()
    )

    resp = await citation_service.search_citations(uuid4(), "öğrenme", "tr")
    assert resp.total_results == 1
    assert resp.synonyms_tried  # synonym dictionary'den fallback denendi
    assert resp.papers[0].paper_id == "W2"


@pytest.mark.asyncio
async def test_compute_balance_old_heavy_suggests_recent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue: list[Any] = [
        # 1. çağrı = mevcut atıf yılları (4 eski + 1 yeni)
        [
            {"paper_id": f"W{i}", "year": 2010, "title": "t", "authors": [], "venue": "v", "doi": None, "citations_count": 1}
            for i in range(4)
        ]
        + [
            {"paper_id": "Wn", "year": 2024, "title": "t", "authors": [], "venue": "v", "doi": None, "citations_count": 1}
        ],
        # 2. çağrı = recent öneri
        [
            {"paper_id": "Wnew", "title": "Recent paper", "authors": [{"name": "A B"}], "year": 2024, "venue": "V", "doi": None, "citations_count": 99, "metadata": {}}
        ],
    ]

    async def _fake_supa(_fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        return SimpleNamespace(data=queue.pop(0))

    monkeypatch.setattr(citation_service, "supabase_call_async", _fake_supa)
    monkeypatch.setattr(
        citation_service, "get_supabase_admin", lambda: SimpleNamespace()
    )

    out = await citation_service.compute_balance(uuid4(), [f"W{i}" for i in range(5)])
    assert out["total"] == 5
    assert out["old_count"] == 4
    assert out["recent_count"] == 1
    assert out["old_pct"] >= 70
    assert len(out["suggested_papers"]) == 1
    assert out["suggested_papers"][0].paper_id == "Wnew"


@pytest.mark.asyncio
async def test_format_one_citation_apa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_supa(_fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        return SimpleNamespace(
            data=[
                {
                    "paper_id": "W42",
                    "title": "Sample paper",
                    "authors": [{"name": "Smith, John"}],
                    "year": 2023,
                    "venue": "Nature",
                    "doi": "10.x/y",
                    "metadata": {"volume": "1"},
                }
            ]
        )

    monkeypatch.setattr(citation_service, "supabase_call_async", _fake_supa)
    monkeypatch.setattr(
        citation_service, "get_supabase_admin", lambda: SimpleNamespace()
    )

    resp = await citation_service.format_one_citation("W42", "apa")
    assert resp.style == "apa"
    assert "Smith" in resp.formatted_citation
    assert "@article{Smith2023" in resp.bibtex_entry
