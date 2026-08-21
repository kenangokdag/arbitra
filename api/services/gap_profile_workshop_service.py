"""F13-S11 4.2 Atölye Boşluk Profili — service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTF:  Page_Design/Sayfa_Plani_v2/4.2_bosluk_profili.rtf §Plan-Detayı

GET /api/workshop/gap/{matrix_id}/{axis_x}/{axis_y}

Mevcut /api/gap-profile cell + trend döner; bu yeni endpoint AYRICA:
  - 7-boyut radar (wir/wts/wd/q_weak/cd_5/beauty/pagerank), cell vs corpus
  - Top-3 paper (Standart Yayın Kartı)
  - Komşu hücre tablosu (top-4 neighbor)
  - Venue distribution → journal önerisi
  - LLM hikaye (Flash, 3-5 cümle)

Hücre paper'ları: M1 için fact_paper_topic.theme_id=axis_x ∩ fact_paper_metod.metod_id=axis_y.
"""

from __future__ import annotations

import asyncio
import logging
import statistics
from collections import Counter
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.workshop_analytics import (
    GapCellMeta,
    GapProfileWorkshopResponse,
    GapStoryLLMOutput,
    GapTopPaper,
    JournalSuggestion,
    NeighborCell,
    RadarPoint,
    SparklinePoint,
)
from api.services.llm_service import LLMServiceError
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_TOP_PAPERS = 3
_NEIGHBORS = 4
_JOURNALS = 5
_SPARKLINE_YEARS = 10
_CELL_PAPER_LIMIT = 200
_CORPUS_BASELINE_FALLBACK = 0.5
_DIMENSIONS = ("wir", "wts", "wd", "q_weak", "cd_5", "b", "pagerank")


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
        .select(
            "matrix_id,axis_x,axis_y,depth,depth_norm,neighbor,e_value,"
            "feasibility,publishability,gap_value,matrix_confidence_calibrated"
        )
        .eq("matrix_id", matrix_id)
        .eq("axis_x", axis_x)
        .eq("axis_y", axis_y)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return rows[0] if rows else None


def _fetch_cell_paper_ids(axis_x: str, axis_y: str) -> list[str]:
    """M1: axis_x=theme_id ∩ axis_y=metod_id."""
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


def _avg(values: list[float]) -> float | None:
    clean = [v for v in values if v is not None]
    return statistics.fmean(clean) if clean else None


def _fetch_w_estra(paper_ids: list[str]) -> dict[str, list[float]]:
    if not paper_ids:
        return {"wir": [], "wts": [], "wd": []}
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_w_estra")
        .select("paper_id,wir,wts,wd")
        .in_("paper_id", paper_ids)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    out: dict[str, list[float]] = {"wir": [], "wts": [], "wd": []}
    for r in rows:
        for k in out:
            v = r.get(k)
            if isinstance(v, int | float):
                out[k].append(float(v))
    return out


def _fetch_quality(paper_ids: list[str]) -> list[float]:
    if not paper_ids:
        return []
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_quality_v3")
        .select("paper_id,q_weak")
        .in_("paper_id", paper_ids)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return [float(r["q_weak"]) for r in rows if isinstance(r.get("q_weak"), int | float)]


def _fetch_disruption_avg(paper_ids: list[str]) -> list[float]:
    if not paper_ids:
        return []
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_disruption")
        .select("paper_id,cd_5,cd_undefined")
        .in_("paper_id", paper_ids)
        .eq("cd_undefined", False)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return [float(r["cd_5"]) for r in rows if isinstance(r.get("cd_5"), int | float)]


def _fetch_beauty_avg(paper_ids: list[str]) -> list[float]:
    if not paper_ids:
        return []
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_beauty")
        .select("paper_id,b,b_undefined")
        .in_("paper_id", paper_ids)
        .eq("b_undefined", False)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return [float(r["b"]) for r in rows if isinstance(r.get("b"), int | float)]


def _fetch_centrality(paper_ids: list[str]) -> list[float]:
    if not paper_ids:
        return []
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_centrality")
        .select("paper_id,pagerank")
        .in_("paper_id", paper_ids)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return [
        float(r["pagerank"])
        for r in rows
        if isinstance(r.get("pagerank"), int | float)
    ]


