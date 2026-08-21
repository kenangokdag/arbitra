"""F9 P095 /api/project/{id}/research-area/anchor-candidates integration tests.

Plan: docs/plans/F9_kesif_workbench.md §12 (test stratejisi, 1 integration)
Coverage:
1. 200 happy: HyDE → fan-out (vec+lex mock) → RRF → rerank → 3 AnchorCandidate
2. K-031 RLS zırh: başka user'ın project_id → 404
3. Stage A henüz tamamlanmadı (no parsed_understanding) → 409
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


# ── FakeSupabase recorder ─────────────────────────────────────────────────────


class _FakeBuilder:
    def __init__(self, recorder: _FakeSupabase, table: str) -> None:
        self._rec = recorder
        self._table = table
        self._op: str | None = None
        self._filters: dict[str, Any] = {}
        self._in: tuple[str, list[Any]] | None = None
        self._order: list[tuple[str, bool]] = []
        self._limit: int | None = None

    def select(self, _cols: str = "*", **_kw: Any) -> _FakeBuilder:
        self._op = "select"
        return self

    def eq(self, col: str, val: Any) -> _FakeBuilder:
        self._filters[col] = val
        return self

    def in_(self, col: str, vals: list[Any]) -> _FakeBuilder:
        self._in = (col, list(vals))
        return self

    def order(self, col: str, desc: bool = False) -> _FakeBuilder:
        self._order.append((col, desc))
        return self

    def limit(self, n: int) -> _FakeBuilder:
        self._limit = n
        return self

    def text_search(self, col: str, q: str, options: dict[str, Any]) -> _FakeBuilder:
        self._op = "text_search"
        return self

    def execute(self) -> SimpleNamespace:
        call = {
            "table": self._table,
            "op": self._op,
            "filters": dict(self._filters),
            "in_": self._in,
            "order": list(self._order),
            "limit": self._limit,
        }
        self._rec.calls.append(call)
        return self._rec.respond(call)


class _FakeSupabase:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.projects: list[dict[str, Any]] = []
        self.messages: list[dict[str, Any]] = []
        self.papers_rows: list[dict[str, Any]] = []
        self.card_rows: list[dict[str, Any]] = []
        self.quality_rows: list[dict[str, Any]] = []
        self.lex_rows: list[dict[str, Any]] = []

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
                if m.get("project_id") == f.get("project_id")
                and m.get("role") == f.get("role", m.get("role"))
            ]
            # latest by attempt then turn (mock simulates DESC ORDER + LIMIT 1)
            rows = sorted(
                rows,
                key=lambda r: (int(r.get("attempt_no", 0)), int(r.get("turn_no", 0))),
                reverse=True,
            )
            if call["limit"]:
                rows = rows[: call["limit"]]
            return SimpleNamespace(data=rows)
        if t == "papers" and op == "text_search":
            return SimpleNamespace(data=list(self.lex_rows))
        if t == "papers" and op == "select":
            ids = set(call["in_"][1]) if call["in_"] else set()
            rows = [r for r in self.papers_rows if r["paper_id"] in ids]
            return SimpleNamespace(data=rows)
        if t == "fact_paper_id_card" and op == "select":
            ids = set(call["in_"][1]) if call["in_"] else set()
            rows = [r for r in self.card_rows if r["paper_id"] in ids]
            if f.get("is_suspicious") is False:
                rows = [r for r in rows if not r.get("is_suspicious", False)]
            return SimpleNamespace(data=rows)
        if t == "fact_paper_quality_v3" and op == "select":
            ids = set(call["in_"][1]) if call["in_"] else set()
            rows = [r for r in self.quality_rows if r["paper_id"] in ids]
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=[])


def _fake_completion_response(json_payload: dict[str, Any]) -> Any:
    class _Msg:
        def __init__(self, c: str) -> None:
            self.content = c

    class _Choice:
        def __init__(self, c: str) -> None:
            self.message = _Msg(c)

    class _Usage:
        prompt_tokens = 200
        completion_tokens = 90

    class _Resp:
        def __init__(self, c: str) -> None:
            self.choices = [_Choice(c)]
            self.usage = _Usage()

    return _Resp(json.dumps(json_payload, ensure_ascii=False))


_PARSED_UNDERSTANDING = {
    "focuses": ["a", "b", "c"],
    "field": "Mühendislik",
    "subfield": "Endüstri Mühendisliği",
    "interdisc": True,
    "confidence": "med",
    "adviser_text": "Tamam.",
    "finished": True,
}

_HYDE_PAYLOAD = {
    "pseudo_paragraph": (
        "Bu çalışma çok kriterli karar verme yöntemleri kullanarak yükseköğretim "
        "akreditasyonu sürecinde kalite göstergelerini incelemektedir. AHP "
        "yaklaşımı kriter ağırlıklarını belirler ve TOPSIS sonuçları sıralar."
    ),
    "keywords": ["MCDM", "akreditasyon", "yükseköğretim"],
}


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
        {"id": "prj-1", "user_id": "user-1", "inherited_research_focus": None},
        {"id": "prj-2", "user_id": "user-other", "inherited_research_focus": None},
    ]
    fake.messages = [
        {
            "project_id": "prj-1",
            "role": "adviser",
            "attempt_no": 1,
            "turn_no": 2,
            "parsed_understanding": dict(_PARSED_UNDERSTANDING),
        }
    ]
    fake.papers_rows = [
        {"paper_id": f"W{i}", "title": f"Title {i}", "abstract": f"Abs {i}",
         "year": 2020 + i, "lang": "en"}
        for i in range(1, 6)
    ]
    fake.card_rows = [
        {"paper_id": f"W{i}", "language": "en", "year": 2020 + i,
         "is_suspicious": False}
        for i in range(1, 6)
    ]
    fake.quality_rows = [
        {"paper_id": f"W{i}", "q_weak": 0.5 + i * 0.05} for i in range(1, 6)
    ]
    fake.lex_rows = [{"paper_id": f"W{i}"} for i in (3, 4, 5)]

    monkeypatch.setattr("api.routes.research_area._supabase", lambda: fake)

    async def _direct_call(fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)
    yield fake


@pytest.fixture
def patch_pipeline(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """LLM + Pinecone + encoder + reranker mocks."""
    seen: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> Any:
        seen["last_kwargs"] = kwargs
        return _fake_completion_response(_HYDE_PAYLOAD)

    monkeypatch.setattr("api.services.llm_service.acompletion", fake_acompletion)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class _M:
        def __init__(self, mid: str, score: float) -> None:
            self.id = mid
            self.score = score

    class _Idx:
        async def query_async(
            self,
            vector: list[float],
            top_k: int,
            filter: dict[str, Any] | None,
            include_metadata: bool,
        ) -> dict[str, Any]:
            del vector, top_k, filter, include_metadata
            return {"matches": [_M(f"W{i}", 0.9 - i * 0.05) for i in range(1, 6)]}

    monkeypatch.setattr("api.db.pinecone_client.get_pinecone_index", lambda: _Idx())

    class _Enc:
        def encode(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] * 8 for _ in texts]

    class _Reranker:
        async def rerank(
            self,
            candidates: list[str],
            query: str,
            top_k: int = 10,
            candidate_texts: dict[str, str] | None = None,
        ) -> list[tuple[str, float]]:
            del query, candidate_texts
            return [(c, 1.0 - i * 0.1) for i, c in enumerate(candidates[:top_k])]

    # Default factories — _QueryEncoder() / BgeReranker() çağrıldığında bunları döner
    monkeypatch.setattr("api.services.anchor_finder._QueryEncoder", lambda: _Enc())
    import api.services.reranker as _rr_mod
    monkeypatch.setattr(_rr_mod, "BgeReranker", lambda: _Reranker())
    return seen


# ── 1. 200 happy ─────────────────────────────────────────────────────────────


def test_anchor_candidates_happy_returns_5(
    authed_client: TestClient,
    fake_db: _FakeSupabase,
    patch_pipeline: dict[str, Any],
) -> None:
    """V1-S17 P005 (KD-V1-S17-04): top-K 3 → 5, signals_13 her aday üstünde."""
    del patch_pipeline
    r = authed_client.post(
        "/api/project/prj-1/research-area/anchor-candidates",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "candidates" in body
    assert len(body["candidates"]) == 5
    assert body["packet_p"] == _HYDE_PAYLOAD["pseudo_paragraph"]
    assert body["packet_s"] == _HYDE_PAYLOAD["keywords"]
    for c in body["candidates"]:
        assert c["paper_id"].startswith("W")
        assert c["decision_band"] in {"high", "med", "low"}
        assert 0.0 <= c["q_weak"] <= 1.0
        assert isinstance(c["signals_13"], dict)
        assert len(c["signals_13"]) == 13


# ── 2. K-031 RLS zırh: başka user'ın project_id → 404 ────────────────────────


def test_anchor_candidates_other_user_404(
    authed_client: TestClient,
    fake_db: _FakeSupabase,
    patch_pipeline: dict[str, Any],
) -> None:
    del patch_pipeline
    r = authed_client.post(
        "/api/project/prj-2/research-area/anchor-candidates",
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "project_not_found"
    proj_select = next(
        c for c in fake_db.calls
        if c["table"] == "projects" and c["op"] == "select"
    )
    assert proj_select["filters"]["id"] == "prj-2"
    assert proj_select["filters"]["user_id"] == "user-1"


# ── 3. Stage A henüz tamamlanmadı → 409 ──────────────────────────────────────


def test_anchor_candidates_stage_a_incomplete_409(
    authed_client: TestClient,
    fake_db: _FakeSupabase,
    patch_pipeline: dict[str, Any],
) -> None:
    del patch_pipeline
    fake_db.messages = []  # adviser turn yok
    r = authed_client.post(
        "/api/project/prj-1/research-area/anchor-candidates",
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"].startswith("stage_a_incomplete")
