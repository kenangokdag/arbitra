"""POST /api/search — F3a §3 P010 atomic.

5-katman pipeline orchestration:
  Listener → Anchor → PoolRouter → Reranker → Curator
+ Redis cache (q: 1h TTL) + faithfulness_meta + decision_band + latency_ms.

P010: mock concrete impl injected (api.services._mocks); P004-P008 gelince DI swap.
P013 (2026-05-01): outer try/except + 503/504 mapping (ResilienceTimeoutError →
                   504, Pinecone/SupabaseQueryError → 503); diğer hatalar 500.
"""

import hashlib
import logging
import time
from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException

from api.config import get_settings
from api.db.pinecone_client import PineconeQueryError
from api.db.redis_client import CacheNamespace, cache_get, cache_set
from api.db.supabase_client import SupabaseQueryError
from api.models.search import SearchRequest, SearchResponse
from api.services._mocks import (
    MockAnchor,
    MockListener,
    MockPoolRouter,
    MockReranker,
)
from api.services.anchor import Anchor, OpenAlexAnchor
from api.services.curator import Curator, OutlinesCurator
from api.services.listener import GeminiListener, Listener
from api.services.pool_router import HybridPoolRouter, PoolRouter
from api.services.reranker import BgeReranker, Reranker
from api.utils.resilience import ResilienceTimeoutError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])


# Dependency factory — P004-P008 gerçek impl'ler gelince burada swap edilir.
#
# A.6/N-8: @lru_cache(maxsize=1) ile process-singleton. BgeReranker (350+ MB) +
# HybridPoolRouter (Pinecone client + _QueryEncoder) per-request instantiate
# edilirse cold-start 30+ sn ve memory bloat. Tests `app.dependency_overrides`
# kullanıyor → @lru_cache testlerle uyumlu (factory hiç çağrılmaz).


@lru_cache(maxsize=1)
def get_listener() -> Listener:
    """F8 DM-LLM-10: GEMINI_API_KEY doluysa GeminiListener; aksi MockListener (test/dev)."""
    settings = get_settings()
    if settings.GEMINI_API_KEY:
        return GeminiListener()
    return MockListener()


@lru_cache(maxsize=1)
def get_anchor() -> Anchor:
    """OpenAlexAnchor when OPENALEX_EMAIL set; MockAnchor fallback."""
    settings = get_settings()
    if settings.OPENALEX_EMAIL:
        return OpenAlexAnchor(email=settings.OPENALEX_EMAIL)
    return MockAnchor()


