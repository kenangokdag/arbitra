"""F9 P094 ROLE_MODULE: librarian — Stage A 2-tur sohbet orchestrator.

Plan: docs/plans/F9_kesif_workbench.md §3 (commit P094) + §7 + §8
- LIBRARIAN_BRIEF: `prompts/librarian_v1.md` lazy yüklenir (lru_cache);
  ROLE_MODULES dict'e "librarian" key'iyle eklenir (api/services/role_modules/__init__.py).
- run(project_id, user_id, content, attempt_no, db) → MessageResponse.
  1) projects + project_anchor SELECT (manuel .eq("user_id", uid) zırh — K-031).
  2) project_chat_messages SELECT → max(turn_no) WHERE attempt_no=req.attempt_no.
  3) LLMService.call(prompt=content, tier="flash", mode="librarian", project_ctx,
     page_state={attempt_no, profile, rejected, reasons},
     structured_output_schema=ParsedUnderstanding).
  4) chat_messages 2-row INSERT (user + adviser).
  5) MessageResponse.
- LLM hatası / Pydantic ValidationError → LLMServiceError (route 503'e map eder).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from postgrest.types import JSON
from pydantic import ValidationError
from supabase import Client

from api.models.llm import ProjectContext
from api.models.research_area import MessageResponse, ParsedUnderstanding
from api.services.llm_service import LLMServiceError
from api.services.llm_service import call as llm_call

_PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "librarian_v1.md"


@lru_cache(maxsize=1)
def _load_brief() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


LIBRARIAN_BRIEF = _load_brief()


class ProjectNotFoundError(Exception):
    """Proje bulunamadı veya kullanıcının değil."""


async def _fetch_project_context(
    db: Client, project_id: str, user_id: str
) -> dict[str, Any]:
    """projects + project_anchor + user_profiles tek atış oku.

    K-031 zırhı: her SELECT'e .eq("user_id", uid) — service-role RLS bypass
    durumunda manuel ownership doğrulama.
    """
    from api.db.supabase_client import supabase_call_async

    proj_resp = await supabase_call_async(
        lambda: db.table("projects")
        .select("id,name,inherited_field_ids,inherited_subfield_ids,inherited_research_focus")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    proj_rows = cast(list[dict[str, Any]], proj_resp.data or [])
    if not proj_rows:
        raise ProjectNotFoundError(f"project {project_id} not found for user {user_id}")
    project = proj_rows[0]

    # project_anchor: rejected_anchors + reject_reasons (uyumsuzluk hafızası)
    anchor_resp = await supabase_call_async(
        lambda: db.table("project_anchor")
        .select("rejected_anchors,reject_reasons")
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    anchor_rows = cast(list[dict[str, Any]], anchor_resp.data or [])
    rejected_focuses: list[str] = []
    reject_reasons: list[str] = []
    if anchor_rows:
        rejected_focuses = list(anchor_rows[0].get("rejected_anchors") or [])
        reject_reasons = list(anchor_rows[0].get("reject_reasons") or [])

    return {
        "project": project,
        "rejected_focuses": rejected_focuses,
        "reject_reasons": reject_reasons,
    }


async def _next_turn_no(db: Client, project_id: str, attempt_no: int) -> int:
    """turn_no = max(existing) + 1, attempt scope'unda; cap=2."""
    from api.db.supabase_client import supabase_call_async

    msg_resp = await supabase_call_async(
        lambda: db.table("project_chat_messages")
        .select("turn_no")
        .eq("project_id", project_id)
        .eq("attempt_no", attempt_no)
        .eq("role", "user")
        .execute()
    )
    rows = cast(list[dict[str, Any]], msg_resp.data or [])
    existing = [int(r["turn_no"]) for r in rows]
    next_no = (max(existing) + 1) if existing else 1
    return min(next_no, 2)


async def _persist_messages(
    db: Client,
    *,
    project_id: str,
    attempt_no: int,
    turn_no: int,
    user_content: str,
    parsed: ParsedUnderstanding,
) -> None:
    from api.db.supabase_client import supabase_call_async

    parsed_dump = parsed.model_dump()
    payload = [
        {
            "project_id": project_id,
            "attempt_no": attempt_no,
            "turn_no": turn_no,
            "role": "user",
            "content": user_content,
        },
        {
            "project_id": project_id,
            "attempt_no": attempt_no,
            "turn_no": turn_no,
            "role": "adviser",
            "content": parsed.adviser_text,
            "parsed_understanding": parsed_dump,
        },
    ]
    await supabase_call_async(
        lambda: db.table("project_chat_messages").insert(cast(JSON, payload)).execute()
    )


async def run(
    *,
    db: Client,
    project_id: str,
    user_id: str,
    content: str,
    attempt_no: int,
) -> MessageResponse:
    """Stage A bir tur: kullanıcı mesajını al, Gemini Flash ile parse et, kaydet."""
    ctx = await _fetch_project_context(db, project_id, user_id)
    project = cast(dict[str, Any], ctx["project"])
    rejected_focuses = cast(list[str], ctx["rejected_focuses"])
    reject_reasons = cast(list[str], ctx["reject_reasons"])

    turn_no = await _next_turn_no(db, project_id, attempt_no)

    page_state: dict[str, Any] = {
        "attempt_no": attempt_no,
        "turn_no": turn_no,
        "inherited_field_ids": list(project.get("inherited_field_ids") or []),
        "inherited_subfield_ids": list(project.get("inherited_subfield_ids") or []),
        "inherited_research_focus": project.get("inherited_research_focus"),
        "rejected_focuses": rejected_focuses,
        "reject_reasons": reject_reasons,
    }
    project_ctx = ProjectContext(
        project_id=project_id,
        user_id=user_id,
        topic=project.get("inherited_research_focus"),
    )

    try:
        response = await llm_call(
            prompt=content,
            tier="flash",
            mode="librarian",
            project_ctx=project_ctx,
            page_state=page_state,
            structured_output_schema=ParsedUnderstanding,
            max_tokens=1500,
        )
    except ValidationError as exc:
        raise LLMServiceError(f"librarian schema invalid: {exc}") from exc

    if response.parsed_output is None or not isinstance(
        response.parsed_output, ParsedUnderstanding
    ):
        raise LLMServiceError("librarian parsed_output missing")

    parsed: ParsedUnderstanding = response.parsed_output
    # Tur 2 sınırı: model finished=False yazsa bile cap edilir.
    finished = parsed.finished if turn_no < 2 else True
    if finished != parsed.finished:
        parsed = parsed.model_copy(update={"finished": finished})

    await _persist_messages(
        db,
        project_id=project_id,
        attempt_no=attempt_no,
        turn_no=turn_no,
        user_content=content,
        parsed=parsed,
    )

    return MessageResponse(
        turn_no=turn_no,
        parsed_understanding=parsed,
        adviser_text=parsed.adviser_text,
        finished=finished,
    )


__all__ = [
    "LIBRARIAN_BRIEF",
    "ProjectNotFoundError",
    "run",
]
