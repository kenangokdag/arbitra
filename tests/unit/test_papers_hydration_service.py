"""F13-S11-P000 unit tests — papers_hydration_service.

Hedef: _normalize_ids + _preview_to_row pure logic + hydrate_paper_ids akışı
(mock OpenAlex + mock Supabase).
"""

from __future__ import annotations

from typing import Any

import pytest

from api.models.q import PaperPreview
from api.services import papers_hydration_service as svc

pytestmark = pytest.mark.unit


def test_normalize_ids_strips_url_prefix() -> None:
    out = svc._normalize_ids(
        ["https://openalex.org/W123", "W456", "  W789  "]
    )
    assert out == ["W123", "W456", "W789"]


def test_normalize_ids_dedups_and_skips_empty() -> None:
    out = svc._normalize_ids(["W1", "W1", "", "https://openalex.org/W1", "W2"])
    assert out == ["W1", "W2"]


def test_preview_to_row_maps_fields() -> None:
    preview = PaperPreview(
        openalex_id="https://openalex.org/W999",
        doi="10.1/x",
        title="Test",
        abstract="abs",
        year=2024,
        venue="JTest",
        authors=["Smith J", "Doe A"],
        cited_by_count=42,
    )
    row = svc._preview_to_row(preview)
    assert row["paper_id"] == "W999"
    assert row["doi"] == "10.1/x"
    assert row["title"] == "Test"
    assert row["abstract"] == "abs"
    assert row["authors"] == [{"name": "Smith J"}, {"name": "Doe A"}]
    assert row["year"] == 2024
    assert row["year_verified"] is False
    assert row["venue"] == "JTest"
    assert row["citations_count"] == 42


def test_preview_to_row_handles_missing_title() -> None:
    preview = PaperPreview(openalex_id="W1", title="(başlıksız)")
    row = svc._preview_to_row(preview)
    assert row["title"] == "(başlıksız)"
    assert row["abstract"] is None
    assert row["authors"] == []
    assert row["citations_count"] == 0


@pytest.mark.asyncio
async def test_hydrate_empty_returns_zero() -> None:
    assert await svc.hydrate_paper_ids([]) == 0


@pytest.mark.asyncio
async def test_hydrate_all_existing_skips_openalex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_existing(ids: list[str]) -> set[str]:
        return {"W1", "W2"}

    async def fake_fetch(ids: list[str]) -> list[PaperPreview]:  # noqa: ARG001
        raise AssertionError("OpenAlex should not be called when all exist")

    monkeypatch.setattr(svc, "_fetch_existing", fake_existing)
    monkeypatch.setattr(svc, "fetch_papers_by_ids", fake_fetch)

    result = await svc.hydrate_paper_ids(["W1", "W2"])
    assert result == 0


@pytest.mark.asyncio
async def test_hydrate_missing_fetches_and_upserts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_existing(ids: list[str]) -> set[str]:
        return {"W1"}

    async def fake_fetch(ids: list[str]) -> list[PaperPreview]:
        assert ids == ["W2", "W3"]
        return [
            PaperPreview(openalex_id="W2", title="Two", year=2023),
            PaperPreview(openalex_id="W3", title="Three", year=2024),
        ]

    captured: dict[str, Any] = {}

    class FakeTable:
        def upsert(self, rows: list[dict[str, Any]], on_conflict: str) -> "FakeTable":
            captured["rows"] = rows
            captured["on_conflict"] = on_conflict
            return self

        def execute(self) -> Any:
            class Resp:
                data = captured["rows"]

            return Resp()

    class FakeClient:
        def table(self, name: str) -> FakeTable:
            assert name == "papers"
            return FakeTable()

    async def fake_call_async(fn: Any) -> Any:
        return fn()

    monkeypatch.setattr(svc, "_fetch_existing", fake_existing)
    monkeypatch.setattr(svc, "fetch_papers_by_ids", fake_fetch)
    monkeypatch.setattr(svc, "get_supabase_admin", lambda: FakeClient())
    monkeypatch.setattr(svc, "supabase_call_async", fake_call_async)

    result = await svc.hydrate_paper_ids(["W1", "W2", "W3"])
    assert result == 2
    assert captured["on_conflict"] == "paper_id"
    assert [r["paper_id"] for r in captured["rows"]] == ["W2", "W3"]


@pytest.mark.asyncio
async def test_hydrate_openalex_empty_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_existing(ids: list[str]) -> set[str]:
        return set()

    async def fake_fetch(ids: list[str]) -> list[PaperPreview]:  # noqa: ARG001
        return []

    monkeypatch.setattr(svc, "_fetch_existing", fake_existing)
    monkeypatch.setattr(svc, "fetch_papers_by_ids", fake_fetch)

    result = await svc.hydrate_paper_ids(["W1"])
    assert result == 0
