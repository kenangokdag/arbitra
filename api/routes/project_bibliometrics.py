"""V1-S14 P005 — POST /api/project/{project_id}/bibliometrics.

Plan: docs/plans/V1_S14_mock_to_live.md §3 P005 (REVİZE 2026-05-10, B-029).
V1-S17 P004 REVİZE 2026-05-26: paper_id kaynak zinciri
  req.paper_ids → project_cluster (V1-S17 Stage C çıktısı) → project_seed_papers (V1-S14 legacy)
  Cluster fallback `cluster_status='ready'` proje için anlamlı zenginleştirme.

Auth: AuthMiddleware request.state.user_id; dev fallback bibliometric için
kritik değil (read-only aggregate, RLS warehouse 'authenticated' read_all).
SUPABASE config yoksa boş summary döner.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from supabase import Client

from api.db.supabase_client import supabase_call_async
from api.models.bibliometric import (
    BibliometricConfidence,
    BibliometricRequest,
    BibliometricSummary,
)
from api.services.bibliometric_service import compute_bibliometric_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["bibliometric"])


def _empty_summary(total: int = 0) -> BibliometricSummary:
    return BibliometricSummary(
        total_papers=total,
        median_year=None,
        mean_citations=0.0,
        most_cited=None,
        publications_by_year=[],
        language_dist=[],
        top_areas=[],
        top_methods=[],
        confidence=BibliometricConfidence(
            card_metrics="C",
            beauty_metrics="C",
            top_areas="C",
            top_methods="C",
        ),
    )


async def _fetch_seed_paper_ids(db: Client, project_id: str) -> list[str]:
    """project.py:344 pattern — admin client ile project_seed_papers query."""

    def _q() -> Any:
        return (
            db.table("project_seed_papers")
            .select("paper_id")
            .eq("project_id", project_id)
            .execute()
        )

    try:
        resp = await supabase_call_async(_q)
        rows = cast(list[dict[str, Any]], resp.data or [])
        return [r["paper_id"] for r in rows if isinstance(r.get("paper_id"), str)]
    except Exception as exc:
        logger.warning("project_seed_papers lookup failed: %s", exc)
        return []


async def _fetch_cluster_paper_ids(db: Client, project_id: str) -> list[str]:
    """V1-S17 P004 — project_cluster (Stage C çıktısı) paper_ids.

    Cluster_expander populated table; rank_final ASC sıra korunur.
    """

    def _q() -> Any:
        return (
            db.table("project_cluster")
            .select("paper_id,rank_final")
            .eq("project_id", project_id)
            .execute()
        )

    try:
        resp = await supabase_call_async(_q)
        rows = cast(list[dict[str, Any]], resp.data or [])
        rows.sort(key=lambda r: r.get("rank_final") or 10_000)
        return [r["paper_id"] for r in rows if isinstance(r.get("paper_id"), str)]
    except Exception as exc:
        logger.warning("project_cluster lookup failed: %s", exc)
        return []


@router.post(
    "/project/{project_id}/bibliometrics",
    response_model=BibliometricSummary,
)
async def project_bibliometrics(
    project_id: str, req: BibliometricRequest
) -> BibliometricSummary:
    from api.config import get_settings

    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        logger.warning("bibliometrics: SUPABASE config yok, boş summary")
        return _empty_summary(len(req.paper_ids))

    from api.db.supabase_client import get_supabase_admin

    try:
        db = get_supabase_admin()
        paper_ids = req.paper_ids
        if not paper_ids:
            paper_ids = await _fetch_cluster_paper_ids(db, project_id)
        if not paper_ids:
            paper_ids = await _fetch_seed_paper_ids(db, project_id)
        if not paper_ids:
            return _empty_summary()
        return await compute_bibliometric_summary(db, paper_ids)
    except Exception as exc:
        logger.exception("bibliometrics aggregate failed")
        raise HTTPException(status_code=502, detail="bibliometrics_failed") from exc
