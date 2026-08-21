"""POST /api/enrich — F3d (OpenAlex polite pool, KD-32).

OpenAlex .edu.tr polite pool ile ghost paper abstract/metadata enrichment.
Redis 7d TTL cache; KD-32 Sercan handoff (async Celery task haline gelecek).
"""

from __future__ import annotations

import hashlib
import logging

import httpx
from fastapi import APIRouter, HTTPException

from api.config import get_settings
from api.db.redis_client import CacheNamespace, cache_get, cache_set
from api.models.enrich import EnrichRequest, EnrichResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["enrich"])

_OPENALEX_BASE = "https://api.openalex.org"


def _cache_key(paper_id: str) -> str:
    return hashlib.sha256(f"enrich:{paper_id}".encode()).hexdigest()[:32]


async def _fetch_openalex(paper_id: str) -> dict | None:
    """OpenAlex works endpoint — DOI veya OpenAlex ID ile sorgula."""
    settings = get_settings()
    email = settings.OPENALEX_EMAIL
    params: dict = {"mailto": email} if email else {}

    # paper_id DOI formatındaysa (10.xxx) veya OpenAlex W-id (W123...)
    if paper_id.startswith("10."):
        url = f"{_OPENALEX_BASE}/works/doi:{paper_id}"
    elif paper_id.startswith("W"):
        url = f"{_OPENALEX_BASE}/works/{paper_id}"
    else:
        url = f"{_OPENALEX_BASE}/works/doi:{paper_id}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("OpenAlex fetch failed paper_id=%s err=%s", paper_id, type(exc).__name__)
        return None


@router.post("/enrich", response_model=EnrichResponse)
async def enrich(req: EnrichRequest) -> EnrichResponse:
    """Ghost paper enrichment — OpenAlex polite pool; Redis 7d TTL."""
    key = _cache_key(req.paper_id)
    cached = cache_get(CacheNamespace.QUERY, key)
    if cached is not None:
        return EnrichResponse.model_validate(cached)

    oa_data = await _fetch_openalex(req.paper_id)
    if oa_data is None:
        raise HTTPException(status_code=404, detail=f"Paper not found in OpenAlex: {req.paper_id}")

    authors = ", ".join(
        a.get("author", {}).get("display_name", "") for a in oa_data.get("authorships", [])[:5]
    )
    host = oa_data.get("primary_location", {}) or {}
    source = host.get("source") or {}

    enriched: dict[str, str] = {}
    if title := oa_data.get("title"):
        enriched["title"] = title
    if abstract := oa_data.get("abstract"):
        enriched["abstract"] = abstract
    if authors:
        enriched["authors"] = authors
    if journal := source.get("display_name"):
        enriched["journal"] = journal
    if year := oa_data.get("publication_year"):
        enriched["year"] = str(year)
    if doi := oa_data.get("doi"):
        enriched["doi"] = doi
    if cited := oa_data.get("cited_by_count"):
        enriched["cited_by_count"] = str(cited)

    response = EnrichResponse(
        paper_id=req.paper_id,
        sources_hit=["openalex"],
        cache_hit=False,
        enriched_fields=enriched,
    )

    cache_set(CacheNamespace.QUERY, key, response.model_dump(mode="json"))
    return response
