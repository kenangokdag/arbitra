"""POST /api/search end-to-end integration tests (F3a §4 S2-S7).

Mock 5-katman backend ile çalışır. Cache helpers monkeypatch ile in-memory dict.
"""

import json
from collections.abc import Iterator

import jwt
import pytest
from fastapi.testclient import TestClient

from api.middleware.rate_limit import _window

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _clear_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Her test öncesi rate window + cache temizle, route cache helper'ı in-memory'ye bind."""
    _window.clear()
    storage: dict[str, str] = {}

    def fake_cache_get(namespace: str, key: str) -> object | None:
        raw = storage.get(f"{namespace}:{key}")
        if raw is None:
            return None
        return json.loads(raw)

    def fake_cache_set(namespace: str, key: str, value: object, ttl: int | None = None) -> None:
        del ttl  # mock'ta TTL takip etmiyoruz
        storage[f"{namespace}:{key}"] = json.dumps(value)

    monkeypatch.setattr("api.routes.search.cache_get", fake_cache_get)
    monkeypatch.setattr("api.routes.search.cache_set", fake_cache_set)
    yield storage


@pytest.fixture
def auth_token() -> str:
    return jwt.encode({"sub": "user-search-int"}, "x", algorithm="HS256")


@pytest.fixture
def authed_client(client: TestClient, auth_token: str) -> TestClient:
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client


# ---------- S2: TR happy path ----------


def test_search_tr_happy_path(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/search",
        json={"query": "makine öğrenmesi tıp uygulaması", "k": 10, "language_hint": "tr"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "papers" in body
    assert len(body["papers"]) == 10
    assert body["faithfulness_meta"]["jsonschema_pct"] == 100
    assert body["faithfulness_meta"]["minicheck_nli"] >= 0.7
    assert body["faithfulness_meta"]["alce_recall"] >= 0.8
    assert body["decision_band"] in {"canon", "frontier", "strong_evidence", "risk"}
    assert body["latency_ms"] >= 0
    assert 0 <= body["pmid_match_score"] <= 1


def test_search_response_paper_card_shape(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/search", json={"query": "deep learning", "k": 5}
    )
    assert response.status_code == 200
    paper = response.json()["papers"][0]
    assert paper["paper_id"]
    assert paper["pmid"].count(".") == 11  # 12 segment K6
    assert paper["decision_band"] in {"canon", "frontier", "strong_evidence", "risk"}
    assert "signals_13" in paper
    assert "citations_lvr" in paper
    # K5 — her cümle paper_id+span+lvr_distance
    if paper["citations_lvr"]:
        cit = paper["citations_lvr"][0]
        assert cit["paper_id"]
        assert cit["lvr_distance"] >= 0.7


# ---------- S4: 422 schema validation ----------


def test_search_k_above_max_returns_422(authed_client: TestClient) -> None:
    response = authed_client.post("/api/search", json={"query": "test query", "k": 999})
    assert response.status_code == 422


def test_search_query_too_short_returns_422(authed_client: TestClient) -> None:
    response = authed_client.post("/api/search", json={"query": "ab", "k": 5})
    assert response.status_code == 422


def test_search_invalid_language_hint_returns_422(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/search", json={"query": "test query", "language_hint": "fr"}
    )
    assert response.status_code == 422


# ---------- S5: 401 auth ----------


def test_search_missing_auth_returns_401(client: TestClient) -> None:
    response = client.post("/api/search", json={"query": "test query"})
    assert response.status_code == 401


# ---------- S7: cache hit ----------


def test_search_cache_hit_on_repeat(
    authed_client: TestClient, _clear_state: dict[str, str]
) -> None:
    """Aynı request ikinci çağrıda cache'ten döner — storage tek satıra düşer."""
    payload = {"query": "derin öğrenme depresyon tedavisi", "k": 5}
    r1 = authed_client.post("/api/search", json=payload)
    assert r1.status_code == 200
    keys_after_first = list(_clear_state.keys())
    assert any(k.startswith("q:") for k in keys_after_first)

    r2 = authed_client.post("/api/search", json=payload)
    assert r2.status_code == 200
    # İkinci çağrı aynı body shape, latency_ms farklı olabilir
    body1 = r1.json()
    body2 = r2.json()
    assert body1["papers"] == body2["papers"]
    assert body1["faithfulness_meta"] == body2["faithfulness_meta"]
    # Cache hit sinyali — storage'da yeni anahtar yok (aynı hash)
    assert list(_clear_state.keys()) == keys_after_first


