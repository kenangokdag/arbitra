"""V1 Vitrin route integration tests — /api/q · /api/q/literature-review · /api/q2.

kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md §7

Akış: TestClient + FakeRedis monkeypatch + mocked dış servisler
       (search_papers, fetch_papers_by_ids, llm_call).

Kapsam:
  - tier_gate: anon /api/q geçer (limit=25); /api/q2 → 403.
  - Quota: anon /api/q günde 3 → 4. istekte 429 + Retry-After.
  - literature-review: anon happy path (3 paper), authed 25 paper, anon>3 → 403,
    paper_ids boş → 422, OpenAlex 0 sonuç → 422, LLM grounding fail → 502.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from api.middleware.rate_limit import _window
from api.models.q import (
    LiteratureReviewLLM,
    PaperPreview,
    QueryTranslationLLM,
    Reference,
)

pytestmark = pytest.mark.integration


# ───── FakeRedis: in-memory daily counter ─────


class _FakePipe:
    def __init__(self, store: dict[str, int]) -> None:
        self._store = store
        self._key: str | None = None
        self._next: int = 0

    def incr(self, key: str) -> _FakePipe:
        self._store[key] = self._store.get(key, 0) + 1
        self._key = key
        self._next = self._store[key]
        return self

    def expire(self, key: str, ttl: int) -> _FakePipe:
        return self

    async def execute(self) -> list[Any]:
        return [self._next, True]


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    def pipeline(self) -> _FakePipe:
        return _FakePipe(self.store)


# ───── Mocked external services ─────


def _mock_paper(idx: int = 0) -> PaperPreview:
    return PaperPreview(
        openalex_id=f"https://openalex.org/W{1000 + idx}",
        doi=f"10.1234/mock.{idx}",
        title=f"Mock Paper {idx}",
        abstract=f"Bu mock makalenin özeti #{idx}.",
        year=2023,
        venue="Mock Journal",
        authors=["Smith, J."],
        cited_by_count=42,
        mini_summary=None,
    )


def _mock_review(n_refs: int) -> LiteratureReviewLLM:
    cites = " ".join(f"[{i + 1:02d}]" for i in range(n_refs))
    content = (
        f"Mock literatür inceleme metni. Seçilen kaynaklar arasında sentez ve "
        f"karşılaştırma yapılır {cites}. Her kaynağa kısa bir cümleyle değinilir, "
        f"bulgular yan yana getirilir."
    )
    return LiteratureReviewLLM(
        content=content,
        references=[
            Reference(index=i + 1, citation=f"Smith, J. ({2023 + i % 3}). Mock Paper {i}. Mock Journal.")
            for i in range(n_refs)
        ],
    )


@pytest.fixture(autouse=True)
def _stub_dependencies(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeRedis]:
    """tier_gate redis + dış servisler mock'lanır."""
    _window.clear()

    fake = FakeRedis()
    monkeypatch.setattr("api.middleware.tier_gate._get_redis", lambda: fake)

    async def fake_search(
        query: str,
        *,
        limit: int = 25,
        year_from: int | None = None,
        year_to: int | None = None,
        lang: str | None = None,
        settings: Any = None,
    ) -> list[PaperPreview]:
        return [_mock_paper(i) for i in range(limit)]

    monkeypatch.setattr("api.routes.q.search_papers", fake_search)

    async def fake_by_ids(
        ids: list[str], *, settings: Any = None
    ) -> list[PaperPreview]:
        return [_mock_paper(i) for i, _ in enumerate(ids)]

    monkeypatch.setattr("api.routes.q.fetch_papers_by_ids", fake_by_ids)

    class FakeLLMResponse:
        def __init__(self, parsed: Any) -> None:
            self.text = "(structured)"
            self.parsed_output = parsed
            self.model_used = "gemini-flash-tr"
            self.tokens_in = 10
            self.tokens_out = 200
            self.latency_ms = 150

    async def fake_llm_call(
        prompt: str,
        *,
        tier: str = "flash",
        mode: str = "default",
        structured_output_schema: Any = None,
        **_: Any,
    ) -> FakeLLMResponse:
        if mode == "vitrin_literature":
            # Sayım: prompt'taki paper sayısı = ardışık [NN] referans sayısı
            n = sum(1 for i in range(1, 26) if f"[{i:02d}]" in prompt)
            return FakeLLMResponse(_mock_review(max(n, 1)))
        return FakeLLMResponse(None)

    monkeypatch.setattr("api.routes.q.llm_service.call", fake_llm_call)

    yield fake


@pytest.fixture
def auth_token() -> str:
    return jwt.encode({"sub": "user-vitrin-test"}, "x", algorithm="HS256")


