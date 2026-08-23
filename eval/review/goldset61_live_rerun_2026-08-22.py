"""F14 EVAL — 61-goldset CANLI yeniden-koşum (2026-08-22).

BAĞLAM: 2026-08-20/21'de review pipeline'ın 11 mode'u (writer+5critic+editor +
classifier/dimension_engine/qualitative/quantitative) temperature=0+seed=42+
drop_params=True yapıldı — tek-makale (deneme.pdf) 3-run testinde TAM
bit-birebir tutarlılık kanıtlandı. Guardian sordu: bu, goldset'in insan-skor
korelasyonunu (kalibrasyon DOĞRULUĞU, tutarlılıktan AYRI bir şey) etkiliyor
mu — özellikle manuscript_classifier artık deterministik olduğu için, YANLIŞ
sınıflandırma varsa onu da her seferinde sabitleyebilir.

Bu script: eval/review/goldset.json'daki 61 makaleyi (paper_id → yerel PDF
eşlemesi eval/review/results/reference_splitting_bug_2026-08-15/
goldset61_local_filenames.json'dan) CANLI API üzerinden (gerçek LLM+ağ, dev-mode
JWT bypass) analiz eder, raporları diske kaydeder (tekrar-üretilebilirlik +
denetim izi), sonra eval/review/metrics.evaluate() ile insan-skor karşılığını
hesaplar. Ayrı bir küçük alt-küme (SUBSET_FOR_DETERMINISM_CHECK) İKİ KEZ
koşulur — manuscript_classifier'ın document_type/study_design çıktısının
run-to-run AYNI kalıp kalmadığını (doğru ya da yanlış olması FARK ETMEZ,
sadece TUTARLILIK) doğrudan ölçmek için.

Concurrency: backend'in kendi rate-limit/Vertex kotasını aşmamak için
CONCURRENCY sınırlı (varsayılan 5) — semaphore ile.

Çıktı:
  eval/review/results/goldset61_live_reports_2026-08-22/{paper_id}.json  (her rapor)
  eval/review/results/goldset61_live_rerun_2026-08-22_summary.txt        (metrics.format_summary)
  eval/review/results/goldset61_live_rerun_2026-08-22_summary.json       (ham sayılar)
  eval/review/results/goldset61_classifier_determinism_2026-08-22.json  (alt-küme 2. koşum karşılaştırması)
"""

from __future__ import annotations

import asyncio
import io
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import jwt
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.models.review import ReviewReport  # noqa: E402
from eval.review import metrics  # noqa: E402
from eval.review.run_eval import load_goldset, _DEFAULT_GOLDSET  # noqa: E402

BASE = "http://127.0.0.1:8420"
_HERE = Path(__file__).parent
MAPPING_PATH = _HERE / "results" / "reference_splitting_bug_2026-08-15" / "goldset61_local_filenames.json"
PDF_DIRS = [
    Path(r"C:\Users\USER\Desktop\goldset_pdfs"),
    Path(r"C:\Users\USER\Desktop\goldset_pdfs_v2"),
]
REPORTS_DIR = _HERE / "results" / "goldset61_live_reports_2026-08-22"
SUMMARY_TXT = _HERE / "results" / "goldset61_live_rerun_2026-08-22_summary.txt"
SUMMARY_JSON = _HERE / "results" / "goldset61_live_rerun_2026-08-22_summary.json"
DETERMINISM_JSON = _HERE / "results" / "goldset61_classifier_determinism_2026-08-22.json"

POLL_INTERVAL_S = 10
TIMEOUT_S = 900
CONCURRENCY = 5

# alt-küme: manuscript_classifier determinism kontrolü için 2. kez koşulacak
# paper_id'ler — çeşitli kaynak/alan karışımı (openreview/peerread/plos),
# ucuz tutmak için 61'in tamamı DEĞİL.
SUBSET_FOR_DETERMINISM_CHECK: list[str] = []  # main()'de goldset yüklendikten sonra doldurulur, ilk 6 paper_id


