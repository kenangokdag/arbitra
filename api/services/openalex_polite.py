"""V1 OpenAlex polite-pool client — Q + Q1 makale arama.

kaynak: docs/plans/V1_vitrin_sprint.md §3 V1-01, §11 polite-pool
HK-3: canlı smoke test fixture zorunlu (`tests/fixtures/openalex_search.json`).

OpenAlex polite-pool: https://api.openalex.org/works?search=...&mailto=<email>
- Polite quota: 100K req/gün, 10 req/sec
- Filter: from_publication_date / to_publication_date / language / has_abstract:true
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from api.config import Settings, get_settings
from api.models.q import PaperPreview
from api.utils.resilience import call_resilient

logger = logging.getLogger(__name__)

OPENALEX_BASE = "https://api.openalex.org/works"

# N-2/N-3 (2026-05-27): OpenAlex polite-pool sliding-window rate limiter (10 req/sec).
# Kaynak: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
# Process-local — tek worker'da paralel coroutine'ler aynı kuyruğu paylaşır;
# multi-worker (uvicorn -w N) durumunda her worker bağımsız 10/s kullanır (cluster
# limit 100K/gün quota tarafı ile zaten korunur). Audit: AUDIT_REPORT.md §11 N-2/N-3.
_OPENALEX_RPS = 10
_OPENALEX_WINDOW_SECONDS = 1.0


class _SlidingWindowLimiter:
    """Async sliding-window rate limiter: rate_per_window içinde N istek."""

    def __init__(self, rate: int, window_seconds: float) -> None:
        self._rate = rate
        self._window = window_seconds
        self._lock = asyncio.Lock()
        self._timestamps: list[float] = []

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self._window
            self._timestamps = [t for t in self._timestamps if t > cutoff]
            if len(self._timestamps) >= self._rate:
                sleep_for = self._timestamps[0] + self._window - now + 0.01
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                now = time.monotonic()
                cutoff = now - self._window
                self._timestamps = [t for t in self._timestamps if t > cutoff]
            self._timestamps.append(now)


_RATE_LIMITER = _SlidingWindowLimiter(_OPENALEX_RPS, _OPENALEX_WINDOW_SECONDS)


def _auth_params(cfg: Settings) -> dict[str, str]:
    """OpenAlex kimlik parametreleri (2026-08-10 — bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md
    §36). OpenAlex kullanım-bazlı ücretlendirmeye geçti: `api_key` YOKSA günlük $0.10
    (≈100 arama çağrısı), VARSA günlük $1 (≈1000, 10x). `mailto` her durumda gönderilir
    (polite-pool kimliği, ayrıca gerekli). `OPENALEX_API_KEY` boşsa dürüstçe eski
    mailto-only davranışa düşer — sessizce hata vermez."""
    params: dict[str, str] = {"mailto": cfg.OPENALEX_EMAIL}
    if cfg.OPENALEX_API_KEY:
        params["api_key"] = cfg.OPENALEX_API_KEY
    return params


class OpenAlexError(Exception):
    """OpenAlex API hata sınıfı."""


def _abstract_from_inverted(inv: dict[str, list[int]] | None) -> str | None:
    """OpenAlex inverted_index → düz metin abstract."""
    if not inv:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions) or None


def _to_preview(work: dict[str, Any]) -> PaperPreview:
    """OpenAlex work payload → PaperPreview."""
    authors_raw = work.get("authorships") or []
    authors = [
        a.get("author", {}).get("display_name", "")
        for a in authors_raw
        if a.get("author", {}).get("display_name")
    ]
    venue = (
        (work.get("primary_location") or {}).get("source", {}) or {}
    ).get("display_name")

    return PaperPreview(
        openalex_id=work.get("id", ""),
        doi=work.get("doi"),
        title=work.get("title") or work.get("display_name") or "(başlıksız)",
        abstract=_abstract_from_inverted(work.get("abstract_inverted_index")),
        year=work.get("publication_year"),
        venue=venue,
        authors=authors[:10],
        cited_by_count=int(work.get("cited_by_count") or 0),
        mini_summary=None,
    )


async def search_papers(
    query: str,
    *,
    limit: int = 5,
    year_from: int | None = None,
    year_to: int | None = None,
    lang: str | None = None,
    settings: Settings | None = None,
) -> list[PaperPreview]:
    """OpenAlex polite-pool topic search → PaperPreview listesi.

    Sadece abstract'ı olan, en yüksek atıflı `limit` makale döner.
    """
    cfg = settings or get_settings()
    if not cfg.OPENALEX_EMAIL:
        raise OpenAlexError("OPENALEX_EMAIL not configured (polite-pool gerekli)")

    filters: list[str] = ["has_abstract:true"]
    if year_from is not None:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to is not None:
        filters.append(f"to_publication_date:{year_to}-12-31")
    if lang is not None:
        filters.append(f"language:{lang}")

    # B-6: kısa sorgularda topical relevance > citation-count.
    # OpenAlex `relevance_score` = lexical TF-IDF + meta-boosts; sort=cited_by_count:desc
    # konuyla ilgisiz ama çok atıflı paper'ları öne çıkarıyordu ("transformer attention"
    # sorgusunda "MizAR theorem proving" gibi). Audit: AUDIT_REPORT.md §11 B-6.
    params: dict[str, str | int] = {
        "search": query,
        "filter": ",".join(filters),
        "per-page": min(max(limit, 1), 25),
        "sort": "relevance_score:desc",
        **_auth_params(cfg),
    }

    async def _fetch() -> dict[str, Any]:
        await _RATE_LIMITER.acquire()  # N-2/N-3 polite 10/sec
        async with httpx.AsyncClient(timeout=cfg.OPENALEX_TIMEOUT_SECONDS) as client:
            resp = await client.get(OPENALEX_BASE, params=params)
            # M-8: 4xx (429 hariç) client hatası → retry boşa enerji; OpenAlexError
            # olarak doğrudan fırlat. 5xx/429/network hataları retry_on'a kalır.
            if 400 <= resp.status_code < 500 and resp.status_code != 429:
                raise OpenAlexError(
                    f"openalex client error {resp.status_code}: {resp.text[:200]}"
                )
            resp.raise_for_status()
            payload: dict[str, Any] = resp.json()
            return payload

    try:
        data = await call_resilient(
            _fetch,
            timeout=cfg.OPENALEX_TIMEOUT_SECONDS,
            settings=cfg,
            retry_on=(httpx.HTTPError,),
        )
    except OpenAlexError:
        raise
    except Exception as exc:
        logger.error("openalex search failed query=%r err=%s", query, exc)
        raise OpenAlexError(f"openalex search failed: {exc}") from exc

    works = data.get("results") or []
    return [_to_preview(w) for w in works[:limit]]


async def fetch_papers_by_ids(
    ids: list[str],
    *,
    settings: Settings | None = None,
) -> list[PaperPreview]:
    """OpenAlex polite-pool batch fetch — paper_ids → PaperPreview listesi.

    `ids` OpenAlex work ID'leri ('W12345' veya tam URL). Sıra korunur (input order).
    25 makale tek istekte alınır (?filter=ids.openalex:W1|W2|...).
    """
    cfg = settings or get_settings()
    if not cfg.OPENALEX_EMAIL:
        raise OpenAlexError("OPENALEX_EMAIL not configured (polite-pool gerekli)")
    if not ids:
        return []

    short_ids = [i.rsplit("/", 1)[-1] for i in ids]
    params: dict[str, str | int] = {
        "filter": f"ids.openalex:{'|'.join(short_ids)}",
        "per-page": min(len(short_ids), 25),
        **_auth_params(cfg),
    }

    async def _fetch() -> dict[str, Any]:
        await _RATE_LIMITER.acquire()  # N-2/N-3 polite 10/sec
        async with httpx.AsyncClient(timeout=cfg.OPENALEX_TIMEOUT_SECONDS) as client:
            resp = await client.get(OPENALEX_BASE, params=params)
            # M-8: 4xx (429 hariç) → retry yok, doğrudan OpenAlexError.
            if 400 <= resp.status_code < 500 and resp.status_code != 429:
                raise OpenAlexError(
                    f"openalex client error {resp.status_code}: {resp.text[:200]}"
                )
            resp.raise_for_status()
            payload: dict[str, Any] = resp.json()
            return payload

    try:
        data = await call_resilient(
            _fetch,
            timeout=cfg.OPENALEX_TIMEOUT_SECONDS,
            settings=cfg,
            retry_on=(httpx.HTTPError,),
        )
    except OpenAlexError:
        raise
    except Exception as exc:
        logger.error("openalex by_ids failed ids=%r err=%s", short_ids, exc)
        raise OpenAlexError(f"openalex by_ids failed: {exc}") from exc

    works = data.get("results") or []
    by_short = {w.get("id", "").rsplit("/", 1)[-1]: w for w in works}
    return [_to_preview(by_short[s]) for s in short_ids if s in by_short]


def _normalize_doi(doi: str) -> str:
    """DOI'yi bare forma indir: 'https://doi.org/10.x' / 'doi:10.x' → '10.x'."""
    d = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if d.lower().startswith(prefix):
            d = d[len(prefix):]
            break
    return d.lower()


