"""F13-S11 4.3 Özgünlük Değerlendirme — service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTF:  Page_Design/Sayfa_Plani_v2/4.3_ozgunluk_degerlendirmesi.rtf §Plan-Detayı

GET /api/workshop/originality?project_id=&type=&year_from=&year_to=&theme_id=

Akış:
  1. Proje sahipliği doğrula
  2. project_cluster.paper_id → proje havuzu (rank_final IS NOT NULL)
  3. type=disruption → fact_paper_disruption WHERE cd_5 > config.cd_5_threshold
     type=sleeping_beauty → fact_paper_beauty WHERE b > config.b_threshold
  4. theme_id filtresi → fact_paper_topic JOIN
  5. year_from/year_to → fact_paper_id_card.year filtre
  6. ORDER BY cd_5/b DESC, LIMIT 50
  7. papers JOIN title/year/venue
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.workshop_analytics import (
    OriginalityPaper,
    OriginalityResponse,
    OriginalityType,
)

logger = logging.getLogger(__name__)

_LIMIT = 50
_THRESHOLDS_PATH = (
    Path(__file__).resolve().parents[2]
    / "engine"
    / "calibration"
    / "originality_thresholds.json"
)


def _load_thresholds() -> dict[str, Any]:
    """RTF 4.3 §Plan-Detayı (1) — kalibre eşik yoksa placeholder JSON."""
    with _THRESHOLDS_PATH.open(encoding="utf-8") as f:
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


def _fetch_project_pool(project_id: UUID) -> list[str]:
    client = get_supabase_admin()
    resp = (
        client.table("project_cluster")
        .select("paper_id")
        .eq("project_id", str(project_id))
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return [str(r["paper_id"]) for r in rows if r.get("paper_id")]


def _fetch_disruption(
    paper_ids: list[str], threshold: float
) -> list[dict[str, Any]]:
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_disruption")
        .select(
            "paper_id,pub_year,n_a,n_i,n_j,total_window_papers,cd_5,cd_undefined"
        )
        .in_("paper_id", paper_ids)
        .gt("cd_5", threshold)
        .eq("cd_undefined", False)
        .order("cd_5", desc=True)
        .limit(_LIMIT)
        .execute()
    )
    return cast(list[dict[str, Any]], resp.data or [])


def _fetch_beauty(
    paper_ids: list[str], threshold: float
) -> list[dict[str, Any]]:
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_beauty")
        .select("paper_id,pub_year,c_max,t_m,total_cites,b,b_undefined")
        .in_("paper_id", paper_ids)
        .gt("b", threshold)
        .eq("b_undefined", False)
        .order("b", desc=True)
        .limit(_LIMIT)
        .execute()
    )
    return cast(list[dict[str, Any]], resp.data or [])


def _fetch_theme_paper_ids(paper_ids: list[str], theme_id: str) -> set[str]:
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_topic")
        .select("paper_id")
        .in_("paper_id", paper_ids)
        .eq("theme_id", theme_id)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return {str(r["paper_id"]) for r in rows if r.get("paper_id")}


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


def _within_year(
    row: dict[str, Any],
    year_from: int | None,
    year_to: int | None,
) -> bool:
    yr = row.get("pub_year")
    if not isinstance(yr, int):
        return year_from is None and year_to is None
    if year_from is not None and yr < year_from:
        return False
    return not (year_to is not None and yr > year_to)


def _build_disruption_paper(
    fact: dict[str, Any], meta: dict[str, Any]
) -> OriginalityPaper:
    return OriginalityPaper(
        paper_id=str(fact["paper_id"]),
        title=meta.get("title"),
        year=fact.get("pub_year") or meta.get("year"),
        venue=meta.get("venue"),
        cd_5=float(fact["cd_5"]) if fact.get("cd_5") is not None else None,
        n_a=int(fact["n_a"]) if fact.get("n_a") is not None else None,
        n_i=int(fact["n_i"]) if fact.get("n_i") is not None else None,
        n_j=int(fact["n_j"]) if fact.get("n_j") is not None else None,
        total_window_papers=(
            int(fact["total_window_papers"])
            if fact.get("total_window_papers") is not None
            else None
        ),
    )


def _build_beauty_paper(
    fact: dict[str, Any], meta: dict[str, Any]
) -> OriginalityPaper:
    return OriginalityPaper(
        paper_id=str(fact["paper_id"]),
        title=meta.get("title"),
        year=fact.get("pub_year") or meta.get("year"),
        venue=meta.get("venue"),
        b=float(fact["b"]) if fact.get("b") is not None else None,
        t_m=int(fact["t_m"]) if fact.get("t_m") is not None else None,
        c_max=int(fact["c_max"]) if fact.get("c_max") is not None else None,
        total_cites=(
            int(fact["total_cites"])
            if fact.get("total_cites") is not None
            else None
        ),
    )


async def fetch_originality(
    user_id: UUID,
    project_id: UUID,
    origin_type: OriginalityType,
    year_from: int | None,
    year_to: int | None,
    theme_id: str | None,
) -> OriginalityResponse:
    """Atölye 4.3 — yıkıcı veya sleeping beauty paper listesi."""
    await supabase_call_async(
        lambda: _check_ownership(project_id, user_id), timeout=8.0
    )
    pool = await supabase_call_async(
        lambda: _fetch_project_pool(project_id), timeout=10.0
    )
    if not pool:
        thresholds = _load_thresholds()
        thr = (
            thresholds["disruption"]["cd_5_threshold"]
            if origin_type == "disruption"
            else thresholds["sleeping_beauty"]["b_threshold"]
        )
        return OriginalityResponse(
            type=origin_type,
            papers=[],
            threshold_used=float(thr),
            threshold_source=thresholds["version"],
            pool_size=0,
        )

    if theme_id is not None:
        keep = await supabase_call_async(
            lambda: _fetch_theme_paper_ids(pool, theme_id), timeout=10.0
        )
        pool = [pid for pid in pool if pid in keep]
    if not pool:
        thresholds = _load_thresholds()
        thr = (
            thresholds["disruption"]["cd_5_threshold"]
            if origin_type == "disruption"
            else thresholds["sleeping_beauty"]["b_threshold"]
        )
        return OriginalityResponse(
            type=origin_type,
            papers=[],
            threshold_used=float(thr),
            threshold_source=thresholds["version"],
            pool_size=0,
        )

    thresholds = _load_thresholds()
    if origin_type == "disruption":
        cd_thr = float(thresholds["disruption"]["cd_5_threshold"])
        facts = await supabase_call_async(
            lambda: _fetch_disruption(pool, cd_thr), timeout=12.0
        )
        threshold_used = cd_thr
    else:
        b_thr = float(thresholds["sleeping_beauty"]["b_threshold"])
        facts = await supabase_call_async(
            lambda: _fetch_beauty(pool, b_thr), timeout=12.0
        )
        threshold_used = b_thr

    facts_filtered = [f for f in facts if _within_year(f, year_from, year_to)]
    fact_ids = [str(f["paper_id"]) for f in facts_filtered]
    meta_map = await supabase_call_async(
        lambda: _fetch_paper_meta(fact_ids), timeout=10.0
    )

    builder = (
        _build_disruption_paper
        if origin_type == "disruption"
        else _build_beauty_paper
    )
    papers = [builder(f, meta_map.get(str(f["paper_id"]), {})) for f in facts_filtered]

    return OriginalityResponse(
        type=origin_type,
        papers=papers,
        threshold_used=threshold_used,
        threshold_source=str(thresholds["version"]),
        pool_size=len(pool),
    )


__all__ = ["fetch_originality"]
