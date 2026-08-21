"""M-8 regression: OpenAlex 4xx (429 hariç) retry yapmamalı.

Önceki davranış: `retry_on=(httpx.HTTPError,)` HTTPStatusError'ı kapsadığı için
400/422 client hataları RETRY_ATTEMPTS kez tekrarlanıyordu (3× boşuna istek).
Yeni davranış: 400 ≤ status < 500 ve status != 429 → tek seferde OpenAlexError.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from api.services.openalex_polite import (
    OpenAlexError,
    _auth_params,
    fetch_papers_by_ids,
    search_papers,
)

pytestmark = pytest.mark.unit


class _CountingTransport(httpx.AsyncBaseTransport):
    """httpx transport — her request'i sayar ve sabit status döner."""

    def __init__(self, status_code: int, body: str = "{}") -> None:
        self.status_code = status_code
        self.body = body
        self.calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return httpx.Response(self.status_code, text=self.body)


@pytest.fixture(autouse=True)
def _ensure_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_EMAIL", "test@example.invalid")
    monkeypatch.setenv("RETRY_ATTEMPTS", "3")
    from api.config import get_settings

    get_settings.cache_clear()


def _patched_client_factory(
    transport: httpx.AsyncBaseTransport,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """openalex_polite.httpx.AsyncClient'i transport enjekte edilmiş versiyonla değiştir."""
    real_cls = httpx.AsyncClient

    def _factory(*a: Any, **kw: Any) -> httpx.AsyncClient:
        kw["transport"] = transport
        return real_cls(*a, **kw)

    import api.services.openalex_polite as op

    monkeypatch.setattr(op.httpx, "AsyncClient", _factory)


@pytest.mark.asyncio
async def test_openalex_search_400_no_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """400 client error → 1 deneme + OpenAlexError (3× retry yok)."""
    transport = _CountingTransport(status_code=400, body='{"error":"bad_query"}')
    _patched_client_factory(transport, monkeypatch)

    with pytest.raises(OpenAlexError, match="openalex client error 400"):
        await search_papers("test", limit=5)

    assert transport.calls == 1, f"Expected 1 call, got {transport.calls}"


@pytest.mark.asyncio
async def test_openalex_search_429_does_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 (rate limit) → retry yapılır (RETRY_ATTEMPTS=3)."""
    transport = _CountingTransport(status_code=429, body='{"error":"rate"}')
    _patched_client_factory(transport, monkeypatch)

    with pytest.raises(OpenAlexError):
        await search_papers("test", limit=5)

    assert transport.calls == 3, f"Expected 3 retries on 429, got {transport.calls}"


@pytest.mark.asyncio
async def test_openalex_by_ids_422_no_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """422 (invalid ids) → 1 deneme."""
    transport = _CountingTransport(status_code=422, body='{"error":"invalid_ids"}')
    _patched_client_factory(transport, monkeypatch)

    with pytest.raises(OpenAlexError, match="openalex client error 422"):
        await fetch_papers_by_ids(["W1"])

    assert transport.calls == 1


# ── N-2/N-3 polite-pool sliding-window limiter ─────────────────────────────
@pytest.mark.asyncio
async def test_rate_limiter_throttles_burst() -> None:
    """rate+1 paralel acquire: ek istek ~1 saniye bekler.

    10 acquire'ı paralel başlat; 11. ~1s gecikmeli olmalı (window dolmuş).
    """
    import asyncio
    import time

    from api.services.openalex_polite import _SlidingWindowLimiter

    limiter = _SlidingWindowLimiter(rate=10, window_seconds=1.0)
    start = time.monotonic()
    # 10 hızlı ardarda acquire
    for _ in range(10):
        await limiter.acquire()
    burst_elapsed = time.monotonic() - start
    assert burst_elapsed < 0.5, f"10 acquire should be fast, took {burst_elapsed:.2f}s"

    # 11. istek pencereyi aşar → ~1s beklemeli
    t0 = time.monotonic()
    await limiter.acquire()
    wait_elapsed = time.monotonic() - t0
    assert 0.9 <= wait_elapsed <= 1.5, (
        f"11th acquire should wait ~1s, took {wait_elapsed:.2f}s"
    )


# ── 2026-08-10: OPENALEX_API_KEY (bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md §36) ──
# OpenAlex kullanim-bazli ucretlendirmeye gecti: api_key YOKSA gunluk $0.10
# (~100 arama), VARSA gunluk $1 (10x). Bu testler api_key'in (a) dogru
# kosulda parametrelere eklendigini, (b) bossa dogru eski davranisa
# (mailto-only) dustugunu, (c) GERCEK giden HTTP istegine ulastigini kanitlar.


class _CapturingTransport(httpx.AsyncBaseTransport):
    """httpx transport - son isteğin tam URL'ini (query string dahil) yakalar."""

    def __init__(self, status_code: int = 200, body: str = '{"results": []}') -> None:
        self.status_code = status_code
        self.body = body
        self.last_request: httpx.Request | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.last_request = request
        return httpx.Response(self.status_code, text=self.body)


def test_auth_params_includes_api_key_when_configured() -> None:
    from api.config import Settings

    cfg = Settings(OPENALEX_EMAIL="x@y.com", OPENALEX_API_KEY="secret123")
    assert _auth_params(cfg) == {"mailto": "x@y.com", "api_key": "secret123"}


def test_auth_params_omits_api_key_when_empty() -> None:
    """Bos OPENALEX_API_KEY -> durustce eski mailto-only davranisa duser,
    'api_key=' gibi bos bir parametre GONDERILMEZ (sessiz hata riski)."""
    from api.config import Settings

    cfg = Settings(OPENALEX_EMAIL="x@y.com", OPENALEX_API_KEY="")
    assert _auth_params(cfg) == {"mailto": "x@y.com"}
    assert "api_key" not in _auth_params(cfg)


@pytest.mark.asyncio
async def test_search_papers_sends_api_key_in_real_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """api_key konfigure edildiginde GERCEKTEN giden HTTP istegine ulasiyor mu -
    sadece _auth_params()'in kendi cikti sozlesmesini degil, wiring'in ucuna
    kadar (search_papers -> httpx request) dogru gittigini kanitlar."""
    monkeypatch.setenv("OPENALEX_API_KEY", "secret123")
    from api.config import get_settings

    get_settings.cache_clear()

    transport = _CapturingTransport()
    _patched_client_factory(transport, monkeypatch)

    await search_papers("test query", limit=1)

    assert transport.last_request is not None
    query = str(transport.last_request.url.params)
    assert "api_key=secret123" in query
    assert "mailto=test%40example.invalid" in query
