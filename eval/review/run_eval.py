"""F14 EVAL — RUNNER (altın-set → motor → metrik raporu).

İki mod:
  --dry-run (varsayılan): motoru ÇAĞIRMAZ. Kayıtlı örnek raporları
      (eval/review/sample_reports.json varsa) ya da boş motor çıktısını kullanır;
      metrik motorunun + altın-set'in CANLI çalıştığını LLM'siz gösterir.
  --live: her gerçek girdi için run_orchestration çağırır (CANLI LLM + ağ +
      Omer key'leri gerekir). PDF indirme/parse henüz bu runner'a bağlı DEĞİL
      (S1 parser entegrasyonu ayrı iş) → şu an --live, hazır Manuscript
      sağlanmadan NotImplementedError ile dürüst durur. Uydurma rapor YOK.

Çıktı: insan-dili özet (metrics.format_summary) + opsiyonel JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from api.models.review import ReviewReport
from eval.review import metrics
from eval.review.schema import GoldSet

_HERE = Path(__file__).resolve().parent
_DEFAULT_GOLDSET = _HERE / "goldset.json"
_SAMPLE_REPORTS = _HERE / "sample_reports.json"


def load_goldset(path: Path) -> GoldSet:
    """goldset.json → GoldSet (extra=forbid doğrular)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return GoldSet.model_validate(raw)


def load_sample_reports(path: Path) -> tuple[dict[str, ReviewReport], bool]:
    """sample_reports.json → (paper_id → ReviewReport, illüstratif_mi).

    İki biçim desteklenir:
      - {"_illustrative": true, "reports": {pid: rapor}}  (işaretli illüstratif)
      - {pid: rapor}  (düz; illüstratif değil sayılır)
    Dosya yoksa ({}, False).
    """
    if not path.exists():
        return {}, False
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "reports" in raw and isinstance(raw["reports"], dict):
        illustrative = bool(raw.get("_illustrative", False))
        body = raw["reports"]
    else:
        illustrative = False
        body = raw
    reports = {pid: ReviewReport.model_validate(rep) for pid, rep in body.items()}
    return reports, illustrative


def run_dry(goldset: GoldSet) -> tuple[metrics.EvalResult, bool]:
    """Motor ÇAĞIRMADAN: kayıtlı örnek raporlarla metrik hesapla.

    Döner: (sonuç, illüstratif_mi). illüstratif=True ise çağıran LOUD uyarı basar
    (bu sayılar KALİTE KANITI değil — sahte başarı raporu yasağı)."""
    reports, illustrative = load_sample_reports(_SAMPLE_REPORTS)
    return metrics.evaluate(reports, goldset), illustrative


def run_live(goldset: GoldSet) -> metrics.EvalResult:
    """CANLI motor koşumu. PDF→Manuscript parse hattı bu runner'a henüz
    bağlı olmadığından, hazır Manuscript sağlanana kadar dürüst durur."""
    raise NotImplementedError(
        "Canlı eval, her altın-set girdisi için hazır Manuscript + EvidencePack "
        "ister (S1 parser entegrasyonu ayrı iş). Omer key'leri + parse hattı "
        "bağlanınca run_orchestration buradan çağrılır. Şimdilik --dry-run kullan."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F14 hakemlik EVAL runner")
    parser.add_argument(
        "--goldset",
        type=Path,
        default=_DEFAULT_GOLDSET,
        help="Altın-set JSON yolu (varsayılan: eval/review/goldset.json)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="CANLI motor koşumu (LLM + key gerekir). Varsayılan: dry-run.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Metrik sonucunu JSON olarak da bu yola yaz.",
    )
    args = parser.parse_args(argv)

    goldset = load_goldset(args.goldset)

    if args.live:
        result = run_live(goldset)
    else:
        result, illustrative = run_dry(goldset)
        if illustrative:
            banner = (
                "!!! İLLÜSTRATİF KOŞUM — BU SAYILAR KALİTE KANITI DEĞİL !!!\n"
                "Örnek raporlar insan skoruna gürültü eklenerek KURGULANDI "
                "(gerçek motor çıktısı değil).\n"
                "Gerçek R-3 kanıtı için: run_eval --live (Omer key + parse hattı)."
            )
            print("\n".join(f"  {line}" for line in banner.splitlines()))
            print()

    summary = metrics.format_summary(
        result, stanford_ref=goldset.meta.stanford_reference
    )
    print(summary)

    if args.json_out is not None:
        payload = {
            "verdict_accuracy": result.verdict_accuracy.__dict__,
            "dimension_agreement": [da.__dict__ for da in result.dimension_agreement],
            "confusion": {
                "labels": list(result.confusion.labels),
                "matrix": result.confusion.matrix,
            },
            "matched_paper_ids": result.matched_paper_ids,
            "unmatched_engine_ids": result.unmatched_engine_ids,
            "skipped_placeholder_ids": result.skipped_placeholder_ids,
        }
        args.json_out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\nJSON yazıldı: {args.json_out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
