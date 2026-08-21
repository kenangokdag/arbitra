"""GET /api/connected-papers/{paper_id} — fact_paper_bibcoupling_top50 (B42-030).

Top-50 bibliographic coupling neighbors; titles enriched via OpenAlex batch.
Redis 1h cache per paper.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.config import get_settings
from api.db.redis_client import CacheNamespace, cache_get, cache_set
from api.db.supabase_client import SupabaseQueryError, get_supabase_admin, supabase_call_async
from api.utils.resilience import ResilienceTimeoutError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["connected-papers"])

_CACHE_TTL = 3600


class ConnectedPaper(BaseModel):
    paper_id: str
    title: str
    cosine_score: float
    raw_count: int
    rank: int


class ConnectedPapersResponse(BaseModel):
    source_paper_id: str
    neighbors: list[ConnectedPaper]
    total: int


def _fetch_neighbors(paper_id: str, top_k: int) -> list[dict]:
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_bibcoupling_top50")
        .select("neighbor_id,cosine_score,raw_count,rank")
        .eq("paper_id", paper_id)
        .order("rank")
        .limit(top_k)
        .execute()
    )
    return resp.data or []


async def _fetch_titles(w_ids: list[str], email: str | None) -> dict[str, str]:
    """OpenAlex batch title fetch for neighbor_ids."""
    if not w_ids:
        return {}
    ids_filter = "|".join(w_ids[:50])
    url = f"https://api.openalex.org/works?filter=ids.openalex:{ids_filter}&select=id,title&per-page=50"
    params: dict = {"mailto": email} if email else {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        result: dict[str, str] = {}
        for work in data.get("results", []):
            wid = work.get("id", "").split("/")[-1]
            title = work.get("title") or ""
            if wid and title:
                result[wid] = title
        return result
    except Exception as exc:
        logger.warning("OpenAlex title fetch for connected-papers failed: %s", exc)
        return {}


@router.get("/connected-papers/{paper_id}", response_model=ConnectedPapersResponse)
async def connected_papers(
    paper_id: str,
    top_k: int = Query(default=20, ge=1, le=50),
) -> ConnectedPapersResponse:
    """Bibliographic coupling neighbors for a given paper."""
    cache_key = f"connpap:{paper_id}:{top_k}"
    cached = cache_get(CacheNamespace.QUERY, cache_key)
    if cached is not None:
        return ConnectedPapersResponse.model_validate(cached)

    try:
        raw = await supabase_call_async(
            lambda: _fetch_neighbors(paper_id, top_k),
            timeout=15.0,
        )
    except (ResilienceTimeoutError, SupabaseQueryError) as exc:
        logger.warning("connected_papers fetch failed paper_id=%s: %s", paper_id, exc)
        raise HTTPException(status_code=503, detail="Connected papers temporarily unavailable")

    if not raw:
        raise HTTPException(status_code=404, detail=f"No neighbors found for paper_id={paper_id}")

    neighbor_ids = [r["neighbor_id"] for r in raw]
    settings = get_settings()
    titles = await _fetch_titles(neighbor_ids, settings.OPENALEX_EMAIL)

    neighbors = [
        ConnectedPaper(
            paper_id=r["neighbor_id"],
            title=titles.get(r["neighbor_id"]) or r["neighbor_id"],
            cosine_score=float(r.get("cosine_score") or 0),
            raw_count=int(r.get("raw_count") or 0),
            rank=int(r.get("rank") or 0),
        )
        for r in raw
    ]

    response = ConnectedPapersResponse(
        source_paper_id=paper_id,
        neighbors=neighbors,
        total=len(neighbors),
    )
    cache_set(CacheNamespace.QUERY, cache_key, response.model_dump(mode="json"), ttl=_CACHE_TTL)
    return response
