"""public.user_notes CRUD service (Supabase admin client + Python-level user_id filter).

Migration 0035 sonrası aktif — paper-başına çoklu not.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.notes import NoteItem
from api.services.papers_mirror import ensure_paper_row

logger = logging.getLogger(__name__)

_TABLE = "user_notes"


def _row_to_item(row: dict[str, Any]) -> NoteItem:
    created = row["created_at"]
    updated = row["updated_at"]
    return NoteItem(
        id=str(row["id"]),
        paper_id=row.get("paper_id"),
        content=row["content"],
        tags=list(row.get("tags") or []),
        created_at=datetime.fromisoformat(created.replace("Z", "+00:00"))
        if isinstance(created, str)
        else created,
        updated_at=datetime.fromisoformat(updated.replace("Z", "+00:00"))
        if isinstance(updated, str)
        else updated,
    )


async def list_notes(user_id: UUID, paper_id: str | None = None) -> list[NoteItem]:
    db = get_supabase_admin()

    def _q() -> Any:
        q = (
            db.from_(_TABLE)
            .select("id,paper_id,content,tags,created_at,updated_at")
            .eq("user_id", str(user_id))
        )
        if paper_id:
            q = q.eq("paper_id", paper_id)
        return q.order("updated_at", desc=True).execute()

    r = await supabase_call_async(_q)
    return [_row_to_item(row) for row in (r.data or [])]


async def create_note(
    user_id: UUID, paper_id: str | None, content: str, tags: list[str]
) -> NoteItem:
    if paper_id:
        ensured = await ensure_paper_row(paper_id)
        if not ensured:
            # 0035 trigger eklemedik ama paper_id'siz not yine de yazılabilir;
            # paper_id verildiyse meta yoksa caller'a hata.
            raise LookupError(
                f"paper_not_found_or_metadata_unavailable: {paper_id}"
            )

    db = get_supabase_admin()
    row: dict[str, Any] = {
        "user_id": str(user_id),
        "paper_id": paper_id,
        "paper_kind": "corpus" if paper_id else None,
        "content": content,
        "tags": tags or [],
    }

    def _insert() -> Any:
        return db.from_(_TABLE).insert(row).execute()

    resp = await supabase_call_async(_insert)
    rows = resp.data or []
    if not rows:
        raise RuntimeError(f"{_TABLE} insert returned empty")
    return _row_to_item(rows[0])


async def update_note(
    user_id: UUID,
    note_id: str,
    content: str | None,
    tags: list[str] | None,
) -> NoteItem | None:
    db = get_supabase_admin()
    updates: dict[str, Any] = {}
    if content is not None:
        updates["content"] = content
    if tags is not None:
        updates["tags"] = tags
    if not updates:
        return await _find_by_id(user_id, note_id)

    def _q() -> Any:
        return (
            db.from_(_TABLE)
            .update(updates)
            .eq("id", note_id)
            .eq("user_id", str(user_id))
            .execute()
        )

    r = await supabase_call_async(_q)
    rows = r.data or []
    return _row_to_item(rows[0]) if rows else None


async def _find_by_id(user_id: UUID, note_id: str) -> NoteItem | None:
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.from_(_TABLE)
            .select("id,paper_id,content,tags,created_at,updated_at")
            .eq("id", note_id)
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

    r = await supabase_call_async(_q)
    rows = r.data or []
    return _row_to_item(rows[0]) if rows else None


async def delete_note(user_id: UUID, note_id: str) -> bool:
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.from_(_TABLE)
            .delete()
            .eq("id", note_id)
            .eq("user_id", str(user_id))
            .execute()
        )

    r = await supabase_call_async(_q)
    return bool(r.data)
