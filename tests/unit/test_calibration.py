"""Faithfulness calibration fixture + script unit tests (Council 38)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parent.parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "faithfulness_calibration.json"


def test_fixture_exists_and_has_100_samples() -> None:
    assert FIXTURE.exists(), f"Missing: {FIXTURE}"
    data = json.loads(FIXTURE.read_text())
    assert len(data["samples"]) == 100


def test_fixture_80_positive_20_negative() -> None:
    data = json.loads(FIXTURE.read_text())
    pos = [s for s in data["samples"] if s["label"] == "faithful"]
    neg = [s for s in data["samples"] if s["label"] == "hallucinated"]
    assert len(pos) == 80
    assert len(neg) == 20


def test_fixture_three_domains() -> None:
    data = json.loads(FIXTURE.read_text())
    domains = {s["domain"] for s in data["samples"]}
    assert domains == {"Health", "Life", "Physical"}


def test_fixture_positive_scores_above_negative() -> None:
    data = json.loads(FIXTURE.read_text())
    pos_min = min(s["lvr_sim"] for s in data["samples"] if s["label"] == "faithful")
    neg_max = max(s["lvr_sim"] for s in data["samples"] if s["label"] == "hallucinated")
    assert pos_min > neg_max, f"Overlap: pos_min={pos_min} <= neg_max={neg_max}"


def test_calibrate_script_roc_auc() -> None:
    """Calibration script ROC AUC >= 0.85."""
    # Import from scripts
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    from calibrate_faithfulness import compute_auc, compute_roc, load_samples

    samples = load_samples()
    points = compute_roc(samples)
    auc = compute_auc(points)
    assert auc >= 0.85, f"AUC={auc} < 0.85"


def test_calibrate_optimal_threshold_in_range() -> None:
    """Optimal threshold should be between 0.5 and 0.85."""
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    from calibrate_faithfulness import (
        compute_roc,
        find_optimal_threshold,
        load_samples,
    )

    samples = load_samples()
    points = compute_roc(samples)
    threshold, f1 = find_optimal_threshold(points)
    assert 0.5 <= threshold <= 0.85, f"threshold={threshold} out of range"
    assert f1 >= 0.9, f"F1={f1} too low"
