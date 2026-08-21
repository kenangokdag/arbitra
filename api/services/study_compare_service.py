"""F13-S11 4.4 Çalışma Karşılaştırma — service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTF:  Page_Design/Sayfa_Plani_v2/4.4_calisma_karsilastirma.rtf §Plan-Detayı

POST /api/workshop/compare
  body: { project_id, gap_cells: [{matrix_id,axis_x,axis_y}], weights }

5 eksen (RTF §Plan-Detayı (1) compound formüller):
  Risk        = (1 - depth_norm) * neighbor
  Disruption  = AVG(cd_5)
  Virgin      = (1 - depth_norm) * (1 - AVG(q_weak))
  Sleeping Beauty oranı = COUNT(b > threshold) / COUNT(*)
  Publishability = fact_gap_matrix.publishability

Tüm formüller [0,1] clip; ağırlık normalize; LLM "Hangisini önereyim?" Flash.
"""

from __future__ import annotations

import asyncio
import json
import logging
import statistics
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.workshop_analytics import (
    CompareGapRow,
    CompareRecommendationLLMOutput,
    CompareRequest,
    CompareResponse,
    GapAxisScores,
    GapCellRef,
    GapTopPaper,
)
from api.services.llm_service import LLMServiceError
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_CELL_PAPER_LIMIT = 200
_TOP_PAPERS = 3
_CALIBRATION_DIR = Path(__file__).resolve().parents[2] / "engine" / "calibration"