# ---------- P013: resilience exception → HTTP status mapping ----------


class _RaisingPoolRouter:
    """Test-only PoolRouter — fan_out her zaman verilen exception'ı raise eder."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def fan_out(
        self,
        sub_queries: list[str],
        anchor_ids: list[str],
        top_k: int = 200,
        filter: dict[str, object] | None = None,
    ) -> list[tuple[str, float]]:
        del sub_queries, anchor_ids, top_k, filter
        raise self._exc


def _override_pool_router(client: TestClient, exc: Exception) -> None:
    from api.routes import search as search_route

    client.app.dependency_overrides[search_route.get_pool_router] = (
        lambda: _RaisingPoolRouter(exc)
    )


def _clear_pool_router_override(client: TestClient) -> None:
    from api.routes import search as search_route

    client.app.dependency_overrides.pop(search_route.get_pool_router, None)


def test_search_pool_router_timeout_returns_504(
    authed_client: TestClient,
) -> None:
    """ResilienceTimeoutError → HTTP 504 Gateway Timeout."""
    from api.utils.resilience import ResilienceTimeoutError

    _override_pool_router(authed_client, ResilienceTimeoutError("simulated"))
    try:
        response = authed_client.post(
            "/api/search", json={"query": "timeout simülasyonu", "k": 5}
        )
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"].lower()
    finally:
        _clear_pool_router_override(authed_client)


def test_search_pinecone_failure_returns_503(
    authed_client: TestClient,
) -> None:
    """PineconeQueryError → HTTP 503 Service Unavailable."""
    from api.db.pinecone_client import PineconeQueryError

    _override_pool_router(authed_client, PineconeQueryError("simulated outage"))
    try:
        response = authed_client.post(
            "/api/search", json={"query": "pinecone outage testi", "k": 5}
        )
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()
    finally:
        _clear_pool_router_override(authed_client)


def test_search_supabase_failure_returns_503(
    authed_client: TestClient,
) -> None:
    """SupabaseQueryError → HTTP 503 Service Unavailable."""
    from api.db.supabase_client import SupabaseQueryError

    _override_pool_router(authed_client, SupabaseQueryError("simulated outage"))
    try:
        response = authed_client.post(
            "/api/search", json={"query": "supabase outage testi", "k": 5}
        )
        assert response.status_code == 503
    finally:
        _clear_pool_router_override(authed_client)


def test_search_unhandled_exception_returns_500(auth_token: str) -> None:
    """Beklenmedik RuntimeError 503/504 mapping'e girmez → 500.

    Framework varsayılanı `raise_server_exceptions=True` testte exception'ı
    propagate eder; bu test gerçek prod davranışını taklit etmek için
    `raise_server_exceptions=False` ile yeniden TestClient kurar.
    """
    from api.main import create_app
    from api.routes import search as search_route

    app = create_app()
    app.dependency_overrides[search_route.get_pool_router] = (
        lambda: _RaisingPoolRouter(RuntimeError("generic"))
    )
    with TestClient(app, raise_server_exceptions=False) as fresh:
        fresh.headers["Authorization"] = f"Bearer {auth_token}"
        response = fresh.post(
            "/api/search",
            json={"query": "generic exception", "k": 5},
        )
        assert response.status_code == 500
