"""F9 P093 /api/project integration — POST/GET round-trip + miras kopyalama.

Plan: docs/plans/F9_kesif_workbench.md §7 + §12
FakeSupabase recorder pattern test_onboarding_route.py'den paralel:
- user_profile_fields/_subfields/_profiles SELECT döner
- projects INSERT/SELECT executed call'larını kaydeder, mock satır döner
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
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
        self._filters: dict[str, tuple[str, Any]] = {}
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._select_cols: str | None = None

    def select(self, cols: str = "*", **_kw: Any) -> _FakeBuilder:
        self._op = "select"
        self._select_cols = cols
        return self

    def insert(self, payload: Any) -> _FakeBuilder:
        self._op = "insert"
        self._payload = payload
        return self

    def eq(self, col: str, val: Any) -> _FakeBuilder:
        self._filters[col] = ("eq", val)
        return self

    def order(self, col: str, desc: bool = False) -> _FakeBuilder:
        self._order = (col, desc)
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
            "order": self._order,
            "limit": self._limit,
            "select_cols": self._select_cols,
        }
        self._rec.calls.append(call)
        return self._rec.respond(call)


class _FakeSupabase:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.profile_fields: list[str] = []
        self.profile_subfields: list[str] = []
        self.profile_metadata: dict[str, Any] | None = None
        self.projects_listing: list[dict[str, Any]] = []
        # F11 Phase A: GET /api/project/{id} için tek-satır + seed_papers
        self.project_row: dict[str, Any] | None = None
        self.seed_papers_rows: list[dict[str, Any]] = []
        self.seed_papers_inserted: list[dict[str, Any]] = []
        # V1-S16-P001: GET /api/project/{id} parsed_understanding fetch
        self.chat_messages: list[dict[str, Any]] = []
        self._inserted_seq = 0

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)

    def respond(self, call: dict[str, Any]) -> SimpleNamespace:
        t, op = call["table"], call["op"]

        if t == "user_profile_fields" and op == "select":
            return SimpleNamespace(
                data=[{"field_id": fid} for fid in self.profile_fields]
            )
        if t == "user_profile_subfields" and op == "select":
            return SimpleNamespace(
                data=[{"subfield_id": sid} for sid in self.profile_subfields]
            )
        if t == "user_profiles" and op == "select":
            if self.profile_metadata is None:
                return SimpleNamespace(data=[])
            return SimpleNamespace(
                data=[{"metadata": json.dumps(self.profile_metadata)}]
            )
        if t == "projects" and op == "insert":
            self._inserted_seq += 1
            payload = call["payload"]
            now = datetime.now(UTC).isoformat()
            row = {
                "id": f"prj-{self._inserted_seq:04d}",
                "user_id": payload["user_id"],
                "name": payload["name"],
                "status": "active",
                "current_stage": "1.1",
                "inherited_field_ids": payload.get("inherited_field_ids", []),
                "inherited_subfield_ids": payload.get("inherited_subfield_ids", []),
                "inherited_research_focus": payload.get("inherited_research_focus"),
                "seed_query": payload.get("seed_query"),
                "seed_lang": payload.get("seed_lang"),
                "seed_source": payload.get("seed_source", "manual"),
                "created_at": now,
                "updated_at": now,
            }
            return SimpleNamespace(data=[row])
        if t == "projects" and op == "select":
            # GET /{id}: tek satır → project_row, GET /: listing
            if call["filters"].get("id") and self.project_row is not None:
                return SimpleNamespace(data=[self.project_row])
            return SimpleNamespace(data=list(self.projects_listing))
        if t == "project_seed_papers" and op == "insert":
            payload = call["payload"]
            rows = payload if isinstance(payload, list) else [payload]
            self.seed_papers_inserted.extend(rows)
            return SimpleNamespace(data=list(rows))
        if t == "project_seed_papers" and op == "select":
            return SimpleNamespace(data=list(self.seed_papers_rows))
        if t == "project_chat_messages" and op == "select":
            rows = list(self.chat_messages)
            f = call["filters"]
            if "project_id" in f:
                rows = [r for r in rows if r.get("project_id") == f["project_id"][1]]
            if "role" in f:
                rows = [r for r in rows if r.get("role") == f["role"][1]]
            order = call.get("order")
            if order:
                col, desc = order
                rows = sorted(rows, key=lambda r: r.get(col) or 0, reverse=desc)
            limit = call.get("limit")
            if limit:
                rows = rows[:limit]
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=[])


@pytest.fixture
def auth_token() -> str:
    return jwt.encode({"sub": "user-prj-1"}, "x", algorithm="HS256")


@pytest.fixture
def authed_client(client: TestClient, auth_token: str) -> TestClient:
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeSupabase]:
    fake = _FakeSupabase()
    monkeypatch.setattr("api.routes.project._supabase", lambda: fake)

    async def _direct_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109 — mock signature
    ) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)
    yield fake


# ── 1. POST happy: miras 3 alan boş → ProjectRead 201 ────────────────────────


def test_post_project_201_with_empty_inheritance(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """Onboarding profili yok → inherited_* boş, 201 + ProjectRead."""
    response = authed_client.post("/api/project", json={"name": "Test Proje"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Test Proje"
    assert body["status"] == "active"
    assert body["current_stage"] == "1.1"
    assert body["inherited_field_ids"] == []
    assert body["inherited_subfield_ids"] == []
    assert body["inherited_research_focus"] is None
    assert body["anchor"] is None

    ops = [(c["table"], c["op"]) for c in fake_db.calls]
    assert ops == [
        ("user_profile_fields", "select"),
        ("user_profile_subfields", "select"),
        ("user_profiles", "select"),
        ("projects", "insert"),
    ]
    insert_payload = fake_db.calls[3]["payload"]
    assert insert_payload["user_id"] == "user-prj-1"
    assert insert_payload["name"] == "Test Proje"


def test_post_project_201_inherits_full_profile(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """Full miras path: 2 field + 2 subfield + research_focus_en kopyalanır."""
    fake_db.profile_fields = ["medicine", "computer_science"]
    fake_db.profile_subfields = ["pharmacology", "ml"]
    fake_db.profile_metadata = {
        "research_focus": "Yapay zekâ ile literatür tarama",
        "research_focus_en": "AI-driven literature retrieval",
    }
    response = authed_client.post("/api/project", json={"name": "Miras"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["inherited_field_ids"] == ["medicine", "computer_science"]
    assert body["inherited_subfield_ids"] == ["pharmacology", "ml"]
    assert body["inherited_research_focus"] == "AI-driven literature retrieval"

    insert_payload = fake_db.calls[3]["payload"]
    assert insert_payload["inherited_field_ids"] == ["medicine", "computer_science"]
    assert insert_payload["inherited_subfield_ids"] == ["pharmacology", "ml"]
    assert (
        insert_payload["inherited_research_focus"] == "AI-driven literature retrieval"
    )


# ── 2. POST name='' → 422 (Pydantic, DB'siz) ─────────────────────────────────


def test_post_project_empty_name_422(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    response = authed_client.post("/api/project", json={"name": ""})
    assert response.status_code == 422
    assert fake_db.calls == []


# ── 3. GET / → 200 + ProjectListItem[] DESC by updated_at ────────────────────


def test_get_projects_returns_listing_desc(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """2 fixture proje, updated_at DESC sırasında list'leme."""
    now = datetime.now(UTC)
    older = (now - timedelta(hours=2)).isoformat()
    newer = now.isoformat()
    fake_db.projects_listing = [
        {
            "id": "p-newer",
            "name": "Yeni",
            "status": "active",
            "current_stage": "1.1",
            "updated_at": newer,
        },
        {
            "id": "p-older",
            "name": "Eski",
            "status": "active",
            "current_stage": "1.1",
            "updated_at": older,
        },
    ]
    response = authed_client.get("/api/project")
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 2
    assert [r["id"] for r in body] == ["p-newer", "p-older"]
    assert all(r["status"] == "active" for r in body)

    select_call = fake_db.calls[0]
    assert select_call["table"] == "projects"
    assert select_call["op"] == "select"
    assert select_call["filters"]["user_id"] == ("eq", "user-prj-1")
    assert select_call["order"] == ("updated_at", True)
    assert (
        select_call["select_cols"]
        == "id,name,status,current_stage,updated_at"
    )


