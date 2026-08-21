"""F9 P095 anchor_finder unit tests.

Plan: docs/plans/F9_kesif_workbench.md §12 (5 unit)
Coverage:
1. 3 aday top-3 happy path (vec+lex pools both populated → RRF → enrich → rerank)
2. Pinecone fail → graceful degrade (sadece tsvector kullanılır)
3. tsvector empty → vec only ile çalışır
4. Reranker uniform fallback (candidate_texts None'a düşmez ama rerank score sırası)
5. RRF k=60 invariant — pool_router._rrf_merge çağrılır
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

from api.models.research_area import HydePacket
from api.services import anchor_finder

pytestmark = pytest.mark.unit


# ── FakeSupabase recorder (project + chat + papers + cards + quality) ────────


class _FakeBuilder:
    def __init__(self, recorder: _FakeSupabase, table: str) -> None:
        self._rec = recorder
        self._table = table
        self._op: str | None = None
        self._filters: dict[str, Any] = {}
        self._in: tuple[str, list[Any]] | None = None
        self._order: list[tuple[str, bool]] = []
        self._limit: int | None = None
        self._text_search: tuple[str, str, dict[str, Any]] | None = None

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
        self._text_search = (col, q, dict(options))
        return self

    def execute(self) -> SimpleNamespace:
        call = {
            "table": self._table,
            "op": self._op,
            "filters": dict(self._filters),
            "in_": self._in,
            "order": list(self._order),
            "limit": self._limit,
            "text_search": self._text_search,
        }
        self._rec.calls.append(call)
        return self._rec.respond(call)


class _FakeSupabase:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.project_row: dict[str, Any] | None = None
        self.parsed_row: dict[str, Any] | None = None
        self.papers_rows: list[dict[str, Any]] = []
        self.card_rows: list[dict[str, Any]] = []
        self.quality_rows: list[dict[str, Any]] = []
        self.lex_rows: list[dict[str, Any]] = []

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)

    def respond(self, call: dict[str, Any]) -> SimpleNamespace:
        t, op = call["table"], call["op"]
        if t == "projects" and op == "select":
            return SimpleNamespace(data=[self.project_row] if self.project_row else [])
        if t == "project_chat_messages" and op == "select":
            return SimpleNamespace(data=[self.parsed_row] if self.parsed_row else [])
        if t == "papers" and op == "text_search":
            return SimpleNamespace(data=list(self.lex_rows))
        if t == "papers" and op == "select":
            ids = set(call["in_"][1]) if call["in_"] else set()
            rows = [r for r in self.papers_rows if r["paper_id"] in ids]
            return SimpleNamespace(data=rows)
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


_HYDE_PAYLOAD = {
    "pseudo_paragraph": (
        "Bu çalışma çok kriterli karar verme yöntemleri kullanarak yükseköğretim "
        "akreditasyon kriterlerinin ağırlıklandırılmasını incelemektedir. AHP "
        "ve TOPSIS yaklaşımları karşılaştırılmış, kalite göstergelerinin "
        "sıralanmasında tutarlı sonuçlar elde edilmiştir."
    ),
    "keywords": ["MCDM", "ÇKKV", "AHP", "TOPSIS", "akreditasyon"],
}


@pytest.fixture
def fake_db() -> _FakeSupabase:
    fake = _FakeSupabase()
    fake.project_row = {"id": "prj-1", "inherited_research_focus": None}
    fake.parsed_row = {
        "parsed_understanding": {
            "focuses": ["a", "b", "c"],
            "field": "Mühendislik",
            "subfield": "Endüstri Müh.",
            "interdisc": True,
            "confidence": "med",
            "adviser_text": "onay",
            "finished": True,
        },
        "attempt_no": 1,
        "turn_no": 2,
    }
    # Papers PI..P5 enriched
    fake.papers_rows = [
        {"paper_id": f"W{i}", "title": f"Title {i}", "abstract": f"Abs {i} body",
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
    return fake


@pytest.fixture
def patch_io(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """LLM + supabase + Pinecone + encoder mock'ları."""
    seen: dict[str, Any] = {"hyde": _HYDE_PAYLOAD}

    async def fake_acompletion(**kwargs: Any) -> Any:
        seen["last_kwargs"] = kwargs
        return _fake_completion_response(seen["hyde"])

    monkeypatch.setattr("api.services.llm_service.acompletion", fake_acompletion)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def _direct_call(fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)
    return seen


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
        # İlk candidate-id sırası deterministik top-k.
        return [(c, 1.0 - i * 0.1) for i, c in enumerate(candidates[:top_k])]


