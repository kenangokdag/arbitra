"""F9 P094 librarian role_module unit tests.

Plan: docs/plans/F9_kesif_workbench.md §12 (test stratejisi, 6 unit)
Coverage:
1. Tur 1 happy (ÇKKV akreditasyon → 3 focus + field=Mühendislik + finished=False)
2. Tur 2 düzeltme (turn_no=2, parsed güncellenir, finished=True cap)
3. Reset hafıza (rejected_focuses + reject_reasons page_state'e enjekte)
4. Gemini provider fail → LLMServiceError zarflandı
5. ParsedUnderstanding şema invalid JSON → ValidationError → LLMServiceError
6. extra=forbid: route 422 (TestClient)
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from api.models.research_area import ParsedUnderstanding
from api.services.llm_service import LLMServiceError
from api.services.role_modules import librarian

pytestmark = pytest.mark.unit


# ── FakeSupabase recorder (project_anchor + project_chat_messages için) ──────


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
        self.project_row: dict[str, Any] | None = None
        self.anchor_row: dict[str, Any] | None = None
        self.existing_messages: list[dict[str, Any]] = []

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)

    def respond(self, call: dict[str, Any]) -> SimpleNamespace:
        t, op = call["table"], call["op"]
        if t == "projects" and op == "select":
            return SimpleNamespace(data=[self.project_row] if self.project_row else [])
        if t == "project_anchor" and op == "select":
            return SimpleNamespace(data=[self.anchor_row] if self.anchor_row else [])
        if t == "project_chat_messages" and op == "select":
            attempt = int(call["filters"].get("attempt_no", 1))
            rows = [m for m in self.existing_messages if int(m["attempt_no"]) == attempt]
            return SimpleNamespace(data=rows)
        if t == "project_chat_messages" and op == "insert":
            for row in call["payload"]:
                self.existing_messages.append(dict(row))
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
        prompt_tokens = 120
        completion_tokens = 60

    class _Resp:
        def __init__(self, c: str) -> None:
            self.choices = [_Choice(c)]
            self.usage = _Usage()

    return _Resp(json.dumps(json_payload, ensure_ascii=False))


@pytest.fixture
def fake_db() -> _FakeSupabase:
    fake = _FakeSupabase()
    fake.project_row = {
        "id": "prj-1",
        "name": "Test",
        "inherited_field_ids": ["engineering"],
        "inherited_subfield_ids": [],
        "inherited_research_focus": None,
    }
    return fake


@pytest.fixture
def captured_llm(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """LLM Router chokepoint mock + supabase async passthrough."""
    seen: dict[str, Any] = {}

    parsed_default: dict[str, Any] = {
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
    seen["next_payload"] = parsed_default

    async def fake_acompletion(**kwargs: Any) -> Any:
        seen["last_kwargs"] = kwargs
        return _fake_completion_response(seen["next_payload"])

    monkeypatch.setattr("api.services.llm_service.acompletion", fake_acompletion)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def _direct_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109 — mock sig
    ) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)
    return seen


# ── 1. Tur 1 happy: 3 focus + finished=False ─────────────────────────────────


async def test_librarian_turn1_happy_path(
    fake_db: _FakeSupabase, captured_llm: dict[str, Any]
) -> None:
    resp = await librarian.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        content="yükseköğretimde kalite akreditasyonu için ÇKKV",
        attempt_no=1,
    )
    assert resp.turn_no == 1
    assert resp.finished is False
    assert len(resp.parsed_understanding.focuses) == 3
    assert resp.parsed_understanding.field == "Mühendislik"
    # 2 INSERT row (user + adviser)
    inserts = [c for c in fake_db.calls if c["op"] == "insert"]
    assert len(inserts) == 1
    assert len(inserts[0]["payload"]) == 2
    roles = [r["role"] for r in inserts[0]["payload"]]
    assert roles == ["user", "adviser"]
    # K-031 zırh: projects SELECT'inde user_id filter var
    proj_select = next(c for c in fake_db.calls if c["table"] == "projects")
    assert proj_select["filters"]["user_id"] == "user-1"
    assert proj_select["filters"]["id"] == "prj-1"


# ── 2. Tur 2 düzeltme: finished=True cap ─────────────────────────────────────


async def test_librarian_turn2_finished_cap(
    fake_db: _FakeSupabase, captured_llm: dict[str, Any]
) -> None:
    # Tur 1 zaten kayıtlı (FakeSupabase'e ekle)
    fake_db.existing_messages = [
        {"attempt_no": 1, "turn_no": 1, "role": "user", "content": "ilk mesaj"},
        {"attempt_no": 1, "turn_no": 1, "role": "adviser", "content": "ilk yanıt"},
    ]
    # Model hâlâ finished=False yazıyor; route cap edip True yapmalı
    captured_llm["next_payload"]["finished"] = False

    resp = await librarian.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        content="hayır odak X yerine Y olsun",
        attempt_no=1,
    )
    assert resp.turn_no == 2
    assert resp.finished is True  # cap
    assert resp.parsed_understanding.finished is True


# ── 3. Uyumsuzluk hafızası page_state'e enjekte ──────────────────────────────


async def test_librarian_rejection_memory_in_page_state(
    fake_db: _FakeSupabase, captured_llm: dict[str, Any]
) -> None:
    fake_db.anchor_row = {
        "rejected_anchors": ["eski odak A", "eski odak B"],
        "reject_reasons": ["çok teknik", "alanım dışı"],
    }
    await librarian.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        content="yeni mesaj",
        attempt_no=2,
    )
    system = captured_llm["last_kwargs"]["messages"][0]["content"]
    assert "eski odak A" in system
    assert "çok teknik" in system
    assert "rejected_focuses" in system or "reject_reasons" in system


# ── 4. Gemini provider fail → LLMServiceError ────────────────────────────────


async def test_librarian_gemini_provider_fail(
    monkeypatch: pytest.MonkeyPatch, fake_db: _FakeSupabase
) -> None:
    async def boom(**_: Any) -> Any:
        raise RuntimeError("provider down")

    monkeypatch.setattr("api.services.llm_service.acompletion", boom)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def _direct_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)

    with pytest.raises(LLMServiceError, match="provider down"):
        await librarian.run(
            db=fake_db,  # type: ignore[arg-type]
            project_id="prj-1",
            user_id="user-1",
            content="x",
            attempt_no=1,
        )


# ── 5. ParsedUnderstanding şema invalid → LLMServiceError ────────────────────


async def test_librarian_invalid_schema_raises(
    monkeypatch: pytest.MonkeyPatch, fake_db: _FakeSupabase
) -> None:
    async def fake(**_: Any) -> Any:
        return _fake_completion_response({"focuses": ["only-one"], "wrong": True})

    monkeypatch.setattr("api.services.llm_service.acompletion", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def _direct_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)

    with pytest.raises(LLMServiceError):
        await librarian.run(
            db=fake_db,  # type: ignore[arg-type]
            project_id="prj-1",
            user_id="user-1",
            content="x",
            attempt_no=1,
        )


# ── 6. Route extra=forbid → 422 ──────────────────────────────────────────────


def test_research_area_messages_extra_forbid_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from api.main import create_app

    app = create_app()
    token = jwt.encode({"sub": "user-x"}, "x", algorithm="HS256")
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {token}"

    r = client.post(
        "/api/project/prj-1/research-area/messages",
        json={"content": "merhaba", "attempt_no": 1, "extra_field": "x"},
    )
    assert r.status_code == 422, r.text


def test_parsed_understanding_focuses_min_3() -> None:
    """ParsedUnderstanding: focuses kesin 3 öğe."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ParsedUnderstanding(
            focuses=["a", "b"],
            field="X",
            adviser_text="?",
            confidence="high",
        )


_ = Iterator  # keep import non-flaky for ruff
