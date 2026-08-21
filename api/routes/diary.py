"""F13-S1-P003 /api/diary/* — Araştırma Defteri zaman çizgisi.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S1-P003)
Sayfa: Page_Design/Sayfa_Plani_v2/S1_arastirma_defteri.rtf §Backend (satır 70-83)

Endpoints:
- POST   /api/diary/event           (3 sayfa-içi buton tek endpoint'e gider)
- GET    /api/diary/timeline        (cursor-based, 50/sayfa)
- PATCH  /api/diary/event/{id}      (Düzenle / Resolve / Geri aç)

Auth: AuthMiddleware request.state.user_id zorunlu.
Service role + Python-level user_id filter (project.py:20-22 zırh patterni).
SUPABASE config yok → 503 (notes in-memory fallback'i diary için anlamlı değil;
veri kaybı kullanıcı için sayfa felsefesini bozar).
"""

from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from api.models.diary import (
    DiaryEvent,
    DiaryEventCreate,
    DiaryEventPatch,
    DiaryPreAdvisorRequest,
    DiaryPreAdvisorResponse,
    DiaryTimelineResponse,
)
from api.services import diary_service
from api.services.llm_service import LLMServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["diary"])


def _user_id(request: Request) -> UUID:
    """request.state.user_id → UUID. Eksik/geçersizse 401."""
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="missing_user_id")
    try:
        return UUID(cast(str, uid))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="invalid_user_id") from exc


def _ensure_supabase() -> None:
    """SUPABASE config yoksa 503 — diary için fallback yok."""
    from api.config import get_settings

    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SECRET_KEY:
        raise HTTPException(
            status_code=503, detail="supabase_unavailable_diary_disabled"
        )


@router.post(
    "/diary/event",
    response_model=DiaryEvent,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(req: DiaryEventCreate, request: Request) -> DiaryEvent:
    """3 sayfa-içi buton (Ajandama Kaydet / Danışmana Sor / Kütüphaneme Ekle)
    + serbest not bu tek endpoint'i çağırır (event_type ile ayrışır).
    """
    user_id = _user_id(request)
    _ensure_supabase()
    return await diary_service.insert_event(user_id, req)


@router.get("/diary/timeline", response_model=DiaryTimelineResponse)
async def get_timeline(
    request: Request,
    project_id: UUID | None = None,
    page_slug: str | None = None,
    paper_id: str | None = None,
    cursor: str | None = None,
) -> DiaryTimelineResponse:
    """Zaman çizgisi: cursor (ISO created_at) ile pagination, 50/sayfa."""
    user_id = _user_id(request)
    _ensure_supabase()
    return await diary_service.list_timeline(
        user_id,
        project_id=project_id,
        page_slug=page_slug,
        paper_id=paper_id,
        cursor=cursor,
    )


@router.patch("/diary/event/{event_id}", response_model=DiaryEvent)
async def patch_event(
    event_id: UUID, req: DiaryEventPatch, request: Request
) -> DiaryEvent:
    """Düzenle (payload), Resolve (resolved_at=now), Geri aç (resolved_at=None)."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await diary_service.patch_event(user_id, event_id, req)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="event_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/diary/pre-advisor-summary",
    response_model=DiaryPreAdvisorResponse,
)
async def pre_advisor_summary(
    req: DiaryPreAdvisorRequest, request: Request
) -> DiaryPreAdvisorResponse:
    """Sayfa_Plani_v2/S1 §4 — danışmana gitmeden son 30 gün özeti (Gemini Flash).
    LLM hatası → 503 (defter sayfası degrade fallback'i yok)."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await diary_service.summarize_pre_advisor(user_id, req.project_id)
    except LLMServiceError as exc:
        logger.exception("diary pre-advisor LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc
