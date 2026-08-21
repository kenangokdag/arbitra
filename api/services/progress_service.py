"""F13-S2 5.1 Yayın Formatı — Supabase CRUD service (project_progress).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S2-P002 + P003
Pattern: diary_service.py — get_supabase_admin + supabase_call_async + Python-level
sahiplik kontrolü (RLS bypass + projects.user_id JOIN filter).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.progress import (
    AdvisorSummaryResponse,
    MaturityResponse,
    MaturityStep,
    ProgressStep,
    ProgressUpsert,
    PublicationType,
)
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_PROGRESS_TABLE = "project_progress"
_PROJECTS_TABLE = "projects"

# Yayın türü maskesi — RTF §Plan-Detayı (2b) + brief §4 (Omer onayı 2026-05-10).
# step_id konvansiyonu: web/src/lib/nav-config.ts:61-117 FE route slug.
_REQUIRED_STEPS: dict[PublicationType, set[str]] = {
    "tez": {
        "discovery-1", "discovery-2", "discovery-3", "discovery-4", "discovery-5",
        "curation-1", "curation-2", "curation-3", "curation-4", "curation-5",
        "gapatlas-1", "gapatlas-2", "gapatlas-3", "gapatlas-4", "gapatlas-5",
        "authoring-1", "authoring-2", "authoring-3", "authoring-4",
    },
    "makale": {
        "discovery-1", "discovery-3",
        "curation-1", "curation-4",
        "gapatlas-1", "gapatlas-4",
    },
    "bildiri": {
        "discovery-1", "gapatlas-1", "curation-4",
    },
}

_ALL_STEPS: set[str] = (
    {f"discovery-{i}" for i in range(1, 6)}
    | {f"curation-{i}" for i in range(1, 6)}
    | {f"gapatlas-{i}" for i in range(1, 6)}
    | {f"authoring-{i}" for i in range(1, 5)}
)

# Ağırlık: zorunlu %70, opsiyonel %30 (RTF §Plan (2d)).
_REQUIRED_WEIGHT = 0.70
_OPTIONAL_WEIGHT = 0.30


async def _assert_project_owner(user_id: UUID, project_id: UUID) -> None:
    """Sahiplik kontrolü — projects.user_id eq filter."""
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_PROJECTS_TABLE)
            .select("id")
            .eq("id", str(project_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    if not rows:
        raise LookupError(f"project {project_id} not found or not owned by {user_id}")


async def upsert_step(user_id: UUID, payload: ProgressUpsert) -> ProgressStep:
    """PUT /api/workshop/progress — sahiplik + upsert.

    completed_at: status='completed' olunca now() set; geri alınırsa NULL.
    """
    await _assert_project_owner(user_id, payload.project_id)
    db = get_supabase_admin()

    row: dict[str, Any] = {
        "project_id": str(payload.project_id),
        "step_id": payload.step_id,
        "status": payload.status,
        "meta": payload.meta,
    }
    # completed_at: status'a göre. now() DB-side: Supabase upsert'te None geçince trigger
    # update etmiyor → SQL fonksiyonu çağıramayız PostgREST'ten; Python'da hesapla.
    if payload.status == "completed":
        row["completed_at"] = datetime.now(UTC).isoformat()
    else:
        row["completed_at"] = None

    def _q() -> Any:
        return (
            db.table(_PROGRESS_TABLE)
            .upsert(row, on_conflict="project_id,step_id")
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    if not rows:
        raise RuntimeError(f"{_PROGRESS_TABLE} upsert returned empty")
    return ProgressStep.model_validate(rows[0])


async def list_steps(user_id: UUID, project_id: UUID) -> list[ProgressStep]:
    """Bir projenin tüm step'lerini getir — sahiplik kontrolü zorunlu."""
    await _assert_project_owner(user_id, project_id)
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_PROGRESS_TABLE)
            .select("*")
            .eq("project_id", str(project_id))
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    return [ProgressStep.model_validate(r) for r in rows]


