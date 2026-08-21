"""F9 P094 /api/project/{id}/research-area/messages integration tests.

Plan: docs/plans/F9_kesif_workbench.md §12 (test stratejisi, 2 integration)
Coverage:
1. 2-tur dialog happy: tur 1 (finished=False) → tur 2 (finished=True)
   → project_chat_messages tablosunda 4 row (2 user + 2 adviser)
2. K-031 RLS zırh: başka user'ın project_id'i ile POST → 404 (UX güvenli)
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


# ── FakeSupabase recorder (project + project_anchor + project_chat_messages) ─


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

    def insert(self, payload: Any) -> _FakeBuilder:
        self._op = "insert"
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
        if t == "project_anchor" and op == "select":
            rows = [a for a in self.anchors if a["project_id"] == f.get("project_id")]
            return SimpleNamespace(data=rows)
        if t == "project_chat_messages" and op == "select":
            rows = [
                m for m in self.messages
                if m["project_id"] == f.get("project_id")
                and int(m["attempt_no"]) == int(f.get("attempt_no", 0))
                and m["role"] == f.get("role", m["role"])
            ]
            return SimpleNamespace(data=rows)
        if t == "project_chat_messages" and op == "insert":
            for row in call["payload"]:
                self.messages.append(dict(row))
            return SimpleNamespace(data=list(call["payload"]))
        return SimpleNamespace(data=[])


def _fake_completion_response(json_payload: dict[str, Any]) -> Any:
    class _Msg:
        def __init__(self, c: str) -> None:
            self.content = c

    class _Choice:
        def __init__(self, c: str) -> None:
            self.message = _Msg(c)

    class _Usage:
        prompt_tokens = 110
        completion_tokens = 55

    class _Resp:
        def __init__(self, c: str) -> None:
            self.choices = [_Choice(c)]
            self.usage = _Usage()

    return _Resp(json.dumps(json_payload, ensure_ascii=False))


# ── Fixtures ─────────────────────────────────────────────────────────────────


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
        {
            "id": "prj-1",
            "user_id": "user-1",
            "name": "Test",
            "inherited_field_ids": ["engineering"],
            "inherited_subfield_ids": [],
            "inherited_research_focus": None,
        },
        # K-031 testi: başka user'ın projesi
        {
            "id": "prj-2",
            "user_id": "user-other",
            "name": "Başkasının",
            "inherited_field_ids": [],
            "inherited_subfield_ids": [],
            "inherited_research_focus": None,
        },
    ]
    monkeypatch.setattr("api.routes.research_area._supabase", lambda: fake)

    async def _direct_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109 — mock signature
    ) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)
    yield fake


@pytest.fixture
def llm_payloads(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Tur 1: finished=False; Tur 2: finished=True. acompletion mock'u."""
    state: dict[str, Any] = {"call_count": 0}

    base_payload: dict[str, Any] = {
        "focuses": [
            "ÇKKV ile akreditasyon kriterlerinin ağırlıklandırılması",
            "Yükseköğretim akreditasyonunda metodoloji karşılaştırması",
            "Akreditasyon süreçlerinde ÇKKV uygulama vakaları",
        ],
        "field": "Mühendislik",
        "subfield": "Endüstri Mühendisliği",
        "interdisc": True,
        "confidence": "med",
        "adviser_text": "Bu üç odakla devam edebilir miyiz?",
        "finished": False,
    }

    async def fake_acompletion(**_: Any) -> Any:
        state["call_count"] = int(state["call_count"]) + 1
        # Tur 2: finished=True dön
        payload = dict(base_payload)
        if state["call_count"] >= 2:
            payload["finished"] = True
            payload["adviser_text"] = "Tamam, bu üç odakla devam ediyoruz."
        return _fake_completion_response(payload)

    monkeypatch.setattr("api.services.llm_service.acompletion", fake_acompletion)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    return state


# ── 1. 2-tur dialog happy: 4 row (2 user + 2 adviser) ────────────────────────


def test_two_turn_dialog_persists_four_rows(
    authed_client: TestClient,
    fake_db: _FakeSupabase,
    llm_payloads: dict[str, Any],
) -> None:
    """Tur 1 (finished=False) + Tur 2 (finished=True) → 4 chat row."""
    # Tur 1
    r1 = authed_client.post(
        "/api/project/prj-1/research-area/messages",
        json={"content": "yükseköğretimde kalite akreditasyonu için ÇKKV", "attempt_no": 1},
    )
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["turn_no"] == 1
    assert body1["finished"] is False
    assert len(body1["parsed_understanding"]["focuses"]) == 3

    # Tur 2 — model finished=True dönecek (mock)
    r2 = authed_client.post(
        "/api/project/prj-1/research-area/messages",
        json={"content": "evet bu üçle devam edelim", "attempt_no": 1},
    )
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["turn_no"] == 2
    assert body2["finished"] is True

    # 4 row: 2 user + 2 adviser
    assert len(fake_db.messages) == 4
    roles = [m["role"] for m in fake_db.messages]
    assert roles == ["user", "adviser", "user", "adviser"]
    turn_nos = [int(m["turn_no"]) for m in fake_db.messages]
    assert turn_nos == [1, 1, 2, 2]
    attempts = [int(m["attempt_no"]) for m in fake_db.messages]
    assert all(a == 1 for a in attempts)

    # acompletion 2 kez çağrılmış
    assert llm_payloads["call_count"] == 2


# ── 2. K-031 RLS zırh: başka user'ın project_id → 404 ────────────────────────


def test_other_user_project_returns_404(
    authed_client: TestClient,
    fake_db: _FakeSupabase,
    llm_payloads: dict[str, Any],
) -> None:
    """user-1 token + prj-2 (user-other'a ait) → manuel .eq zırhı 404."""
    del llm_payloads  # llm fixture sadece monkeypatch için
    r = authed_client.post(
        "/api/project/prj-2/research-area/messages",
        json={"content": "deneme", "attempt_no": 1},
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "project_not_found"

    # K-031 doğrulama: projects SELECT'inde user_id=user-1 filter olmalı
    proj_select = next(
        c for c in fake_db.calls
        if c["table"] == "projects" and c["op"] == "select"
    )
    assert proj_select["filters"]["id"] == "prj-2"
    assert proj_select["filters"]["user_id"] == "user-1"

    # INSERT olmamalı (proje doğrulaması düştü)
    inserts = [c for c in fake_db.calls if c["op"] == "insert"]
    assert inserts == []
    # chat_messages dokunulmadı
    assert fake_db.messages == []
