"""V1-S14 P005 — Bibliometric service unit tests.

Plan: docs/plans/V1_S14_mock_to_live.md §3 P005 (REVİZE 2026-05-10, B-029).

Tasarım: Supabase client'ı `_FakeClient` ile mock'la (table().select().in_().execute()
zinciri). 6 aggregate + endpoint smoke + empty paper_ids edge case.
"""

from __future__ import annotations

from typing import Any

import pytest

from api.models.bibliometric import BibliometricSummary
from api.services.bibliometric_service import compute_bibliometric_summary

pytestmark = pytest.mark.unit


class _FakeResp:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _FakeQuery:
    def __init__(self, store: dict[str, list[dict[str, Any]]], table: str) -> None:
        self._store = store
        self._table = table
        self._key = "paper_id"
        self._values: list[str] = []

    def select(self, _columns: str) -> _FakeQuery:
        return self

    def in_(self, key: str, values: list[str]) -> _FakeQuery:
        self._key = key
        self._values = values
        return self

    def execute(self) -> _FakeResp:
        rows = self._store.get(self._table, [])
        keep = set(self._values)
        filtered = [r for r in rows if r.get(self._key) in keep]
        return _FakeResp(filtered)


class _FakeClient:
    def __init__(self, store: dict[str, list[dict[str, Any]]]) -> None:
        self._store = store

    def table(self, name: str) -> _FakeQuery:
        return _FakeQuery(self._store, name)


