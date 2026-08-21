"""POST/GET/PATCH/DELETE /api/reading-list — Supabase persist (2026-05-26 Madde 1).

Tablo: public.user_reading_list (0001_init_schema_v1.sql:247)
RLS  : auth.uid() = user_id — backend admin client kullanır, Python-level filter.
papers FK: ensure_paper_row() OpenAlex meta upsert (corpus paper_kind trigger için).
"""

from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from api.models.reading_list import (
    ReadingListAddRequest,
    ReadingListItem,
    ReadingListResponse,
    ReadingListUpdateRequest,
)
from api.services import reading_list_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["reading-list"])


def _user_id(request: Request) -> UUID:
    """request.state.user_id → UUID. Eksik/geçersizse 401/400."""
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="missing_user_id")
    try:
        return UUID(cast(str, uid))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="invalid_user_id") from exc


@router.get("/reading-list", response_model=ReadingListResponse)
async def list_items(request: Request) -> ReadingListResponse:
    user_id = _user_id(request)
    items = await reading_list_service.list_items(user_id)
    return ReadingListResponse(items=items, count=len(items))


@router.post("/reading-list", response_model=ReadingListItem, status_code=201)
async def add_item(req: ReadingListAddRequest, request: Request) -> ReadingListItem:
    user_id = _user_id(request)
    try:
        return await reading_list_service.add_item(
            user_id, req.paper_id, req.status, req.notes
        )
    except LookupError as exc:
        # OpenAlex meta yoksa papers upsert edilemedi → 502 (upstream blocker)
        logger.warning("reading_list add: %s", exc)
        raise HTTPException(
            status_code=502, detail={"error": "paper_metadata_unavailable", "paper_id": req.paper_id}
        ) from exc


@router.patch("/reading-list/{item_id}", response_model=ReadingListItem)
async def update_item(
    item_id: str, req: ReadingListUpdateRequest, request: Request
) -> ReadingListItem:
    user_id = _user_id(request)
    item = await reading_list_service.update_item(
        user_id, item_id, req.status, req.notes
    )
    if item is None:
        raise HTTPException(
            status_code=404, detail={"error": "item_not_found", "item_id": item_id}
        )
    return item


@router.delete("/reading-list/{item_id}", status_code=204)
async def delete_item(item_id: str, request: Request) -> None:
    user_id = _user_id(request)
    deleted = await reading_list_service.delete_item(user_id, item_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail={"error": "item_not_found", "item_id": item_id}
        )
