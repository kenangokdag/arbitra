"""2026-08-12 - SS41 (OpenAlex provider-hatasi gorunurlugu) commit'lendikten
SONRA 61 makalelik goldset'in CANLI (sifirdan LLM+OpenAlex) kosumunun
metriklerini hesaplar.

SS40'takinden fark: bu kosumda review_citation_service.py:308-329'un sessiz
hata-yutma davranisi ARTIK YOK - ParsedReference.resolution_degraded +
CitationIntegritySummary.provider_errors + degraded_features'a gorunur
'citations:openalex_resolution_failed:N' flag'i eklendi. Bu script SS40'in
"44 temiz makale alt sinirdi, gercek sayi netlesecek" sorusuna cevap veriyor:
simdi coverage:openalex_unavailable YANINDA citations:openalex_resolution_failed
flag'i de sayiliyor - gercek "provider-kesintisiz" makale sayisi ilk kez tam
olculuyor.

Ham veri: goldset_live_reports_v8 (bu session'in scratchpad'i) - 61/61 dosya
taramasiyla dogrulandi (report != None), script'in kendi "basarili" sayimina
guvenilmedi (SS40 dersi).
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")

from api.models.review import ReviewReport  # noqa: E402
from eval.review import metrics  # noqa: E402
from eval.review.run_eval import load_goldset, _DEFAULT_GOLDSET  # noqa: E402

REPORTS_DIR = Path(
    r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main"
    r"\3e56c8a7-1c60-4124-9a6a-0f99102f8e39\scratchpad\goldset_live_reports_v8"
)


def _load_reports() -> dict[str, ReviewReport]:
    out = {}
    for f in REPORTS_DIR.glob("*.json"):
        entry = json.loads(f.read_text(encoding="utf-8"))
        rep_dict = entry.get("report")
        if rep_dict is None:
            continue
        out[entry["paper_id"]] = ReviewReport.model_validate(rep_dict)
    return out


def main() -> None:
    goldset = load_goldset(_DEFAULT_GOLDSET)
    human = {e.paper_id: e.human_verdict for e in goldset.entries}
    all_reports = _load_reports()
    print(f"Yuklenen rapor sayisi: {len(all_reports)}/61")

    # SS41'in asil sorusu: provider-kesintili makale sayisi artik iki ayri
    # flag'den olculebiliyor (coverage YANINDA citations da).
    coverage_flagged = set()
    citation_flagged = set()
    for pid, rep in all_reports.items():
        for d in rep.evidence_pack.degraded_features:
            if "coverage:openalex_unavailable" in d:
                coverage_flagged.add(pid)
            if "citations:openalex_resolution_failed" in d:
                citation_flagged.add(pid)
    any_flagged = coverage_flagged | citation_flagged
    clean_reports = {pid: rep for pid, rep in all_reports.items() if pid not in any_flagged}

    print(f"\ncoverage:openalex_unavailable flagli: {len(coverage_flagged)}/61")
    print(f"citations:openalex_resolution_failed flagli (SS41 YENI): {len(citation_flagged)}/61")
    print(f"sadece citation-flagli (coverage-flagli DEGIL - SS40'in 'alt sinir' iddiasinin somut kanit): "
          f"{len(citation_flagged - coverage_flagged)}/61")
    print(f"herhangi bir provider-kesinti flagi (union): {len(any_flagged)}/61")
    print(f"TAMAMEN temiz (SS41 sonrasi gercek sayi): {len(clean_reports)}/61")

    for label, reports in (
        ("TUM 61", all_reports),
        (f"PROVIDER-KESINTISIZ ALT-KUME ({len(clean_reports)})", clean_reports),
    ):
        print(f"\n=== {label} ===")
        result = metrics.evaluate(reports, goldset)
        summary = metrics.format_summary(result, stanford_ref=goldset.meta.stanford_reference)
        print(summary.encode("ascii", "replace").decode("ascii"))

    # sinif-dengeli dogruluk (metrics.py'de yok, SS29'dan beri ayri hesaplaniyor)
    motor_dist: dict[str, int] = {}
    confusion: dict[str, dict[str, int]] = {}
    for pid, rep in all_reports.items():
        h = human.get(pid)
        motor_dist[rep.verdict] = motor_dist.get(rep.verdict, 0) + 1
        if h:
            confusion.setdefault(h, {})
            confusion[h][rep.verdict] = confusion[h].get(rep.verdict, 0) + 1
    by_class = {
        h: (confusion.get(h, {}).get(h, 0), sum(confusion.get(h, {}).values()))
        for h in ("accept", "minor_revision", "major_revision", "reject")
    }
    accs = [c / t for c, t in by_class.values() if t > 0]
    balanced = sum(accs) / len(accs) if accs else None
    print(f"\nmotor dagilim: {motor_dist}")
    print(f"sinif basi dogruluk: {by_class}")
    print(f"sinif-dengeli dogruluk: {balanced * 100:.1f}%" if balanced else "N/A")

    payload = {
        "n_reports": len(all_reports),
        "coverage_flagged": len(coverage_flagged),
        "citation_flagged_new_ss41": len(citation_flagged),
        "citation_only_flagged": len(citation_flagged - coverage_flagged),
        "any_provider_flagged_union": len(any_flagged),
        "clean_after_ss41": len(clean_reports),
        "motor_dagilim": motor_dist,
        "confusion_matrix_insan_satir_motor_sutun": confusion,
        "sinif_basi_dogruluk": {k: {"dogru": v[0], "toplam": v[1]} for k, v in by_class.items()},
        "sinif_dengeli_dogruluk": balanced,
    }
    out = Path(
        r"C:\Users\USER\Desktop\arbitra-main\eval\review\results"
        r"\v8_confusion_and_balanced_accuracy.json"
    )
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nyazildi: {out}")


if __name__ == "__main__":
    main()
