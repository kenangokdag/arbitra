"""V1-S17 P002 — cluster/expand + cluster/status integration tests.

Plan: docs/plans/V1_S17_cascade_5rc.md §4 C002 — 3 integration test PASS gate.

Coverage:
1. POST /cluster/expand happy → 202 + BG queued + response shape
2. POST /cluster/expand anchor yok → 409 anchor_not_locked
3. GET /cluster/status — ready durumda size>0, started/completed/error doğru map
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

    def select(self, _cols: str = "*", **_kw: Any) -> _FakeBuilder:
        self._op = "select"
        return self

    def update(self, payload: Any) -> _FakeBuilder:
        self._op = "update"
        self._payload = payload
        return self

    def insert(self, payload: Any) -> _FakeBuilder:
        self._op = "insert"
        self._payload = payload
        return self

    def delete(self) -> _FakeBuilder:
        self._op = "delete"
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
        }
        self._rec.calls.append(call)
        return self._rec.respond(call)


class _FakeSupabase:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.projects: list[dict[str, Any]] = []
        self.anchors: list[dict[str, Any]] = []
        self.clusters: list[dict[str, Any]] = []

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)

    def respond(self, call: dict[str, Any]) -> SimpleNamespace:
        t, op, f = call["table"], call["op"], call["filters"]
        if t == "projects" and op == "select":
            rows = [
                p
                for p in self.projects
                if p["id"] == f.get("id")
                and ("user_id" not in f or p["user_id"] == f["user_id"])
            ]
            return SimpleNamespace(data=rows)
        if t == "project_anchor" and op == "select":
            rows = [
                a for a in self.anchors if a.get("project_id") == f.get("project_id")
            ]
            return SimpleNamespace(data=rows)
        if t == "project_cluster" and op == "select":
            rows = [
                c for c in self.clusters if c.get("project_id") == f.get("project_id")
            ]
            return SimpleNamespace(data=rows)
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
        {"id": "prj-ready", "user_id": "user-1", "current_stage": "2.2"},
        {"id": "prj-noanchor", "user_id": "user-1", "current_stage": "1.1"},
    ]
    fake.anchors = [
        {
            "project_id": "prj-ready",
            "anchor_paper_id": "W_anchor",
            "cluster_status": "ready",
            "cluster_started_at": "2026-05-26T22:00:00+00:00",
            "cluster_completed_at": "2026-05-26T22:00:05+00:00",
            "cluster_error": None,
        },
    ]
    fake.clusters = [
        {"project_id": "prj-ready", "paper_id": f"W{i}"} for i in range(1, 6)
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

    bg_calls: list[str] = []

    async def _bg_noop(project_id: str) -> None:
        bg_calls.append(project_id)

    monkeypatch.setattr(
        "api.routes.research_area._run_cluster_expander_bg", _bg_noop
    )
    fake.bg_calls = bg_calls  # type: ignore[attr-defined]
    yield fake


# ── 1. POST /cluster/expand happy path → 202 + BG queued ──────────────────────


def test_cluster_expand_happy_202(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    r = authed_client.post("/api/project/prj-ready/cluster/expand")
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["project_id"] == "prj-ready"
    assert body["anchor_paper_id"] == "W_anchor"
    assert body["cluster_status"] == "expanding"
    assert isinstance(body["accepted_at"], str) and body["accepted_at"]
    assert fake_db.bg_calls == ["prj-ready"]  # type: ignore[attr-defined]


# ── 2. POST /cluster/expand anchor yok → 409 ──────────────────────────────────


def test_cluster_expand_without_anchor_409(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    r = authed_client.post("/api/project/prj-noanchor/cluster/expand")
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "anchor_not_locked"
    assert fake_db.bg_calls == []  # type: ignore[attr-defined]


# ── 3. GET /cluster/status — ready durumda size + timestamps ─────────────────


def test_cluster_status_ready_shape(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    r = authed_client.get("/api/project/prj-ready/cluster/status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {
        "project_id": "prj-ready",
        "anchor_paper_id": "W_anchor",
        "cluster_status": "ready",
        "cluster_size": 5,
        "started_at": "2026-05-26T22:00:00+00:00",
        "completed_at": "2026-05-26T22:00:05+00:00",
        "cluster_error": None,
    }
