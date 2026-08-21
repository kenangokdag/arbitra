"""2026-08-08 - v3: skor-tabanli esiklerle verdict'i OFFLINE yeniden hesapla.

Onemli: risk_radar/readiness skoru bu degisiklikte DOKUNULMADI (sadece karar
esikleri degisti) - yani LLM'i yeniden cagirmaya gerek yok. Her raporun zaten
sakli 'executive_verdict.overall_readiness_score'undan yeni esiklerle (78.5/72.0)
verdict'i yeniden turetip metrikleri yeniden hesapliyoruz. Bu, ~61*7.5dk'lik
pipeline'i yeniden kosmaktan cok daha hizli ve TAM AYNI sonucu verir (readiness
degismedigi icin deterministik).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")

from api.models.review import ReviewReport
from engine.academic.report_synthesis import (
    ACCEPT_READINESS_THRESHOLD,
    REJECT_READINESS_THRESHOLD,
)
from eval.review import metrics
from eval.review.run_eval import load_goldset, _DEFAULT_GOLDSET

REPORTS_DIR = Path(
    r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main"
    r"\492975e2-533f-4eaf-b2e8-4d52c4badcb1\scratchpad\goldset_live_reports"
)


def _new_decision(readiness: float) -> str:
    if readiness >= ACCEPT_READINESS_THRESHOLD:
        return "accept"
    if readiness < REJECT_READINESS_THRESHOLD:
        return "reject"
    return "major_revision"


reports: dict[str, ReviewReport] = {}
old_new_pairs = []
for f in REPORTS_DIR.glob("*.json"):
    if "_all_results" in f.name or "real_metrics" in f.name:
        continue
    entry = json.loads(f.read_text(encoding="utf-8"))
    rep_dict = entry.get("report")
    if rep_dict is None:
        continue
    rep = ReviewReport.model_validate(rep_dict)
    if rep.executive_verdict is None:
        print(f"!! {entry['paper_id']}: executive_verdict yok, atlaniyor")
        continue
    readiness = rep.executive_verdict.overall_readiness_score
    old_verdict = rep.verdict
    new_verdict = _new_decision(readiness)
    old_new_pairs.append((entry["paper_id"], readiness, old_verdict, new_verdict))
    # rapor nesnesini yeni karara gore mutasyona ugrat (offline yeniden turetme)
    rep.verdict = new_verdict
    rep.executive_verdict.recommended_decision = new_verdict
    reports[entry["paper_id"]] = rep

print(f"{len(reports)} rapor yuklendi, verdict yeni esiklerle yeniden turetildi.\n")

changed = [p for p in old_new_pairs if p[2] != p[3]]
print(f"Eski->yeni verdict degisen: {len(changed)}/{len(old_new_pairs)}\n")
for pid, r, old, new in changed:
    print(f"  {pid}: readiness={r:.1f}  {old} -> {new}")

goldset = load_goldset(_DEFAULT_GOLDSET)
result = metrics.evaluate(reports, goldset)
summary_text = metrics.format_summary(result, stanford_ref=goldset.meta.stanford_reference)
print("\n" + summary_text.encode("ascii", "replace").decode("ascii"))

out_txt = REPORTS_DIR / "real_metrics_result_v3_summary.txt"
out_txt.write_text(summary_text, encoding="utf-8")

out_json = REPORTS_DIR / "real_metrics_result_v3_score_thresholds.json"
payload = {
    "verdict_accuracy": result.verdict_accuracy.__dict__,
    "dimension_agreement": [da.__dict__ for da in result.dimension_agreement],
}
out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nJSON: {out_json}\nTXT: {out_txt}")