def _load_json(p: Path) -> dict[str, Any]:
    with p.open(encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def _check_ownership(project_id: UUID, user_id: UUID) -> None:
    client = get_supabase_admin()
    resp = (
        client.table("projects")
        .select("id,user_id")
        .eq("id", str(project_id))
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        raise LookupError("project_not_found")
    if str(rows[0].get("user_id")) != str(user_id):
        raise PermissionError("project_not_owned")


def _fetch_cell(matrix_id: str, axis_x: str, axis_y: str) -> dict[str, Any] | None:
    client = get_supabase_admin()
    resp = (
        client.table("fact_gap_matrix")
        .select("axis_x,axis_y,depth_norm,neighbor,publishability,gap_value")
        .eq("matrix_id", matrix_id)
        .eq("axis_x", axis_x)
        .eq("axis_y", axis_y)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return rows[0] if rows else None


def _fetch_cell_paper_ids(axis_x: str, axis_y: str) -> list[str]:
    client = get_supabase_admin()
    topic_resp = (
        client.table("fact_paper_topic")
        .select("paper_id")
        .eq("theme_id", axis_x)
        .limit(_CELL_PAPER_LIMIT * 10)
        .execute()
    )
    metod_resp = (
        client.table("fact_paper_metod")
        .select("paper_id")
        .eq("metod_id", axis_y)
        .limit(_CELL_PAPER_LIMIT * 10)
        .execute()
    )
    topic_ids = {
        str(r["paper_id"])
        for r in cast(list[dict[str, Any]], topic_resp.data or [])
        if r.get("paper_id")
    }
    metod_ids = {
        str(r["paper_id"])
        for r in cast(list[dict[str, Any]], metod_resp.data or [])
        if r.get("paper_id")
    }
    return list(topic_ids & metod_ids)[:_CELL_PAPER_LIMIT]


def _avg(values: list[float]) -> float:
    clean = [v for v in values if isinstance(v, int | float)]
    return statistics.fmean(clean) if clean else 0.0


def _fetch_quality_avg(paper_ids: list[str]) -> float:
    if not paper_ids:
        return 0.0
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_quality_v3")
        .select("q_weak")
        .in_("paper_id", paper_ids)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return _avg([float(r["q_weak"]) for r in rows if r.get("q_weak") is not None])


def _fetch_disruption_avg(paper_ids: list[str]) -> float:
    if not paper_ids:
        return 0.0
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_disruption")
        .select("cd_5,cd_undefined")
        .in_("paper_id", paper_ids)
        .eq("cd_undefined", False)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return _avg([float(r["cd_5"]) for r in rows if r.get("cd_5") is not None])


def _fetch_beauty_ratio(paper_ids: list[str], threshold: float) -> float:
    if not paper_ids:
        return 0.0
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_beauty")
        .select("b,b_undefined")
        .in_("paper_id", paper_ids)
        .eq("b_undefined", False)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    valid = [float(r["b"]) for r in rows if isinstance(r.get("b"), int | float)]
    if not valid:
        return 0.0
    over = sum(1 for b in valid if b > threshold)
    return over / len(valid)


def _fetch_top3_paper_rows(
    paper_ids: list[str],
) -> list[tuple[str, float | None]]:
    if not paper_ids:
        return []
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_quality_v3")
        .select("paper_id,q_weak")
        .in_("paper_id", paper_ids)
        .order("q_weak", desc=True)
        .limit(_TOP_PAPERS)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return [
        (
            str(r["paper_id"]),
            float(r["q_weak"]) if isinstance(r.get("q_weak"), int | float) else None,
        )
        for r in rows
        if r.get("paper_id")
    ]


def _fetch_paper_meta(paper_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not paper_ids:
        return {}
    client = get_supabase_admin()
    resp = (
        client.table("papers")
        .select("paper_id,title,year,venue")
        .in_("paper_id", paper_ids)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return {str(r["paper_id"]): r for r in rows if r.get("paper_id")}


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def _disruption_to_unit(cd_avg: float) -> float:
    """RTF: cd_5 ∈ [-1,1] tipik; (cd+1)/2 ile [0,1]'e map."""
    return _clip((cd_avg + 1.0) / 2.0)


async def _compute_cell_row(
    ref: GapCellRef,
    beauty_thr: float,
) -> tuple[CompareGapRow, list[str]] | None:
    """Tek hücre için 5 eksen + top-3 paper. None → hücre yok."""
    cell = await supabase_call_async(
        lambda: _fetch_cell(ref.matrix_id, ref.axis_x, ref.axis_y),
        timeout=10.0,
    )
    if cell is None:
        return None

    cell_papers = await supabase_call_async(
        lambda: _fetch_cell_paper_ids(ref.axis_x, ref.axis_y),
        timeout=12.0,
    )
    q_task = supabase_call_async(
        lambda: _fetch_quality_avg(cell_papers), timeout=12.0
    )
    cd_task = supabase_call_async(
        lambda: _fetch_disruption_avg(cell_papers), timeout=12.0
    )
    beauty_task = supabase_call_async(
        lambda: _fetch_beauty_ratio(cell_papers, beauty_thr), timeout=12.0
    )
    top3_task = supabase_call_async(
        lambda: _fetch_top3_paper_rows(cell_papers), timeout=10.0
    )
    q_avg, cd_avg, beauty_ratio, top3_rows = await asyncio.gather(
        q_task, cd_task, beauty_task, top3_task
    )

    depth_norm = float(cell.get("depth_norm") or 0.0)
    neighbor = float(cell.get("neighbor") or 0.0)
    publishability = float(cell.get("publishability") or 0.0)

    risk = _clip((1.0 - depth_norm) * neighbor)
    virgin = _clip((1.0 - depth_norm) * (1.0 - q_avg))
    disruption = _disruption_to_unit(cd_avg)

    top3_ids = [pid for pid, _ in top3_rows]
    meta = await supabase_call_async(
        lambda: _fetch_paper_meta(top3_ids), timeout=10.0
    )
    top_papers = [
        GapTopPaper(
            paper_id=pid,
            title=meta.get(pid, {}).get("title"),
            year=meta.get(pid, {}).get("year"),
            venue=meta.get(pid, {}).get("venue"),
            q_weak=q,
        )
        for pid, q in top3_rows
    ]

    return (
        CompareGapRow(
            cell=ref,
            axes=GapAxisScores(
                risk=round(risk, 4),
                disruption=round(disruption, 4),
                virgin=round(virgin, 4),
                sleeping_beauty=round(_clip(beauty_ratio), 4),
                publishability=round(_clip(publishability), 4),
            ),
            weighted_score=0.0,
            top_papers=top_papers,
        ),
        top3_ids,
    )


def _normalize_weights(w: Any) -> dict[str, float]:
    """Sum=1 normalize; tüm ağırlık 0 ise eşit (0.2 her biri)."""
    raw = {
        "risk": float(w.risk),
        "disruption": float(w.disruption),
        "virgin": float(w.virgin),
        "sleeping_beauty": float(w.sleeping_beauty),
        "publishability": float(w.publishability),
    }
    total = sum(raw.values())
    if total <= 0:
        return dict.fromkeys(raw, 0.2)
    return {k: v / total for k, v in raw.items()}


def _weighted(axes: GapAxisScores, weights: dict[str, float]) -> float:
    return round(
        axes.risk * weights["risk"]
        + axes.disruption * weights["disruption"]
        + axes.virgin * weights["virgin"]
        + axes.sleeping_beauty * weights["sleeping_beauty"]
        + axes.publishability * weights["publishability"],
        4,
    )


async def _llm_recommendation(
    gaps: list[CompareGapRow], normalized_weights: dict[str, float]
) -> str | None:
    rows_txt = "\n".join(
        f"- Gap-{i + 1} ({g.cell.matrix_id} {g.cell.axis_x}×{g.cell.axis_y}) "
        f"risk={g.axes.risk:.3f} disruption={g.axes.disruption:.3f} "
        f"virgin={g.axes.virgin:.3f} sb={g.axes.sleeping_beauty:.3f} "
        f"pub={g.axes.publishability:.3f} weighted={g.weighted_score:.3f}"
        for i, g in enumerate(gaps)
    )
    weights_txt = ", ".join(
        f"{k}=%{round(v * 100)}" for k, v in normalized_weights.items()
    )
    prompt = (
        "Aşağıdaki 2-5 gap hücresinin 5 eksen skoru + kullanıcı ağırlıkları "
        "verildi. Türkçe 1 paragraf 'Hangisini önereyim?' yön gösterici akademik "
        "tavsiye yaz.\n\n"
        f"Kullanıcı ağırlıkları (normalize): {weights_txt}\n"
        f"Gaps:\n{rows_txt}\n\n"
        'Çıktı SADECE JSON: {"recommendation_text": str}'
    )
    try:
        resp = await llm_call(
            prompt,
            tier="flash",
            mode="study_compare_advice",
            structured_output_schema=CompareRecommendationLLMOutput,
            max_tokens=500,
        )
    except LLMServiceError:
        logger.exception("study_compare_advice LLM call failed")
        return None
    parsed = resp.parsed_output
    if isinstance(parsed, CompareRecommendationLLMOutput):
        return parsed.recommendation_text
    return None


async def compare_gaps(user_id: UUID, req: CompareRequest) -> CompareResponse:
    """4.4 atölye karşılaştırma orchestration."""
    await supabase_call_async(
        lambda: _check_ownership(req.project_id, user_id), timeout=8.0
    )
    originality_thr = _load_json(
        _CALIBRATION_DIR / "originality_thresholds.json"
    )
    beauty_thr = float(originality_thr["sleeping_beauty"]["b_threshold"])

    rows_results = await asyncio.gather(
        *(_compute_cell_row(ref, beauty_thr) for ref in req.gap_cells)
    )
    rows = [r[0] for r in rows_results if r is not None]
    if len(rows) < 2:
        raise LookupError("compare_needs_min_2_valid_cells")

    weights = _normalize_weights(req.weights)
    for r in rows:
        r.weighted_score = _weighted(r.axes, weights)

    recommendation = await _llm_recommendation(rows, weights)

    return CompareResponse(
        gaps=rows,
        weights=req.weights,
        recommendation_text=recommendation,
    )


__all__ = ["compare_gaps"]
