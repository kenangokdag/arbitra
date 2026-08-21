"""2026-08-10/11 - SS39 moat-gate kademelendirmesinin (evidence GECIRILEREK)
v5 goldset uzerindeki GERCEK etkisini olcer.

Guardian bulgusu: onceki v4/v5 recompute scriptleri build_executive_verdict()'i
evidence PARAMETRESI OLMADAN cagiriyordu - yani SS39'un count-tabanli
kademelendirmesi hic tetiklenmiyordu, hepsi evidence=None fallback dalina
(major_revision) dusuyordu. Bu script rep.evidence_pack'i GERCEKTEN geciriyor.

NOT: bu recompute assessment.py'nin SS38 kanitsizlik-guard'ini ICERMIYOR (o
guard sadece TAZE pipeline kosumunda calisir, zaten var olan Finding
verisine retroaktif uygulanmaz) - yani bu olcum SADECE SS39'un (moat-gate
kademelendirmesi) izole etkisini gosteriyor, SS38+SS39 birlikte etkisini
degil. O olcum icin goldset'in tam kosumu gerekir (henuz yapilmadi).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")

from api.models.review import ReviewReport  # noqa: E402
from eval.review import metrics  # noqa: E402
from eval.review.run_eval import load_goldset, _DEFAULT_GOLDSET  # noqa: E402
import engine.academic.report_synthesis as rs  # noqa: E402

REPORTS_DIR = Path(
    r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main"
    r"\492975e2-533f-4eaf-b2e8-4d52c4badcb1\scratchpad\goldset_live_reports_v5"
)


def main() -> None:
    goldset = load_goldset(_DEFAULT_GOLDSET)
    human = {e.paper_id: e.human_verdict for e in goldset.entries}

    base_reports: dict[str, ReviewReport] = {}
    for f in REPORTS_DIR.glob("*.json"):
        entry = json.loads(f.read_text(encoding="utf-8"))
        rep_dict = entry.get("report")
        if rep_dict is None:
            continue
        base_reports[entry["paper_id"]] = ReviewReport.model_validate(rep_dict)

    new_reports = {}
    gate_details = []
    for pid, rep in base_reports.items():
        ev = rs.build_executive_verdict(rep.findings, rep.risk_radar, rep.evidence_pack)
        new_reports[pid] = rep.model_copy(update={"verdict": ev.recommended_decision})
        if "MOAT-GATE" in ev.one_sentence_diagnosis:
            gate_details.append((pid, human.get(pid), ev.recommended_decision))

    result = metrics.evaluate(new_reports, goldset)
    summary = metrics.format_summary(result, stanford_ref=goldset.meta.stanford_reference)
    print(summary.encode("ascii", "replace").decode("ascii"))
    print("\nmoat-gate'in karari fiilen degistirdigi makaleler:")
    for pid, h, dec in gate_details:
        print(f"  {pid}: insan={h} motor={dec}")

    out_txt = REPORTS_DIR.parent.parent.parent / "eval" / "review" / "results" / "real_metrics_result_v6_moat_gate_graduated_summary.txt"
    out_txt = Path(r"C:\Users\USER\Desktop\arbitra-main\eval\review\results\real_metrics_result_v6_moat_gate_graduated_summary.txt")
    out_txt.write_text(summary, encoding="utf-8")
    print(f"\nyazıldı: {out_txt}")


if __name__ == "__main__":
    main()
