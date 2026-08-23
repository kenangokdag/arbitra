"""2026-08-23 — Semantic Scholar (S2) EN-DAR-KAPSAMLI fallback resolver.

BAĞLAM: `review_citation_service.py`'nin OpenAlex-tabanlı çözümü, arXiv/OpenReview
gibi kaynakları (`net/forum?id=...` linkleri) sistematik olarak daha az buluyor
(bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md — OpenAlex kapsam boşluğu, ML/CS makaleleri
haksız cezalanabiliyor). Kullanıcı onayı: OpenAlex `not_found_in_index` derse
S2 dene, OpenAlex akışına DOKUNMA.

KAPSAM BİLİNÇLİ DAR TUTULDU (guardian 2026-08-23 onayı):
  - ScholarlyProvider Protocol'ünü TAM implement ETMEZ (5 metot gereksiz —
    sadece resolve_reference'a benzer bir yardımcı fonksiyon var).
  - Sadece not_found_in_index → resolved YÜKSELTMESİ için kullanılır.
  - ASLA "fabricated" tespiti için KULLANILMAZ (yeni bir yanlış-suçlama yüzeyi
    açmamak için bilinçli sınır — moat-gate'in fabricated/retracted sayaçlarına
    hiç dokunmaz).
  - S2 arızası (ağ/429/timeout) SESSİZCE yutulur ama LOGLANIR (uyarı) — referans
    olduğu gibi (S2 hiç yokmuş gibi) not_found_in_index kalır, ASLA daha kötü
    olmaz (best-effort, regresyon riski yok).

RATE LIMIT UYARISI (canlı doğrulandı, 2026-08-23): anonim/key'siz tek bir S2
arama isteği bile HEMEN 429 döndürdü (WebFetch ile gözlemlendi, bu oturumda).
Resmi rate-limit rakamını dış dokümantasyondan doğrulayamadım (API docs sayfası
JS-render, WebFetch içeriği çekemedi) — bu yüzden ÇOK TEMKİNLİ, gözlemlenen
kanıta dayalı bir limiter kullanılıyor (1 istek / ~4 saniye), OpenAlex'in
10 req/sec limitinden BAĞIMSIZ ve çok daha yavaş.

İSTEMCİ REUSE: sliding-window limiter deseni openalex_polite.py'deki
_SlidingWindowLimiter'dan AYNEN alınır (import edilir, yeniden yazılmaz).
call_resilient (api/utils/resilience.py) reuse edilir AMA 429'da retry
YAPILMAZ (S2'nin gözlemlenen agresif rate-limitinde retry durumu kötüleştirir
— OpenAlex'in aksine, orada 429 retry edilir çünkü polite-pool limiti gevşek).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from api.config import Settings, get_settings
from api.services.openalex_polite import _SlidingWindowLimiter

logger = logging.getLogger(__name__)

S2_TIMEOUT_SECONDS = 10.0

# Gözlemlenen agresif rate-limit karşısında temkinli: 1 istek / 4 saniye.
# Resmi rakam doğrulanamadı (bkz. modül docstring) — bilinçli aşırı-temkinli.
_S2_RPS = 1
_S2_WINDOW_SECONDS = 4.0
_S2_RATE_LIMITER = _SlidingWindowLimiter(_S2_RPS, _S2_WINDOW_SECONDS)


class SemanticScholarError(Exception):
    """S2 çağrısı başarısız (ağ/429/malformed) — çağıran SESSİZCE yutar,
    sadece loglar (bkz. modül docstring — best-effort, asla daha kötü değil)."""


class SemanticScholarMatch:
    """S2 arama sonucundan indirgenmiş, resolve_reference'ın _resolve_via_work
    ile aynı şekle (title/year/authors/doi) eşlenebilir minimal alan seti."""

    __slots__ = ("title", "year", "authors", "doi", "paper_id")

    def __init__(
        self,
        *,
        title: str | None,
        year: int | None,
        authors: list[str],
        doi: str | None,
        paper_id: str | None,
    ) -> None:
        self.title = title
        self.year = year
        self.authors = authors
        self.doi = doi
        self.paper_id = paper_id


def _match_from_raw(raw: dict[str, Any]) -> SemanticScholarMatch:
    external_ids = raw.get("externalIds") or {}
    authors_raw = raw.get("authors") or []
    authors = [a.get("name", "") for a in authors_raw if isinstance(a, dict) and a.get("name")]
    return SemanticScholarMatch(
        title=raw.get("title"),
        year=raw.get("year") if isinstance(raw.get("year"), int) else None,
        authors=authors,
        doi=external_ids.get("DOI"),
        paper_id=raw.get("paperId"),
    )


async def search_semantic_scholar(
    query: str,
    *,
    limit: int = 5,
    settings: Settings | None = None,
) -> list[SemanticScholarMatch]:
    """Başlık(+yazar) sorgusuyla S2 arar → indirgenmiş eşleşme listesi.

    HATA-YUTMA YOK (çağırana kadar): ağ/429/malformed → SemanticScholarError
    raise eder. Çağıran (review_citation_service.py) bunu SESSİZCE yutup
    not_found_in_index'te bırakır — burada değil, orada (best-effort sınırı
    açıkça çağıran tarafta olsun, bu fonksiyon dürüst arıza bildirir).

    2026-08-23 (canlı testte kanıtlandı): SEMANTIC_SCHOLAR_API_KEY boşsa HİÇ
    AĞ ÇAĞRISI YAPILMAZ — key'siz anonim kota HEMEN 429 veriyor (ham S2
    yanıtı: "apply for a key for higher rate limits"), boşuna gecikme
    eklemesin diye erken, dürüst "not configured" hatası fırlatılır
    (OpenAlex'in auth_missing deseniyle AYNI mantık, openalex_polite.py'deki
    `if not cfg.OPENALEX_EMAIL: raise` ile birebir simetrik)."""
    cfg = settings or get_settings()
    if not cfg.SEMANTIC_SCHOLAR_API_KEY:
        raise SemanticScholarError("semantic_scholar not configured (no API key)")

    params: dict[str, str | int] = {
        "query": query,
        "limit": limit,
        "fields": "title,year,authors,externalIds",
    }
    headers = {"x-api-key": cfg.SEMANTIC_SCHOLAR_API_KEY}
    # api/config.py:SEMANTIC_SCHOLAR_BASE_URL — .env.example'da ZATEN
    # tanımlıydı (S2 fallback'in her zaman planlandığının bir başka kanıtı),
    # sadece hiç kullanılmıyordu; şimdi gerçekten bağlandı.
    search_url = cfg.SEMANTIC_SCHOLAR_BASE_URL.rstrip("/") + "/paper/search"

    await _S2_RATE_LIMITER.acquire()
    try:
        async with httpx.AsyncClient(timeout=S2_TIMEOUT_SECONDS) as client:
            resp = await client.get(search_url, params=params, headers=headers)
    except httpx.HTTPError as exc:
        raise SemanticScholarError(f"semantic_scholar network error: {exc}") from exc

    if resp.status_code == 429:
        # Retry YOK (bilinçli — modül docstring). Dürüst arıza.
        raise SemanticScholarError("semantic_scholar rate_limited (429)")
    if resp.status_code == 404:
        return []
    if resp.status_code >= 400:
        raise SemanticScholarError(
            f"semantic_scholar HTTP {resp.status_code}: {resp.text[:200]}"
        )

    try:
        payload = resp.json()
        raw_items = payload.get("data") or []
    except Exception as exc:  # malformed JSON — dürüst arıza, uydurma sonuç yok.
        raise SemanticScholarError(f"semantic_scholar malformed response: {exc}") from exc

    return [_match_from_raw(item) for item in raw_items if isinstance(item, dict)]


__all__ = [
    "SemanticScholarError",
    "SemanticScholarMatch",
    "search_semantic_scholar",
]
