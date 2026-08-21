"""Faithfulness threshold calibration script (Council 38).

Reads `tests/fixtures/faithfulness_calibration.json` (100 paper x ground-truth),
computes optimal LVR similarity threshold via ROC analysis, and optionally
updates `config/faithfulness_thresholds.yaml`.

Usage:
    cd ~/Desktop/papermind-app
    uv run python scripts/calibrate_faithfulness.py
    uv run python scripts/calibrate_faithfulness.py --apply  # write to YAML
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "faithfulness_calibration.json"
THRESHOLDS_YAML = REPO / "config" / "faithfulness_thresholds.yaml"


def load_samples() -> list[dict]:
    if not FIXTURE.exists():
        sys.exit(f"FAIL: fixture not found: {FIXTURE}")
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data["samples"]


def compute_roc(
    samples: list[dict],
) -> list[tuple[float, float, float, float]]:
    """Compute ROC curve points for LVR similarity threshold.

    Returns list of (threshold, tpr, fpr, f1) sorted by threshold.
    """
    positives = [s for s in samples if s["label"] == "faithful"]
    negatives = [s for s in samples if s["label"] == "hallucinated"]
    n_pos = len(positives)
    n_neg = len(negatives)

    if n_pos == 0 or n_neg == 0:
        sys.exit("FAIL: need both positive and negative samples")

    # Sweep thresholds from 0.0 to 1.0
    points: list[tuple[float, float, float, float]] = []
    for t_int in range(0, 101):
        threshold = t_int / 100.0
        tp = sum(1 for s in positives if s["lvr_sim"] >= threshold)
        fp = sum(1 for s in negatives if s["lvr_sim"] >= threshold)
        tpr = tp / n_pos
        fpr = fp / n_neg
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = (
            2 * precision * tpr / (precision + tpr)
            if (precision + tpr) > 0
            else 0.0
        )
        points.append((threshold, tpr, fpr, f1))

    return points


def compute_auc(points: list[tuple[float, float, float, float]]) -> float:
    """Trapezoidal AUC from ROC points."""
    # Sort by FPR ascending
    roc = sorted([(fpr, tpr) for _, tpr, fpr, _ in points])
    auc = 0.0
    for i in range(1, len(roc)):
        dx = roc[i][0] - roc[i - 1][0]
        avg_y = (roc[i][1] + roc[i - 1][1]) / 2
        auc += dx * avg_y
    return auc


def find_optimal_threshold(
    points: list[tuple[float, float, float, float]],
) -> tuple[float, float]:
    """Find threshold that maximizes F1 score.

    Returns (optimal_threshold, best_f1).
    """
    best = max(points, key=lambda p: p[3])
    return best[0], best[3]


def print_report(
    samples: list[dict],
    points: list[tuple[float, float, float, float]],
    auc: float,
    optimal_threshold: float,
    best_f1: float,
) -> None:
    n_pos = sum(1 for s in samples if s["label"] == "faithful")
    n_neg = sum(1 for s in samples if s["label"] == "hallucinated")

    # Domain distribution
    domains: dict[str, int] = {}
    for s in samples:
        domains[s["domain"]] = domains.get(s["domain"], 0) + 1

    # Language distribution
    langs: dict[str, int] = {}
    for s in samples:
        langs[s["lang"]] = langs.get(s["lang"], 0) + 1

    print("=" * 60)
    print("Faithfulness Calibration Report")
    print("=" * 60)
    print(f"Samples:    {len(samples)} ({n_pos} positive, {n_neg} negative)")
    print(f"Domains:    {domains}")
    print(f"Languages:  {langs}")
    print()

    # Score distributions
    pos_scores = [s["lvr_sim"] for s in samples if s["label"] == "faithful"]
    neg_scores = [s["lvr_sim"] for s in samples if s["label"] == "hallucinated"]
    print(f"Positive LVR range: [{min(pos_scores):.2f}, {max(pos_scores):.2f}]  mean={sum(pos_scores)/len(pos_scores):.3f}")
    print(f"Negative LVR range: [{min(neg_scores):.2f}, {max(neg_scores):.2f}]  mean={sum(neg_scores)/len(neg_scores):.3f}")
    print()

    print(f"AUC:              {auc:.4f}  (target >= 0.85)")
    print(f"Optimal threshold: {optimal_threshold:.2f}")
    print(f"Best F1:          {best_f1:.4f}")
    print()

    # Key threshold comparison
    for t in [0.60, 0.65, 0.70, 0.75, 0.80]:
        point = next((p for p in points if abs(p[0] - t) < 0.005), None)
        if point:
            print(f"  t={t:.2f}  TPR={point[1]:.2f}  FPR={point[2]:.2f}  F1={point[3]:.4f}")

    print()
    if auc >= 0.85:
        print("PASS: AUC >= 0.85 target met.")
    else:
        print(f"WARN: AUC {auc:.4f} < 0.85 target. Manual label review needed (KD-34).")
    print("=" * 60)


def apply_threshold(threshold: float) -> None:
    """Update lvr_min_distance in faithfulness_thresholds.yaml."""
    if not THRESHOLDS_YAML.exists():
        print(f"WARN: {THRESHOLDS_YAML} not found, skipping apply.")
        return

    content = THRESHOLDS_YAML.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines: list[str] = []
    updated = False
    for line in lines:
        if line.startswith("lvr_min_distance:"):
            old_val = line.split(":")[1].strip().split("#")[0].strip()
            comment = ""
            if "#" in line:
                comment = "  #" + line.split("#", 1)[1]
            new_line = f"lvr_min_distance: {threshold:.2f}{comment}"
            new_lines.append(new_line)
            updated = True
            print(f"Updated: lvr_min_distance {old_val} -> {threshold:.2f}")
        else:
            new_lines.append(line)

    if updated:
        THRESHOLDS_YAML.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"Written: {THRESHOLDS_YAML}")
    else:
        print("WARN: lvr_min_distance line not found in YAML.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Faithfulness threshold calibration")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write optimal threshold to config/faithfulness_thresholds.yaml",
    )
    args = parser.parse_args()

    samples = load_samples()
    points = compute_roc(samples)
    auc = compute_auc(points)
    optimal_threshold, best_f1 = find_optimal_threshold(points)

    print_report(samples, points, auc, optimal_threshold, best_f1)

    if args.apply:
        print()
        apply_threshold(optimal_threshold)

    return 0 if auc >= 0.85 else 1


if __name__ == "__main__":
    sys.exit(main())
