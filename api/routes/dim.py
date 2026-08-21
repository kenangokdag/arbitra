"""GET /api/dim/* — onboarding alan/subalan dropdown taksonomisi (F5-PRE).

Plan: PROMPT #4-PRE brief §1.A
- GET /api/dim/fields                       → DimFieldListResponse (alfabetik, cache 1h)
- GET /api/dim/subfields?field_ids=a,b,c    → DimSubfieldListResponse (parent filtre, max 3)

Brain: K-007 (taxonomy), K-010/K-011 (DB EN-only), K-019 (~26), K-019 ext (~252).
DM_RULES: R4 (zero-hallucination), R10 (RLS) — backend admin client (RLS bypass) ile read.

Auth: middleware (anon + authenticated); no per-endpoint auth (read-only public).
Hata: SupabaseQueryError → 503 (mevcut pattern: gap_profile, paper_detail).
Cache: HTTP `Cache-Control: public, max-age=3600, stale-while-revalidate=300` —
       Redis layer post-MVP (brief §2: erken optimizasyon).

Dev/test fallback: SUPABASE yoksa boş liste döner (onboarding pattern paraleli).
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, Response
from supabase import Client

from api.models.dim import (
    DimField,
    DimFieldListResponse,
    DimSubfield,
    DimSubfieldListResponse,
)

router = APIRouter(prefix="/api/dim", tags=["dim"])

_CACHE_HEADER = "public, max-age=3600, stale-while-revalidate=300"
_MAX_FIELD_IDS = 3


def _supabase() -> Client | None:
    from api.config import get_settings

    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SECRET_KEY:
        return None
    from api.db.supabase_client import get_supabase_admin

    return get_supabase_admin()


@router.get("/fields", response_model=DimFieldListResponse)
async def list_fields(response: Response) -> DimFieldListResponse:
    response.headers["Cache-Control"] = _CACHE_HEADER
    db = _supabase()
    if db is None:
        return DimFieldListResponse(fields=[])

    from api.db.supabase_client import SupabaseQueryError, supabase_call_async

    try:
        result = await supabase_call_async(
            lambda: db.table("dim_field")
            .select("field_id, name_en, slug, paper_count_total")
            .order("name_en")
            .execute()
        )
    except SupabaseQueryError as exc:
        raise HTTPException(
            status_code=503, detail={"error": "dim_field_query_failed"}
        ) from exc

    rows = cast(list[dict[str, Any]], result.data or [])
    return DimFieldListResponse(fields=[DimField(**r) for r in rows])


@router.get("/subfields", response_model=DimSubfieldListResponse)
async def list_subfields(
    response: Response,
    field_ids: str = Query(
        ...,
        description=f"virgülle ayrı parent field_id'ler, max {_MAX_FIELD_IDS}",
    ),
) -> DimSubfieldListResponse:
    response.headers["Cache-Control"] = _CACHE_HEADER

    parsed = [fid.strip() for fid in field_ids.split(",") if fid.strip()]
    if not parsed:
        raise HTTPException(
            status_code=422, detail={"error": "empty_field_ids"}
        )
    if len(parsed) > _MAX_FIELD_IDS:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "too_many_field_ids",
                "max": _MAX_FIELD_IDS,
                "got": len(parsed),
            },
        )

    db = _supabase()
    if db is None:
        return DimSubfieldListResponse(subfields=[])

    from api.db.supabase_client import SupabaseQueryError, supabase_call_async

    try:
        result = await supabase_call_async(
            lambda: db.table("dim_subfield")
            .select("subfield_id, field_id, name_en, slug, paper_count_total")
            .in_("field_id", parsed)
            .order("name_en")
            .execute()
        )
    except SupabaseQueryError as exc:
        raise HTTPException(
            status_code=503, detail={"error": "dim_subfield_query_failed"}
        ) from exc

    rows = cast(list[dict[str, Any]], result.data or [])
    return DimSubfieldListResponse(subfields=[DimSubfield(**r) for r in rows])
