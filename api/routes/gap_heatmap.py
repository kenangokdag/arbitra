"""GET /api/gap-heatmap — fact_gap_matrix M1 (theme×method) sliced view.

Returns top-N methods × top-M themes by gap_value, joined with dim_theme labels.
Redis 1h cache (query string key).

V1-S17 P004: opsiyonel `project_id` query — set ise project_cluster paper_ids
üzerinden fact_paper_topic (theme) + fact_paper_metod (method) bridges ile
heatmap'i proje kapsamına daraltır. Bridge boşsa global sonuç döner (graceful).
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.db.redis_client import CacheNamespace, cache_get, cache_set
from api.db.supabase_client import SupabaseQueryError, get_supabase_admin, supabase_call_async
from api.utils.resilience import ResilienceTimeoutError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["gap-heatmap"])

_CACHE_TTL = 3600  # 1h — matrix data rarely changes


class MethodItem(BaseModel):
    id: str
    label: str
    family: str


class TopicItem(BaseModel):
    id: str
    label: str
    group: str


class GapCellItem(BaseModel):
    method_id: str
    topic_id: str
    n_papers: int
    gap_score: float      # [0, 1] — 1 = maximum gap
    depth_norm: float     # [0, 1] — log-normalized paper depth
    is_gold: bool         # gap_score >= 0.75


class GapHeatmapResponse(BaseModel):
    methods: list[MethodItem]
    topics: list[TopicItem]
    cells: list[GapCellItem]
    total_cells: int
    matrix_id: str


def _cache_key(
    matrix_id: str,
    top_methods: int,
    top_topics: int,
    project_id: str | None = None,
) -> str:
    raw = f"gap:{matrix_id}:{top_methods}:{top_topics}:{project_id or '_'}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _fetch_project_paper_ids(project_id: str) -> list[str]:
    """V1-S17 P004 — project_cluster paper_ids (sync, supabase_call_async ile çağrılır)."""
    client = get_supabase_admin()
    resp = (
        client.table("project_cluster")
        .select("paper_id")
        .eq("project_id", project_id)
        .execute()
    )
    rows = resp.data or []
    return [r["paper_id"] for r in rows if isinstance(r.get("paper_id"), str)]


def _fetch_project_theme_ids(paper_ids: list[str]) -> set[str]:
    """fact_paper_topic bridge → unique theme_id set (rank≤3 schema-level CHECK)."""
    if not paper_ids:
        return set()
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_topic")
        .select("theme_id")
        .in_("paper_id", paper_ids)
        .execute()
    )
    return {r["theme_id"] for r in (resp.data or []) if r.get("theme_id")}


def _fetch_project_method_ids(paper_ids: list[str]) -> set[str]:
    """fact_paper_metod bridge → unique metod_id set."""
    if not paper_ids:
        return set()
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_metod")
        .select("metod_id")
        .in_("paper_id", paper_ids)
        .execute()
    )
    return {r["metod_id"] for r in (resp.data or []) if r.get("metod_id")}


def _fetch_gap_cells(matrix_id: str, limit: int) -> list[dict]:
    """Sync: fetch top gap_value rows from fact_gap_matrix."""
    client = get_supabase_admin()
    resp = (
        client.table("fact_gap_matrix")
        .select("axis_x,axis_y,depth,depth_norm,gap_value")
        .eq("matrix_id", matrix_id)
        .order("gap_value", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def _fetch_theme_labels(theme_ids: list[str]) -> dict[str, dict]:
    """Sync: fetch name_tr + metadata.group from dim_theme for given IDs."""
    if not theme_ids:
        return {}
    client = get_supabase_admin()
    resp = (
        client.table("dim_theme")
        .select("theme_id,name_tr,metadata")
        .in_("theme_id", theme_ids)
        .execute()
    )
    result: dict[str, dict] = {}
    for row in resp.data or []:
        result[row["theme_id"]] = row
    return result


def _build_response(
    raw_cells: list[dict],
    top_methods: int,
    top_topics: int,
) -> GapHeatmapResponse:
    """Slice top_methods × top_topics from raw cells, build response."""
    # Count occurrences to find top methods and topics
    method_scores: dict[str, float] = {}
    topic_scores: dict[str, float] = {}

    for row in raw_cells:
        mx = row["axis_x"]  # theme_id
        my = row["axis_y"]  # metod_id
        gv = float(row.get("gap_value") or 0)
        method_scores[my] = max(method_scores.get(my, 0.0), gv)
        topic_scores[mx] = max(topic_scores.get(mx, 0.0), gv)

    top_method_ids = sorted(method_scores, key=lambda k: method_scores[k], reverse=True)[:top_methods]
    top_topic_ids = sorted(topic_scores, key=lambda k: topic_scores[k], reverse=True)[:top_topics]

    method_set = set(top_method_ids)
    topic_set = set(top_topic_ids)

    # Build cell dict for fast lookup
    cell_map: dict[tuple[str, str], dict] = {}
    for row in raw_cells:
        mx, my = row["axis_x"], row["axis_y"]
        if mx in topic_set and my in method_set:
            cell_map[(my, mx)] = row

    # Build MethodItem list (label = metod_id, family = first char cluster)
    method_items: list[MethodItem] = []
    for mid in top_method_ids:
        label = mid.replace("_", " ").title()
        family = _infer_method_family(mid)
        method_items.append(MethodItem(id=mid, label=label, family=family))

    # Build TopicItem list — labels from dim_theme
    topic_label_map: dict[str, dict] = {}  # filled below after supabase join; placeholder here

    topic_items: list[TopicItem] = []
    for tid in top_topic_ids:
        meta = topic_label_map.get(tid, {})
        label = meta.get("name_tr") or tid.replace("_", " ").title()
        group = (meta.get("metadata") or {}).get("group") or "Diger"
        topic_items.append(TopicItem(id=tid, label=label, group=group))

    # Build GapCellItem list
    cells: list[GapCellItem] = []
    for method_item in method_items:
        for topic_item in topic_items:
            row = cell_map.get((method_item.id, topic_item.id))
            if row is None:
                continue
            gv = float(row.get("gap_value") or 0)
            dn = float(row.get("depth_norm") or 0)
            depth = int(row.get("depth") or 0)
            cells.append(GapCellItem(
                method_id=method_item.id,
                topic_id=topic_item.id,
                n_papers=depth,
                gap_score=round(gv, 4),
                depth_norm=round(dn, 4),
                is_gold=gv >= 0.75,
            ))

    return GapHeatmapResponse(
        methods=method_items,
        topics=topic_items,
        cells=cells,
        total_cells=len(cells),
        matrix_id="M1",
    )


def _infer_method_family(metod_id: str) -> str:
    """Heuristic family grouping from metod_id text."""
    m = metod_id.lower()
    if any(k in m for k in ("fuzzy", "type2", "intuitionistic")):
        return "Fuzzy"
    if any(k in m for k in ("ahp", "anp", "macbeth", "dematel")):
        return "Network/Pairwise"
    if any(k in m for k in ("topsis", "vikor", "electre", "promethee", "moora")):
        return "Reference-based"
    if any(k in m for k in ("entropy", "critic", "bwm", "best_worst")):
        return "Weighting"
    if any(k in m for k in ("wsm", "wpm", "saw", "maut")):
        return "Aggregation"
    return "Other"


@router.get("/gap-heatmap", response_model=GapHeatmapResponse)
async def gap_heatmap(
    matrix_id: str = Query(default="M1", pattern="^(M1|M7|M8)$"),
    top_methods: int = Query(default=14, ge=5, le=30),
    top_topics: int = Query(default=18, ge=5, le=50),
    project_id: str | None = Query(default=None),
) -> GapHeatmapResponse:
    """Fetch gap matrix slice: top_methods × top_topics, ordered by gap_value.

    V1-S17 P004: `project_id` verilirse project_cluster paper_ids üzerinden
    fact_paper_topic/fact_paper_metod bridges ile theme/method filter uygulanır.
    """
    ck = _cache_key(matrix_id, top_methods, top_topics, project_id)
    cached = cache_get(CacheNamespace.QUERY, ck)
    if cached is not None:
        return GapHeatmapResponse.model_validate(cached)

    # Pull enough rows to find top methods/topics (project filter sonrası daraltma için ×5 buffer)
    fetch_limit = top_methods * top_topics * (5 if project_id else 3)

    try:
        raw_cells = await supabase_call_async(
            lambda: _fetch_gap_cells(matrix_id, fetch_limit),
            timeout=20.0,
        )
    except (ResilienceTimeoutError, SupabaseQueryError) as exc:
        logger.warning("gap_heatmap fetch failed: %s", exc)
        raise HTTPException(status_code=503, detail="Gap heatmap data temporarily unavailable")

    if not raw_cells:
        raise HTTPException(status_code=404, detail="No gap matrix data found")

    # Project filter: project_cluster → fact_paper_topic + fact_paper_metod bridges
    theme_filter: set[str] | None = None
    method_filter: set[str] | None = None
    if project_id:
        try:
            project_paper_ids = await supabase_call_async(
                lambda: _fetch_project_paper_ids(project_id),
                timeout=10.0,
            )
            if project_paper_ids:
                theme_filter = await supabase_call_async(
                    lambda: _fetch_project_theme_ids(project_paper_ids),
                    timeout=10.0,
                )
                method_filter = await supabase_call_async(
                    lambda: _fetch_project_method_ids(project_paper_ids),
                    timeout=10.0,
                )
        except Exception as exc:
            logger.warning("gap_heatmap project filter failed (%s); global fallback", exc)

        if theme_filter is not None and method_filter is not None and (theme_filter or method_filter):
            raw_cells = [
                row
                for row in raw_cells
                if (not theme_filter or row.get("axis_x") in theme_filter)
                and (not method_filter or row.get("axis_y") in method_filter)
            ]
            if not raw_cells:
                raise HTTPException(status_code=404, detail="No gap cells for project scope")

    # Collect unique theme_ids for dim_theme label join
    theme_ids = list({row["axis_x"] for row in raw_cells})
    try:
        theme_label_map = await supabase_call_async(
            lambda: _fetch_theme_labels(theme_ids),
            timeout=10.0,
        )
    except Exception:
        theme_label_map = {}

    # Inject theme labels into cells before building response
    for row in raw_cells:
        row["_theme_meta"] = theme_label_map.get(row["axis_x"], {})

    response = _build_response_with_labels(raw_cells, top_methods, top_topics, theme_label_map)

    cache_set(CacheNamespace.QUERY, ck, response.model_dump(mode="json"), ttl=_CACHE_TTL)
    return response


def _build_response_with_labels(
    raw_cells: list[dict],
    top_methods: int,
    top_topics: int,
    theme_label_map: dict[str, dict],
) -> GapHeatmapResponse:
    """Same as _build_response but uses real dim_theme labels."""
    method_scores: dict[str, float] = {}
    topic_scores: dict[str, float] = {}

    for row in raw_cells:
        mx = row["axis_x"]
        my = row["axis_y"]
        gv = float(row.get("gap_value") or 0)
        method_scores[my] = max(method_scores.get(my, 0.0), gv)
        topic_scores[mx] = max(topic_scores.get(mx, 0.0), gv)

    top_method_ids = sorted(method_scores, key=lambda k: method_scores[k], reverse=True)[:top_methods]
    top_topic_ids = sorted(topic_scores, key=lambda k: topic_scores[k], reverse=True)[:top_topics]

    method_set = set(top_method_ids)
    topic_set = set(top_topic_ids)

    cell_map: dict[tuple[str, str], dict] = {}
    for row in raw_cells:
        mx, my = row["axis_x"], row["axis_y"]
        if mx in topic_set and my in method_set:
            key = (my, mx)
            existing = cell_map.get(key)
            if existing is None or float(row.get("gap_value") or 0) > float(existing.get("gap_value") or 0):
                cell_map[key] = row

    method_items: list[MethodItem] = [
        MethodItem(id=mid, label=mid.replace("_", " ").title(), family=_infer_method_family(mid))
        for mid in top_method_ids
    ]

    topic_items: list[TopicItem] = []
    for tid in top_topic_ids:
        meta = theme_label_map.get(tid, {})
        label = meta.get("name_tr") or tid.replace("_", " ").title()
        group = (meta.get("metadata") or {}).get("group") or "Diger"
        topic_items.append(TopicItem(id=tid, label=label, group=group))

    cells: list[GapCellItem] = []
    for method_item in method_items:
        for topic_item in topic_items:
            row = cell_map.get((method_item.id, topic_item.id))
            if row is None:
                continue
            gv = float(row.get("gap_value") or 0)
            dn = float(row.get("depth_norm") or 0)
            depth = int(row.get("depth") or 0)
            cells.append(GapCellItem(
                method_id=method_item.id,
                topic_id=topic_item.id,
                n_papers=depth,
                gap_score=round(gv, 4),
                depth_norm=round(dn, 4),
                is_gold=gv >= 0.75,
            ))

    return GapHeatmapResponse(
        methods=method_items,
        topics=topic_items,
        cells=cells,
        total_cells=len(cells),
        matrix_id="M1",
    )
