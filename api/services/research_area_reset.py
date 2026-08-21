"""F13-S12 — POST /api/project/{id}/research-area/reset service.

Plan: Page_Design/Sayfa_Plani_v2/2.1_arastirma_alani.rtf:262-265,376-379

Akış:
  1) projects ownership (K-031 manuel .eq("user_id", uid) zırh) → 404 sızdırma yok.
  2) project_chat_messages max(attempt_no) → current_attempt.
  3) Son adviser turn parsed_understanding → focuses (Stage A "anladığım").
  4) project_anchor upsert:
     - rejected_anchors jsonb array += focuses (kümülatif uyumsuzluk hafızası)
     - reject_reasons jsonb array += reject_reason
  5) new_attempt = min(current_attempt + 1, 10) — CHECK constraint sınırı.
  6) ResetResponse { attempt_no, rejected_count }.

Hatalar:
  - ProjectNotFoundError → 404 (route map eder).
  - AttemptCapReachedError → 409 (10 attempt sonrası kullanıcı zaten sıfırdan).

Not (HK-2): focuses listesi parsed_understanding.focuses içindedir; başka
  uzun string'ler (adviser_text, content) rejected_anchors'a yazılmaz —
  bu liste librarian.py page_state'inde sistem prompt'a verilir.
"""

from __future__ import annotations

from typing import Any, cast

from postgrest.types import JSON
from supabase import Client

from api.models.research_area import ResetResponse


class ProjectNotFoundError(Exception):
    """Proje bulunamadı veya kullanıcının değil."""


class AttemptCapReachedError(Exception):
    """attempt_no=10 — CHECK constraint sınırı. Daha fazla reset yok."""


async def _verify_ownership(db: Client, project_id: str, user_id: str) -> None:
    from api.db.supabase_client import supabase_call_async

    resp = await supabase_call_async(
        lambda: db.table("projects")
        .select("id")
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


async def _current_attempt(db: Client, project_id: str) -> int:
    from api.db.supabase_client import supabase_call_async

    resp = await supabase_call_async(
        lambda: db.table("project_chat_messages")
        .select("attempt_no")
        .eq("project_id", project_id)
        .order("attempt_no", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        return 0
    return int(rows[0].get("attempt_no") or 0)


async def _last_focuses(db: Client, project_id: str, attempt_no: int) -> list[str]:
    """Bu attempt'in son adviser turn'unun parsed_understanding.focuses listesi."""
    from api.db.supabase_client import supabase_call_async

    if attempt_no < 1:
        return []
    resp = await supabase_call_async(
        lambda: db.table("project_chat_messages")
        .select("parsed_understanding,turn_no")
        .eq("project_id", project_id)
        .eq("attempt_no", attempt_no)
        .eq("role", "adviser")
        .order("turn_no", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        return []
    parsed = rows[0].get("parsed_understanding") or {}
    focuses = parsed.get("focuses") if isinstance(parsed, dict) else None
    if not isinstance(focuses, list):
        return []
    return [str(f).strip() for f in focuses if str(f).strip()]


async def _append_rejection(
    db: Client,
    *,
    project_id: str,
    focuses: list[str],
    reject_reason: str,
) -> int:
    """project_anchor.rejected_anchors + reject_reasons append. Yeni length döner."""
    from api.db.supabase_client import supabase_call_async

    resp = await supabase_call_async(
        lambda: db.table("project_anchor")
        .select("rejected_anchors,reject_reasons")
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    existing_focuses: list[str] = []
    existing_reasons: list[str] = []
    if rows:
        existing_focuses = list(rows[0].get("rejected_anchors") or [])
        existing_reasons = list(rows[0].get("reject_reasons") or [])

    new_focuses = [*existing_focuses, *focuses]
    new_reasons = [*existing_reasons, reject_reason]

    payload: dict[str, Any] = {
        "project_id": project_id,
        "rejected_anchors": new_focuses,
        "reject_reasons": new_reasons,
    }
    await supabase_call_async(
        lambda: db.table("project_anchor")
        .upsert(cast(JSON, payload), on_conflict="project_id")
        .execute()
    )
    return len(new_focuses)


async def run(
    *, db: Client, project_id: str, user_id: str, reject_reason: str
) -> ResetResponse:
    await _verify_ownership(db, project_id, user_id)
    current = await _current_attempt(db, project_id)
    if current >= 10:
        raise AttemptCapReachedError(
            f"attempt_no cap=10 reached for project {project_id}"
        )
    focuses = await _last_focuses(db, project_id, current)
    rejected_count = await _append_rejection(
        db,
        project_id=project_id,
        focuses=focuses,
        reject_reason=reject_reason,
    )
    new_attempt = max(current, 0) + 1
    return ResetResponse(attempt_no=new_attempt, rejected_count=rejected_count)


__all__ = [
    "AttemptCapReachedError",
    "ProjectNotFoundError",
    "run",
]
