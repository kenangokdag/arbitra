"""2026-08-08 - v4: moat-gate'li build_executive_verdict()'i OFFLINE yeniden calistir.

61 raporun zaten sakli findings + risk_radar'indan GERCEK build_executive_verdict()
fonksiyonunu (guncel moat-gate mantigiyla) tekrar cagiriyoruz - manuel yeniden-
implementasyon degil, ayni kod yolu. LLM'e tekrar gidilmiyor (findings/risk_radar
degismedi, sadece decision-tree fonksiyonu degisti).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")

from api.models.review import ReviewReport
from engine.academic.report_synthesis import build_executive_verdict
from eval.review import metrics
from eval.review.run_eval import load_goldset, _DEFAULT_GOLDSET

REPORTS_DIR = Path(
    r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main"
    r"\492975e2-533f-4eaf-b2e8-4d52c4badcb1\scratchpad\goldset_live_reports"
)

reports: dict[str, ReviewReport] = {}
changed = []
gate_fired = []
for f in REPORTS_DIR.glob("*.json"):
    if "_all_results" in f.name or "real_metrics" in f.name:
        continue
    entry = json.loads(f.read_text(encoding="utf-8"))
    rep_dict = entry.get("report")
    if rep_dict is None:
        continue
    rep = ReviewReport.model_validate(rep_dict)
    if rep.executive_verdict is None:
        continue
    old_verdict = rep.verdict
    new_ev = build_executive_verdict(rep.findings, rep.risk_radar)
    new_verdict = new_ev.recommended_decision
    if "MOAT-GATE" in new_ev.one_sentence_diagnosis:
        gate_fired.append((entry["paper_id"], new_ev.overall_readiness_score, old_verdict, new_verdict))
    if old_verdict != new_verdict:
        changed.append((entry["paper_id"], old_verdict, new_verdict))
    rep.verdict = new_verdict
    rep.executive_verdict = new_ev
    reports[entry["paper_id"]] = rep

print(f"{len(reports)} rapor yuklendi.\n")
print(f"moat-gate tetiklenen: {len(gate_fired)}/{len(reports)}")
for pid, r, old, new in gate_fired:
    print(f"  {pid}: readiness={r:.1f}  eski(v3-skor-tabanli)={old} -> yeni(v4-gate)={new}")

print(f"\nv3->v4 arasinda degisen (sadece gate'ten degil, v3'un kendisi de bu \n"
      f"scriptte v3-skor-tabanliydi, simdi karsilastiriyoruz): {len(changed)}\n")

goldset = load_goldset(_DEFAULT_GOLDSET)
result = metrics.evaluate(reports, goldset)
summary_text = metrics.format_summary(result, stanford_ref=goldset.meta.stanford_reference)
print("\n" + summary_text.encode("ascii", "replace").decode("ascii"))

out_txt = REPORTS_DIR / "real_metrics_result_v4_moat_gate_summary.txt"
out_txt.write_text(summary_text, encoding="utf-8")
out_json = REPORTS_DIR / "real_metrics_result_v4_moat_gate.json"
payload = {
    "verdict_accuracy": result.verdict_accuracy.__dict__,
    "dimension_agreement": [da.__dict__ for da in result.dimension_agreement],
}
out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nJSON: {out_json}\nTXT: {out_txt}")
