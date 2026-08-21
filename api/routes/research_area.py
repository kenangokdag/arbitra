"""F9 P094 /api/project/{id}/research-area — Stage A Kütüphaneci sohbeti.

Plan: docs/plans/F9_kesif_workbench.md §7 (endpoint sözleşmesi)
- POST /api/project/{id}/research-area/messages → MessageResponse
  · 422 Pydantic validation
  · 401 missing user_id (AuthMiddleware)
  · 403 başka user'ın project_id'i (K-031 RLS+manuel zırh; UX güvenli 404 döner)
  · 503 Gemini fail / parsed_output yok / şema invalid (LLMServiceError)
- HK-1: extra=forbid; HK-6: no Any.
- Auth: AuthMiddleware request.state.user_id.
- Dev/test fallback: SUPABASE yoksa 503 (Stage A LLM gerektirir, placeholder yok).

⚠ Service-role client RLS BYPASS — K-031 kanonu: librarian.py içinde tüm
   SELECT/INSERT'lerde manuel .eq("user_id", uid) zırhı. Bu route auth gate
   + ownership 404 sınır kontrolü uygular.
"""

from __future__ import annotations

import logging
from typing import cast

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from supabase import Client

logger = logging.getLogger(__name__)

from api.models.research_area import (
    AnchorCandidatesResponse,
    ClusterExpandAcceptedResponse,
    ClusterStatusResponse,
    LockRequest,
    LockResponse,
    MessageRequest,
    MessageResponse,
    ResetRequest,
    ResetResponse,
)
from api.services import (
    anchor_finder,
    anchor_lock,
    cluster_expander,
    research_area_reset,
)
from api.services.llm_service import LLMServiceError
from api.services.role_modules import librarian

router = APIRouter(prefix="/api/project", tags=["research-area"])


def _supabase() -> Client | None:
    from api.config import get_settings

    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SECRET_KEY:
        return None
    from api.db.supabase_client import get_supabase_admin

    return get_supabase_admin()


def _user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="missing_user_id")
    return cast(str, uid)


@router.post(
    "/{project_id}/research-area/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def post_research_area_message(
    project_id: str, req: MessageRequest, request: Request
) -> MessageResponse:
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        # Dev fallback: Stage A gerçek LLM gerektirir; placeholder güvenli değil.
        raise HTTPException(status_code=503, detail="supabase_unavailable")

    try:
        return await librarian.run(
            db=db,
            project_id=project_id,
            user_id=user_id,
            content=req.content,
            attempt_no=req.attempt_no,
        )
    except librarian.ProjectNotFoundError:
        # RLS bypass + manuel filter → satır yok = 404 (UX güvenli, 403 sızdırmaz)
        raise HTTPException(status_code=404, detail="project_not_found") from None
    except LLMServiceError as exc:
        raise HTTPException(status_code=503, detail=f"llm_unavailable: {exc}") from exc


@router.post(
    "/{project_id}/research-area/anchor-candidates",
    response_model=AnchorCandidatesResponse,
    status_code=status.HTTP_200_OK,
)
async def post_anchor_candidates(
    project_id: str, request: Request
) -> AnchorCandidatesResponse:
    """F9 P095 BÖLÜM 2 — HyDE → fan-out → RRF → rerank → top-3.

    409 conflict: Stage A henüz tamamlanmadı (parsed_understanding yok).
    503 llm_unavailable: HyDE Gemini fail.
    504 pools_empty: Pinecone+tsvector birleşimi boş veya hepsi suspicious.
    """
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        raise HTTPException(status_code=503, detail="supabase_unavailable")
    try:
        return await anchor_finder.run(
            db=db, project_id=project_id, user_id=user_id
        )
    except anchor_finder.ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="project_not_found") from None
    except anchor_finder.ParsedUnderstandingMissingError as exc:
        raise HTTPException(status_code=409, detail=f"stage_a_incomplete: {exc}") from exc
    except anchor_finder.AnchorCandidatesEmptyError as exc:
        raise HTTPException(status_code=504, detail=f"pools_empty: {exc}") from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=503, detail=f"llm_unavailable: {exc}") from exc


@router.post(
    "/{project_id}/research-area/reset",
    response_model=ResetResponse,
    status_code=status.HTTP_200_OK,
)
async def post_research_area_reset(
    project_id: str, req: ResetRequest, request: Request
) -> ResetResponse:
    """F13-S12 — uyumsuzluk hafızası + attempt_no inkrement.

    409 attempt_cap_reached: attempt_no=10 sınırı (CHECK constraint).
    """
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        raise HTTPException(status_code=503, detail="supabase_unavailable")
    try:
        return await research_area_reset.run(
            db=db,
            project_id=project_id,
            user_id=user_id,
            reject_reason=req.reject_reason,
        )
    except research_area_reset.ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="project_not_found") from None
    except research_area_reset.AttemptCapReachedError as exc:
        raise HTTPException(status_code=409, detail=f"attempt_cap_reached: {exc}") from exc