# ── 4. F11 Phase A — POST /api/project/from-q happy path ─────────────────────


def test_post_project_from_q_creates_project_and_seed_papers(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """Q'dan dönüştürme: projects insert (seed_*='q') + seed_papers bulk insert."""
    # Onboarding profili boş — sadece Q'dan miras kontrol ediliyor.
    body = {
        "q_query": "bahasa indonesia mcdm",
        "q_lang": "tr",
        "selected_paper_ids": ["W123", "W456", "W789"],
    }
    response = authed_client.post("/api/project/from-q", json=body)
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["seed_query"] == "bahasa indonesia mcdm"
    assert payload["seed_paper_count"] == 3
    assert payload["project_id"].startswith("prj-")

    # 3 onboarding select + 1 projects insert + 1 seed_papers insert = 5 call
    ops = [(c["table"], c["op"]) for c in fake_db.calls]
    assert ops == [
        ("user_profile_fields", "select"),
        ("user_profile_subfields", "select"),
        ("user_profiles", "select"),
        ("projects", "insert"),
        ("project_seed_papers", "insert"),
    ]
    proj_payload = fake_db.calls[3]["payload"]
    assert proj_payload["seed_query"] == "bahasa indonesia mcdm"
    assert proj_payload["seed_lang"] == "tr"
    assert proj_payload["seed_source"] == "q"
    assert proj_payload["name"].startswith("Q: ")
    assert "bahasa" in proj_payload["name"]

    seed_payload = fake_db.calls[4]["payload"]
    assert isinstance(seed_payload, list)
    assert len(seed_payload) == 3
    assert {row["paper_id"] for row in seed_payload} == {"W123", "W456", "W789"}
    assert all(row["source_query"] == "bahasa indonesia mcdm" for row in seed_payload)
    assert all(row["source_lang"] == "tr" for row in seed_payload)


# ── 5. F11 Phase A — GET /api/project/{id} seed_paper_count döner ────────────


def test_get_project_includes_seed_query_and_count(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    now = datetime.now(UTC).isoformat()
    fake_db.project_row = {
        "id": "prj-0042",
        "user_id": "user-prj-1",
        "name": "Q: bahasa",
        "status": "active",
        "current_stage": "1.1",
        "inherited_field_ids": [],
        "inherited_subfield_ids": [],
        "inherited_research_focus": None,
        "seed_query": "bahasa indonesia mcdm",
        "seed_lang": "tr",
        "seed_source": "q",
        "created_at": now,
        "updated_at": now,
    }
    fake_db.seed_papers_rows = [
        {"paper_id": "W123"},
        {"paper_id": "W456"},
        {"paper_id": "W789"},
    ]
    response = authed_client.get("/api/project/prj-0042")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["seed_query"] == "bahasa indonesia mcdm"
    assert body["seed_lang"] == "tr"
    assert body["seed_source"] == "q"
    assert body["seed_paper_count"] == 3


# ── 6. V1-S16-P001 — GET parsed_understanding son adviser turn'den döner ─────


def test_get_project_returns_parsed_understanding_when_chat_exists(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """Son adviser turn (en yüksek attempt+turn) parsed_understanding döner."""
    now = datetime.now(UTC).isoformat()
    fake_db.project_row = {
        "id": "prj-pu-1",
        "user_id": "user-prj-1",
        "name": "PU Test",
        "status": "active",
        "current_stage": "1.1",
        "inherited_field_ids": [],
        "inherited_subfield_ids": [],
        "inherited_research_focus": None,
        "seed_query": None,
        "seed_lang": None,
        "seed_source": "manual",
        "created_at": now,
        "updated_at": now,
    }
    fake_db.chat_messages = [
        {
            "project_id": "prj-pu-1",
            "attempt_no": 1,
            "turn_no": 1,
            "role": "adviser",
            "parsed_understanding": {
                "focuses": ["A", "B", "C"],
                "field": "X",
                "confidence": "low",
            },
        },
        {
            "project_id": "prj-pu-1",
            "attempt_no": 1,
            "turn_no": 2,
            "role": "adviser",
            "parsed_understanding": {
                "focuses": ["A1", "B1", "C1"],
                "field": "X1",
                "confidence": "high",
            },
        },
        {
            "project_id": "prj-pu-1",
            "attempt_no": 1,
            "turn_no": 1,
            "role": "user",
            "parsed_understanding": None,
        },
    ]
    response = authed_client.get("/api/project/prj-pu-1")
    assert response.status_code == 200, response.text
    body = response.json()
    pu = body["parsed_understanding"]
    assert pu is not None
    assert pu["focuses"] == ["A1", "B1", "C1"]
    assert pu["confidence"] == "high"


def test_get_project_parsed_understanding_null_when_no_chat(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """Adviser turn yoksa parsed_understanding=None."""
    now = datetime.now(UTC).isoformat()
    fake_db.project_row = {
        "id": "prj-pu-2",
        "user_id": "user-prj-1",
        "name": "Empty Chat",
        "status": "active",
        "current_stage": "1.1",
        "inherited_field_ids": [],
        "inherited_subfield_ids": [],
        "inherited_research_focus": None,
        "seed_query": None,
        "seed_lang": None,
        "seed_source": "manual",
        "created_at": now,
        "updated_at": now,
    }
    response = authed_client.get("/api/project/prj-pu-2")
    assert response.status_code == 200, response.text
    assert response.json()["parsed_understanding"] is None
