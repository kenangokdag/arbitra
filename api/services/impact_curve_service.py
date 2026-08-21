"""F13-S11 4.5 Akademik Etki Eğrisi — service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTF:  Page_Design/Sayfa_Plani_v2/4.5_akademik_etki_egrisi.rtf §Plan-Detayı

GET /api/workshop/impact-curve?project_id=&dimension=&value=&years=

Akış:
  1. Proje sahipliği doğrula
  2. dimension=topic → fact_paper_topic WHERE theme_id=value
     dimension=method → fact_paper_metod WHERE metod_id=value
     dimension=keyword → V1 desteklenmiyor (papers.keywords yok)
  3. fact_paper_id_card.year ile yıllık COUNT(*) son N yıl
  4. ★ noktalar: project_pool ∩ fact_paper_disruption WHERE cd_5 > threshold
  5. ♦ noktalar: project_pool ∩ fact_paper_beauty WHERE b > threshold
  6. Pytrends fallback (V1: kütüphane kurulu değil → trends_available=False)
  7. Momentum hesap: akademik slope (% / yıl)
  8. Gemini Flash 1-cümle yorum (best-effort)
"""

from __future__ import annotations

import json
import logging
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.workshop_analytics import (
    BeautyPoint,
    ImpactCurveLLMOutput,
    ImpactCurveResponse,
    ImpactDimension,
    ImpactPoint,
    MomentumColor,
    StarPoint,
)
from api.services.llm_service import LLMServiceError
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_TRENDS_AVAILABLE = False  # V1: Pytrends pyproject'te yok; RTF fallback aktif
_THRESHOLDS_DIR = Path(__file__).resolve().parents[2] / "engine" / "calibration"
_ORIG_PATH = _THRESHOLDS_DIR / "originality_thresholds.json"
_MOM_PATH = _THRESHOLDS_DIR / "momentum_thresholds.json"


def _load(p: Path) -> dict[str, Any]:
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


def _fetch_dim_paper_ids(dimension: ImpactDimension, value: str) -> list[str]:
    client = get_supabase_admin()
    if dimension == "topic":
        resp = (
            client.table("fact_paper_topic")
            .select("paper_id")
            .eq("theme_id", value)
            .execute()
        )
    elif dimension == "method":
        resp = (
            client.table("fact_paper_metod")
            .select("paper_id")
            .eq("metod_id", value)
            .execute()
        )
    else:
        raise ValueError("dimension_keyword_unsupported_v1")
    rows = cast(list[dict[str, Any]], resp.data or [])
    return [str(r["paper_id"]) for r in rows if r.get("paper_id")]


def _fetch_paper_years(paper_ids: list[str]) -> list[int]:
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


def _fetch_pool_disruption(
    pool: list[str], threshold: float
) -> list[dict[str, Any]]:
    if not pool:
        return []
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_disruption")
        .select("paper_id,pub_year,cd_5,cd_undefined")
        .in_("paper_id", pool)
        .gt("cd_5", threshold)
        .eq("cd_undefined", False)
        .order("cd_5", desc=True)
        .limit(25)
        .execute()
    )
    return cast(list[dict[str, Any]], resp.data or [])


def _fetch_pool_beauty(pool: list[str], threshold: float) -> list[dict[str, Any]]:
    if not pool:
        return []
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_beauty")
        .select("paper_id,pub_year,t_m,b,b_undefined")
        .in_("paper_id", pool)
        .gt("b", threshold)
        .eq("b_undefined", False)
        .order("b", desc=True)
        .limit(25)
        .execute()
    )
    return cast(list[dict[str, Any]], resp.data or [])


