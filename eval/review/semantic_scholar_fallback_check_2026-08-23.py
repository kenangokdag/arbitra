"""2026-08-23 — S2 fallback öncesi/sonrası karşılaştırması (kullanıcı+guardian
onaylı test planı).

3 OpenReview makalesi (goldset.json'daki AYNI 3 paper_id, önceki 2026-08-22
koşumunda ZATEN analiz edilmişti — "önce" verisi
eval/review/results/goldset61_live_reports_2026-08-22/openreview_*.json'da
hazır) S2 fallback AKTİFKEN yeniden canlı analiz edilir. Karşılaştırılan:
  - not_found_in_index sayısı (düştü mü?)
  - semantic_scholar_recovered sayısı (yeni alan, kaç referans S2'den geldi?)
  - citation_integrity dimension score (guardian'ın sorusu: sadece sayı değil,
    kalibrasyon etkisi de ölçülüyor mu?)
  - verdict (insan etiketine yakınsıyor mu?)
insan-etiketiyle (goldset.json human_verdict) karşılaştırılır.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import importlib.util

_HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("g61", _HERE / "goldset61_live_rerun_2026-08-22.py")
g61 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g61)  # type: ignore[union-attr]

from eval.review.run_eval import load_goldset, _DEFAULT_GOLDSET  # noqa: E402

BEFORE_DIR = _HERE / "results" / "goldset61_live_reports_2026-08-22"
AFTER_DIR = _HERE / "results" / "semantic_scholar_fallback_reports_2026-08-23"
SUMMARY_JSON = _HERE / "results" / "semantic_scholar_fallback_check_2026-08-23.json"

TEST_PAPER_IDS = ["openreview:w7P92BEsb2", "openreview:imT03YXlG2", "openreview:PwxYoMvmvy"]


def _before_data(paper_id: str) -> dict:
    fname = g61._sanitize(paper_id) + ".json"
    raw = json.loads((BEFORE_DIR / fname).read_text(encoding="utf-8"))
    report = raw.get("report") or {}
    ci = (report.get("evidence_pack") or {}).get("citation_integrity") or {}
    dims = {d["key"]: d["score"] for d in (report.get("dimension_scores") or [])}
    return {
        "not_found_in_index": ci.get("not_found_in_index"),
        "resolved": ci.get("resolved"),
        "total": ci.get("total"),
        "semantic_scholar_recovered": ci.get("semantic_scholar_recovered", 0),
        "citation_integrity_score": dims.get("citation_integrity"),
        "verdict": report.get("verdict"),
    }


async def _after_data(paper_id: str, pdf_path: Path) -> dict:
    AFTER_DIR.mkdir(parents=True, exist_ok=True)
    r = await asyncio.to_thread(g61._analyze_one_sync, paper_id, pdf_path, "s2after")
    (AFTER_DIR / (g61._sanitize(paper_id) + ".json")).write_text(
        json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if "report" not in r:
        return {"error": r.get("error", "?")}
    report = r["report"]
    ci = (report.get("evidence_pack") or {}).get("citation_integrity") or {}
    dims = {d["key"]: d["score"] for d in (report.get("dimension_scores") or [])}
    return {
        "not_found_in_index": ci.get("not_found_in_index"),
        "resolved": ci.get("resolved"),
        "total": ci.get("total"),
        "semantic_scholar_recovered": ci.get("semantic_scholar_recovered", 0),
        "citation_integrity_score": dims.get("citation_integrity"),
        "verdict": report.get("verdict"),
        "elapsed_s": r.get("elapsed_s"),
    }


async def main() -> None:
    goldset = load_goldset(_DEFAULT_GOLDSET)
    human = {e.paper_id: e.human_verdict for e in goldset.entries}
    mapping: dict[str, str] = json.loads(g61.MAPPING_PATH.read_text(encoding="utf-8"))

    results = []
    for pid in TEST_PAPER_IDS:
        print(f"--- {pid} ---")
        before = _before_data(pid)
        fname = mapping[pid]
        pdf_path = g61._resolve_pdf(fname)
        if pdf_path is None:
            print(f"  PDF bulunamadı, atlanıyor")
            continue
        t0 = time.time()
        after = await _after_data(pid, pdf_path)
        print(f"  önce: not_found={before['not_found_in_index']}/{before['total']}, "
              f"citation_integrity={before['citation_integrity_score']}, verdict={before['verdict']}")
        print(f"  sonra: not_found={after.get('not_found_in_index')}/{after.get('total')}, "
              f"s2_recovered={after.get('semantic_scholar_recovered')}, "
              f"citation_integrity={after.get('citation_integrity_score')}, "
              f"verdict={after.get('verdict')} ({time.time()-t0:.0f}s)")
        print(f"  insan etiketi: {human.get(pid)}")
        results.append({"paper_id": pid, "human_verdict": human.get(pid), "before": before, "after": after})
        print()

    SUMMARY_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"yazıldı: {SUMMARY_JSON}")


if __name__ == "__main__":
    asyncio.run(main())
