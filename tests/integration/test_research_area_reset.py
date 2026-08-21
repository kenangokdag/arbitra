"""F13-S12 — /api/project/{id}/research-area/reset integration tests.

Coverage:
1. Happy path: ilk reset (current_attempt=1, anchor row var) → attempt_no=2 + focuses append
2. Cap reached: current_attempt=10 → 409 attempt_cap_reached
3. K-031 RLS zırh: başka user'ın project_id → 404
4. Anchor row YOK (yeni proje): upsert ile insert + focuses=[] (chat henüz yok)
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
        self._order_col: str | None = None
        self._order_desc: bool = False
        self._on_conflict: str | None = None

    def select(self, _cols: str = "*", **_kw: Any) -> _FakeBuilder:
        self._op = "select"
        return self

    def insert(self, payload: Any) -> _FakeBuilder:
        self._op = "insert"
        self._payload = payload
        return self

    def upsert(
        self, payload: Any, *, on_conflict: str | None = None
    ) -> _FakeBuilder:
        self._op = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def eq(self, col: str, val: Any) -> _FakeBuilder:
        self._filters[col] = val
        return self

    def order(self, col: str, *, desc: bool = False) -> _FakeBuilder:
        self._order_col = col
        self._order_desc = desc
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
            "order_col": self._order_col,
            "order_desc": self._order_desc,
            "on_conflict": self._on_conflict,
        }
        self._rec.calls.append(call)
        return self._rec.respond(call)


class _FakeSupabase:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.projects: list[dict[str, Any]] = []
        self.anchors: list[dict[str, Any]] = []
        self.messages: list[dict[str, Any]] = []

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
        if t == "project_chat_messages" and op == "select":
            rows = [
                m for m in self.messages
                if m["project_id"] == f.get("project_id")
            ]
            if "attempt_no" in f:
                rows = [m for m in rows if int(m["attempt_no"]) == int(f["attempt_no"])]
            if "role" in f:
                rows = [m for m in rows if m["role"] == f["role"]]
            if call["order_col"]:
                rows = sorted(
                    rows,
                    key=lambda r: r.get(call["order_col"]) or 0,
                    reverse=call["order_desc"],
                )
            if call["limit"]:
                rows = rows[: call["limit"]]
            return SimpleNamespace(data=rows)
        if t == "project_anchor" and op == "select":
            rows = [a for a in self.anchors if a["project_id"] == f.get("project_id")]
            return SimpleNamespace(data=rows)
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
        {"id": "prj-1", "user_id": "user-1"},
        {"id": "prj-2", "user_id": "user-other"},
        {"id": "prj-new", "user_id": "user-1"},
        {"id": "prj-cap", "user_id": "user-1"},
    ]
    monkeypatch.setattr("api.routes.research_area._supabase", lambda: fake)

    async def _direct_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)
    yield fake


# ── 1. Happy path: attempt 1 → attempt 2, focuses append ─────────────────────


def test_reset_happy_path_appends_focuses(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    fake_db.messages = [
        {
            "project_id": "prj-1",
            "attempt_no": 1,
            "turn_no": 2,
            "role": "adviser",
            "parsed_understanding": {
                "focuses": ["A", "B", "C"],
                "field": "X",
            },
        }
    ]
    fake_db.anchors = [
        {
            "project_id": "prj-1",
            "rejected_anchors": ["Z"],
            "reject_reasons": ["eski"],
        }
    ]

    r = authed_client.post(
        "/api/project/prj-1/research-area/reset",
        json={"reject_reason": "yön değiştirdim"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["attempt_no"] == 2
    assert body["rejected_count"] == 4  # ["Z","A","B","C"]

    anchor = fake_db.anchors[0]
    assert anchor["rejected_anchors"] == ["Z", "A", "B", "C"]
    assert anchor["reject_reasons"] == ["eski", "yön değiştirdim"]


# ── 2. Cap reached: attempt=10 → 409 ─────────────────────────────────────────


def test_reset_cap_reached_returns_409(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    fake_db.messages = [
        {
            "project_id": "prj-cap",
            "attempt_no": 10,
            "turn_no": 1,
            "role": "user",
            "parsed_understanding": None,
        }
    ]
    r = authed_client.post(
        "/api/project/prj-cap/research-area/reset",
        json={"reject_reason": "son deneme"},
    )
    assert r.status_code == 409, r.text
    assert "attempt_cap_reached" in r.json()["detail"]
    assert fake_db.anchors == []


# ── 3. K-031 RLS zırh: başka user → 404 ──────────────────────────────────────


def test_reset_other_user_returns_404(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    r = authed_client.post(
        "/api/project/prj-2/research-area/reset",
        json={"reject_reason": "test"},
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "project_not_found"
    assert fake_db.anchors == []


# ── 4. Anchor row yok (yeni proje, chat henüz yok) ───────────────────────────


def test_reset_creates_anchor_row_when_missing(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """Hiç chat yok → current_attempt=0 → focuses=[] → upsert insert + attempt=1."""
    r = authed_client.post(
        "/api/project/prj-new/research-area/reset",
        json={"reject_reason": "tekrar düşüneceğim"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["attempt_no"] == 1
    assert body["rejected_count"] == 0

    assert len(fake_db.anchors) == 1
    anchor = fake_db.anchors[0]
    assert anchor["project_id"] == "prj-new"
    assert anchor["rejected_anchors"] == []
    assert anchor["reject_reasons"] == ["tekrar düşüneceğim"]


# ── 5. 401 missing auth ──────────────────────────────────────────────────────


def test_reset_without_auth_returns_401(
    client: TestClient, fake_db: _FakeSupabase
) -> None:
    del fake_db
    r = client.post(
        "/api/project/prj-1/research-area/reset",
        json={"reject_reason": "test"},
    )
    assert r.status_code == 401


# ── 6. Empty reject_reason → 422 ─────────────────────────────────────────────


def test_reset_empty_reason_returns_422(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    del fake_db
    r = authed_client.post(
        "/api/project/prj-1/research-area/reset",
        json={"reject_reason": "   "},
    )
    assert r.status_code == 422
