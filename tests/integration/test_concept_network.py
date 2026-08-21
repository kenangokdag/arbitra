"""V1-S17 P003 — GET /api/project/{id}/concept-network integration test.

Plan: docs/plans/V1_S17_cascade_5rc.md §4 C003 — `pytest tests/integration/test_concept_network.py -q` PASS.

Coverage:
1. cluster_status='ready' + 4 abstract → 200 body shape (nodes + edges)
2. cluster_status='pending' → 409 cluster_not_ready
3. başka user → 404 project_not_found
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
        self._filters: dict[str, Any] = {}
        self._in_filters: dict[str, list[Any]] = {}
        self._limit: int | None = None

    def select(self, _cols: str = "*", **_kw: Any) -> _FakeBuilder:
        self._op = "select"
        return self

    def eq(self, col: str, val: Any) -> _FakeBuilder:
        self._filters[col] = val
        return self

    def in_(self, col: str, vals: list[Any]) -> _FakeBuilder:
        self._in_filters[col] = list(vals)
        return self

    def limit(self, n: int) -> _FakeBuilder:
        self._limit = n
        return self

    def execute(self) -> SimpleNamespace:
        return self._rec.respond(
            {
                "table": self._table,
                "op": self._op,
                "filters": dict(self._filters),
                "in_filters": dict(self._in_filters),
                "limit": self._limit,
            }
        )


class _FakeSupabase:
    def __init__(self) -> None:
        self.projects: list[dict[str, Any]] = []
        self.anchors: list[dict[str, Any]] = []
        self.clusters: list[dict[str, Any]] = []
        self.papers: list[dict[str, Any]] = []

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)

    def respond(self, call: dict[str, Any]) -> SimpleNamespace:
        t, op, f, inf = (
            call["table"],
            call["op"],
            call["filters"],
            call["in_filters"],
        )
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
        if t == "papers" and op == "select":
            ids = set(inf.get("paper_id") or [])
            rows = [p for p in self.papers if p.get("paper_id") in ids]
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
        {"id": "prj-pending", "user_id": "user-1", "current_stage": "2.2"},
        {"id": "prj-other", "user_id": "user-other", "current_stage": "2.2"},
    ]
    fake.anchors = [
        {
            "project_id": "prj-ready",
            "anchor_paper_id": "W_anchor",
            "cluster_status": "ready",
        },
        {
            "project_id": "prj-pending",
            "anchor_paper_id": "W_anchor",
            "cluster_status": "pending",
        },
    ]
    fake.clusters = [
        {"project_id": "prj-ready", "paper_id": "W1"},
        {"project_id": "prj-ready", "paper_id": "W2"},
        {"project_id": "prj-ready", "paper_id": "W3"},
        {"project_id": "prj-ready", "paper_id": "W4"},
    ]
    fake.papers = [
        {
            "paper_id": "W1",
            "abstract": "Deep learning neural networks improve medical imaging segmentation.",
        },
        {
            "paper_id": "W2",
            "abstract": "Neural networks and transformers advance medical imaging classification.",
        },
        {
            "paper_id": "W3",
            "abstract": "Transformer based deep learning applied to clinical decision support.",
        },
        {
            "paper_id": "W4",
            "abstract": "Medical imaging segmentation with transformers and reinforcement learning.",
        },
    ]

    monkeypatch.setattr("api.routes.project_graph._supabase", lambda: fake)

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
    yield fake


# ── 1. Happy 200 — nodes + edges ─────────────────────────────────────────────


def test_concept_network_ready_returns_nodes_and_edges(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    del fake_db
    r = authed_client.get("/api/project/prj-ready/concept-network")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == "prj-ready"
    assert body["anchor_paper_id"] == "W_anchor"
    assert body["paper_count"] == 4
    assert isinstance(body["nodes"], list) and body["nodes"], "node listesi boş"
    assert isinstance(body["edges"], list) and body["edges"], "edge listesi boş"
    for n in body["nodes"]:
        assert set(n.keys()) == {"id", "label", "weight", "doc_count"}
    for e in body["edges"]:
        assert set(e.keys()) == {"source", "target", "weight"}
        assert 0.15 <= e["weight"] <= 1.0


# ── 2. cluster_status='pending' → 409 ─────────────────────────────────────────


def test_concept_network_cluster_not_ready_returns_409(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    del fake_db
    r = authed_client.get("/api/project/prj-pending/concept-network")
    assert r.status_code == 409, r.text
    assert "cluster_not_ready" in r.json()["detail"]


# ── 3. başka user → 404 ───────────────────────────────────────────────────────


def test_concept_network_other_user_returns_404(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    del fake_db
    r = authed_client.get("/api/project/prj-other/concept-network")
    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "project_not_found"
