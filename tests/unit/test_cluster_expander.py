"""V1-S17 P001 cluster_expander Stage C unit tests.

Plan: docs/plans/V1_S17_cascade_5rc.md §2 P001 + §4 C001

Coverage:
1. Happy path: vec+lex pools, RRF, enrich, rerank → ready (cluster_size>0)
2. Pinecone fail → lex only graceful
3. Anchor abstract empty → keyword extraction title-only fallback
4. Both pools empty → ClusterPoolEmptyError + cluster_status='failed'
5. All candidates is_suspicious=true → ClusterPoolEmptyError + 'failed'
6. AnchorNotFoundError when project_anchor row missing
7. Anchor papers row absent (ghost) → encoder skip + ClusterPoolEmptyError + 'failed'
8. Idempotent re-run — persist delete-then-insert pattern verified
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from api.services import cluster_expander

pytestmark = pytest.mark.unit


class _FakeBuilder:
    def __init__(self, recorder: _FakeSupabase, table: str) -> None:
        self._rec = recorder
        self._table = table
        self._op: str | None = None
        self._filters: dict[str, Any] = {}
        self._in: tuple[str, list[Any]] | None = None
        self._update_payload: dict[str, Any] | None = None
        self._insert_payload: Any | None = None
        self._limit: int | None = None
        self._text_search: tuple[str, str, dict[str, Any]] | None = None

    def select(self, _cols: str = "*", **_kw: Any) -> _FakeBuilder:
        self._op = "select"
        return self

    def update(self, payload: dict[str, Any]) -> _FakeBuilder:
        self._op = "update"
        self._update_payload = dict(payload)
        return self

    def insert(self, payload: Any) -> _FakeBuilder:
        self._op = "insert"
        self._insert_payload = payload
        return self

    def delete(self) -> _FakeBuilder:
        self._op = "delete"
        return self

    def eq(self, col: str, val: Any) -> _FakeBuilder:
        self._filters[col] = val
        return self

    def in_(self, col: str, vals: list[Any]) -> _FakeBuilder:
        self._in = (col, list(vals))
        return self

    def limit(self, n: int) -> _FakeBuilder:
        self._limit = n
        return self

    def text_search(
        self, col: str, q: str, options: dict[str, Any]
    ) -> _FakeBuilder:
        self._op = "text_search"
        self._text_search = (col, q, dict(options))
        return self

    def execute(self) -> SimpleNamespace:
        call = {
            "table": self._table,
            "op": self._op,
            "filters": dict(self._filters),
            "in_": self._in,
            "update_payload": self._update_payload,
            "insert_payload": self._insert_payload,
            "limit": self._limit,
            "text_search": self._text_search,
        }
        self._rec.calls.append(call)
        return self._rec.respond(call)


class _FakeSupabase:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.anchor_row: dict[str, Any] | None = None
        self.papers_rows: list[dict[str, Any]] = []
        self.card_rows: list[dict[str, Any]] = []
        self.quality_rows: list[dict[str, Any]] = []
        self.lex_rows: list[dict[str, Any]] = []

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)

    def respond(self, call: dict[str, Any]) -> SimpleNamespace:
        t, op = call["table"], call["op"]
        if t == "project_anchor" and op == "select":
            return SimpleNamespace(
                data=[self.anchor_row] if self.anchor_row else []
            )
        if t == "project_anchor" and op == "update":
            return SimpleNamespace(data=[])
        if t == "project_cluster" and op in {"delete", "insert"}:
            return SimpleNamespace(data=[])
        if t == "papers" and op == "select":
            if call["in_"]:
                ids = set(call["in_"][1])
                rows = [r for r in self.papers_rows if r["paper_id"] in ids]
            elif call["filters"].get("paper_id"):
                rows = [
                    r
                    for r in self.papers_rows
                    if r["paper_id"] == call["filters"]["paper_id"]
                ]
            else:
                rows = list(self.papers_rows)
            return SimpleNamespace(data=rows)
        if t == "papers" and op == "text_search":
            return SimpleNamespace(data=list(self.lex_rows))
        if t == "fact_paper_id_card" and op == "select":
            ids = set(call["in_"][1]) if call["in_"] else set()
            rows = [r for r in self.card_rows if r["paper_id"] in ids]
            if call["filters"].get("is_suspicious") is False:
                rows = [r for r in rows if not r.get("is_suspicious", False)]
            return SimpleNamespace(data=rows)
        if t == "fact_paper_quality_v3" and op == "select":
            ids = set(call["in_"][1]) if call["in_"] else set()
            rows = [r for r in self.quality_rows if r["paper_id"] in ids]
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=[])


class _FakeMatch:
    def __init__(self, mid: str, score: float) -> None:
        self.id = mid
        self.score = score


class _FakePineconeIndex:
    def __init__(self, matches: list[_FakeMatch] | Exception) -> None:
        self._matches = matches

    async def query_async(
        self,
        vector: list[float],
        top_k: int,
        filter: dict[str, Any] | None,
        include_metadata: bool,
    ) -> dict[str, Any]:
        del vector, top_k, filter, include_metadata
        if isinstance(self._matches, Exception):
            raise self._matches
        return {"matches": list(self._matches)}


class _FakeEncoder:
    def __init__(self) -> None:
        self.calls = 0

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[0.1] * 8 for _ in texts]


class _FakeReranker:
    def __init__(self) -> None:
        self.last_query: str | None = None
        self.last_candidates: list[str] = []
        self.last_top_k: int | None = None

    async def rerank(
        self,
        candidates: list[str],
        query: str,
        top_k: int = 10,
        candidate_texts: dict[str, str] | None = None,
    ) -> list[tuple[str, float]]:
        del candidate_texts
        self.last_query = query
        self.last_candidates = list(candidates)
        self.last_top_k = top_k
        return [(c, 1.0 - i * 0.1) for i, c in enumerate(candidates[:top_k])]


@pytest.fixture
def fake_db() -> _FakeSupabase:
    fake = _FakeSupabase()
    fake.anchor_row = {"anchor_paper_id": "W100"}
    fake.papers_rows = [
        {
            "paper_id": "W100",
            "title": "Anchor paper title with several long descriptive tokens",
            "abstract": "Anchor abstract body discussing multi criteria decision making methods",
            "year": 2024,
            "lang": "en",
        },
        *[
            {
                "paper_id": f"W{i}",
                "title": f"Title {i}",
                "abstract": f"Abstract body {i}",
                "year": 2020 + i,
                "lang": "en",
            }
            for i in range(1, 6)
        ],
    ]
    fake.card_rows = [
        {"paper_id": f"W{i}", "language": "en", "year": 2020 + i, "is_suspicious": False}
        for i in range(1, 6)
    ]
    fake.quality_rows = [
        {"paper_id": f"W{i}", "q_weak": 0.5 + i * 0.05} for i in range(1, 6)
    ]
    return fake


@pytest.fixture
def patch_io(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    async def _direct_call(fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)
    return seen


# ── 1. Happy path ─────────────────────────────────────────────────────────────


async def test_cluster_happy_ready(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matches = [_FakeMatch(f"W{i}", 0.9 - i * 0.05) for i in range(1, 6)]
    fake_idx = _FakePineconeIndex(matches)
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = [{"paper_id": f"W{i}"} for i in (3, 4, 5)]

    encoder = _FakeEncoder()
    reranker = _FakeReranker()

    resp = await cluster_expander.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        encoder=encoder,  # type: ignore[arg-type]
        reranker=reranker,  # type: ignore[arg-type]
    )
    assert resp.cluster_status == "ready"
    assert resp.anchor_paper_id == "W100"
    assert resp.cluster_size >= 1
    assert resp.cluster_size <= 50
    assert encoder.calls == 1
    # Reranker query == anchor title (truncated 600)
    assert reranker.last_query and "Anchor paper title" in reranker.last_query
    assert reranker.last_top_k == 50
    # Anchor kendisi cluster'a girmedi
    assert "W100" not in reranker.last_candidates
    # cluster_status flipped expanding → ready
    statuses = [
        c["update_payload"]["cluster_status"]
        for c in fake_db.calls
        if c["table"] == "project_anchor" and c["op"] == "update"
    ]
    assert "expanding" in statuses
    assert "ready" in statuses


# ── 2. Pinecone fail → lex only graceful ──────────────────────────────────────


async def test_cluster_pinecone_fail_lex_only(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.db.pinecone_client import PineconeQueryError

    fake_idx = _FakePineconeIndex(PineconeQueryError("vec down"))
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = [{"paper_id": f"W{i}"} for i in (1, 2, 3)]

    resp = await cluster_expander.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        encoder=_FakeEncoder(),  # type: ignore[arg-type]
        reranker=_FakeReranker(),  # type: ignore[arg-type]
    )
    assert resp.cluster_status == "ready"
    assert 1 <= resp.cluster_size <= 3


# ── 3. Anchor abstract empty → keywords still extracted from title ───────────


async def test_cluster_anchor_no_abstract_title_keywords(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Anchor row'da abstract YOK
    fake_db.papers_rows[0]["abstract"] = ""

    matches = [_FakeMatch(f"W{i}", 0.9 - i * 0.05) for i in range(1, 4)]
    fake_idx = _FakePineconeIndex(matches)
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = [{"paper_id": "W2"}, {"paper_id": "W3"}]

    resp = await cluster_expander.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        encoder=_FakeEncoder(),  # type: ignore[arg-type]
        reranker=_FakeReranker(),  # type: ignore[arg-type]
    )
    assert resp.cluster_status == "ready"


# ── 4. Both pools empty → ClusterPoolEmptyError + 'failed' ────────────────────


async def test_cluster_both_pools_empty_failed(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_idx = _FakePineconeIndex([])  # empty matches
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = []  # empty

    with pytest.raises(cluster_expander.ClusterPoolEmptyError):
        await cluster_expander.run(
            db=fake_db,  # type: ignore[arg-type]
            project_id="prj-1",
            encoder=_FakeEncoder(),  # type: ignore[arg-type]
            reranker=_FakeReranker(),  # type: ignore[arg-type]
        )
    # cluster_status='failed' set edildi
    failed_calls = [
        c
        for c in fake_db.calls
        if c["table"] == "project_anchor"
        and c["op"] == "update"
        and c["update_payload"]
        and c["update_payload"].get("cluster_status") == "failed"
    ]
    assert failed_calls, "cluster_status='failed' set edilmedi"


# ── 5. All candidates is_suspicious → 'failed' + raise ───────────────────────


async def test_cluster_all_suspicious_failed(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matches = [_FakeMatch(f"W{i}", 0.9 - i * 0.05) for i in range(1, 4)]
    fake_idx = _FakePineconeIndex(matches)
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = []
    # Tüm card'lar is_suspicious=true
    for r in fake_db.card_rows:
        r["is_suspicious"] = True

    with pytest.raises(cluster_expander.ClusterPoolEmptyError):
        await cluster_expander.run(
            db=fake_db,  # type: ignore[arg-type]
            project_id="prj-1",
            encoder=_FakeEncoder(),  # type: ignore[arg-type]
            reranker=_FakeReranker(),  # type: ignore[arg-type]
        )
    failed_calls = [
        c
        for c in fake_db.calls
        if c["table"] == "project_anchor"
        and c["op"] == "update"
        and c["update_payload"]
        and c["update_payload"].get("cluster_status") == "failed"
    ]
    assert failed_calls


# ── 6. AnchorNotFoundError when row missing ──────────────────────────────────


async def test_cluster_anchor_not_found(
    patch_io: dict[str, Any],
) -> None:
    fake_db = _FakeSupabase()
    fake_db.anchor_row = None

    with pytest.raises(cluster_expander.AnchorNotFoundError):
        await cluster_expander.run(
            db=fake_db,  # type: ignore[arg-type]
            project_id="prj-missing",
            encoder=_FakeEncoder(),  # type: ignore[arg-type]
            reranker=_FakeReranker(),  # type: ignore[arg-type]
        )


# ── 7. Anchor in project_anchor ama papers row YOK (lazy mirror miss) ────────


async def test_cluster_anchor_papers_row_missing(
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = _FakeSupabase()
    fake_db.anchor_row = {"anchor_paper_id": "W_ghost"}
    # papers_rows boş — anchor title/abstract elde edilemez
    fake_db.papers_rows = [
        {
            "paper_id": "W1",
            "title": "Cand 1",
            "abstract": "abs",
            "year": 2024,
            "lang": "en",
        }
    ]
    fake_db.card_rows = [
        {"paper_id": "W1", "language": "en", "year": 2024, "is_suspicious": False}
    ]
    fake_db.quality_rows = [{"paper_id": "W1", "q_weak": 0.7}]
    # Vec dolu, lex boş (keyword yok)
    matches = [_FakeMatch("W1", 0.8)]
    fake_idx = _FakePineconeIndex(matches)
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = []

    encoder = _FakeEncoder()
    # Ghost anchor (no papers row): anchor_text boş → vec skip + lex boş →
    # ClusterPoolEmptyError + status='failed'. Pinecone client'ta fetch-by-id
    # yok, encoder boş metni embed etmesin (gereksiz model çağrısı).
    with pytest.raises(cluster_expander.ClusterPoolEmptyError):
        await cluster_expander.run(
            db=fake_db,  # type: ignore[arg-type]
            project_id="prj-ghost",
            encoder=encoder,  # type: ignore[arg-type]
            reranker=_FakeReranker(),  # type: ignore[arg-type]
        )
    assert encoder.calls == 0
    # cluster_status='failed' anchor update'inde damgalanmalı
    failed_calls = [
        c
        for c in fake_db.calls
        if c["table"] == "project_anchor"
        and c["op"] == "update"
        and (c["update_payload"] or {}).get("cluster_status") == "failed"
    ]
    assert failed_calls, "ghost anchor failed marker bekleniyor"


# ── 8. Idempotent persist: delete-then-insert pattern doğrulama ──────────────


async def test_cluster_persist_idempotent_delete_then_insert(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matches = [_FakeMatch(f"W{i}", 0.9 - i * 0.05) for i in range(1, 4)]
    fake_idx = _FakePineconeIndex(matches)
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = []

    await cluster_expander.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        encoder=_FakeEncoder(),  # type: ignore[arg-type]
        reranker=_FakeReranker(),  # type: ignore[arg-type]
    )
    cluster_calls = [c for c in fake_db.calls if c["table"] == "project_cluster"]
    ops = [c["op"] for c in cluster_calls]
    # Önce delete, sonra insert (idempotency)
    assert ops == ["delete", "insert"], f"Beklenen [delete, insert], gelen {ops}"
    insert_call = cluster_calls[1]
    assert insert_call["insert_payload"], "insert payload boş"
    payload = insert_call["insert_payload"]
    # Her satır rank_final 1..N artan
    ranks = [row["rank_final"] for row in payload]
    assert ranks == sorted(ranks)
    assert ranks[0] == 1
    # source enum 'vec' (0016 CHECK)
    assert all(row["source"] == "vec" for row in payload)
