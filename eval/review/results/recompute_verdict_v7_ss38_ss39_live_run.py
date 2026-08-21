"""2026-08-11/12 - SS38 (kanitsizlik-guard'i) + SS39 (moat-gate kademelendirmesi)
IKISI BIRDEN aktifken 61 makalelik goldset'in CANLI (yeniden-uretilen degil,
sifirdan LLM+OpenAlex cagrilariyla) kosumunun metriklerini hesaplar.

Onceki v3-v6 recompute scriptlerinden farki: bunlar HEP AYNI, onceden-uretilmis
findings/risk_radar/evidence_pack verisini (goldset_live_reports_v5) yeniden
puanliyordu (sadece karar mantigi degisiyordu). BU script ise goldset_full_
rerun_v7.py'nin URETTIGI TAMAMEN YENI 61 rapor uzerinde calisir - findings'in
kendisi de bu kosumda YENIDEN uretildi (LLM stokastik, deterministik degil).

Guardian bulgusu (2026-08-12): moat_grounding_accuracy'nin bu kosumdaki "%100"
sonucu KISMEN DAIRESEL - guard zaten ungrounded critical/major'i moderate'e
indirip metrigin kapsaminin DISINA cikariyor, kalanin "kanitli" cikmasi
guard'in VAR OLDUGUNU kanitlar, iyi KALIBRE oldugunu degil (yanlis-negatif
orani - guard'in gercek sahtecilik vakalarini yanlislikla indirip indirmedigi -
hic olculemiyor, bagimsiz ground truth yok).

Ayrica: review_citation_service.py:308-329'daki resolve_reference SESSIZ
OpenAlex-hata-fallback'i (not_found_in_index'e duser) hicbir degraded_features
flag'i URETMIYOR (sadece find_coverage_gaps basarisizligi coverage:openalex_
unavailable flag'i aliyor) - yani asagidaki "coverage-flagli/temiz" ayrimi
GERCEK kontaminasyonun bir ALT SINIRI, tam olcum degil.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")

from api.models.review import ReviewReport  # noqa: E402
from eval.review import metrics  # noqa: E402
from eval.review.run_eval import load_goldset, _DEFAULT_GOLDSET  # noqa: E402

REPORTS_DIR = Path(
    r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main"
    r"\492975e2-533f-4eaf-b2e8-4d52c4badcb1\scratchpad\goldset_live_reports_v7"
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

    clean_reports = {
        pid: rep
        for pid, rep in all_reports.items()
        if not any("openalex_unavailable" in d for d in rep.evidence_pack.degraded_features)
    }

    for label, reports in (("TUM 61", all_reports), (f"COVERAGE-FLAGSIZ ALT-KUME ({len(clean_reports)})", clean_reports)):
        print(f"\n=== {label} ===")
        result = metrics.evaluate(reports, goldset)
        summary = metrics.format_summary(result, stanford_ref=goldset.meta.stanford_reference)
        print(summary.encode("ascii", "replace").decode("ascii"))

    # sinif-dengeli dogruluk (metrics.py'de yok, ayri hesaplaniyor - guardian
    # bulgusu: bu SS29'dan beri bilinen bir bosluk, ham/pooled accuracy class-
    # imbalance altinda yanlis).
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


if __name__ == "__main__":
    main()
