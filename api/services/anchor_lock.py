"""V1-S15.pre — POST /api/project/{id}/research-area/anchor/lock service.

Plan: docs/plans/V1_S15_pre_anchor_lock.md + Omer 2026-05-26 revize.

Karar matrisi (Omer 2026-05-26):
  - current_stage ∈ {1.x, 2.x}: idempotent UPDATE (kullanıcı keşif aşamasında,
    aday değiştirebilir; "already_locked 409" YOK).
  - current_stage 3.x/4.x/5.x: FrozenStageError → 409 (keşif kapalı).
  - Aday listede üyelik kontrolü YOK (paper_id ile user ilişkisi yok; FE'nin
    sunduğu butona basıyor, manipülasyon yüzeyi minimal).
  - İlk lock (current_stage '1.x'): aynı işlemde projects.current_stage='2.2'.
  - cluster_status='pending' (Stage C deferred).
  - 200 senkron (BackgroundTasks YOK; 202 yalan olur, Stage C yok).

Akış:
  1) _verify_ownership_and_load_stage (K-031 manuel .eq user_id zırh).
  2) _is_frozen(current_stage) → FrozenStageError.
  3) project_anchor upsert: anchor_paper_id, locked_at, cluster_status='pending'.
  4) current_stage '1.x' ise projects.current_stage='2.2' UPDATE.
  5) LockResponse {anchor_paper_id, locked_at, cluster_status}.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from postgrest.types import JSON
from supabase import Client

from api.models.research_area import LockResponse


class ProjectNotFoundError(Exception):
    """Proje bulunamadı veya kullanıcının değil (K-031 zırh sonrası)."""


class FrozenStageError(Exception):
    """current_stage 3.x+ — keşif kapalı, çapa değişimi yasak."""


async def _verify_ownership_and_load_stage(
    db: Client, project_id: str, user_id: str
) -> str:
    from api.db.supabase_client import supabase_call_async

    resp = await supabase_call_async(
        lambda: db.table("projects")
        .select("current_stage")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        raise ProjectNotFoundError(
            f"project {project_id} not found for user {user_id}"
        )
    return str(rows[0].get("current_stage") or "1.1")


def _is_frozen(current_stage: str) -> bool:
    """Keşif kapatıldıktan sonra (3.x+) çapa değişimi yasak."""
    if not current_stage:
        return False
    head = current_stage.split(".", 1)[0]
    return head in {"3", "4", "5"}


async def _upsert_anchor(
    db: Client, project_id: str, paper_id: str, locked_at: str
) -> None:
    from api.db.supabase_client import supabase_call_async

    payload: dict[str, Any] = {
        "project_id": project_id,
        "anchor_paper_id": paper_id,
        "locked_at": locked_at,
        "cluster_status": "pending",
    }
    await supabase_call_async(
        lambda: db.table("project_anchor")
        .upsert(cast(JSON, payload), on_conflict="project_id")
        .execute()
    )


async def _advance_stage_if_first_lock(
    db: Client, project_id: str, current_stage: str
) -> None:
    """1.x → 2.2 advance. 2.x'te dokunma (geriye gitme önlemi)."""
    from api.db.supabase_client import supabase_call_async

    head = current_stage.split(".", 1)[0]
    if head != "1":
        return
    await supabase_call_async(
        lambda: db.table("projects")
        .update({"current_stage": "2.2"})
        .eq("id", project_id)
        .execute()
    )


async def run(
    *, db: Client, project_id: str, user_id: str, paper_id: str
) -> LockResponse:
    current_stage = await _verify_ownership_and_load_stage(
        db, project_id, user_id
    )
    if _is_frozen(current_stage):
        raise FrozenStageError(
            f"project {project_id} current_stage={current_stage} frozen"
        )
    locked_at_iso = datetime.now(UTC).isoformat()
    await _upsert_anchor(db, project_id, paper_id, locked_at_iso)
    await _advance_stage_if_first_lock(db, project_id, current_stage)
    return LockResponse(
        anchor_paper_id=paper_id,
        locked_at=locked_at_iso,
        cluster_status="pending",
    )


__all__ = [
    "FrozenStageError",
    "ProjectNotFoundError",
    "run",
]
