"""GET /api/gap-profile — single M1 cell detail + theme year trend.

Returns gap_value components + year trend for a method×topic pair.
Redis 1h cache.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.db.redis_client import CacheNamespace, cache_get, cache_set
from api.db.supabase_client import SupabaseQueryError, get_supabase_admin, supabase_call_async
from api.utils.resilience import ResilienceTimeoutError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["gap-profile"])

_CACHE_TTL = 3600


class GapSegment(BaseModel):
    label: str
    value: float          # [0, 1]
    description: str


class TrendPoint(BaseModel):
    year: int
    paper_count: int
    c_k: float | None


class GapProfileResponse(BaseModel):
    method_id: str
    topic_id: str
    topic_label: str
    gap_value: float
    depth_norm: float
    neighbor: float
    e_value: float
    feasibility: float
    publishability: float
    segments: list[GapSegment]
    trend: list[TrendPoint]


def _fetch_gap_cell(method_id: str, topic_id: str) -> dict | None:
    client = get_supabase_admin()
    resp = (
        client.table("fact_gap_matrix")
        .select("axis_x,axis_y,depth_norm,neighbor,e_value,feasibility,publishability,gap_value")
        .eq("matrix_id", "M1")
        .eq("axis_x", topic_id)
        .eq("axis_y", method_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def _fetch_theme_trend(topic_id: str) -> list[dict]:
    client = get_supabase_admin()
    resp = (
        client.table("fact_theme_year_aggregates")
        .select("year,paper_count,c_k")
        .eq("theme_id", topic_id)
        .order("year")
        .execute()
    )
    return resp.data or []


def _fetch_theme_label(topic_id: str) -> str:
    client = get_supabase_admin()
    resp = (
        client.table("dim_theme")
        .select("name_tr")
        .eq("theme_id", topic_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0].get("name_tr", topic_id) if rows else topic_id


@router.get("/gap-profile", response_model=GapProfileResponse)
async def gap_profile(
    method_id: str = Query(...),
    topic_id: str = Query(...),
) -> GapProfileResponse:
    """Detailed gap profile for a method × topic cell."""
    ck = f"gap-profile:{method_id}:{topic_id}"
    cached = cache_get(CacheNamespace.QUERY, ck)
    if cached is not None:
        return GapProfileResponse.model_validate(cached)

    try:
        cell, trend_raw, topic_label = await _parallel_fetch(method_id, topic_id)
    except (ResilienceTimeoutError, SupabaseQueryError) as exc:
        logger.warning("gap_profile fetch failed %s×%s: %s", method_id, topic_id, exc)
        raise HTTPException(status_code=503, detail="Gap profile temporarily unavailable")

    if cell is None:
        raise HTTPException(status_code=404, detail=f"No gap cell found for {method_id}×{topic_id}")

    gv = float(cell.get("gap_value") or 0)
    dn = float(cell.get("depth_norm") or 0)
    nb = float(cell.get("neighbor") or 0)
    ev = float(cell.get("e_value") or 0)
    fe = float(cell.get("feasibility") or 0.5)
    pb = float(cell.get("publishability") or 0)

    segments = [
        GapSegment(label="Gap Degeri", value=gv, description="Genel bosluk skoru (0=doygun, 1=tam bosluk)"),
        GapSegment(label="Kapsam Derinligi", value=1 - dn, description="Dusuk kapsam → yuksek gap firsat"),
        GapSegment(label="Komsu Sinyal", value=nb, description="Yakin hucrelerin ortalama sinyal gucu"),
        GapSegment(label="ESTRA E", value=min(1.0, abs(ev)), description="d-ESTRA etki skoru"),
        GapSegment(label="Uygulanabilirlik", value=fe, description="Arastirma uygulama potansiyeli"),
        GapSegment(label="Yayinlanabilirlik", value=pb, description="Tahmini yayin potansiyeli"),
    ]

    trend = [
        TrendPoint(
            year=int(r.get("year") or 0),
            paper_count=int(r.get("paper_count") or 0),
            c_k=float(r["c_k"]) if r.get("c_k") is not None else None,
        )
        for r in trend_raw
    ]

    response = GapProfileResponse(
        method_id=method_id,
        topic_id=topic_id,
        topic_label=topic_label,
        gap_value=round(gv, 4),
        depth_norm=round(dn, 4),
        neighbor=round(nb, 4),
        e_value=round(ev, 4),
        feasibility=round(fe, 4),
        publishability=round(pb, 4),
        segments=segments,
        trend=trend,
    )

    cache_set(CacheNamespace.QUERY, ck, response.model_dump(mode="json"), ttl=_CACHE_TTL)
    return response


async def _parallel_fetch(method_id: str, topic_id: str):
    import asyncio

    cell_task = supabase_call_async(lambda: _fetch_gap_cell(method_id, topic_id), timeout=12.0)
    trend_task = supabase_call_async(lambda: _fetch_theme_trend(topic_id), timeout=10.0)
    label_task = supabase_call_async(lambda: _fetch_theme_label(topic_id), timeout=8.0)

    cell, trend, label = await asyncio.gather(cell_task, trend_task, label_task, return_exceptions=False)
    return cell, trend, label
