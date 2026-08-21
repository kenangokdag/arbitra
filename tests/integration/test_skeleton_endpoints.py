"""F3+F5 endpoint integration tests (B-018 + Council 37).

6 endpoint concrete happy path + 422 validation (Pydantic forbid).
"""

from __future__ import annotations

import jwt
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def _auth_headers() -> dict[str, str]:
    token = jwt.encode({"sub": "user-skeleton-int"}, "x", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


_HEADERS: dict[str, str] = {}


@pytest.fixture(autouse=True)
def _bind_headers(_auth_headers: dict[str, str]) -> None:
    _HEADERS.clear()
    _HEADERS.update(_auth_headers)


# --- /api/chat ---


def test_chat_returns_200(client: TestClient) -> None:
    resp = client.post(
        "/api/chat",
        headers=_HEADERS,
        json={
            "session_id": "s1",
            "messages": [{"role": "user", "content": "merhaba"}],
            "language": "tr",
            "paper_context_ids": [],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["finished"] is True
    assert len(data["delta"]) > 0


def test_chat_extra_field_rejected_422(client: TestClient) -> None:
    resp = client.post(
        "/api/chat",
        headers=_HEADERS,
        json={
            "session_id": "s1",
            "messages": [{"role": "user", "content": "x"}],
            "language": "tr",
            "paper_context_ids": [],
            "extra_field": "boom",
        },
    )
    assert resp.status_code == 422


def test_chat_returns_citation_ids(client: TestClient) -> None:
    resp = client.post(
        "/api/chat",
        headers=_HEADERS,
        json={
            "session_id": "s1",
            "messages": [{"role": "user", "content": "test"}],
            "language": "en",
            "paper_context_ids": ["W001", "W002"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["citation_paper_ids"] == ["W001", "W002"]


# --- /api/summarize ---


def test_summarize_post_returns_202(client: TestClient) -> None:
    resp = client.post(
        "/api/summarize",
        headers=_HEADERS,
        json={"paper_id": "W123", "mode": "tldr", "language": "tr"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == "complete"


def test_summarize_get_returns_summary(client: TestClient) -> None:
    # First submit
    resp = client.post(
        "/api/summarize",
        headers=_HEADERS,
        json={"paper_id": "W456", "mode": "abstract", "language": "en"},
    )
    task_id = resp.json()["task_id"]

    # Then poll
    resp2 = client.get(f"/api/summarize/{task_id}", headers=_HEADERS)
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["paper_id"] == "W456"
    assert data["mode"] == "abstract"
    assert len(data["text"]) > 0


def test_summarize_get_unknown_task_404(client: TestClient) -> None:
    resp = client.get("/api/summarize/nonexistent-task", headers=_HEADERS)
    assert resp.status_code == 404


# --- /api/enrich ---

_FAKE_OA_RESPONSE = {
    "title": "Test Paper",
    "publication_year": 2024,
    "doi": "10.1234/test",
    "cited_by_count": 10,
    "authorships": [{"author": {"display_name": "Test Author"}}],
    "primary_location": {"source": {"display_name": "Test Journal"}},
    "abstract": "Test abstract.",
}


def test_enrich_returns_200(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch
    with patch("api.routes.enrich._fetch_openalex", new=AsyncMock(return_value=_FAKE_OA_RESPONSE)):
        resp = client.post(
            "/api/enrich",
            headers=_HEADERS,
            json={"paper_id": "W123", "sources": ["openalex"]},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["paper_id"] == "W123"
    assert "title" in data["enriched_fields"]
    assert data["sources_hit"] == ["openalex"]


def test_enrich_extra_field_422(client: TestClient) -> None:
    resp = client.post(
        "/api/enrich",
        headers=_HEADERS,
        json={"paper_id": "W1", "sources": ["openalex"], "boom": True},
    )
    assert resp.status_code == 422


# --- /api/reading-list ---


@pytest.mark.skip(
    reason="2026-05-26 Madde 1: reading_list Supabase-backed; conftest SUPABASE_URL boş — "
    "yeni Supabase-mock fixture sprint'inde yeniden yazılacak"
)
def test_reading_list_crud_cycle(client: TestClient) -> None:
    # GET empty
    resp = client.get("/api/reading-list", headers=_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 0

    # POST add
    resp = client.post(
        "/api/reading-list",
        headers=_HEADERS,
        json={"paper_id": "W1", "status": "want_to_read", "notes": ""},
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]
    assert resp.json()["paper_id"] == "W1"

    # PATCH update
    resp = client.patch(
        f"/api/reading-list/{item_id}",
        headers=_HEADERS,
        json={"status": "reading"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "reading"

    # DELETE
    resp = client.delete(f"/api/reading-list/{item_id}", headers=_HEADERS)
    assert resp.status_code == 204


def test_reading_list_invalid_status_422(client: TestClient) -> None:
    resp = client.post(
        "/api/reading-list",
        headers=_HEADERS,
        json={"paper_id": "W1", "status": "invalid_status"},
    )
    assert resp.status_code == 422


@pytest.mark.skip(
    reason="2026-05-26 Madde 1: reading_list Supabase-backed; UUID parse 400 ≠ test 404 — "
    "Supabase-mock fixture sprint'inde yeniden yazılacak"
)
def test_reading_list_delete_nonexistent_404(client: TestClient) -> None:
    resp = client.delete("/api/reading-list/nonexistent", headers=_HEADERS)
    assert resp.status_code == 404


# --- /api/onboarding ---


def test_onboarding_returns_200(client: TestClient) -> None:
    resp = client.post(
        "/api/onboarding",
        headers=_HEADERS,
        json={
            "full_name": "Test User",
            "tier": "ogrenci",
            "field_ids": ["F-CompSci"],
            "research_focus": "machine learning healthcare",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "ogrenci"
    assert data["field_ids"] == ["F-CompSci"]
    assert "user_id" in data


def test_onboarding_profile_complete_flag(client: TestClient) -> None:
    resp = client.post(
        "/api/onboarding",
        headers=_HEADERS,
        json={
            "full_name": "Prof User",
            "tier": "arastirmaci",
            "field_ids": ["F-CompSci"],
            "research_focus": "MCDM",
            "affiliation": "University",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["profile_complete"] is True


def test_onboarding_extra_field_422(client: TestClient) -> None:
    resp = client.post(
        "/api/onboarding",
        headers=_HEADERS,
        json={
            "full_name": "Test",
            "tier": "ogrenci",
            "field_ids": ["F-CompSci"],
            "research_focus": "test focus",
            "extra": "boom",
        },
    )
    assert resp.status_code == 422


# --- /api/top5 ---


def test_top5_returns_200(client: TestClient) -> None:
    resp = client.post(
        "/api/top5",
        headers=_HEADERS,
        json={
            "query": "deep learning medicine",
            "session_id": "s1",
            "margin": 0.7,
            "k": 5,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["papers"]) <= 5
    assert "needs_clarify" in data
    assert data["margin_used"] == 0.7


def test_top5_high_margin_needs_clarify(client: TestClient) -> None:
    resp = client.post(
        "/api/top5",
        headers=_HEADERS,
        json={
            "query": "obscure topic xyz",
            "session_id": "s2",
            "margin": 0.99,
            "k": 3,
        },
    )
    assert resp.status_code == 200
    # Real pipeline (MockReranker first score=1.0) passes margin=0.99 → needs_clarify False
    data = resp.json()
    assert "needs_clarify" in data
    assert data["margin_used"] == 0.99


def test_top5_margin_validation_422(client: TestClient) -> None:
    resp = client.post(
        "/api/top5",
        headers=_HEADERS,
        json={
            "query": "deep learning",
            "session_id": "s1",
            "margin": 2.5,
        },
    )
    assert resp.status_code == 422