def _sanitize(paper_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", paper_id)


def _dev_token(sub: str) -> str:
    return jwt.encode({"sub": sub, "email": f"{sub}@arbitra.local"}, "any-secret", algorithm="HS256")


def _resolve_pdf(filename: str) -> Path | None:
    for d in PDF_DIRS:
        p = d / filename
        if p.exists():
            return p
    return None


async def analyze_one(
    paper_id: str, pdf_path: Path, run_tag: str, sem: asyncio.Semaphore
) -> dict[str, Any]:
    """Tek makaleyi yükle → poll → rapor çek. Senkron requests, thread'e alınır
    (event loop'u bloklamasın diye — CONCURRENCY paralel çalışacak)."""
    async with sem:
        return await asyncio.to_thread(_analyze_one_sync, paper_id, pdf_path, run_tag)


def _analyze_one_sync(paper_id: str, pdf_path: Path, run_tag: str) -> dict[str, Any]:
    result: dict[str, Any] = {"paper_id": paper_id, "run_tag": run_tag}
    # her paper+run_tag kombinasyonu için BENZERSİZ user_id — idempotency
    # çakışmasından kaçınmak için (2026-08-20'de bulunan gerçek bug, bkz
    # temperature_zero_consistency_check.py:_unique_run_sub).
    sub = f"goldset61-{_sanitize(paper_id)}-{run_tag}-{time.time_ns()}"
    token = _dev_token(sub)
    headers = {"Authorization": f"Bearer {token}"}
    t0 = time.time()
    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (pdf_path.name, f, "application/pdf")}
            data = {"mode": "author", "language": "en"}
            resp = requests.post(f"{BASE}/api/review/upload", headers=headers, files=files, data=data, timeout=60)
        if resp.status_code != 200:
            result["error"] = f"upload HTTP {resp.status_code}: {resp.text[:300]}"
            return result
        job_id = resp.json()["job_id"]
        result["job_id"] = job_id
    except Exception as exc:
        result["error"] = f"upload istisnası: {exc}"
        return result

    status = None
    while True:
        elapsed = time.time() - t0
        if elapsed > TIMEOUT_S:
            result["error"] = f"ZAMAN AŞIMI ({TIMEOUT_S}s), son status={status}"
            return result
        try:
            resp = requests.get(f"{BASE}/api/review/{job_id}/status", headers=headers, timeout=15)
            body = resp.json()
            status = body.get("status")
            if status in ("done", "failed"):
                break
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_S)

    result["elapsed_s"] = round(time.time() - t0, 1)
    result["final_status"] = status
    if status == "failed":
        try:
            resp = requests.get(f"{BASE}/api/review/{job_id}/status", headers=headers, timeout=15)
            result["error"] = resp.json().get("error")
        except Exception as exc:
            result["error"] = f"failed-status okunamadı: {exc}"
        return result

    try:
        resp = requests.get(f"{BASE}/api/review/{job_id}/report", headers=headers, timeout=15)
        if resp.status_code != 200:
            result["error"] = f"report HTTP {resp.status_code}: {resp.text[:300]}"
            return result
        report = resp.json()["report"]
    except Exception as exc:
        result["error"] = f"report istisnası: {exc}"
        return result

    result["report"] = report
    dc = report.get("document_classification") or {}
    result["document_type"] = dc.get("document_type")
    result["study_design"] = dc.get("study_design")
    result["verdict"] = report.get("verdict")
    return result


async def run_batch(entries: list[tuple[str, Path]], run_tag: str) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [analyze_one(pid, path, run_tag, sem) for pid, path in entries]
    out: list[dict[str, Any]] = []
    for i, coro in enumerate(asyncio.as_completed(tasks), 1):
        r = await coro
        out.append(r)
        status = "OK" if "error" not in r else f"HATA: {r['error'][:120]}"
        print(f"  [{i}/{len(tasks)}] {r['paper_id']} ({run_tag}) — {status}")
    return out


async def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    goldset = load_goldset(_DEFAULT_GOLDSET)
    mapping: dict[str, str] = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))

    entries: list[tuple[str, Path]] = []
    unresolved: list[str] = []
    for e in goldset.entries:
        fname = mapping.get(e.paper_id)
        pdf_path = _resolve_pdf(fname) if fname else None
        if pdf_path is None:
            unresolved.append(e.paper_id)
            continue
        entries.append((e.paper_id, pdf_path))

    print(f"=== goldset61 canlı yeniden-koşum ===")
    print(f"toplam goldset girdisi: {len(goldset.entries)}, çözülen PDF: {len(entries)}, çözülemeyen: {len(unresolved)}")
    if unresolved:
        print(f"  ÇÖZÜLEMEYEN (atlandı): {unresolved}")
    print(f"concurrency={CONCURRENCY}, tahmini süre ~{len(entries) / CONCURRENCY * 500 / 60:.0f} dk (kaba tahmin)\n")

    t_start = time.time()
    results = await run_batch(entries, "main")
    elapsed_total = time.time() - t_start
    print(f"\n=== ana koşum bitti, {elapsed_total/60:.1f} dk ===\n")

    reports: dict[str, ReviewReport] = {}
    ok_count = 0
    fail_count = 0
    for r in results:
        pid = r["paper_id"]
        (REPORTS_DIR / f"{_sanitize(pid)}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if "report" in r:
            try:
                reports[pid] = ReviewReport.model_validate(r["report"])
                ok_count += 1
            except Exception as exc:
                print(f"  UYARI: {pid} raporu ReviewReport şemasına uymuyor: {exc}")
                fail_count += 1
        else:
            fail_count += 1

    print(f"başarılı rapor: {ok_count}/{len(entries)}, başarısız: {fail_count}/{len(entries)}\n")

    eval_result = metrics.evaluate(reports, goldset)
    summary = metrics.format_summary(eval_result, stanford_ref=goldset.meta.stanford_reference)
    print(summary)
    SUMMARY_TXT.write_text(summary, encoding="utf-8")

    # ham sayılar da JSON olarak (karşılaştırma/analiz kolaylığı için)
    summary_json = {
        "n_entries_total": len(goldset.entries),
        "n_pdf_resolved": len(entries),
        "n_reports_ok": ok_count,
        "n_reports_failed": fail_count,
        "elapsed_total_s": round(elapsed_total, 1),
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

    # --- alt-küme: manuscript_classifier determinism (2. koşum) -------------
    subset = entries[:6]
    print(f"\n=== classifier determinism alt-koşum ({len(subset)} makale, 2. kez) ===\n")
    subset_results_2 = await run_batch(subset, "det2")

    det_compare = []
    first_by_pid = {r["paper_id"]: r for r in results if r["paper_id"] in {p for p, _ in subset}}
    for r2 in subset_results_2:
        pid = r2["paper_id"]
        r1 = first_by_pid.get(pid)
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

    print("\n=== TAMAMEN BİTTİ ===")


if __name__ == "__main__":
    asyncio.run(main())