async def _get_json(
    url: str,
    params: dict[str, str | int],
    cfg: Settings,
    *,
    op: str,
) -> dict[str, Any] | None:
    """Tek OpenAlex GET — rate-limit + resilience; 404 → None (yok, hata değil).

    F14-S2 reuse: tek-Work çözümü (DOI / W-id / arama) bu yardımcıyı kullanır;
    aynı sliding-window limiter + call_resilient + 4xx-no-retry sözleşmesi.
    """

    async def _fetch() -> dict[str, Any] | None:
        await _RATE_LIMITER.acquire()  # N-2/N-3 polite 10/sec
        async with httpx.AsyncClient(timeout=cfg.OPENALEX_TIMEOUT_SECONDS) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 404:
                return None
            # 4xx (429 hariç) → retry boşa; doğrudan hata.
            if 400 <= resp.status_code < 500 and resp.status_code != 429:
                raise OpenAlexError(
                    f"openalex client error {resp.status_code}: {resp.text[:200]}"
                )
            resp.raise_for_status()
            payload: dict[str, Any] = resp.json()
            return payload

    try:
        return await call_resilient(
            _fetch,
            timeout=cfg.OPENALEX_TIMEOUT_SECONDS,
            settings=cfg,
            retry_on=(httpx.HTTPError,),
        )
    except OpenAlexError:
        raise
    except Exception as exc:
        logger.error("openalex %s failed url=%s err=%s", op, url, exc)
        raise OpenAlexError(f"openalex {op} failed: {exc}") from exc


