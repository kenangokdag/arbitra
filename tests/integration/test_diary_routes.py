"""F13-S1-P003 — /api/diary/* integration tests.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (5 integration + live smoke fixture)
Strateji: TestClient + JWT (HS256("x")) + diary_service monkeypatch.
SUPABASE config testte boş (conftest) → SUPABASE_URL/SECRET_KEY override
ile route'un _ensure_supabase guard'ı aşılır; service çağrısı bypass edilir.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

_USER_ID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = jwt.encode({"sub": _USER_ID}, "x", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patched_supabase(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """SUPABASE config'ı doldur (route guard pass) + service'i mock'la.

    Returns: shared {"data": [...]} dict — testler doldurabilir.
    """
    monkeypatch.setenv("SUPABASE_URL", "http://test.local")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test-key")
    from api.config import get_settings

    get_settings.cache_clear()

    state: dict[str, Any] = {"data": [], "last_fn": None}

    async def _fake_call(fn: Any, *, timeout: float | None = None) -> Any:
        state["last_fn"] = fn
        return SimpleNamespace(data=state["data"])

    from api.services import diary_service

    monkeypatch.setattr(diary_service, "supabase_call_async", _fake_call)
    monkeypatch.setattr(diary_service, "get_supabase_admin", lambda: SimpleNamespace())
    return state


def _row(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "user_id": _USER_ID,
        "page_slug": "S1_arastirma_defteri",
        "paper_id": None,
        "event_type": "kayit",
        "payload": {"note": "test"},
        "created_at": datetime.now(UTC).isoformat(),
        "resolved_at": None,
    }
    base.update(overrides)
    return base


# ── Test 1: POST /api/diary/event happy path → 201 ──────────────────────────
def test_post_event_happy(
    client: TestClient,
    auth_headers: dict[str, str],
    patched_supabase: dict[str, Any],
) -> None:
    inserted = _row(event_type="kayit", page_slug="5.1_yayin_formati")
    patched_supabase["data"] = [inserted]

    resp = client.post(
        "/api/diary/event",
        headers=auth_headers,
        json={
            "project_id": str(uuid4()),
            "page_slug": "5.1_yayin_formati",
            "event_type": "kayit",
            "payload": {"karar": "makale"},
        },
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["event_type"] == "kayit"
    assert body["user_id"] == _USER_ID


# ── Test 2: POST without auth → 401 ──────────────────────────────────────────
def test_post_event_no_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/diary/event",
        json={
            "project_id": str(uuid4()),
            "page_slug": "x",
            "event_type": "not",
            "payload": {},
        },
    )
    assert resp.status_code == 401


# ── Test 3: GET /api/diary/timeline + project_id filter → 200 ───────────────
def test_get_timeline_filtered(
    client: TestClient,
    auth_headers: dict[str, str],
    patched_supabase: dict[str, Any],
) -> None:
    project_id = uuid4()
    rows = [_row(project_id=str(project_id)) for _ in range(3)]
    patched_supabase["data"] = rows

    resp = client.get(
        f"/api/diary/timeline?project_id={project_id}", headers=auth_headers
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    assert body["next_cursor"] is None
    assert all(item["project_id"] == str(project_id) for item in body["items"])


# ── Test 4: PATCH ownership fail (0 rows) → 404 ─────────────────────────────
def test_patch_event_not_found(
    client: TestClient,
    auth_headers: dict[str, str],
    patched_supabase: dict[str, Any],
) -> None:
    patched_supabase["data"] = []  # update returned 0 rows

    resp = client.patch(
        f"/api/diary/event/{uuid4()}",
        headers=auth_headers,
        json={"payload": {"note": "yeni"}},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "event_not_found"


# ── Test 5: PATCH resolve (resolved_at=now) → 200 ────────────────────────────
def test_patch_event_resolve(
    client: TestClient,
    auth_headers: dict[str, str],
    patched_supabase: dict[str, Any],
) -> None:
    resolved_at = datetime.now(UTC)
    updated = _row(resolved_at=resolved_at.isoformat())
    patched_supabase["data"] = [updated]

    resp = client.patch(
        f"/api/diary/event/{uuid4()}",
        headers=auth_headers,
        json={"resolved_at": resolved_at.isoformat()},
    )

    assert resp.status_code == 200
    assert resp.json()["resolved_at"] is not None


# ── Fixture-based smoke: response shape doğrulaması ──────────────────────────
def test_fixture_shape_validates() -> None:
    """tests/fixtures/diary_event_v1.json model_validate ile parse edilir.

    Live smoke: bu fixture canlı Supabase round-trip'inden alınmıştır
    (insert→read→patch); şema değişikliklerinde regen gerekir.
    """
    from api.models.diary import DiaryEvent

    fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "diary_event_v1.json"
    )
    with fixture.open() as f:
        payload = json.load(f)

    event = DiaryEvent.model_validate(payload)
    assert event.event_type in ("kayit", "danismana_sor", "kutuphane_ekle", "not")
