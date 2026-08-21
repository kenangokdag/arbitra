"""F13-S11 4.2-4.5 atölye analitik — pure helper unit tests.

Mock'lu Supabase orchestration testleri ileri faza ertelendi (yüksek mock
karmaşıklığı). Bu dosya saf fonksiyonları + momentum matrisini + weight
normalize edge case'lerini kapsar.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from api.models.workshop_analytics import (
    CompareWeights,
    GapAxisScores,
    GapCellRef,
    ImpactPoint,
)
from api.services import (
    gap_profile_workshop_service as gap_svc,
)
from api.services import (
    impact_curve_service as impact_svc,
)
from api.services import (
    originality_service as orig_svc,
)
from api.services import (
    study_compare_service as cmp_svc,
)

pytestmark = pytest.mark.unit


# ── originality_service ─────────────────────────────────────────────────────


def test_within_year_no_bounds_keeps_all() -> None:
    assert orig_svc._within_year({"pub_year": 2020}, None, None) is True


def test_within_year_lower_bound() -> None:
    assert orig_svc._within_year({"pub_year": 2010}, 2015, None) is False
    assert orig_svc._within_year({"pub_year": 2020}, 2015, None) is True


def test_within_year_upper_bound() -> None:
    assert orig_svc._within_year({"pub_year": 2020}, None, 2018) is False
    assert orig_svc._within_year({"pub_year": 2015}, None, 2018) is True


def test_within_year_missing_pub_year_with_bounds_drops_row() -> None:
    assert orig_svc._within_year({}, 2010, 2020) is False


def test_within_year_missing_pub_year_no_bounds_keeps_row() -> None:
    assert orig_svc._within_year({}, None, None) is True


def test_build_disruption_paper_maps_fields() -> None:
    fact = {
        "paper_id": "W1",
        "pub_year": 2018,
        "cd_5": 0.42,
        "n_a": 3,
        "n_i": 5,
        "n_j": 7,
        "total_window_papers": 100,
    }
    meta = {"title": "T", "year": 2018, "venue": "JEdu"}
    p = orig_svc._build_disruption_paper(fact, meta)
    assert p.paper_id == "W1"
    assert p.cd_5 == 0.42
    assert p.n_a == 3
    assert p.title == "T"
    assert p.b is None  # disruption rows have no b


def test_build_beauty_paper_maps_fields() -> None:
    fact = {
        "paper_id": "W2",
        "pub_year": 2005,
        "b": 84.0,
        "t_m": 12,
        "c_max": 120,
        "total_cites": 400,
    }
    meta = {"title": "T", "year": 2005, "venue": "Nat"}
    p = orig_svc._build_beauty_paper(fact, meta)
    assert p.b == 84.0
    assert p.t_m == 12
    assert p.cd_5 is None  # beauty rows have no cd_5


# ── impact_curve_service ────────────────────────────────────────────────────


def test_series_from_years_fills_zeros() -> None:
    current = datetime.now(UTC).year
    series = impact_svc._series_from_years([current, current - 1, current - 1], 5)
    assert len(series) == 5
    assert series[-1].value == 1.0
    assert series[-2].value == 2.0
    assert all(p.value == 0.0 for p in series[:-2])


def test_series_from_years_drops_out_of_window() -> None:
    current = datetime.now(UTC).year
    series = impact_svc._series_from_years([current - 50], 5)
    assert sum(p.value for p in series) == 0.0


def test_slope_pct_growing_returns_positive() -> None:
    series = [
        ImpactPoint(year=2020, value=1.0),
        ImpactPoint(year=2021, value=2.0),
        ImpactPoint(year=2022, value=3.0),
        ImpactPoint(year=2023, value=4.0),
        ImpactPoint(year=2024, value=5.0),
    ]
    s = impact_svc._slope_pct(series)
    assert s is not None and s > 0


def test_slope_pct_flat_returns_zero() -> None:
    series = [
        ImpactPoint(year=y, value=10.0) for y in range(2020, 2025)
    ]
    s = impact_svc._slope_pct(series)
    assert s == 0.0


def test_slope_pct_single_point_returns_none() -> None:
    assert impact_svc._slope_pct([ImpactPoint(year=2024, value=5.0)]) is None


def test_slope_pct_all_zero_returns_none() -> None:
    series = [ImpactPoint(year=y, value=0.0) for y in range(2020, 2025)]
    assert impact_svc._slope_pct(series) is None


_MOMENTUM_THR = {
    "academic_slope": {
        "green_min_pct_per_year": 5.0,
        "red_max_pct_per_year": -5.0,
    },
    "trends_slope": {
        "green_min_points_per_year": 5.0,
        "red_max_points_per_year": -5.0,
    },
}


def test_momentum_both_green() -> None:
    assert impact_svc._momentum_color(10.0, 10.0, _MOMENTUM_THR) == "green"


def test_momentum_any_red_wins() -> None:
    assert impact_svc._momentum_color(10.0, -10.0, _MOMENTUM_THR) == "red"
    assert impact_svc._momentum_color(-10.0, 10.0, _MOMENTUM_THR) == "red"


def test_momentum_mixed_is_yellow() -> None:
    assert impact_svc._momentum_color(10.0, 0.0, _MOMENTUM_THR) == "yellow"
    assert impact_svc._momentum_color(0.0, 10.0, _MOMENTUM_THR) == "yellow"


def test_momentum_both_unknown() -> None:
    assert impact_svc._momentum_color(None, None, _MOMENTUM_THR) == "unknown"


def test_momentum_trends_only_green_biases_yellow() -> None:
    """RTF: academic yoksa green'i sarıya düşür."""
    assert impact_svc._momentum_color(None, 10.0, _MOMENTUM_THR) == "yellow"