_OPENALEX_SELECT = (
    "id,title,abstract_inverted_index,authorships,publication_year,doi,"
    "primary_location,cited_by_count,open_access,language,referenced_works_count"
)


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """OpenAlex abstract_inverted_index → plain text. None/empty → None."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        if isinstance(idxs, list):
            for i in idxs:
                if isinstance(i, int):
                    positions.append((i, word))
    if not positions:
        return None
    positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in positions)


def _project_work(work: dict) -> dict:
    """OpenAlex work dict → curator-shaped meta."""
    authorships = work.get("authorships") or []
    authors: list[str] = []
    for a in authorships:
        if not isinstance(a, dict):
            continue
        author_obj = a.get("author") or {}
        name = author_obj.get("display_name") if isinstance(author_obj, dict) else None
        if isinstance(name, str) and name:
            authors.append(name)
    primary = work.get("primary_location") or {}
    source = primary.get("source") if isinstance(primary, dict) else None
    venue = source.get("display_name") if isinstance(source, dict) else None
    oa = work.get("open_access") or {}
    is_oa = oa.get("is_oa") if isinstance(oa, dict) else None
    return {
        "title": work.get("title"),
        "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
        "authors": authors,
        "venue": venue,
        "year": work.get("publication_year"),
        "doi": work.get("doi"),
        "cited_by_count": work.get("cited_by_count"),
        "language": work.get("language"),
        "is_oa": is_oa,
        "url": primary.get("landing_page_url") if isinstance(primary, dict) else None,
    }


async def _fetch_candidate_metadata(
    paper_ids: list[str], email: str | None
) -> dict[str, dict]:
    """OpenAlex batch full-metadata fetch.

    Returns {paper_id: {title, abstract, authors, venue, year, doi,
                        cited_by_count, language, is_oa, url}}.
    Hata olursa boş dict döner — curator placeholder fallback'e düşer.
    """
    w_ids = [pid for pid in paper_ids if pid.startswith("W")]
    if not w_ids:
        return {}
    ids_filter = "|".join(w_ids[:50])
    url = "https://api.openalex.org/works"
    params: dict = {
        "filter": f"ids.openalex:{ids_filter}",
        "select": _OPENALEX_SELECT,
        "per-page": 50,
    }
    if email:
        params["mailto"] = email
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        result: dict[str, dict] = {}
        for work in data.get("results", []):
            wid = (work.get("id") or "").split("/")[-1]
            if wid:
                result[wid] = _project_work(work)
        return result
    except Exception as exc:
        logger.warning("candidate_metadata fetch failed: %s", exc)
        return {}


async def _fetch_candidate_texts(paper_ids: list[str], email: str | None) -> dict[str, str]:
    """Title-only projection over _fetch_candidate_metadata (reranker contract)."""
    meta = await _fetch_candidate_metadata(paper_ids, email)
    return {pid: (m.get("title") or "") for pid, m in meta.items() if m.get("title")}


@lru_cache(maxsize=1)
def get_pool_router() -> PoolRouter:
    """B-012 sonrasi: HybridPoolRouter concrete (Pinecone mdv1 + theme pgvector)."""
    settings = get_settings()
    if settings.PINECONE_API_KEY:
        return HybridPoolRouter(settings=settings)
    return MockPoolRouter()


@lru_cache(maxsize=1)
def get_reranker() -> Reranker:
    """BgeReranker when OPENALEX_EMAIL set (candidate_texts available); MockReranker fallback."""
    settings = get_settings()
    if settings.OPENALEX_EMAIL:
        return BgeReranker(settings=settings)
    return MockReranker()


@lru_cache(maxsize=1)
def get_curator() -> Curator:
    """B-018: OutlinesCurator iskelet aktif (Pinecone hariç parçalar concrete)."""
    return OutlinesCurator()


def _cache_key(req: SearchRequest) -> str:
    """Deterministic SHA-256 hash from canonical request JSON."""
    payload = req.model_dump_json()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


@router.post("/search", response_model=SearchResponse)
async def search(
    req: SearchRequest,
    listener: Annotated[Listener, Depends(get_listener)],
    anchor: Annotated[Anchor, Depends(get_anchor)],
    pool_router: Annotated[PoolRouter, Depends(get_pool_router)],
    reranker: Annotated[Reranker, Depends(get_reranker)],
    curator: Annotated[Curator, Depends(get_curator)],
) -> SearchResponse:
    """5-katman pipeline + Redis cache + faithfulness gate (mock P010)."""
    started = time.monotonic()

    cache_key = _cache_key(req)
    cached = cache_get(CacheNamespace.QUERY, cache_key)
    if cached is not None:
        cached_response = SearchResponse.model_validate(cached)
        return cached_response.model_copy(
            update={"latency_ms": int((time.monotonic() - started) * 1000)}
        )

    settings = get_settings()
    user_lang = req.language_hint.value if req.language_hint else "en"
    try:
        sub_queries = await listener.listen(req.query, lang=user_lang)
        anchor_ids = await anchor.match(req.query, top_k=10)
        pool_results = await pool_router.fan_out(sub_queries, anchor_ids, top_k=50)
        candidate_ids = [pid for pid, _score in pool_results]
        candidate_meta = await _fetch_candidate_metadata(candidate_ids, settings.OPENALEX_EMAIL)
        candidate_texts = {pid: (m.get("title") or "") for pid, m in candidate_meta.items() if m.get("title")}
        scored = await reranker.rerank(candidate_ids, req.query, top_k=req.k, candidate_texts=candidate_texts)
        curated = await curator.curate(scored, req.query, user_lang=user_lang, candidate_meta=candidate_meta)
    except ResilienceTimeoutError as exc:
        logger.warning("search timeout query=%r error=%s", req.query, exc)
        raise HTTPException(
            status_code=504,
            detail="Search timed out — upstream service slow",
        ) from exc
    except (PineconeQueryError, SupabaseQueryError) as exc:
        logger.warning(
            "search dependency failure query=%r error=%s",
            req.query,
            exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Search temporarily unavailable — retry shortly",
        ) from exc

    elapsed_ms = int((time.monotonic() - started) * 1000)
    response = SearchResponse(
        papers=curated["papers"],
        faithfulness_meta=curated["faithfulness_meta"],
        decision_band=curated["decision_band"],
        gate_warnings=curated["gate_warnings"],
        latency_ms=elapsed_ms,
        pmid_match_score=curated["pmid_match_score"],
    )

    cache_set(CacheNamespace.QUERY, cache_key, response.model_dump(mode="json"))
    return response
