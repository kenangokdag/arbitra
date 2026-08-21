"""V1-S17 P003 — GET /api/project/{id}/concept-network (RC4 derive katmanı).

Plan: docs/plans/V1_S17_cascade_5rc.md §2 P003 + §3 KD-V1-S17-03.

Pipeline: project_cluster.paper_id × papers.abstract → TF-IDF top-20 ngram(1,2)
TR+EN stopword → co-citation cosine ≥ 0.15 → ConceptNetworkResponse.

Pre-condition: project_anchor.cluster_status='ready'; aksi halde 409 cluster_not_ready.
Ownership: projects.user_id manuel filter (K-031 zırh; RLS bypass admin client).
"""

from __future__ import annotations

import logging
from typing import cast

from fastapi import APIRouter, HTTPException, Request, status
from supabase import Client

from api.services import concept_graph
from api.services.concept_graph import ConceptNetworkResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/project", tags=["concept-network"])


def _supabase() -> Client | None:
    from api.config import get_settings

    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SECRET_KEY:
        return None
    from api.db.supabase_client import get_supabase_admin

    return get_supabase_admin()


def _user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="missing_user_id")
    return cast(str, uid)


@router.get(
    "/{project_id}/concept-network",
    response_model=ConceptNetworkResponse,
    status_code=status.HTTP_200_OK,
)
async def get_concept_network(
    project_id: str, request: Request
) -> ConceptNetworkResponse:
    """V1-S17 P003 — ConceptNetwork derive endpoint.

    404 project_not_found: ownership reddi (RLS bypass + manuel filter).
    409 cluster_not_ready: cluster_status != 'ready' veya project_cluster boş.
    """
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        raise HTTPException(status_code=503, detail="supabase_unavailable")

    from api.db.supabase_client import supabase_call_async

    own_resp = await supabase_call_async(
        lambda: db.table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not (own_resp.data or []):
        raise HTTPException(status_code=404, detail="project_not_found")

    try:
        return await concept_graph.run(db=db, project_id=project_id)
    except concept_graph.ClusterNotReadyError as exc:
        raise HTTPException(
            status_code=409, detail=f"cluster_not_ready: {exc}"
        ) from exc