def test_momentum_trends_only_red_stays_red() -> None:
    assert impact_svc._momentum_color(None, -10.0, _MOMENTUM_THR) == "red"


def test_momentum_academic_only_propagates() -> None:
    assert impact_svc._momentum_color(10.0, None, _MOMENTUM_THR) == "green"
    assert impact_svc._momentum_color(-10.0, None, _MOMENTUM_THR) == "red"


# ── gap_profile_workshop_service ────────────────────────────────────────────


def test_sparkline_counts_year_bucket() -> None:
    current = datetime.now(UTC).year
    out = gap_svc._sparkline([current, current, current - 1], 10)
    assert len(out) == 10
    assert out[-1].paper_count == 2
    assert out[-2].paper_count == 1


def test_radar_uses_affinity_when_present() -> None:
    radar = gap_svc._radar(
        cell_w_estra={"wir": [0.5], "wts": [0.6], "wd": [0.7]},
        cell_q=[0.4],
        cell_cd=[0.3],
        cell_b=[20.0],
        cell_pr=[0.001],
        affinity={"mean_q_weak": 0.55, "mean_centrality": 0.002},
    )
    by_dim = {p.dimension: p for p in radar}
    assert by_dim["q_weak"].corpus_value == 0.55
    assert by_dim["pagerank"].corpus_value == 0.002
    # Fallback baseline 0.5 for non-precomputed dims
    assert by_dim["wir"].corpus_value == gap_svc._CORPUS_BASELINE_FALLBACK


def test_radar_fallback_when_affinity_missing() -> None:
    radar = gap_svc._radar(
        cell_w_estra={"wir": [], "wts": [], "wd": []},
        cell_q=[],
        cell_cd=[],
        cell_b=[],
        cell_pr=[],
        affinity={"mean_q_weak": None, "mean_centrality": None},
    )
    by_dim = {p.dimension: p for p in radar}
    assert by_dim["q_weak"].corpus_value == gap_svc._CORPUS_BASELINE_FALLBACK
    assert all(p.cell_value == 0.0 for p in radar)


def test_journals_from_papers_top_n_by_count() -> None:
    rows = [
        {"venue": "A"},
        {"venue": "A"},
        {"venue": "B"},
        {"venue": None},
        {"venue": "   "},
    ]
    out = gap_svc._journals_from_papers(rows)
    assert out[0].venue == "A"
    assert out[0].paper_count == 2
    assert out[1].venue == "B"
    assert len(out) == 2


# ── study_compare_service ───────────────────────────────────────────────────


def _w(**kwargs: float) -> CompareWeights:
    defaults: dict[str, float] = {
        "risk": 0.20,
        "disruption": 0.20,
        "virgin": 0.20,
        "sleeping_beauty": 0.20,
        "publishability": 0.20,
    }
    defaults.update(kwargs)
    return CompareWeights(**defaults)


def test_normalize_weights_sums_to_one() -> None:
    w = _w(risk=1.0, disruption=1.0, virgin=0.0, sleeping_beauty=0.0, publishability=0.0)
    out = cmp_svc._normalize_weights(w)
    assert pytest.approx(sum(out.values()), rel=1e-9) == 1.0
    assert pytest.approx(out["risk"], rel=1e-9) == 0.5
    assert out["virgin"] == 0.0


def test_normalize_weights_all_zero_yields_equal_split() -> None:
    w = _w(risk=0.0, disruption=0.0, virgin=0.0, sleeping_beauty=0.0, publishability=0.0)
    out = cmp_svc._normalize_weights(w)
    assert all(v == 0.2 for v in out.values())


def test_weighted_dot_product() -> None:
    axes = GapAxisScores(
        risk=1.0, disruption=0.0, virgin=0.0, sleeping_beauty=0.0, publishability=0.0
    )
    score = cmp_svc._weighted(axes, {
        "risk": 0.5, "disruption": 0.1, "virgin": 0.1,
        "sleeping_beauty": 0.2, "publishability": 0.1,
    })
    assert score == 0.5


def test_disruption_to_unit_maps_minus_one_to_zero() -> None:
    assert cmp_svc._disruption_to_unit(-1.0) == 0.0


def test_disruption_to_unit_maps_one_to_one() -> None:
    assert cmp_svc._disruption_to_unit(1.0) == 1.0


def test_disruption_to_unit_maps_zero_to_half() -> None:
    assert cmp_svc._disruption_to_unit(0.0) == 0.5


def test_clip_bounds() -> None:
    assert cmp_svc._clip(-0.5) == 0.0
    assert cmp_svc._clip(1.5) == 1.0
    assert cmp_svc._clip(0.7) == 0.7


def test_avg_empty_returns_zero() -> None:
    assert cmp_svc._avg([]) == 0.0


def test_avg_simple_mean() -> None:
    assert cmp_svc._avg([1.0, 2.0, 3.0]) == 2.0


def test_compare_request_rejects_single_cell() -> None:
    from pydantic import ValidationError

    from api.models.workshop_analytics import CompareRequest

    with pytest.raises(ValidationError):
        CompareRequest(
            project_id="11111111-1111-1111-1111-111111111111",  # type: ignore[arg-type]
            gap_cells=[GapCellRef(matrix_id="m1", axis_x="ax", axis_y="ay")],
        )


def test_compare_request_accepts_two_cells() -> None:
    from uuid import uuid4

    from api.models.workshop_analytics import CompareRequest

    req = CompareRequest(
        project_id=uuid4(),
        gap_cells=[
            GapCellRef(matrix_id="m1", axis_x="ax", axis_y="ay"),
            GapCellRef(matrix_id="m1", axis_x="bx", axis_y="by"),
        ],
    )
    assert len(req.gap_cells) == 2
    assert req.weights.risk == 0.20
