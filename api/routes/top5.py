"""POST /api/top5 — F5 concrete (B-018 + Council 37f).

Real 5-layer pipeline — reuses DI factories from search.py.
Margin gate applied on raw reranker scores before curation.
needs_clarify flag triggers chat clarify branch.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.config import get_settings
from api.db.pinecone_client import PineconeQueryError
from api.db.redis_client import CacheNamespace, cache_get, cache_set
from api.db.supabase_client import SupabaseQueryError
from api.models.top5 import Top5Request, Top5Response
from api.routes.search import (
    _fetch_candidate_metadata,
    get_anchor,
    get_curator,
    get_listener,
    get_pool_router,
    get_reranker,
)
from api.services.anchor import Anchor
from api.services.curator import Curator
from api.services.listener import Listener
from api.services.pool_router import PoolRouter
from api.services.reranker import Reranker
from api.utils.resilience import ResilienceTimeoutError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["top5"])


def _cache_key(req: Top5Request) -> str:
    raw = f"top5:{req.session_id}:{req.query}:{req.margin}:{req.k}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


@router.post("/top5", response_model=Top5Response)
async def top5(
    req: Top5Request,
    listener: Annotated[Listener, Depends(get_listener)],
    anchor: Annotated[Anchor, Depends(get_anchor)],
    pool_router: Annotated[PoolRouter, Depends(get_pool_router)],
    reranker: Annotated[Reranker, Depends(get_reranker)],
    curator: Annotated[Curator, Depends(get_curator)],
) -> Top5Response:
    """Top-5 papers with margin gate — real 5-layer pipeline."""
    key = _cache_key(req)
    cached = cache_get(CacheNamespace.QUERY, key)
    if cached is not None:
        return Top5Response.model_validate(cached)

    settings = get_settings()
    try:
        sub_queries = await listener.listen(req.query, lang="auto")
        anchor_ids = await anchor.match(req.query, top_k=10)
        pool_results = await pool_router.fan_out(sub_queries, anchor_ids, top_k=50)
        candidate_ids = [pid for pid, _score in pool_results]
        candidate_meta = await _fetch_candidate_metadata(candidate_ids, settings.OPENALEX_EMAIL)
        candidate_texts = {pid: (m.get("title") or "") for pid, m in candidate_meta.items() if m.get("title")}
        scored = await reranker.rerank(candidate_ids, req.query, top_k=req.k * 3, candidate_texts=candidate_texts)
    except ResilienceTimeoutError as exc:
        logger.warning("top5 timeout query=%r", req.query)
        raise HTTPException(status_code=504, detail="Top5 timed out") from exc
    except (PineconeQueryError, SupabaseQueryError) as exc:
        logger.warning("top5 dependency failure: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="Top5 temporarily unavailable") from exc

    # Margin gate on raw reranker scores (before curator translates to PaperCard)
    above_margin = [(pid, s) for pid, s in scored if s >= req.margin]
    needs_clarify = len(above_margin) == 0
    scored_for_curate = (above_margin if not needs_clarify else scored)[: req.k]

    try:
        curated = await curator.curate(
            scored_for_curate, req.query, user_lang="tr", candidate_meta=candidate_meta
        )
    except ResilienceTimeoutError as exc:
        logger.warning("top5 curator timeout query=%r", req.query)
        raise HTTPException(status_code=504, detail="Curator timed out") from exc

    response = Top5Response(
        papers=curated["papers"][: req.k],
        needs_clarify=needs_clarify,
        margin_used=req.margin,
    )

    cache_set(CacheNamespace.QUERY, key, response.model_dump(mode="json"))
    return response
