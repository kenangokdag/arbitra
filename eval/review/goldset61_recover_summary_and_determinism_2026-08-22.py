"""2026-08-22 KURTARMA script'i — goldset61_live_rerun_2026-08-22.py'nin ana
61-makale koşumu BAŞARIYLA bitti (61/61 rapor diske yazıldı, format_summary
metni de kaydedildi) ama sonrasındaki JSON-özet kodu bir attribute-adı
hatasıyla (`dimension_agreements` yerine gerçek ad `dimension_agreement` —
kod yazmadan önce Grep ile doğrulanmalıydı, doğrulanmadı) çöktü — determinism
alt-koşumu (6 makale, 2. kez) hiç çalışmadı.

Bu script PAHALI kısmı (61 canlı analiz) TEKRARLAMAZ — diskteki raporları
okur, doğru attribute adıyla JSON özeti üretir, SONRA sadece determinism
alt-koşumunu (6 makale × 1 ek canlı analiz) çalıştırır.
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.models.review import ReviewReport  # noqa: E402
from eval.review import metrics  # noqa: E402
from eval.review.run_eval import load_goldset, _DEFAULT_GOLDSET  # noqa: E402

import importlib.util

_HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("g61", _HERE / "goldset61_live_rerun_2026-08-22.py")
g61 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g61)  # type: ignore[union-attr]

REPORTS_DIR = _HERE / "results" / "goldset61_live_reports_2026-08-22"
SUMMARY_TXT = _HERE / "results" / "goldset61_live_rerun_2026-08-22_summary.txt"
SUMMARY_JSON = _HERE / "results" / "goldset61_live_rerun_2026-08-22_summary.json"
DETERMINISM_JSON = _HERE / "results" / "goldset61_classifier_determinism_2026-08-22.json"


def rebuild_summary() -> dict:
    goldset = load_goldset(_DEFAULT_GOLDSET)
    reports: dict[str, ReviewReport] = {}
    raw_by_pid: dict[str, dict] = {}
    n_ok = 0
    n_fail = 0
    for f in REPORTS_DIR.glob("*.json"):
        entry = json.loads(f.read_text(encoding="utf-8"))
        pid = entry["paper_id"]
        raw_by_pid[pid] = entry
        if "report" in entry:
            try:
                reports[pid] = ReviewReport.model_validate(entry["report"])
                n_ok += 1
            except Exception as exc:
                print(f"  UYARI: {pid} şemaya uymuyor: {exc}")
                n_fail += 1
        else:
            n_fail += 1

    print(f"diskten yüklenen rapor: {n_ok} ok, {n_fail} başarısız/eksik")

    eval_result = metrics.evaluate(reports, goldset)
    summary = metrics.format_summary(eval_result, stanford_ref=goldset.meta.stanford_reference)
    print(summary)
    SUMMARY_TXT.write_text(summary, encoding="utf-8")

    summary_json = {
        "n_entries_total": len(goldset.entries),
        "n_reports_ok": n_ok,
        "n_reports_failed": n_fail,
        "verdict_accuracy": {
            "n": eval_result.verdict_accuracy.n,
            "exact": eval_result.verdict_accuracy.exact,
            "within_one": eval_result.verdict_accuracy.within_one,
            "exact_accuracy": eval_result.verdict_accuracy.exact_accuracy,
            "within_one_accuracy": eval_result.verdict_accuracy.within_one_accuracy,
        },
        "dimension_agreements": [
            {
                "dimension": da.dimension,
                "n": da.n,
                "spearman": da.spearman,
                "pearson": da.pearson,
                "mean_abs_diff": da.mean_abs_diff,
                "mean_signed_diff": da.mean_signed_diff,
            }
            for da in eval_result.dimension_agreement
        ],
    }
    SUMMARY_JSON.write_text(json.dumps(summary_json, ensure_ascii=False, indent=2), encoding="utf-8")

    # raw_by_pid run1 olarak determinism kıyaslamasında kullanılacak
    return raw_by_pid


async def run_determinism_subset(raw_by_pid: dict[str, dict]) -> None:
    goldset = load_goldset(_DEFAULT_GOLDSET)
    mapping: dict[str, str] = json.loads(g61.MAPPING_PATH.read_text(encoding="utf-8"))

    entries: list[tuple[str, Path]] = []
    for e in goldset.entries:
        fname = mapping.get(e.paper_id)
        pdf_path = g61._resolve_pdf(fname) if fname else None
        if pdf_path is not None:
            entries.append((e.paper_id, pdf_path))

    subset = entries[:6]
    print(f"\n=== classifier determinism alt-koşum ({len(subset)} makale, 2. kez) ===\n")
    subset_results_2 = await g61.run_batch(subset, "det2")

    det_compare = []
    for r2 in subset_results_2:
        pid = r2["paper_id"]
        r1 = raw_by_pid.get(pid)
        same_doc_type = r1 is not None and r1.get("document_type") == r2.get("document_type")
        same_study_design = r1 is not None and r1.get("study_design") == r2.get("study_design")
        det_compare.append(
            {
                "paper_id": pid,
                "run1_document_type": r1.get("document_type") if r1 else None,
                "run2_document_type": r2.get("document_type"),
                "run1_study_design": r1.get("study_design") if r1 else None,
                "run2_study_design": r2.get("study_design"),
                "same_document_type": same_doc_type,
                "same_study_design": same_study_design,
                "run1_verdict": r1.get("verdict") if r1 else None,
                "run2_verdict": r2.get("verdict"),
            }
        )
        print(
            f"  {pid}: doc_type {r1.get('document_type') if r1 else '?'}=={r2.get('document_type')} "
            f"({'OK' if same_doc_type else 'FARK'}), study_design "
            f"{r1.get('study_design') if r1 else '?'}=={r2.get('study_design')} "
            f"({'OK' if same_study_design else 'FARK'})"
        )
    DETERMINISM_JSON.write_text(json.dumps(det_compare, ensure_ascii=False, indent=2), encoding="utf-8")

    n_same_doc = sum(1 for d in det_compare if d["same_document_type"])
    n_same_design = sum(1 for d in det_compare if d["same_study_design"])
    print(f"\nclassifier determinism: document_type {n_same_doc}/{len(det_compare)} aynı, "
          f"study_design {n_same_design}/{len(det_compare)} aynı")


async def main() -> None:
    raw_by_pid = rebuild_summary()
    await run_determinism_subset(raw_by_pid)
    print("\n=== KURTARMA TAMAMEN BİTTİ ===")


if __name__ == "__main__":
    asyncio.run(main())