def _fetch_paper_titles(paper_ids: list[str]) -> dict[str, str]:
    if not paper_ids:
        return {}
    client = get_supabase_admin()
    resp = (
        client.table("papers")
        .select("paper_id,title")
        .in_("paper_id", paper_ids)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return {
        str(r["paper_id"]): str(r.get("title") or "")
        for r in rows
        if r.get("paper_id")
    }


def _series_from_years(years: list[int], window: int) -> list[ImpactPoint]:
    current = datetime.now(UTC).year
    year_min = current - window + 1
    counts: dict[int, int] = dict.fromkeys(range(year_min, current + 1), 0)
    for y in years:
        if year_min <= y <= current:
            counts[y] += 1
    return [
        ImpactPoint(year=y, value=float(c)) for y, c in sorted(counts.items())
    ]


def _slope_pct(series: list[ImpactPoint]) -> float | None:
    """Son 5 yıl (varsa) basit linear regression → % değişim/yıl."""
    pts = series[-5:] if len(series) >= 5 else series
    if len(pts) < 2:
        return None
    xs = [float(p.year) for p in pts]
    ys = [p.value for p in pts]
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0 or mean_y <= 0:
        return None
    slope = num / den
    return round(slope / mean_y * 100, 2)


def _momentum_color(
    academic_slope_pct: float | None,
    trends_slope: float | None,
    thresholds: dict[str, Any],
) -> MomentumColor:
    a = thresholds["academic_slope"]
    t = thresholds["trends_slope"]

    def _bucket(value: float | None, green_min: float, red_max: float) -> str:
        if value is None:
            return "unknown"
        if value >= green_min:
            return "green"
        if value <= red_max:
            return "red"
        return "yellow"

    aca = _bucket(
        academic_slope_pct,
        float(a["green_min_pct_per_year"]),
        float(a["red_max_pct_per_year"]),
    )
    tre = _bucket(
        trends_slope,
        float(t["green_min_points_per_year"]),
        float(t["red_max_points_per_year"]),
    )
    if aca == "unknown" and tre == "unknown":
        return "unknown"
    if aca == "unknown":
        # Trends-only fallback bias: RTF'ye göre akademik yoksa sarı yan
        if tre == "green":
            return "yellow"
        return cast(MomentumColor, tre)
    if tre == "unknown":
        return cast(MomentumColor, aca)
    if aca == "green" and tre == "green":
        return "green"
    if aca == "red" or tre == "red":
        return "red"
    return "yellow"


async def _llm_comment(
    dimension: ImpactDimension,
    value: str,
    academic_slope_pct: float | None,
    trends_slope: float | None,
    momentum_color: MomentumColor,
    n_stars: int,
    n_beauties: int,
    trends_available: bool,
) -> str | None:
    prompt = (
        "Aşağıdaki etki eğrisi sinyallerine bakarak Türkçe TEK CÜMLE kombine yorum yaz. "
        "Akademik trend ve popüler ilgi (Trends) ekseninde karar destek ver.\n\n"
        f"Boyut: {dimension}\n"
        f"Değer: {value}\n"
        f"Akademik slope (son 5 yıl, %/yıl): "
        f"{academic_slope_pct if academic_slope_pct is not None else 'yok'}\n"
        f"Trends slope (puan/yıl): "
        f"{trends_slope if trends_slope is not None else 'yok'}\n"
        f"Trends verisi alındı: {'evet' if trends_available else 'hayır (V1 fallback)'}\n"
        f"★ Yıkıcı paper sayısı (project_pool): {n_stars}\n"
        f"♦ Sleeping Beauty paper sayısı (project_pool): {n_beauties}\n"
        f"Momentum rozet: {momentum_color}\n\n"
        'Çıktı SADECE JSON: {"comment": str}'
    )
    try:
        resp = await llm_call(
            prompt,
            tier="flash",
            mode="impact_curve_comment",
            structured_output_schema=ImpactCurveLLMOutput,
            max_tokens=300,
        )
    except LLMServiceError:
        logger.exception("impact_curve_comment LLM call failed")
        return None
    parsed = resp.parsed_output
    if isinstance(parsed, ImpactCurveLLMOutput):
        return parsed.comment
    return None


async def fetch_impact_curve(
    user_id: UUID,
    project_id: UUID,
    dimension: ImpactDimension,
    value: str,
    years: int,
) -> ImpactCurveResponse:
    """4.5 atölye etki eğrisi orchestration."""
    await supabase_call_async(
        lambda: _check_ownership(project_id, user_id), timeout=8.0
    )

    if dimension == "keyword":
        raise ValueError("dimension_keyword_unsupported_v1")

    pool = await supabase_call_async(
        lambda: _fetch_project_pool(project_id), timeout=10.0
    )
    dim_papers = await supabase_call_async(
        lambda: _fetch_dim_paper_ids(dimension, value), timeout=15.0
    )

    paper_years = await supabase_call_async(
        lambda: _fetch_paper_years(dim_papers), timeout=15.0
    )
    academic_series = _series_from_years(paper_years, years)

    thresholds_orig = _load(_ORIG_PATH)
    cd_thr = float(thresholds_orig["disruption"]["cd_5_threshold"])
    b_thr = float(thresholds_orig["sleeping_beauty"]["b_threshold"])

    pool_in_dim = [pid for pid in pool if pid in set(dim_papers)] if pool else []
    stars_raw = await supabase_call_async(
        lambda: _fetch_pool_disruption(pool_in_dim, cd_thr), timeout=12.0
    )
    beauties_raw = await supabase_call_async(
        lambda: _fetch_pool_beauty(pool_in_dim, b_thr), timeout=12.0
    )

    title_ids = list(
        {str(r["paper_id"]) for r in stars_raw + beauties_raw if r.get("paper_id")}
    )
    titles = await supabase_call_async(
        lambda: _fetch_paper_titles(title_ids), timeout=10.0
    )

    stars = [
        StarPoint(
            paper_id=str(r["paper_id"]),
            title=titles.get(str(r["paper_id"])) or None,
            year=int(r.get("pub_year") or 0),
            cd_5=float(r.get("cd_5") or 0.0),
        )
        for r in stars_raw
        if isinstance(r.get("pub_year"), int)
    ]
    beauties = [
        BeautyPoint(
            paper_id=str(r["paper_id"]),
            title=titles.get(str(r["paper_id"])) or None,
            publication_year=int(r["pub_year"]),
            awakening_year=int(r["pub_year"]) + int(r.get("t_m") or 0),
            b=float(r.get("b") or 0.0),
        )
        for r in beauties_raw
        if isinstance(r.get("pub_year"), int)
    ]

    aca_slope = _slope_pct(academic_series)
    trends_series: list[ImpactPoint] = []
    trends_slope: float | None = None
    thresholds_mom = _load(_MOM_PATH)
    color = _momentum_color(aca_slope, trends_slope, thresholds_mom)

    comment = await _llm_comment(
        dimension,
        value,
        aca_slope,
        trends_slope,
        color,
        len(stars),
        len(beauties),
        _TRENDS_AVAILABLE,
    )

    return ImpactCurveResponse(
        dimension=dimension,
        value=value,
        academic_series=academic_series,
        trends_series=trends_series,
        trends_available=_TRENDS_AVAILABLE,
        stars=stars,
        beauties=beauties,
        academic_slope_pct=aca_slope,
        trends_slope=trends_slope,
        momentum_color=color,
        llm_comment=comment,
    )


__all__ = ["fetch_impact_curve"]