# ───── /api/q (anon, 25 mk) ─────


def test_q_returns_25_papers(client: TestClient) -> None:
    """KD-V1-S10-01: /api/q tier-bağımsız 25 makale döner."""
    response = client.post("/api/q", json={"query": "metaheuristic"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["papers"]) == 25
    assert body["quota_remaining"] == 2  # anon limit=3, 1 sayıldı


def test_q_anon_quota_exhausted_returns_429(client: TestClient) -> None:
    """anon günlük 3 istek → 4. istek 429 + Retry-After."""
    for _ in range(3):
        r = client.post("/api/q", json={"query": "metaheuristic"})
        assert r.status_code == 200
    overflow = client.post("/api/q", json={"query": "metaheuristic"})
    assert overflow.status_code == 429
    body = overflow.json()
    assert body["detail"]["error"] == "quota_exceeded"
    assert body["detail"]["limit"] == 3
    assert body["detail"]["tier"] == "anon"
    assert "Retry-After" in overflow.headers


# ───── V1-S11: çift dil paralel arama (KD-V1-S11-01..04) ─────


def _make_translate_llm(detected_lang: str, english_query: str) -> Any:
    """Translate_query mode için fake llm helper — başarılı QueryTranslationLLM döner."""

    async def fake_llm(
        prompt: str,
        *,
        tier: str = "flash",
        mode: str = "default",
        structured_output_schema: Any = None,
        **_: Any,
    ) -> Any:
        class _Resp:
            text = "(structured)"
            parsed_output = QueryTranslationLLM(
                detected_lang=detected_lang,  # type: ignore[arg-type]
                english_query=english_query,
            )
            model_used = "gemini-flash-tr"
            tokens_in = 10
            tokens_out = 20
            latency_ms = 100

        return _Resp()

    return fake_llm


def test_q_tr_query_runs_two_parallel_searches(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KD-V1-S11-02/03: TR sorgu → translate → 2 paralel search + translation field."""
    monkeypatch.setattr(
        "api.routes.q.llm_service.call",
        _make_translate_llm("tr", "transformer attention"),
    )

    calls: list[str] = []

    async def tracking_search(
        query: str,
        *,
        limit: int = 25,
        year_from: int | None = None,
        year_to: int | None = None,
        lang: str | None = None,
        settings: Any = None,
    ) -> list[PaperPreview]:
        calls.append(query)
        # Her sorgu farklı openalex_id'li 25 makale döner (dedup test için ayrı)
        offset = len(calls) * 1000
        return [_mock_paper(offset + i) for i in range(limit)]

    monkeypatch.setattr("api.routes.q.search_papers", tracking_search)

    response = client.post("/api/q", json={"query": "transformer dikkat"})
    assert response.status_code == 200, response.text
    body = response.json()

    # 2 paralel search çağrıldı (orig + EN)
    assert len(calls) == 2
    assert "transformer dikkat" in calls
    assert "transformer attention" in calls

    # translation field non-null + içerik
    assert body["translation"] is not None
    assert body["translation"]["original"] == "transformer dikkat"
    assert body["translation"]["detected_lang"] == "tr"
    assert body["translation"]["english_query"] == "transformer attention"

    # KD-V1-S11-01: lang filter geçilmedi
    assert len(body["papers"]) == 25


def test_q_en_query_skips_second_search(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KD-V1-S11-02: detected_lang='en' → 1 search + translation.detected_lang='en'."""
    monkeypatch.setattr(
        "api.routes.q.llm_service.call",
        _make_translate_llm("en", "transformer attention"),
    )

    calls: list[str] = []

    async def tracking_search(
        query: str, *, limit: int = 25, **_: Any
    ) -> list[PaperPreview]:
        calls.append(query)
        return [_mock_paper(i) for i in range(limit)]

    monkeypatch.setattr("api.routes.q.search_papers", tracking_search)

    response = client.post("/api/q", json={"query": "transformer attention"})
    assert response.status_code == 200, response.text
    body = response.json()

    # Tek search (EN ise 2. atlanır)
    assert len(calls) == 1
    assert calls[0] == "transformer attention"
    assert body["translation"]["detected_lang"] == "en"
    assert body["translation"]["english_query"] == "transformer attention"


def test_q_translate_fail_graceful_degrade(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KD-V1-S11-04: translate exception → 1 search + translation=None (degraded)."""

    async def failing_llm(*_a: Any, **_kw: Any) -> Any:
        raise RuntimeError("gemini timeout")

    monkeypatch.setattr("api.routes.q.llm_service.call", failing_llm)

    calls: list[str] = []

    async def tracking_search(
        query: str, *, limit: int = 25, **_: Any
    ) -> list[PaperPreview]:
        calls.append(query)
        return [_mock_paper(i) for i in range(limit)]

    monkeypatch.setattr("api.routes.q.search_papers", tracking_search)

    response = client.post("/api/q", json={"query": "transformer dikkat"})
    assert response.status_code == 200, response.text
    body = response.json()

    # Translate fail → 1 search (sadece kullanıcı dili) + translation null
    assert len(calls) == 1
    assert body["translation"] is None
    assert len(body["papers"]) == 25


def test_q_dedup_by_openalex_id(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KD-V1-S11-03: 2 query çakışan papers → dedup by openalex_id."""
    monkeypatch.setattr(
        "api.routes.q.llm_service.call",
        _make_translate_llm("tr", "transformer attention"),
    )

    call_idx = {"n": 0}

    async def overlapping_search(
        query: str, *, limit: int = 25, **_: Any
    ) -> list[PaperPreview]:
        call_idx["n"] += 1
        # 1. arama: idx 0..24 (cited 100..76) — yüksek cited önce
        # 2. arama: idx 20..29 (cited 50..41) — 5 örtüşme (20..24)
        if call_idx["n"] == 1:
            return [
                PaperPreview(
                    openalex_id=f"https://openalex.org/W{2000 + i}",
                    title=f"P{i}",
                    cited_by_count=100 - i,
                )
                for i in range(25)
            ]
        return [
            PaperPreview(
                openalex_id=f"https://openalex.org/W{2000 + i}",
                title=f"P{i}",
                cited_by_count=50 - (i - 20),
            )
            for i in range(20, 30)
        ]

    monkeypatch.setattr("api.routes.q.search_papers", overlapping_search)

    response = client.post("/api/q", json={"query": "x dikkat"})
    assert response.status_code == 200, response.text
    body = response.json()

    # Toplam unique: 30 (W2000..W2029) — top-25 dönmeli
    assert len(body["papers"]) == 25
    # Tüm openalex_id'ler unique
    ids = [p["openalex_id"] for p in body["papers"]]
    assert len(set(ids)) == 25
    # B-6 sonrası: cited_by_count desc YOK. Sıralama OpenAlex relevance order
    # (mock'ta query gönderim sırası), interleave + ilk-görme öncelikli dedup.
    # 1. arama 25 paper (W2000..W2024), 2. arama 10 paper (W2020..W2029).
    # Interleave: i=0 W2000+W2020, i=1 W2001+W2021, ... her dilden top-relevance
    # erken görünür. İnvariant: W2000 (1. dilin top-1) HER ZAMAN ids[0]; ikinci
    # dilin top-1'i (W2020) ids[1]; yeni W2029 unique-id setinde mutlaka var.
    assert ids[0] == "https://openalex.org/W2000"
    assert ids[1] == "https://openalex.org/W2020"
    assert "https://openalex.org/W2029" in ids


def test_q_response_includes_translation_field(client: TestClient) -> None:
    """QResponse'da translation alanı var (default fake llm None döner)."""
    response = client.post("/api/q", json={"query": "metaheuristic"})
    assert response.status_code == 200
    body = response.json()
    assert "translation" in body  # alan mevcut, değer None olabilir


# ───── /api/q/literature-review ─────


def test_lit_review_anon_3_papers_happy_path(client: TestClient) -> None:
    """Anon 3 paper seçimi → 200, 3 reference, tek blok content."""
    response = client.post(
        "/api/q/literature-review",
        json={"paper_ids": ["W1000", "W1001", "W1002"], "lang": "tr"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    review = body["review"]
    # KD-V1-S10-04 revize: tek blok content, alt-bölüm/title yok.
    assert "content" in review
    assert isinstance(review["content"], str)
    assert len(review["content"]) >= 50
    assert "title" not in review
    assert "introduction" not in review
    assert len(review["references"]) == 3
    assert review["references"][0]["index"] == 1
    assert body["quota_remaining"] == 2  # anon limit=3


def test_lit_review_anon_more_than_3_papers_returns_403(client: TestClient) -> None:
    """KD-V1-S10-02: Anon paper_ids>3 → 403 tier_paper_limit."""
    response = client.post(
        "/api/q/literature-review",
        json={"paper_ids": [f"W{1000+i}" for i in range(4)], "lang": "tr"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["detail"]["error"] == "tier_paper_limit"
    assert body["detail"]["max_papers"] == 3
    assert body["detail"]["submitted"] == 4


def test_lit_review_authed_25_papers(client: TestClient, auth_token: str) -> None:
    """Authed: 25 paper seçimi → 200, 25 reference, content tek blok."""
    response = client.post(
        "/api/q/literature-review",
        json={
            "paper_ids": [f"W{1000+i}" for i in range(25)],
            "lang": "tr",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    review = body["review"]
    assert len(review["references"]) == 25
    assert isinstance(review["content"], str)
    assert "[01]" in review["content"]  # mock cite formatı
    assert body["quota_remaining"] == 9  # ogrenci limit=10


def test_lit_review_empty_paper_ids_returns_422(client: TestClient) -> None:
    """paper_ids boş → 422 (Pydantic min_length=1)."""
    response = client.post(
        "/api/q/literature-review",
        json={"paper_ids": [], "lang": "tr"},
    )
    assert response.status_code == 422


def test_lit_review_paper_ids_over_25_returns_422(
    client: TestClient, auth_token: str
) -> None:
    """paper_ids>25 → 422 (Pydantic max_length=25)."""
    response = client.post(
        "/api/q/literature-review",
        json={"paper_ids": [f"W{1000+i}" for i in range(26)], "lang": "tr"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422


def test_lit_review_invalid_lang_returns_422(client: TestClient) -> None:
    """lang Literal["tr","en","id"] dışı → 422."""
    response = client.post(
        "/api/q/literature-review",
        json={"paper_ids": ["W1000"], "lang": "fr"},
    )
    assert response.status_code == 422


def test_lit_review_openalex_no_results_returns_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OpenAlex 0 sonuç → 422 no_papers_found."""

    async def empty_by_ids(
        ids: list[str], *, settings: Any = None
    ) -> list[PaperPreview]:
        return []

    monkeypatch.setattr("api.routes.q.fetch_papers_by_ids", empty_by_ids)

    response = client.post(
        "/api/q/literature-review",
        json={"paper_ids": ["W9999"], "lang": "tr"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "no_papers_found"


def test_lit_review_llm_failure_returns_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LLM 2 deneme de exception → 502 empty_llm_output."""

    async def bad_llm(*_a: Any, **_kw: Any) -> Any:
        raise RuntimeError("gemini timeout")

    monkeypatch.setattr("api.routes.q.llm_service.call", bad_llm)

    response = client.post(
        "/api/q/literature-review",
        json={"paper_ids": ["W1000"], "lang": "tr"},
    )
    assert response.status_code == 502
    assert response.json()["detail"]["error"] == "empty_llm_output"


def test_lit_review_parse_fail_returns_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B-5 regression: LLM cevap döner ama structured_output parse edilemez
    (parsed_output != LiteratureReviewLLM) → 200 OK + boş content YERİNE 502.
    Pydantic min_length=50 / max_length=5000 ihlali bu yola düşürür."""

    class _NoParseResp:
        text = "garbled non-json"
        parsed_output = None
        model_used = "gemini-flash-tr"
        tokens_in = 10
        tokens_out = 5
        latency_ms = 100

    async def parse_fail_llm(*_a: Any, **_kw: Any) -> Any:
        return _NoParseResp()

    monkeypatch.setattr("api.routes.q.llm_service.call", parse_fail_llm)

    response = client.post(
        "/api/q/literature-review",
        json={"paper_ids": ["W1000"], "lang": "tr"},
    )
    assert response.status_code == 502
    body = response.json()["detail"]
    assert body["error"] == "empty_llm_output"
    assert body["reason"] == "structured_output_missing"


def test_lit_review_request_forbids_extra_fields(client: TestClient) -> None:
    response = client.post(
        "/api/q/literature-review",
        json={"paper_ids": ["W1000"], "evil_extra": "x"},
    )
    assert response.status_code == 422


# ───── /api/q2 (LOCKED_SOON — DM-054 sonsuza dek) ─────


def test_q2_locked_soon_returns_403(client: TestClient) -> None:
    response = client.post("/api/q2", json={})
    assert response.status_code == 403
    body = response.json()
    assert body["detail"]["error"] == "tier_locked_soon"
    assert body["detail"]["soon"] is True


def test_q2_locked_soon_even_with_auth(
    client: TestClient, auth_token: str
) -> None:
    """Authed kullanıcının bile q2 erişimi yok — DM-054."""
    response = client.post(
        "/api/q2", json={}, headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 403


# ───── HK-1: extra forbid ─────


def test_q_request_forbids_extra_fields(client: TestClient) -> None:
    response = client.post(
        "/api/q",
        json={"query": "x", "evil_extra_field": "should reject"},
    )
    assert response.status_code == 422
