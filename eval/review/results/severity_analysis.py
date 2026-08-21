"""2026-08-08 - moat-gate'in %87 major-severity bulgusunun kok nedeni arastirmasi.

61 makalenin (LLM'e yeniden gidilmeden, zaten var olan pipeline ciktilarindan)
findings listesini tarar; severity dagilimini moat/moat-disi, alt-boyut ve
kaynak (openreview/peerj/peerread) kirilimlariyla raporlar.

REPORTS_DIR bu makinedeki oturuma ozgu scratchpad yolu - ham 61 rapor repoya
commit edilmedi (buyuk, LLM ciktisi). Bkz. eval/review/results/README.md.
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")

from api.models.review import ReviewReport  # noqa: E402
from eval.review.run_eval import load_goldset, _DEFAULT_GOLDSET  # noqa: E402

REPORTS_DIR = Path(
    r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main"
    r"\492975e2-533f-4eaf-b2e8-4d52c4badcb1\scratchpad\goldset_live_reports"
)
MOAT_DIMENSION_IDS = {"citation_integrity", "literature_positioning", "literature_depth"}


def is_moat(finding) -> bool:
    return finding.dimension in MOAT_DIMENSION_IDS or finding.finding_id.startswith("quant.")


def main() -> None:
    reports = []
    for f in REPORTS_DIR.glob("*.json"):
        if "_all_results" in f.name or "real_metrics" in f.name:
            continue
        entry = json.loads(f.read_text(encoding="utf-8"))
        rep_dict = entry.get("report")
        if rep_dict is None:
            continue
        reports.append((entry["paper_id"], ReviewReport.model_validate(rep_dict)))

    n = len(reports)
    moat_sev, non_moat_sev = Counter(), Counter()
    moat_hi, non_moat_hi = 0, 0
    major_by_dim, critical_by_dim = Counter(), Counter()
    total_by_dim = Counter()
    by_source = {}

    for pid, rep in reports:
        has_moat_hi = has_nonmoat_hi = False
        src = pid.split(":")[0]
        by_source.setdefault(src, [0, 0])
        by_source[src][1] += 1
        sp_major = False
        for finding in rep.findings:
            total_by_dim[finding.dimension] += 1
            if is_moat(finding):
                moat_sev[finding.severity] += 1
                if finding.severity in ("major", "critical"):
                    has_moat_hi = True
                if finding.severity == "major":
                    major_by_dim[finding.dimension] += 1
                    if finding.dimension in ("sample_and_power", "effect_size_and_uncertainty"):
                        sp_major = True
                elif finding.severity == "critical":
                    critical_by_dim[finding.dimension] += 1
            else:
                non_moat_sev[finding.severity] += 1
                if finding.severity in ("major", "critical"):
                    has_nonmoat_hi = True
        if has_moat_hi:
            moat_hi += 1
        if has_nonmoat_hi:
            non_moat_hi += 1
        if sp_major:
            by_source[src][0] += 1

    print(f"{n} rapor tarandi\n")
    print("MOAT severity dagilimi:", dict(moat_sev))
    print(f"moat critical+major iceren makale: {moat_hi}/{n} ({moat_hi/n*100:.0f}%)\n")
    print("MOAT-DISI severity dagilimi:", dict(non_moat_sev))
    print(f"moat-disi critical+major iceren makale: {non_moat_hi}/{n} ({non_moat_hi/n*100:.0f}%)\n")

    print("=== major severity - moat alt-boyut dagilimi ===")
    for k, v in major_by_dim.most_common(15):
        print(f"  {k}: major={v}/{total_by_dim[k]} kez ({v/n*100:.0f}% makalede)")
    print("\n=== critical severity - moat alt-boyut dagilimi ===")
    for k, v in critical_by_dim.most_common(15):
        print(f"  {k}: critical={v}/{total_by_dim[k]} kez ({v/n*100:.0f}% makalede)")

    print("\n=== kaynak bazinda sample_and_power/effect_size 'major' orani ===")
    for src, (n_yes, n_total) in by_source.items():
        print(f"  {src}: {n_yes}/{n_total} ({n_yes/n_total*100:.0f}%)")


if __name__ == "__main__":
    main()