def _store_for(paper_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    return {
        "fact_paper_id_card": [
            {"paper_id": "W1", "year": 2018, "language": "en", "pmid": "PM1"},
            {"paper_id": "W2", "year": 2020, "language": "en", "pmid": "PM2"},
            {"paper_id": "W3", "year": 2022, "language": "tr", "pmid": "PM3"},
            {"paper_id": "W4", "year": 2024, "language": "en", "pmid": "PM4"},
            {"paper_id": "W5", "year": 2024, "language": None, "pmid": "PM5"},
        ],
        "fact_paper_beauty": [
            {"paper_id": "W1", "total_cites": 10},
            {"paper_id": "W2", "total_cites": 100},
            {"paper_id": "W3", "total_cites": 50},
            {"paper_id": "W4", "total_cites": 200},
            {"paper_id": "W5", "total_cites": 5},
        ],
        "fact_paper_field": [
            {"paper_id": "W1", "primary_field": "F1"},
            {"paper_id": "W2", "primary_field": "F1"},
            {"paper_id": "W3", "primary_field": "F2"},
            {"paper_id": "W4", "primary_field": "F2"},
            {"paper_id": "W5", "primary_field": "F1"},
        ],
        "dim_field": [
            {"field_id": "F1", "name_en": "Computer Science"},
            {"field_id": "F2", "name_en": "Medicine"},
        ],
        "fact_paper_sentence_role": [
            {"paper_id": "W1", "dominant_role": "METHOD"},
            {"paper_id": "W2", "dominant_role": "METHOD"},
            {"paper_id": "W3", "dominant_role": "RESULT"},
            {"paper_id": "W4", "dominant_role": "BACKGROUND"},
            {"paper_id": "W5", "dominant_role": "METHOD"},
        ],
    }


@pytest.fixture
def paper_ids() -> list[str]:
    return ["W1", "W2", "W3", "W4", "W5"]


@pytest.fixture
def fake_db(paper_ids: list[str]) -> _FakeClient:
    return _FakeClient(_store_for(paper_ids))


async def test_total_papers_matches_input(
    fake_db: _FakeClient, paper_ids: list[str]
) -> None:
    summary = await compute_bibliometric_summary(fake_db, paper_ids)  # type: ignore[arg-type]
    assert summary.total_papers == 5


async def test_median_year(fake_db: _FakeClient, paper_ids: list[str]) -> None:
    summary = await compute_bibliometric_summary(fake_db, paper_ids)  # type: ignore[arg-type]
    assert summary.median_year == 2022  # median of [2018,2020,2022,2024,2024]


async def test_mean_citations(fake_db: _FakeClient, paper_ids: list[str]) -> None:
    summary = await compute_bibliometric_summary(fake_db, paper_ids)  # type: ignore[arg-type]
    # (10+100+50+200+5)/5 = 73.0
    assert summary.mean_citations == 73.0


async def test_most_cited(fake_db: _FakeClient, paper_ids: list[str]) -> None:
    summary = await compute_bibliometric_summary(fake_db, paper_ids)  # type: ignore[arg-type]
    assert summary.most_cited is not None
    assert summary.most_cited.paper_id == "W4"
    assert summary.most_cited.citations == 200
    assert summary.most_cited.pmid == "PM4"


async def test_publications_by_year(
    fake_db: _FakeClient, paper_ids: list[str]
) -> None:
    summary = await compute_bibliometric_summary(fake_db, paper_ids)  # type: ignore[arg-type]
    years = {yc.year: yc.count for yc in summary.publications_by_year}
    assert years == {2018: 1, 2020: 1, 2022: 1, 2024: 2}


async def test_language_dist(fake_db: _FakeClient, paper_ids: list[str]) -> None:
    summary = await compute_bibliometric_summary(fake_db, paper_ids)  # type: ignore[arg-type]
    langs = {lc.code: lc.count for lc in summary.language_dist}
    assert langs == {"en": 3, "tr": 1, "unknown": 1}


async def test_top_areas_uses_dim_field_names(
    fake_db: _FakeClient, paper_ids: list[str]
) -> None:
    summary = await compute_bibliometric_summary(fake_db, paper_ids)  # type: ignore[arg-type]
    areas = {a.name: a.count for a in summary.top_areas}
    assert areas == {"Computer Science": 3, "Medicine": 2}


async def test_top_methods_with_tr_labels(
    fake_db: _FakeClient, paper_ids: list[str]
) -> None:
    summary = await compute_bibliometric_summary(fake_db, paper_ids)  # type: ignore[arg-type]
    methods = {m.name: m.count for m in summary.top_methods}
    assert methods == {"Yöntem": 3, "Sonuç": 1, "Arka plan": 1}


async def test_empty_paper_ids_returns_zero_summary() -> None:
    db = _FakeClient({})
    summary = await compute_bibliometric_summary(db, [])  # type: ignore[arg-type]
    assert isinstance(summary, BibliometricSummary)
    assert summary.total_papers == 0
    assert summary.median_year is None
    assert summary.mean_citations == 0.0
    assert summary.most_cited is None
    assert summary.publications_by_year == []
    assert summary.language_dist == []
    assert summary.top_areas == []
    assert summary.top_methods == []
    # N-13: boş input → tüm confidence alanları C (tahmin/uygulanmaz).
    assert summary.confidence.card_metrics == "C"
    assert summary.confidence.beauty_metrics == "C"
    assert summary.confidence.top_areas == "C"
    assert summary.confidence.top_methods == "C"


# ── N-13 confidence binding ────────────────────────────────────────────────
async def test_confidence_all_A_when_warehouse_returns(
    fake_db: _FakeClient, paper_ids: list[str]
) -> None:
    """Warehouse 4 alt-sorgu da satır döndürüyor → tümü A."""
    summary = await compute_bibliometric_summary(fake_db, paper_ids)  # type: ignore[arg-type]
    assert summary.confidence.card_metrics == "A"
    assert summary.confidence.beauty_metrics == "A"
    assert summary.confidence.top_areas == "A"
    assert summary.confidence.top_methods == "A"


async def test_confidence_C_when_beauty_table_missing(
    paper_ids: list[str],
) -> None:
    """fact_paper_beauty boş → beauty_metrics=C, diğerleri A."""
    store = _store_for(paper_ids)
    store["fact_paper_beauty"] = []  # warehouse fail / empty
    db = _FakeClient(store)
    summary = await compute_bibliometric_summary(db, paper_ids)  # type: ignore[arg-type]
    assert summary.confidence.beauty_metrics == "C"
    assert summary.confidence.card_metrics == "A"
    assert summary.confidence.top_areas == "A"
    assert summary.confidence.top_methods == "A"
