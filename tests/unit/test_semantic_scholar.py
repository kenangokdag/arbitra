"""2026-08-23 — Semantic Scholar fallback resolver testleri.

Ağ MOCK'lanır (httpx.AsyncClient transport enjeksiyonu, openalex_polite'in
test_openalex_polite.py'deki AYNI deseni — gerçek S2 çağrısı YOK).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from engine.providers.semantic_scholar import (
    SemanticScholarError,
    search_semantic_scholar,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _fast_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    """_S2_RATE_LIMITER modül-seviyesi tekil (1 istek/4sn) — testler arası
    paylaşılıp her testi ~4sn geciktirmesin diye, her testte TAZE ve hızlı
    (pratikte sınırsız) bir limiter'la değiştirilir. Üretim davranışı
    ETKİLENMEZ (bu sadece test izolasyonu, gerçek koddaki değer değişmez)."""
    import engine.providers.semantic_scholar as s2

    monkeypatch.setattr(s2, "_S2_RATE_LIMITER", s2._SlidingWindowLimiter(1000, 0.001))


@pytest.fixture(autouse=True)
def _ensure_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-08-23: SEMANTIC_SCHOLAR_API_KEY boşsa search_semantic_scholar artık
    ağa HİÇ çıkmadan erken hata verir (canlı testte bulunan gerçek regresyon
    düzeltmesi — key'siz kota anında 429 veriyordu). Bu dosyanın testleri HTTP
    katmanını mock'ladığı için sahte ama DOLU bir key gerekiyor."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-key-for-unit-tests")
    from api.config import get_settings

    get_settings.cache_clear()


class _CountingTransport(httpx.AsyncBaseTransport):
    """test_openalex_polite.py:_CountingTransport ile AYNI desen — her isteği
    sayar, sabit status/body döner."""

    def __init__(self, status_code: int, body: str = "{}") -> None:
        self.status_code = status_code
        self.body = body
        self.calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return httpx.Response(self.status_code, text=self.body)


def _patched_client_factory(
    transport: httpx.AsyncBaseTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_cls = httpx.AsyncClient

    def _factory(*a: Any, **kw: Any) -> httpx.AsyncClient:
        kw["transport"] = transport
        return real_cls(*a, **kw)

    import engine.providers.semantic_scholar as s2

    monkeypatch.setattr(s2.httpx, "AsyncClient", _factory)


async def test_search_no_key_skips_network_entirely(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-08-23 kanıtlı regresyon: SEMANTIC_SCHOLAR_API_KEY boşsa hiç ağ
    çağrısı YAPILMAMALI (canlı testte key'siz kota anında 429 veriyordu —
    boşuna gecikme/istek eklenmesin diye erken, dürüst hata)."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "")
    from api.config import get_settings

    get_settings.cache_clear()

    transport = _CountingTransport(status_code=200, body='{"data": []}')
    _patched_client_factory(transport, monkeypatch)

    with pytest.raises(SemanticScholarError, match="not configured"):
        await search_semantic_scholar("some query")
    assert transport.calls == 0  # AĞA HİÇ ÇIKILMADI


async def test_search_returns_parsed_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Başarılı yanıt → title/year/authors/doi doğru indirgenir."""
    body = (
        '{"total": 1, "offset": 0, "data": [{'
        '"paperId": "abc123", "title": "Attention Is All You Need", "year": 2017, '
        '"authors": [{"name": "Ashish Vaswani"}, {"name": "Noam Shazeer"}], '
        '"externalIds": {"DOI": "10.5555/example", "ArXiv": "1706.03762"}'
        "}]}"
    )
    transport = _CountingTransport(status_code=200, body=body)
    _patched_client_factory(transport, monkeypatch)

    matches = await search_semantic_scholar("attention is all you need")
    assert len(matches) == 1
    m = matches[0]
    assert m.title == "Attention Is All You Need"
    assert m.year == 2017
    assert m.authors == ["Ashish Vaswani", "Noam Shazeer"]
    assert m.doi == "10.5555/example"
    assert m.paper_id == "abc123"
    assert transport.calls == 1


async def test_search_404_returns_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """404 → boş liste (yok, hata değil — OpenAlex ile aynı sözleşme)."""
    transport = _CountingTransport(status_code=404, body='{"error":"not_found"}')
    _patched_client_factory(transport, monkeypatch)

    matches = await search_semantic_scholar("nonexistent paper xyz")
    assert matches == []


async def test_search_429_raises_no_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 → SemanticScholarError, TEK deneme (retry YOK — bilinçli, modül
    docstring'inde gerekçeli: S2'nin gözlemlenen agresif rate-limiti)."""
    transport = _CountingTransport(status_code=429, body='{"error":"rate_limited"}')
    _patched_client_factory(transport, monkeypatch)

    with pytest.raises(SemanticScholarError, match="rate_limited"):
        await search_semantic_scholar("some query")
    assert transport.calls == 1


async def test_search_malformed_json_raises_honest_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bozuk JSON → SemanticScholarError (uydurma boş-liste ya da sahte eşleşme
    YOK — dürüst arıza, CLAUDE.md §3 hata-yutma yasağı)."""
    transport = _CountingTransport(status_code=200, body="not-json-at-all{{{")
    _patched_client_factory(transport, monkeypatch)

    with pytest.raises(SemanticScholarError, match="malformed"):
        await search_semantic_scholar("some query")


async def test_search_other_5xx_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """500 gibi diğer sunucu hataları da dürüst raise eder, sessiz boş-liste
    YOK."""
    transport = _CountingTransport(status_code=500, body='{"error":"internal"}')
    _patched_client_factory(transport, monkeypatch)

    with pytest.raises(SemanticScholarError, match="HTTP 500"):
        await search_semantic_scholar("some query")
