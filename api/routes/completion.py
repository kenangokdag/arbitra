"""F13-S13 /api/completion/* + /api/feedback/* — Proje Tamamlama.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S13
Sayfa: Page_Design/Sayfa_Plani_v2/S2_proje_tamamlama.rtf

Endpoints:
- POST /api/completion/snapshot         (proje kapanış snapshot + LLM yorum)
- POST /api/feedback/project-completion (5-soru kullanıcı geri-bildirimi)

Auth: AuthMiddleware request.state.user_id zorunlu.
Service role + projects.user_id JOIN sahiplik (project.py:20-22 zırh patterni).
"""

from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from api.models.completion import (
    FeedbackRequest,
    FeedbackResponse,
    SnapshotRequest,
    SnapshotResponse,
)
from api.services import completion_service
from api.services.llm_service import LLMServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["completion"])


def _user_id(request: Request) -> UUID:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="missing_user_id")
    try:
        return UUID(cast(str, uid))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="invalid_user_id") from exc


def _ensure_supabase() -> None:
    from api.config import get_settings

    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SECRET_KEY:
        raise HTTPException(
            status_code=503, detail="supabase_unavailable_completion_disabled"
        )


@router.post("/completion/snapshot", response_model=SnapshotResponse)
async def completion_snapshot(
    req: SnapshotRequest, request: Request
) -> SnapshotResponse:
    """S2 — proje kapanışı: sinyal topla + rozet + LLM tek paragraf yorum.

    LLM hatası → 503 (snapshot LLM yorumu olmadan anlamlı değil).
    """
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await completion_service.create_snapshot(user_id, req.project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("completion snapshot LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.post("/feedback/project-completion", response_model=FeedbackResponse)
async def feedback_project_completion(
    req: FeedbackRequest, request: Request
) -> FeedbackResponse:
    """S2 — 5-soru kullanıcı geri-bildirimi (topic, process, missing, satisfaction, NPS).

    Snapshot yoksa 404 — kullanıcı önce /api/completion/snapshot çağırmalı.
    """
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await completion_service.record_feedback(
            user_id, req.project_id, req.feedback
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