# ── 1. Happy path: 5 aday top-5 (V1-S17 P005: 3 → 5) ──────────────────────────


async def test_anchor_happy_5_candidates(
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

    resp = await anchor_finder.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        encoder=encoder,  # type: ignore[arg-type]
        reranker=reranker,  # type: ignore[arg-type]
    )
    assert len(resp.candidates) == 5
    assert resp.packet_p == _HYDE_PAYLOAD["pseudo_paragraph"]
    assert resp.packet_s == _HYDE_PAYLOAD["keywords"]
    assert encoder.calls == 1
    # K-031 zırh: projects SELECT user_id filter
    proj_call = next(c for c in fake_db.calls if c["table"] == "projects")
    assert proj_call["filters"]["user_id"] == "user-1"
    assert proj_call["filters"]["id"] == "prj-1"
    # Rerank query == pseudo_paragraph
    assert reranker.last_query == _HYDE_PAYLOAD["pseudo_paragraph"]
    # V1-S17 P005: signals_13 her aday üstünde 13 anahtar
    for cand in resp.candidates:
        assert len(cand.signals_13) == 13
        assert "Q_weak" in cand.signals_13


# ── 2. Pinecone fail → graceful (lex only) ────────────────────────────────────


async def test_anchor_pinecone_fail_graceful(
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

    resp = await anchor_finder.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        encoder=_FakeEncoder(),  # type: ignore[arg-type]
        reranker=_FakeReranker(),  # type: ignore[arg-type]
    )
    assert 1 <= len(resp.candidates) <= 3
    pids = {c.paper_id for c in resp.candidates}
    assert pids.issubset({"W1", "W2", "W3"})


# ── 3. tsvector empty → vec only ──────────────────────────────────────────────


async def test_anchor_tsvector_empty_vec_only(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matches = [_FakeMatch(f"W{i}", 0.9 - i * 0.05) for i in range(1, 4)]
    fake_idx = _FakePineconeIndex(matches)
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = []  # empty

    resp = await anchor_finder.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        encoder=_FakeEncoder(),  # type: ignore[arg-type]
        reranker=_FakeReranker(),  # type: ignore[arg-type]
    )
    assert len(resp.candidates) == 3
    assert {c.paper_id for c in resp.candidates} == {"W1", "W2", "W3"}


# ── 4. Reranker output preserves ranking ──────────────────────────────────────


async def test_anchor_reranker_top3_order(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matches = [_FakeMatch(f"W{i}", 0.9 - i * 0.05) for i in range(1, 6)]
    fake_idx = _FakePineconeIndex(matches)
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = [{"paper_id": f"W{i}"} for i in (1, 2, 3)]

    class _ReverseReranker:
        async def rerank(
            self,
            candidates: list[str],
            query: str,
            top_k: int = 10,
            candidate_texts: dict[str, str] | None = None,
        ) -> list[tuple[str, float]]:
            del query, candidate_texts
            rev = list(reversed(candidates))
            return [(c, 1.0 - i * 0.1) for i, c in enumerate(rev[:top_k])]

    resp = await anchor_finder.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        encoder=_FakeEncoder(),  # type: ignore[arg-type]
        reranker=_ReverseReranker(),  # type: ignore[arg-type]
    )
    # Rerank ters çevirdi → ilk dönen = enriched dict son anahtarı
    # V1-S17 P005: top-5 (3 → 5).
    assert len(resp.candidates) == 5


