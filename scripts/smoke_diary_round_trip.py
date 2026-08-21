"""F13-S1 closure — Supabase canlı insert/read/patch döngüsü.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 closure DoD
    "1 Supabase canlı insert/read/patch döngüsü"

Strateji: get_supabase_admin (RLS bypass) + ilk project'in user_id'si.
Insert → list_timeline'da görünür mü → patch (resolved_at) → cleanup (delete).

Çalıştırma:
    cd /Users/omer/papermind-app
    uv run python scripts/smoke_diary_round_trip.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def _verify_env() -> None:
    if not (REPO / ".env").exists():
        sys.exit(f"FAIL: .env yok ({REPO / '.env'})")
    # pydantic-settings .env yi env_file= ile kendisi okur (inline comment safe).


_verify_env()

from api.db.supabase_client import (  # noqa: E402
    get_supabase_admin,
    supabase_call_async,
)
from api.models.diary import DiaryEventCreate, DiaryEventPatch  # noqa: E402
from api.services import diary_service  # noqa: E402


async def _pick_owner() -> tuple[UUID, UUID]:
    """İlk projeyi bul → (user_id, project_id) döndür."""
    db = get_supabase_admin()

    def _q() -> Any:
        return db.table("projects").select("id,user_id").limit(1).execute()

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    if not rows:
        sys.exit("FAIL: project tablosu boş — smoke için 1 proje gerekli")
    return UUID(rows[0]["user_id"]), UUID(rows[0]["id"])


async def _delete_event(event_id: UUID) -> None:
    db = get_supabase_admin()

    def _q() -> Any:
        return db.table("project_event").delete().eq("id", str(event_id)).execute()

    await supabase_call_async(_q)


async def main() -> None:
    print("F13-S1 closure smoke — Supabase round-trip")
    print(f"   captured_at: {datetime.now(UTC).isoformat()}")

    user_id, project_id = await _pick_owner()
    print(f"   user_id    : {user_id}")
    print(f"   project_id : {project_id}")

    # 1) INSERT
    create = DiaryEventCreate(
        project_id=project_id,
        page_slug="closure_smoke",
        event_type="kayit",
        payload={"note": "F13-S1 closure round-trip smoke"},
    )
    event = await diary_service.insert_event(user_id, create)
    print(f"   ✅ INSERT  : id={event.id}")
    assert event.event_type == "kayit"
    assert event.resolved_at is None

    try:
        # 2) READ via timeline (page_slug filter)
        tl = await diary_service.list_timeline(
            user_id, project_id=project_id, page_slug="closure_smoke"
        )
        ids = [str(e.id) for e in tl.items]
        assert str(event.id) in ids, f"event {event.id} timeline'da yok"
        print(f"   ✅ READ    : timeline {len(tl.items)} olay (event eşleşti)")

        # 3) PATCH resolved_at = now
        now = datetime.now(UTC)
        patched = await diary_service.patch_event(
            user_id, event.id, DiaryEventPatch(resolved_at=now)
        )
        assert patched.resolved_at is not None, "resolved_at None döndü"
        print(f"   ✅ PATCH   : resolved_at={patched.resolved_at.isoformat()}")

        # 4) PATCH geri aç (resolved_at = None)
        reopened = await diary_service.patch_event(
            user_id, event.id, DiaryEventPatch(resolved_at=None)
        )
        assert reopened.resolved_at is None, "geri aç başarısız"
        print("   ✅ REOPEN  : resolved_at=None")
    finally:
        # 5) CLEANUP
        await _delete_event(event.id)
        print(f"   🗑  DELETE  : {event.id}")

    print("\n✅ F13-S1 closure: insert/read/patch/reopen/delete döngüsü PASS")


if __name__ == "__main__":
    asyncio.run(main())
