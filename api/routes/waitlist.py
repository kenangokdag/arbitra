"""V1-S4 waitlist endpoint — POST /api/waitlist (Scope A — Minimal).

kaynak: docs/plans/V1_S4_waitlist_capture.md §1 (kontrat)
HK-1: Pydantic forbid (api/models/waitlist.py)
HK-2: kontrat referansı bu docstring + plan §1
HK-3: dış API yok (Supabase insert sync→thread offload)

Akış:
  AuthMiddleware PUBLIC_PATHS bypass → RateLimitMiddleware (60/min/IP global)
  → honeypot guard (silent 200) → email lower-case normalize
  → Supabase insert (UNIQUE violation → 409)
  → 200 + queued_at ISO
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from supabase import Client

from api.db.supabase_client import (
    SupabaseQueryError,
    get_supabase_admin,
    supabase_call_async,
)
from api.models.waitlist import WaitlistRequest, WaitlistResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["waitlist"])


def _supabase() -> Client | None:
    """Service-role Supabase client; URL/key yoksa None (dev/test bypass)."""
    from api.config import get_settings

    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SECRET_KEY:
        return None
    return get_supabase_admin()


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _is_unique_violation(exc: BaseException) -> bool:
    """Postgres UNIQUE violation tespiti (Supabase exception cause zincirinden)."""
    msg = str(exc).lower()
    cause_msg = str(exc.__cause__).lower() if exc.__cause__ else ""
    return any(
        sig in (msg + cause_msg)
        for sig in ("duplicate key", "unique constraint", "23505", "already exists")
    )


@router.post("/waitlist", response_model=WaitlistResponse)
async def waitlist(req: WaitlistRequest, request: Request) -> WaitlistResponse:
    """Landing waitlist capture — anon-only, no auth."""
    # Honeypot: bot doldurmuş → silent fake-200 (bot'a sinyal verme)
    if req.website:
        logger.info("waitlist honeypot tripped ip=%s", _client_ip(request))
        return WaitlistResponse(ok=True, queued_at=_now_iso())

    email = req.email.lower()
    db = _supabase()
    if db is None:
        # Dev/test fallback — Supabase yok, insert atla (V1 prototip)
        logger.warning("waitlist: SUPABASE_URL not set, dev fallback (no insert)")
        return WaitlistResponse(ok=True, queued_at=_now_iso())

    payload: dict[str, Any] = {
        "email": email,
        "name": req.name,
        "source": req.source.value,
        "ip": _client_ip(request),
        "user_agent": request.headers.get("user-agent"),
    }

    try:
        await supabase_call_async(
            lambda: db.table("waitlist").insert(payload).execute()
        )
    except SupabaseQueryError as exc:
        if _is_unique_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "already_queued"},
            ) from exc
        logger.error("waitlist insert failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "waitlist_unavailable"},
        ) from exc

    return WaitlistResponse(ok=True, queued_at=_now_iso())


__all__ = ["router"]
