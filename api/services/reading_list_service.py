"""public.user_reading_list CRUD service (Supabase admin client + RLS bypass).

API ↔ DB status eşleme:
  want_to_read ↔ to_read
  reading      ↔ reading
  finished     ↔ done
  skipped      ↔ skipped (0036 migration sonrası)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.reading_list import ReadingListItem, ReadingStatus
from api.services.papers_mirror import ensure_paper_row

logger = logging.getLogger(__name__)

_TABLE = "user_reading_list"

_API_TO_DB: dict[ReadingStatus, str] = {
    "want_to_read": "to_read",
    "reading": "reading",
    "finished": "done",
    "skipped": "skipped",
}
_DB_TO_API: dict[str, ReadingStatus] = {v: k for k, v in _API_TO_DB.items()}


def _row_to_item(row: dict[str, Any]) -> ReadingListItem:
    return ReadingListItem(
        id=str(row["id"]),
        paper_id=row["paper_id"],
        status=_DB_TO_API.get(row.get("status") or "to_read", "want_to_read"),
        notes=row.get("note") or "",
        added_at=datetime.fromisoformat(row["added_at"].replace("Z", "+00:00"))
        if isinstance(row.get("added_at"), str)
        else row["added_at"],
        updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
        if isinstance(row.get("updated_at"), str)
        else row["updated_at"],
    )


async def list_items(user_id: UUID) -> list[ReadingListItem]:
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.from_(_TABLE)
            .select("id,paper_id,status,note,added_at,updated_at")
            .eq("user_id", str(user_id))
            .order("added_at", desc=True)
            .execute()
        )

    r = await supabase_call_async(_q)
    return [_row_to_item(row) for row in (r.data or [])]


async def add_item(
    user_id: UUID, paper_id: str, status: ReadingStatus, notes: str
) -> ReadingListItem:
    """Insert reading-list row. papers FK trigger için ensure_paper_row önce."""
    ensured = await ensure_paper_row(paper_id)
    if not ensured:
        # Trigger paper_kind='corpus' kontrolünü düşürür — caller'a 502.
        raise LookupError(f"paper_not_found_or_metadata_unavailable: {paper_id}")

    db = get_supabase_admin()
    row = {
        "user_id": str(user_id),
        "paper_id": paper_id,
        "paper_kind": "corpus",
        "status": _API_TO_DB[status],
        "note": notes or None,
    }

    def _insert() -> Any:
        return db.from_(_TABLE).insert(row).execute()

    try:
        resp = await supabase_call_async(_insert)
    except Exception as exc:
        # UNIQUE (user_id, paper_id) çakışırsa mevcut satırı dön — idempotent UX.
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            existing = await _find_by_paper(user_id, paper_id)
            if existing is not None:
                return existing
        raise

    rows = resp.data or []
    if not rows:
        raise RuntimeError(f"{_TABLE} insert returned empty")
    return _row_to_item(rows[0])


async def _find_by_paper(user_id: UUID, paper_id: str) -> ReadingListItem | None:
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.from_(_TABLE)
            .select("id,paper_id,status,note,added_at,updated_at")
            .eq("user_id", str(user_id))
            .eq("paper_id", paper_id)
            .limit(1)
            .execute()
        )

    r = await supabase_call_async(_q)
    rows = r.data or []
    return _row_to_item(rows[0]) if rows else None


async def update_item(
    user_id: UUID,
    item_id: str,
    status: ReadingStatus | None,
    notes: str | None,
) -> ReadingListItem | None:
    db = get_supabase_admin()
    updates: dict[str, Any] = {}
    if status is not None:
        updates["status"] = _API_TO_DB[status]
    if notes is not None:
        updates["note"] = notes or None
    if not updates:
        # No-op — mevcut satırı dön
        return await _find_by_id(user_id, item_id)

    def _q() -> Any:
        return (
            db.from_(_TABLE)
            .update(updates)
            .eq("id", item_id)
            .eq("user_id", str(user_id))
            .execute()
        )

    r = await supabase_call_async(_q)
    rows = r.data or []
    return _row_to_item(rows[0]) if rows else None


async def _find_by_id(user_id: UUID, item_id: str) -> ReadingListItem | None:
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.from_(_TABLE)
            .select("id,paper_id,status,note,added_at,updated_at")
            .eq("id", item_id)
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

    r = await supabase_call_async(_q)
    rows = r.data or []
    return _row_to_item(rows[0]) if rows else None


async def delete_item(user_id: UUID, item_id: str) -> bool:
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.from_(_TABLE)
            .delete()
            .eq("id", item_id)
            .eq("user_id", str(user_id))
            .execute()
        )

    r = await supabase_call_async(_q)
    return bool(r.data)