async def fetch_work_by_doi(
    doi: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any] | None:
    """DOI → ham OpenAlex Work nesnesi (yoksa None). HATA-YUTMA yok: 404=None, ağ hatası=raise."""
    cfg = settings or get_settings()
    if not cfg.OPENALEX_EMAIL:
        raise OpenAlexError("OPENALEX_EMAIL not configured (polite-pool gerekli)")
    bare = _normalize_doi(doi)
    url = f"{OPENALEX_BASE.rsplit('/', 1)[0]}/works/doi:{bare}"
    return await _get_json(url, _auth_params(cfg), cfg, op="work_by_doi")


async def fetch_work_by_id(
    work_id: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any] | None:
    """OpenAlex W-id → ham Work nesnesi (yoksa None)."""
    cfg = settings or get_settings()
    if not cfg.OPENALEX_EMAIL:
        raise OpenAlexError("OPENALEX_EMAIL not configured (polite-pool gerekli)")
    short = work_id.rsplit("/", 1)[-1]
    url = f"{OPENALEX_BASE.rsplit('/', 1)[0]}/works/{short}"
    return await _get_json(url, _auth_params(cfg), cfg, op="work_by_id")


async def search_works_raw(
    query: str,
    *,
    limit: int = 5,
    filters: list[str] | None = None,
    sort: str = "relevance_score:desc",
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Ham OpenAlex Work listesi (PaperPreview'e indirgemeden — fuzzy match + kapsama için).

    F14-S2: başlık+yazar+yıl fuzzy çözüm. F14-S3: yüksek-atıflı seminal keşfi.
    """
    cfg = settings or get_settings()
    if not cfg.OPENALEX_EMAIL:
        raise OpenAlexError("OPENALEX_EMAIL not configured (polite-pool gerekli)")
    params: dict[str, str | int] = {
        "search": query,
        "per-page": min(max(limit, 1), 25),
        "sort": sort,
        **_auth_params(cfg),
    }
    if filters:
        params["filter"] = ",".join(filters)
    data = await _get_json(OPENALEX_BASE, params, cfg, op="search_works_raw")
    if data is None:
        return []
    results: list[dict[str, Any]] = data.get("results") or []
    return results[:limit]


__all__ = [
    "OpenAlexError",
    "_abstract_from_inverted",
    "_normalize_doi",
    "fetch_papers_by_ids",
    "fetch_work_by_doi",
    "fetch_work_by_id",
    "search_papers",
    "search_works_raw",
]