# ── 5. is_suspicious filter applied (HARD §11 satır 418) ──────────────────────


async def test_anchor_is_suspicious_filter(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # W1, W2 suspicious; sadece W3, W4, W5 geri kalır
    fake_db.card_rows = [
        {"paper_id": "W1", "language": "en", "year": 2021, "is_suspicious": True},
        {"paper_id": "W2", "language": "en", "year": 2022, "is_suspicious": True},
        {"paper_id": "W3", "language": "en", "year": 2023, "is_suspicious": False},
        {"paper_id": "W4", "language": "en", "year": 2024, "is_suspicious": False},
        {"paper_id": "W5", "language": "en", "year": 2025, "is_suspicious": False},
    ]
    matches = [_FakeMatch(f"W{i}", 0.9 - i * 0.05) for i in range(1, 6)]
    fake_idx = _FakePineconeIndex(matches)
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = [{"paper_id": f"W{i}"} for i in (1, 2)]

    resp = await anchor_finder.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        encoder=_FakeEncoder(),  # type: ignore[arg-type]
        reranker=_FakeReranker(),  # type: ignore[arg-type]
    )
    pids = {c.paper_id for c in resp.candidates}
    assert pids.isdisjoint({"W1", "W2"})  # suspicious filtrelendi
    assert pids.issubset({"W3", "W4", "W5"})


# ── 6. ProjectNotFoundError → propagate (route 404'e map) ─────────────────────


async def test_anchor_project_not_found(
    fake_db: _FakeSupabase, patch_io: dict[str, Any]
) -> None:
    fake_db.project_row = None
    with pytest.raises(anchor_finder.ProjectNotFoundError):
        await anchor_finder.run(
            db=fake_db,  # type: ignore[arg-type]
            project_id="prj-x",
            user_id="user-1",
            encoder=_FakeEncoder(),  # type: ignore[arg-type]
            reranker=_FakeReranker(),  # type: ignore[arg-type]
        )


# ── 7. V1-S17 P006 RC2 — OpenAlex metadata fallback ──────────────────────────


async def test_metadata_fallback_backfills_empty_title(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """KD-V1-S17-06: Supabase papers.title boş → OpenAlex batch fetch ile doldur."""
    matches = [_FakeMatch(f"W{i}", 0.9 - i * 0.05) for i in range(1, 6)]
    fake_idx = _FakePineconeIndex(matches)
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = [{"paper_id": f"W{i}"} for i in (1, 2, 3)]
    # W1, W2 Supabase title boş (NULL simulation) — fallback hedefi
    fake_db.papers_rows = [
        {"paper_id": "W1", "title": "", "abstract": "", "year": 2021, "lang": "en"},
        {"paper_id": "W2", "title": None, "abstract": "", "year": 2022, "lang": "en"},
        {"paper_id": "W3", "title": "Existing Title 3", "abstract": "Existing 3",
         "year": 2023, "lang": "en"},
        {"paper_id": "W4", "title": "Existing Title 4", "abstract": "Existing 4",
         "year": 2024, "lang": "en"},
        {"paper_id": "W5", "title": "Existing Title 5", "abstract": "Existing 5",
         "year": 2025, "lang": "en"},
    ]

    seen: dict[str, Any] = {}

    async def fake_fetch(
        paper_ids: list[str], email: str | None
    ) -> dict[str, dict[str, Any]]:
        seen["called_with"] = list(paper_ids)
        seen["email"] = email
        return {
            "W1": {"title": "OA Title W1", "abstract": "OA Abs W1",
                   "language": "en", "year": 2021},
            "W2": {"title": "OA Title W2", "abstract": "OA Abs W2",
                   "language": "en", "year": 2022},
        }

    monkeypatch.setattr(
        "api.routes.search._fetch_candidate_metadata", fake_fetch
    )

    resp = await anchor_finder.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        encoder=_FakeEncoder(),  # type: ignore[arg-type]
        reranker=_FakeReranker(),  # type: ignore[arg-type]
    )
    # Tek batch çağrı (Plan §6 A1: asyncio.gather gerekmez)
    assert "called_with" in seen
    assert set(seen["called_with"]) == {"W1", "W2"}
    titles = {c.paper_id: c.title for c in resp.candidates}
    assert titles.get("W1") == "OA Title W1"
    assert titles.get("W2") == "OA Title W2"
    # Supabase önceliği: dolu olanlar değişmedi
    assert titles.get("W3") == "Existing Title 3"


