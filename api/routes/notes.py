"""POST/GET/PATCH/DELETE /api/notes — Supabase persist (2026-05-26 Madde 1).

Tablo: public.user_notes (0035_user_notes.sql)
RLS  : auth.uid() = user_id — backend admin client + Python user_id filter.
"""

from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from api.models.notes import (
    NoteCreateRequest,
    NoteItem,
    NotesResponse,
    NoteUpdateRequest,
)
from api.services import notes_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["notes"])


def _user_id(request: Request) -> UUID:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="missing_user_id")
    try:
        return UUID(cast(str, uid))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="invalid_user_id") from exc


@router.get("/notes", response_model=NotesResponse)
async def list_notes(
    request: Request, paper_id: str | None = None
) -> NotesResponse:
    user_id = _user_id(request)
    items = await notes_service.list_notes(user_id, paper_id=paper_id)
    return NotesResponse(items=items, count=len(items))


@router.post("/notes", response_model=NoteItem, status_code=201)
async def create_note(req: NoteCreateRequest, request: Request) -> NoteItem:
    user_id = _user_id(request)
    try:
        return await notes_service.create_note(
            user_id, req.paper_id, req.content, req.tags
        )
    except LookupError as exc:
        logger.warning("notes create: %s", exc)
        raise HTTPException(
            status_code=502,
            detail={"error": "paper_metadata_unavailable", "paper_id": req.paper_id},
        ) from exc


@router.patch("/notes/{note_id}", response_model=NoteItem)
async def update_note(
    note_id: str, req: NoteUpdateRequest, request: Request
) -> NoteItem:
    user_id = _user_id(request)
    note = await notes_service.update_note(user_id, note_id, req.content, req.tags)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: str, request: Request) -> None:
    user_id = _user_id(request)
    deleted = await notes_service.delete_note(user_id, note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