def _compute_maturity(
    rows: list[ProgressStep],
    publication_type: PublicationType,
) -> tuple[list[MaturityStep], float, bool, int, int]:
    """Maturity hesapla → (UI satırları, %, button_active, req_total, req_completed).

    Algoritma (RTF §Plan-Detayı (2)):
    - Zorunlu kümesi: _REQUIRED_STEPS[publication_type]
    - Opsiyonel kümesi: _ALL_STEPS - zorunlu
    - row_status[step_id] = DB'den (yoksa not_started)
    - completed_required / required_total → required_pct
    - completed_optional / optional_total → optional_pct
    - maturity_pct = required_pct * 0.70 + optional_pct * 0.30 (× 100)
    - button_active = required_total > 0 ve required_completed == required_total
    """
    required = _REQUIRED_STEPS[publication_type]
    optional = _ALL_STEPS - required

    by_step: dict[str, ProgressStep] = {r.step_id: r for r in rows}

    ui_rows: list[MaturityStep] = []
    for step_id in sorted(_ALL_STEPS):
        existing = by_step.get(step_id)
        ui_rows.append(
            MaturityStep(
                step_id=step_id,
                status=existing.status if existing else "not_started",
                required=step_id in required,
                completed_at=existing.completed_at if existing else None,
            )
        )

    required_total = len(required)
    required_completed = sum(
        1 for s in ui_rows if s.required and s.status == "completed"
    )
    optional_total = len(optional)
    optional_completed = sum(
        1 for s in ui_rows if (not s.required) and s.status == "completed"
    )

    required_pct = (required_completed / required_total) if required_total else 0.0
    optional_pct = (optional_completed / optional_total) if optional_total else 0.0
    maturity_pct = (
        required_pct * _REQUIRED_WEIGHT + optional_pct * _OPTIONAL_WEIGHT
    ) * 100.0

    button_active = required_total > 0 and required_completed == required_total

    return ui_rows, round(maturity_pct, 2), button_active, required_total, required_completed


async def calculate_maturity(
    user_id: UUID, project_id: UUID, publication_type: PublicationType
) -> MaturityResponse:
    """GET /api/workshop/maturity — yayın türüne göre olgunluk yüzdesi + UI checklist."""
    rows = await list_steps(user_id, project_id)
    ui_rows, pct, btn_active, req_total, req_done = _compute_maturity(
        rows, publication_type
    )
    return MaturityResponse(
        project_id=project_id,
        publication_type=publication_type,
        steps=ui_rows,
        maturity_pct=pct,
        button_active=btn_active,
        required_total=req_total,
        required_completed=req_done,
    )


async def fetch_completed_step_meta(
    user_id: UUID, project_id: UUID
) -> list[dict[str, Any]]:
    """Advisor-summary için: tüm 'completed' adımların meta+step_id listesi."""
    rows = await list_steps(user_id, project_id)
    return [
        {"step_id": r.step_id, "meta": r.meta, "completed_at": r.completed_at}
        for r in rows
        if r.status == "completed"
    ]


def _format_step_block(rows: list[dict[str, Any]]) -> str:
    """Tamamlanmış adımları LLM body'sine sıkıştırılmış blok olarak yaz.

    Format:
        - discovery-1 (2026-04-15): meta_anahtar=değer | meta_anahtar=değer
        - curation-4 (2026-04-22): note=...
    """
    lines: list[str] = []
    for r in rows:
        step_id = r.get("step_id", "?")
        completed = r.get("completed_at")
        date_str = str(completed)[:10] if completed else "—"
        meta = r.get("meta") or {}
        meta_str = " | ".join(
            f"{k}={str(v)[:80]}" for k, v in meta.items() if v not in (None, "")
        ) if isinstance(meta, dict) else ""
        lines.append(f"- {step_id} ({date_str})" + (f": {meta_str}" if meta_str else ""))
    return "\n".join(lines)


_ADVISOR_MAX_TOKENS = 3000  # Flash thinking budget + 4-5 paragraf çıktı yastık
_ADVISOR_EMPTY_SUMMARY = (
    "Bu projede tamamlanmış adım bulunmadığı için akademik özet üretilemedi. "
    "Lütfen önce zorunlu adımları tamamlayın."
)


async def summarize_advisor(
    user_id: UUID,
    project_id: UUID,
    publication_type: PublicationType,
) -> AdvisorSummaryResponse:
    """POST /api/workshop/advisor-summary — Gemini Flash ile 4-5 paragraf
    akademik özet (5.1_yayin_formati.rtf §Plan-Detayı (3))."""
    completed_meta = await fetch_completed_step_meta(user_id, project_id)

    if not completed_meta:
        return AdvisorSummaryResponse(
            summary=_ADVISOR_EMPTY_SUMMARY,
            publication_type=publication_type,
            step_count_used=0,
            cache_hit=False,
        )

    body = (
        f"Yayın türü: {publication_type}\n\n"
        "Tamamlanan adımlar (eski → yeni):\n"
        + _format_step_block(
            [
                {
                    "step_id": m["step_id"],
                    "meta": m["meta"],
                    "completed_at": (
                        m["completed_at"].isoformat()
                        if m["completed_at"] is not None
                        else None
                    ),
                }
                for m in completed_meta
            ]
        )
    )

    llm_resp = await llm_call(
        prompt=body,
        tier="flash",
        mode="advisor_summary",
        max_tokens=_ADVISOR_MAX_TOKENS,
    )
    return AdvisorSummaryResponse(
        summary=llm_resp.text.strip(),
        publication_type=publication_type,
        step_count_used=len(completed_meta),
        cache_hit=False,
    )