def _fetch_affinity(metod_id: str, theme_id: str) -> dict[str, float | None]:
    client = get_supabase_admin()
    resp = (
        client.table("fact_method_topic_affinity")
        .select("mean_centrality,mean_q_weak")
        .eq("metod_id", metod_id)
        .eq("theme_id", theme_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        return {"mean_centrality": None, "mean_q_weak": None}
    r = rows[0]
    return {
        "mean_centrality": (
            float(r["mean_centrality"])
            if isinstance(r.get("mean_centrality"), int | float)
            else None
        ),
        "mean_q_weak": (
            float(r["mean_q_weak"])
            if isinstance(r.get("mean_q_weak"), int | float)
            else None
        ),
    }


def _fetch_paper_meta_full(
    paper_ids: list[str],
) -> dict[str, dict[str, Any]]:
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


def _fetch_sparkline_years(paper_ids: list[str]) -> list[int]:
    if not paper_ids:
        return []
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_id_card")
        .select("year")
        .in_("paper_id", paper_ids)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return [int(r["year"]) for r in rows if isinstance(r.get("year"), int)]


def _fetch_neighbors(
    matrix_id: str, axis_x: str, axis_y: str
) -> list[NeighborCell]:
    client = get_supabase_admin()
    resp = (
        client.table("fact_gap_matrix")
        .select("axis_x,axis_y,gap_value,depth_norm,neighbor")
        .eq("matrix_id", matrix_id)
        .order("neighbor", desc=True)
        .limit(20)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    out: list[NeighborCell] = []
    for r in rows:
        if r.get("axis_x") == axis_x and r.get("axis_y") == axis_y:
            continue
        out.append(
            NeighborCell(
                axis_x=str(r["axis_x"]),
                axis_y=str(r["axis_y"]),
                gap_value=float(r.get("gap_value") or 0.0),
                depth_norm=float(r.get("depth_norm") or 0.0),
            )
        )
        if len(out) >= _NEIGHBORS:
            break
    return out


def _top3_paper_rows(
    paper_ids: list[str],
) -> list[tuple[str, float | None]]:
    """En yüksek q_weak'lı 3 paper."""
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


def _sparkline(years: list[int], window: int) -> list[SparklinePoint]:
    current = datetime.now(UTC).year
    ymin = current - window + 1
    counts: dict[int, int] = dict.fromkeys(range(ymin, current + 1), 0)
    for y in years:
        if ymin <= y <= current:
            counts[y] += 1
    return [
        SparklinePoint(year=y, paper_count=c) for y, c in sorted(counts.items())
    ]


def _radar(
    cell_w_estra: dict[str, list[float]],
    cell_q: list[float],
    cell_cd: list[float],
    cell_b: list[float],
    cell_pr: list[float],
    affinity: dict[str, float | None],
) -> list[RadarPoint]:
    cell_values: dict[str, float | None] = {
        "wir": _avg(cell_w_estra["wir"]),
        "wts": _avg(cell_w_estra["wts"]),
        "wd": _avg(cell_w_estra["wd"]),
        "q_weak": _avg(cell_q),
        "cd_5": _avg(cell_cd),
        "b": _avg(cell_b),
        "pagerank": _avg(cell_pr),
    }
    corpus_values: dict[str, float | None] = dict.fromkeys(_DIMENSIONS)
    if affinity.get("mean_q_weak") is not None:
        corpus_values["q_weak"] = affinity["mean_q_weak"]
    if affinity.get("mean_centrality") is not None:
        corpus_values["pagerank"] = affinity["mean_centrality"]
    out: list[RadarPoint] = []
    for dim in _DIMENSIONS:
        out.append(
            RadarPoint(
                dimension=dim,
                cell_value=cell_values.get(dim) or 0.0,
                corpus_value=corpus_values.get(dim) or _CORPUS_BASELINE_FALLBACK,
            )
        )
    return out


def _journals_from_papers(rows: list[dict[str, Any]]) -> list[JournalSuggestion]:
    counter: Counter[str] = Counter()
    for r in rows:
        v = r.get("venue")
        if isinstance(v, str) and v.strip():
            counter[v.strip()] += 1
    return [
        JournalSuggestion(venue=venue, paper_count=count)
        for venue, count in counter.most_common(_JOURNALS)
    ]


async def _llm_story(
    cell_meta: GapCellMeta,
    radar: list[RadarPoint],
    sparkline: list[SparklinePoint],
    journals: list[JournalSuggestion],
) -> str | None:
    prompt = (
        "Aşağıdaki gap profili sinyallerine bakarak Türkçe 3-5 cümle akademik bir "
        "hikaye yaz. Ham skor değil, anlam çıkar.\n\n"
        f"Hücre: {cell_meta.matrix_id} · axis_x={cell_meta.axis_x} · axis_y={cell_meta.axis_y}\n"
        f"gap_value={cell_meta.gap_value:.3f} · depth={cell_meta.depth} · "
        f"depth_norm={cell_meta.depth_norm:.3f}\n"
        f"neighbor={cell_meta.neighbor:.3f} · feasibility={cell_meta.feasibility:.3f} · "
        f"publishability={cell_meta.publishability:.3f}\n"
        "Radar (cell vs corpus):\n"
        + "\n".join(
            f"  {p.dimension}: cell={p.cell_value:.3f} corpus={p.corpus_value:.3f}"
            for p in radar
        )
        + "\n"
        f"Yıllık paper sayısı (son {len(sparkline)} yıl): "
        f"{[p.paper_count for p in sparkline]}\n"
        f"Top venue: {[j.venue for j in journals[:3]]}\n\n"
        'Çıktı SADECE JSON: {"story": str}'
    )
    try:
        resp = await llm_call(
            prompt,
            tier="flash",
            mode="gap_profile_story",
            structured_output_schema=GapStoryLLMOutput,
            max_tokens=500,
        )
    except LLMServiceError:
        logger.exception("gap_profile_story LLM call failed")
        return None
    parsed = resp.parsed_output
    if isinstance(parsed, GapStoryLLMOutput):
        return parsed.story
    return None


async def fetch_gap_profile(
    user_id: UUID,
    project_id: UUID,
    matrix_id: str,
    axis_x: str,
    axis_y: str,
) -> GapProfileWorkshopResponse:
    """4.2 atölye gap profili orchestration."""
    await supabase_call_async(
        lambda: _check_ownership(project_id, user_id), timeout=8.0
    )

    cell_row = await supabase_call_async(
        lambda: _fetch_cell(matrix_id, axis_x, axis_y), timeout=10.0
    )
    if cell_row is None:
        raise LookupError("gap_cell_not_found")

    cell_meta = GapCellMeta(
        matrix_id=str(cell_row["matrix_id"]),
        axis_x=str(cell_row["axis_x"]),
        axis_y=str(cell_row["axis_y"]),
        gap_value=float(cell_row.get("gap_value") or 0.0),
        depth=cell_row.get("depth"),
        depth_norm=float(cell_row.get("depth_norm") or 0.0),
        neighbor=float(cell_row.get("neighbor") or 0.0),
        e_value=float(cell_row.get("e_value") or 0.0),
        feasibility=float(cell_row.get("feasibility") or 0.0),
        publishability=float(cell_row.get("publishability") or 0.0),
        matrix_confidence_calibrated=(
            float(cell_row["matrix_confidence_calibrated"])
            if isinstance(
                cell_row.get("matrix_confidence_calibrated"), int | float
            )
            else None
        ),
    )

    cell_papers = await supabase_call_async(
        lambda: _fetch_cell_paper_ids(axis_x, axis_y), timeout=12.0
    )

    w_estra_task = supabase_call_async(
        lambda: _fetch_w_estra(cell_papers), timeout=12.0
    )
    quality_task = supabase_call_async(
        lambda: _fetch_quality(cell_papers), timeout=12.0
    )
    disruption_task = supabase_call_async(
        lambda: _fetch_disruption_avg(cell_papers), timeout=12.0
    )
    beauty_task = supabase_call_async(
        lambda: _fetch_beauty_avg(cell_papers), timeout=12.0
    )
    centrality_task = supabase_call_async(
        lambda: _fetch_centrality(cell_papers), timeout=12.0
    )
    affinity_task = supabase_call_async(
        lambda: _fetch_affinity(axis_y, axis_x), timeout=10.0
    )
    sparkline_years_task = supabase_call_async(
        lambda: _fetch_sparkline_years(cell_papers), timeout=10.0
    )
    neighbors_task = supabase_call_async(
        lambda: _fetch_neighbors(matrix_id, axis_x, axis_y), timeout=10.0
    )
    top3_task = supabase_call_async(
        lambda: _top3_paper_rows(cell_papers), timeout=10.0
    )

    results = await asyncio.gather(
        w_estra_task,
        quality_task,
        disruption_task,
        beauty_task,
        centrality_task,
        affinity_task,
        sparkline_years_task,
        neighbors_task,
        top3_task,
    )
    w_estra_dim = cast(dict[str, list[float]], results[0])
    cell_q = cast(list[float], results[1])
    cell_cd = cast(list[float], results[2])
    cell_b = cast(list[float], results[3])
    cell_pr = cast(list[float], results[4])
    affinity = cast(dict[str, float | None], results[5])
    spark_years = cast(list[int], results[6])
    neighbors = cast(list[NeighborCell], results[7])
    top3_rows = cast(list[tuple[str, float | None]], results[8])

    radar = _radar(w_estra_dim, cell_q, cell_cd, cell_b, cell_pr, affinity)
    sparkline = _sparkline(spark_years, _SPARKLINE_YEARS)

    top3_ids = [pid for pid, _ in top3_rows]
    paper_meta = await supabase_call_async(
        lambda: _fetch_paper_meta_full(top3_ids), timeout=10.0
    )
    top_papers = [
        GapTopPaper(
            paper_id=pid,
            title=paper_meta.get(pid, {}).get("title"),
            year=paper_meta.get(pid, {}).get("year"),
            venue=paper_meta.get(pid, {}).get("venue"),
            q_weak=q,
        )
        for pid, q in top3_rows
    ]

    venue_pool_ids = cell_papers[:200]
    venue_meta = await supabase_call_async(
        lambda: _fetch_paper_meta_full(venue_pool_ids), timeout=12.0
    )
    journals = _journals_from_papers(list(venue_meta.values()))

    story = await _llm_story(cell_meta, radar, sparkline, journals)

    return GapProfileWorkshopResponse(
        cell_meta=cell_meta,
        radar_7d=radar,
        sparkline=sparkline,
        neighbors=neighbors,
        journals=journals,
        top_papers=top_papers,
        story=story,
    )


__all__ = ["fetch_gap_profile"]
