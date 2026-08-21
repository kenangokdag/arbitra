"""V1-S15.pre A1-P003 — POST /api/project/{id}/research-area/anchor/lock integration tests.

Coverage (Omer 2026-05-26 karar):
1. Happy path 1.1 → 2.2 advance + UPSERT
2. Idempotent re-lock at 2.5 (stage dokunulmaz)
3. Frozen 3.1 → 409 stage_frozen
4. Başka user → 404 project_not_found
5. Auth header yok → 401
6. paper_id boş → 422
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


class _FakeBuilder:
    def __init__(self, recorder: _FakeSupabase, table: str) -> None:
        self._rec = recorder
        self._table = table
        self._op: str | None = None
        self._payload: Any = None
        self._filters: dict[str, Any] = {}
        self._limit: int | None = None
        self._on_conflict: str | None = None

    def select(self, _cols: str = "*", **_kw: Any) -> _FakeBuilder:
        self._op = "select"
        return self

    def upsert(
        self, payload: Any, *, on_conflict: str | None = None
    ) -> _FakeBuilder:
        self._op = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def update(self, payload: Any) -> _FakeBuilder:
        self._op = "update"
        self._payload = payload
        return self

    def eq(self, col: str, val: Any) -> _FakeBuilder:
        self._filters[col] = val
        return self

    def limit(self, n: int) -> _FakeBuilder:
        self._limit = n
        return self

    def execute(self) -> SimpleNamespace:
        call = {
            "table": self._table,
            "op": self._op,
            "payload": self._payload,
            "filters": dict(self._filters),
            "limit": self._limit,
            "on_conflict": self._on_conflict,
        }
        self._rec.calls.append(call)
        return self._rec.respond(call)


class _FakeSupabase:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.projects: list[dict[str, Any]] = []
        self.anchors: list[dict[str, Any]] = []

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)

    def respond(self, call: dict[str, Any]) -> SimpleNamespace:
        t, op, f = call["table"], call["op"], call["filters"]
        if t == "projects" and op == "select":
            rows = [
                p for p in self.projects
                if p["id"] == f.get("id") and p["user_id"] == f.get("user_id")
            ]
            return SimpleNamespace(data=rows)
        if t == "projects" and op == "update":
            for p in self.projects:
                if p["id"] == f.get("id"):
                    p.update(call["payload"])
            return SimpleNamespace(data=[])
        if t == "project_anchor" and op == "upsert":
            payload = call["payload"]
            pid = payload["project_id"]
            existing = next(
                (a for a in self.anchors if a["project_id"] == pid), None
            )
            if existing is None:
                self.anchors.append(dict(payload))
            else:
                existing.update(payload)
            return SimpleNamespace(data=[payload])
        return SimpleNamespace(data=[])


@pytest.fixture
def auth_token() -> str:
    return jwt.encode({"sub": "user-1"}, "x", algorithm="HS256")


@pytest.fixture
def authed_client(client: TestClient, auth_token: str) -> TestClient:
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeSupabase]:
    fake = _FakeSupabase()
    fake.projects = [
        {"id": "prj-1", "user_id": "user-1", "current_stage": "1.1"},
        {"id": "prj-mid", "user_id": "user-1", "current_stage": "2.5"},
        {"id": "prj-frozen", "user_id": "user-1", "current_stage": "3.1"},
        {"id": "prj-other", "user_id": "user-other", "current_stage": "1.1"},
    ]
    monkeypatch.setattr("api.routes.research_area._supabase", lambda: fake)

    async def _direct_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr(
        "api.db.supabase_client.supabase_call_async", _direct_call
    )

    # V1-S17 P002 — anchor/lock 202 + BackgroundTask cluster_expander tetikliyor;
    # bu test dosyası lock kontratını izole tutmak için BG'yi no-op'a sabitler.
    async def _bg_noop(_project_id: str) -> None:
        return None

    monkeypatch.setattr(
        "api.routes.research_area._run_cluster_expander_bg", _bg_noop
    )
    yield fake


# ── 1. Happy path 1.1 → 2.2 advance + UPSERT ─────────────────────────────────


def test_lock_happy_path_advances_stage(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    r = authed_client.post(
        "/api/project/prj-1/research-area/anchor/lock",
        json={"paper_id": "W123"},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["anchor_paper_id"] == "W123"
    assert body["cluster_status"] == "pending"
    assert isinstance(body["locked_at"], str) and body["locked_at"]

    assert len(fake_db.anchors) == 1
    assert fake_db.anchors[0]["anchor_paper_id"] == "W123"
    assert fake_db.anchors[0]["cluster_status"] == "pending"

    prj = next(p for p in fake_db.projects if p["id"] == "prj-1")
    assert prj["current_stage"] == "2.2"


# ── 2. Idempotent re-lock at 2.5 (stage dokunulmaz) ──────────────────────────


def test_lock_idempotent_relock_keeps_stage(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    fake_db.anchors = [
        {
            "project_id": "prj-mid",
            "anchor_paper_id": "W_OLD",
            "locked_at": "2026-05-25T10:00:00+00:00",
            "cluster_status": "pending",
        }
    ]
    r = authed_client.post(
        "/api/project/prj-mid/research-area/anchor/lock",
        json={"paper_id": "W_NEW"},
    )
    assert r.status_code == 202, r.text
    assert r.json()["anchor_paper_id"] == "W_NEW"

    assert fake_db.anchors[0]["anchor_paper_id"] == "W_NEW"
    prj = next(p for p in fake_db.projects if p["id"] == "prj-mid")
    assert prj["current_stage"] == "2.5"


# ── 3. Frozen 3.1 → 409 stage_frozen ─────────────────────────────────────────


def test_lock_frozen_stage_returns_409(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    r = authed_client.post(
        "/api/project/prj-frozen/research-area/anchor/lock",
        json={"paper_id": "W123"},
    )
    assert r.status_code == 409, r.text
    assert "stage_frozen" in r.json()["detail"]
    assert fake_db.anchors == []
    prj = next(p for p in fake_db.projects if p["id"] == "prj-frozen")
    assert prj["current_stage"] == "3.1"


# ── 4. Başka user → 404 ───────────────────────────────────────────────────────


def test_lock_other_user_returns_404(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    r = authed_client.post(
        "/api/project/prj-other/research-area/anchor/lock",
        json={"paper_id": "W123"},
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "project_not_found"
    assert fake_db.anchors == []


# ── 5. Auth yok → 401 ─────────────────────────────────────────────────────────


def test_lock_without_auth_returns_401(
    client: TestClient, fake_db: _FakeSupabase
) -> None:
    del fake_db
    r = client.post(
        "/api/project/prj-1/research-area/anchor/lock",
        json={"paper_id": "W123"},
    )
    assert r.status_code == 401


# ── 6. paper_id boş → 422 ─────────────────────────────────────────────────────


def test_lock_empty_paper_id_returns_422(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    del fake_db
    r = authed_client.post(
        "/api/project/prj-1/research-area/anchor/lock",
        json={"paper_id": "   "},
    )
    assert r.status_code == 422
