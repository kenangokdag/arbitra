"""2026-08-11/12 - v7 (SS38+SS39 birlikte, canli 61-makale kosumu) icin
karisiklik matrisi + sinif-dengeli dogruluk. format_summary()'nin pooled
(ham) sayilarini class-imbalance acisindan baglamlandirir - onceki SS29
dersinin (ham dogruluk yaniltici olabilir) tekrar uygulanmasi.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")

from api.models.review import ReviewReport  # noqa: E402
from eval.review.run_eval import load_goldset, _DEFAULT_GOLDSET  # noqa: E402

REPORTS_DIR = Path(
    r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main"
    r"\492975e2-533f-4eaf-b2e8-4d52c4badcb1\scratchpad\goldset_live_reports_v7"
)


def main() -> None:
    goldset = load_goldset(_DEFAULT_GOLDSET)
    human = {e.paper_id: e.human_verdict for e in goldset.entries}

    motor_dist: dict[str, int] = {}
    confusion: dict[str, dict[str, int]] = {}
    degraded_count = 0
    for f in REPORTS_DIR.glob("*.json"):
        entry = json.loads(f.read_text(encoding="utf-8"))
        rep_dict = entry.get("report")
        if rep_dict is None:
            continue
        rep = ReviewReport.model_validate(rep_dict)
        if any("openalex_unavailable" in d for d in rep.evidence_pack.degraded_features):
            degraded_count += 1
        h = human.get(entry["paper_id"])
        motor_dist[rep.verdict] = motor_dist.get(rep.verdict, 0) + 1
        if h:
            confusion.setdefault(h, {})
            confusion[h][rep.verdict] = confusion[h].get(rep.verdict, 0) + 1

    print("motor dagilim (61 makale):", motor_dist)
    print(f"OpenAlex-kesintili (coverage:openalex_unavailable) makale sayisi: {degraded_count}/61")
    print()
    by_class = {}
    for h in ("accept", "minor_revision", "major_revision", "reject"):
        row = confusion.get(h, {})
        total = sum(row.values())
        correct = row.get(h, 0)
        by_class[h] = (correct, total)
        print(f"  {h}: {row} -> {correct}/{total}")

    accs = [c / t for c, t in by_class.values() if t > 0]
    balanced = sum(accs) / len(accs) if accs else None
    print(f"\nsinif-dengeli dogruluk: {balanced * 100:.1f}%" if balanced else "N/A")

    payload = {
        "motor_dagilim": motor_dist,
        "confusion_matrix_insan_satir_motor_sutun": confusion,
        "sinif_basi_dogruluk": {k: {"dogru": v[0], "toplam": v[1]} for k, v in by_class.items()},
        "sinif_dengeli_dogruluk": balanced,
        "openalex_kesintili_makale_sayisi": degraded_count,
    }
    out = Path(r"C:\Users\USER\Desktop\arbitra-main\eval\review\results\v7_confusion_and_balanced_accuracy.json")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nyazildi: {out}")


if __name__ == "__main__":
    main()