async def _run_cluster_expander_bg(project_id: str) -> None:
    """BackgroundTask helper — supabase admin client'ı task içinde yeniden oluştur.

    HTTP request lifecycle kapandıktan sonra `Request`/dependency injection
    erişilmez; settings + admin client lazy yeniden çekilir.
    """
    from api.config import get_settings

    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SECRET_KEY:
        logger.warning(
            "cluster_expander background skipped (no supabase): project=%s",
            project_id,
        )
        return

    from api.db.supabase_client import get_supabase_admin

    db = get_supabase_admin()
    try:
        await cluster_expander.run(db=db, project_id=project_id)
    except cluster_expander.AnchorNotFoundError as exc:
        logger.error("cluster_expander BG anchor missing: %s", exc)
    except cluster_expander.ClusterPoolEmptyError as exc:
        # _mark_failed zaten çalıştı; log ile kanıt damgası.
        logger.warning("cluster_expander BG pool empty: %s", exc)
    except Exception:  # noqa: BLE001 — BG son durak; sessiz düşmesin
        logger.exception(
            "cluster_expander BG unexpected fail project=%s", project_id
        )


@router.post(
    "/{project_id}/research-area/anchor/lock",
    response_model=LockResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_anchor_lock(
    project_id: str,
    req: LockRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> LockResponse:
    """V1-S15.pre + V1-S17 P002 — çapa kilidi + Stage C BackgroundTask tetikleyici.

    Akış:
      - current_stage ∈ {1.x, 2.x}: idempotent UPDATE.
      - current_stage 3.x+: 409 stage_frozen.
      - Yeni lock → cluster_status='pending' set; aynı response cycle'da
        BackgroundTask cluster_expander.run kuyruğa alınır → 202 Accepted.
      - FE GET /cluster/status 5s interval ile poll eder.
    """
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        raise HTTPException(status_code=503, detail="supabase_unavailable")
    try:
        resp = await anchor_lock.run(
            db=db,
            project_id=project_id,
            user_id=user_id,
            paper_id=req.paper_id,
        )
    except anchor_lock.ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="project_not_found") from None
    except anchor_lock.FrozenStageError as exc:
        raise HTTPException(status_code=409, detail=f"stage_frozen: {exc}") from exc

    background_tasks.add_task(_run_cluster_expander_bg, project_id)
    return resp


@router.post(
    "/{project_id}/cluster/expand",
    response_model=ClusterExpandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_cluster_expand(
    project_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
) -> ClusterExpandAcceptedResponse:
    """V1-S17 P002 — Stage C manuel tetikleyici (retry/admin path).

    Lock endpoint zaten BG'yi kuyruğa atıyor; bu route idempotent re-run için
    (failed → retry, dev/admin manual). 202 + status poll.
    """
    from datetime import UTC, datetime

    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        raise HTTPException(status_code=503, detail="supabase_unavailable")

    # Ownership zırh + anchor varlığı — K-031 manuel filter.
    from api.db.supabase_client import supabase_call_async

    anc_resp = await supabase_call_async(
        lambda: db.table("project_anchor")
        .select("anchor_paper_id, project_id")
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    rows = anc_resp.data or []
    if not rows or not rows[0].get("anchor_paper_id"):
        raise HTTPException(
            status_code=409, detail="anchor_not_locked"
        )
    # Ownership: projects.user_id eşleşmesi
    own_resp = await supabase_call_async(
        lambda: db.table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not (own_resp.data or []):
        raise HTTPException(status_code=404, detail="project_not_found")

    background_tasks.add_task(_run_cluster_expander_bg, project_id)
    return ClusterExpandAcceptedResponse(
        project_id=project_id,
        anchor_paper_id=str(rows[0]["anchor_paper_id"]),
        cluster_status="expanding",
        accepted_at=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/{project_id}/cluster/status",
    response_model=ClusterStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_cluster_status(
    project_id: str, request: Request
) -> ClusterStatusResponse:
    """V1-S17 P002 — Stage C poll endpoint (FE 5s interval).

    Ownership: projects.user_id manuel filter (K-031 zırh).
    Body: cluster_status + cluster_size (project_cluster COUNT) + timestamps.
    """
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        raise HTTPException(status_code=503, detail="supabase_unavailable")

    from api.db.supabase_client import supabase_call_async

    own_resp = await supabase_call_async(
        lambda: db.table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not (own_resp.data or []):
        raise HTTPException(status_code=404, detail="project_not_found")

    anc_resp = await supabase_call_async(
        lambda: db.table("project_anchor")
        .select(
            "anchor_paper_id, cluster_status, cluster_started_at, "
            "cluster_completed_at, cluster_error"
        )
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    rows = anc_resp.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="anchor_not_found")

    row = rows[0]
    size_resp = await supabase_call_async(
        lambda: db.table("project_cluster")
        .select("paper_id")
        .eq("project_id", project_id)
        .execute()
    )
    cluster_size = len(size_resp.data or [])

    cluster_status_val = str(row.get("cluster_status") or "pending")
    err = row.get("cluster_error")
    # Pydantic schema dict[str, str] bekliyor; jsonb dict gelirse hizala.
    err_payload: dict[str, str] | None = None
    if isinstance(err, dict):
        err_payload = {k: str(v) for k, v in err.items()}

    return ClusterStatusResponse(
        project_id=project_id,
        anchor_paper_id=row.get("anchor_paper_id"),
        cluster_status=cluster_status_val,  # type: ignore[arg-type]
        cluster_size=min(cluster_size, 50),
        started_at=row.get("cluster_started_at"),
        completed_at=row.get("cluster_completed_at"),
        cluster_error=err_payload,
    )