async def test_metadata_fallback_skipped_when_all_titles_present(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tüm title'lar dolu ise OpenAlex çağrılmaz (latency budget)."""
    matches = [_FakeMatch(f"W{i}", 0.9 - i * 0.05) for i in range(1, 6)]
    fake_idx = _FakePineconeIndex(matches)
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = [{"paper_id": f"W{i}"} for i in (1, 2, 3)]

    call_count = {"n": 0}

    async def fake_fetch(
        paper_ids: list[str], email: str | None
    ) -> dict[str, dict[str, Any]]:
        del paper_ids, email
        call_count["n"] += 1
        return {}

    monkeypatch.setattr(
        "api.routes.search._fetch_candidate_metadata", fake_fetch
    )

    resp = await anchor_finder.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        encoder=_FakeEncoder(),  # type: ignore[arg-type]
        reranker=_FakeReranker(),  # type: ignore[arg-type]
    )
    assert call_count["n"] == 0
    assert len(resp.candidates) == 5


async def test_metadata_fallback_empty_openalex_graceful(
    fake_db: _FakeSupabase,
    patch_io: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAlex hiç sonuç dönmezse paper_id title fallback'i (mevcut davranış)."""
    matches = [_FakeMatch(f"W{i}", 0.9 - i * 0.05) for i in range(1, 6)]
    fake_idx = _FakePineconeIndex(matches)
    monkeypatch.setattr(
        "api.db.pinecone_client.get_pinecone_index", lambda: fake_idx
    )
    fake_db.lex_rows = [{"paper_id": f"W{i}"} for i in (1, 2, 3)]
    fake_db.papers_rows = [
        {"paper_id": "W1", "title": "", "abstract": "", "year": 2021, "lang": "en"},
        {"paper_id": "W2", "title": "Existing Title 2", "abstract": "Existing 2",
         "year": 2022, "lang": "en"},
        {"paper_id": "W3", "title": "Existing Title 3", "abstract": "Existing 3",
         "year": 2023, "lang": "en"},
        {"paper_id": "W4", "title": "Existing Title 4", "abstract": "Existing 4",
         "year": 2024, "lang": "en"},
        {"paper_id": "W5", "title": "Existing Title 5", "abstract": "Existing 5",
         "year": 2025, "lang": "en"},
    ]

    async def fake_fetch_empty(
        paper_ids: list[str], email: str | None
    ) -> dict[str, dict[str, Any]]:
        del paper_ids, email
        return {}

    monkeypatch.setattr(
        "api.routes.search._fetch_candidate_metadata", fake_fetch_empty
    )

    resp = await anchor_finder.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        encoder=_FakeEncoder(),  # type: ignore[arg-type]
        reranker=_FakeReranker(),  # type: ignore[arg-type]
    )
    titles = {c.paper_id: c.title for c in resp.candidates}
    # AnchorCandidate title boş kabul etmez → run() paper_id'yi fallback yapar
    assert titles.get("W1") == "W1"
    assert titles.get("W2") == "Existing Title 2"


_ = (Iterator, HydePacket)  # keep imports
