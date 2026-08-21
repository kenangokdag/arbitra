"""2026-08-10 - full 61-makale re-run (SS36) sonrasi esik-kalibrasyonu analizi.

readiness skorunun accept/reject sinifi arasindaki ayirt ediciligi bugunku
severity-revizyonlari SONRASI dustu mu diye kontrol eder (SS35'in ongordugu
risk). Gercek build_executive_verdict() (moat-gate dahil) kullanilir.
"""

import json
import statistics
from pathlib import Path
import sys

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")

from api.models.review import ReviewReport  # noqa: E402
from eval.review import metrics  # noqa: E402
from eval.review.run_eval import load_goldset, _DEFAULT_GOLDSET  # noqa: E402
import engine.academic.report_synthesis as rs  # noqa: E402

REPORTS_DIR = Path(
    r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main"
    r"\492975e2-533f-4eaf-b2e8-4d52c4badcb1\scratchpad\goldset_live_reports_v5"
)


def load_reports() -> dict[str, ReviewReport]:
    out = {}
    for f in REPORTS_DIR.glob("*.json"):
        entry = json.loads(f.read_text(encoding="utf-8"))
        rep_dict = entry.get("report")
        if rep_dict is None:
            continue
        out[entry["paper_id"]] = ReviewReport.model_validate(rep_dict)
    return out


def predictions(base_reports, t1, t2):
    old_t1, old_t2 = rs.ACCEPT_READINESS_THRESHOLD, rs.REJECT_READINESS_THRESHOLD
    rs.ACCEPT_READINESS_THRESHOLD, rs.REJECT_READINESS_THRESHOLD = t1, t2
    try:
        out = {}
        for pid, rep in base_reports.items():
            ev = rs.build_executive_verdict(rep.findings, rep.risk_radar)
            out[pid] = ev.recommended_decision
        return out
    finally:
        rs.ACCEPT_READINESS_THRESHOLD, rs.REJECT_READINESS_THRESHOLD = old_t1, old_t2


def balanced_acc(base_reports, human, t1, t2):
    preds = predictions(base_reports, t1, t2)
    by_class: dict[str, list[int]] = {}
    for pid, pred in preds.items():
        h = human.get(pid)
        if not h:
            continue
        by_class.setdefault(h, [0, 0])
        by_class[h][1] += 1
        if pred == h:
            by_class[h][0] += 1
    accs = {h: (c / t if t else 0.0) for h, (c, t) in by_class.items()}
    return sum(accs.values()) / len(accs), by_class


def main() -> None:
    goldset = load_goldset(_DEFAULT_GOLDSET)
    human = {e.paper_id: e.human_verdict for e in goldset.entries}
    base_reports = load_reports()
    print(f"{len(base_reports)} rapor yuklendi\n")

    # 1) eski esiklerle (SS29) tam metrik
    old_reports = {}
    for pid, rep in base_reports.items():
        ev = rs.build_executive_verdict(rep.findings, rep.risk_radar)
        old_reports[pid] = rep.model_copy(update={"verdict": ev.recommended_decision})
    va_old = metrics.evaluate(old_reports, goldset).verdict_accuracy
    print(f"Eski esikler (78.5/72.0, kod HALEN bu degerlerde): {va_old}")

    bacc_old, by_old = balanced_acc(base_reports, human, 78.5, 72.0)
    print(f"  sinif-dengeli dogruluk: {bacc_old*100:.2f}%  {by_old}\n")

    # 2) accept/reject ayrisikligi
    accept_r = [
        rs.build_executive_verdict(r.findings, r.risk_radar).overall_readiness_score
        for pid, r in base_reports.items() if human.get(pid) == "accept"
    ]
    reject_r = [
        rs.build_executive_verdict(r.findings, r.risk_radar).overall_readiness_score
        for pid, r in base_reports.items() if human.get(pid) == "reject"
    ]
    print("accept vs reject readiness ayrisikligi:")
    print(f"  accept: n={len(accept_r)} ort={statistics.mean(accept_r):.1f} stdev={statistics.stdev(accept_r):.1f}")
    print(f"  reject: n={len(reject_r)} ort={statistics.mean(reject_r):.1f} stdev={statistics.stdev(reject_r):.1f}")
    print(f"  fark: {statistics.mean(accept_r)-statistics.mean(reject_r):.1f} puan")
    overlap = sum(1 for r in reject_r if r > statistics.mean(accept_r) - statistics.stdev(accept_r))
    print(f"  {overlap}/{len(reject_r)} reject-etiketli makale accept dagiliminin 1-stdev icine giriyor\n")

    # 3) sinif-dengeli en iyi esik taramasi
    best = None
    for t1x in range(650, 950, 5):
        t1 = t1x / 10
        for t2x in range(600, 900, 5):
            t2 = t2x / 10
            if t1 - t2 < 6:
                continue
            bacc, by_class = balanced_acc(base_reports, human, t1, t2)
            if best is None or bacc > best[0]:
                best = (bacc, t1, t2, by_class)
    bacc, t1, t2, by_class = best
    print(f"EN IYI (sinif-dengeli) esik: t1={t1} t2={t2} balanced_acc={bacc*100:.2f}%  {by_class}")


if __name__ == "__main__":
    main()
