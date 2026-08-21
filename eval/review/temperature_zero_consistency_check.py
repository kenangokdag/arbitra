"""F14 — temperature=0 düzeltmesinin gerçekten işe yaradığını kanıtlama koşusu.

BAĞLAM (2026-08-20, kullanıcı bulgusu): aynı makale art arda analiz edilince
farklı sonuç çıkıyordu ("3 major konu eksik" → "1"). Kök neden: review
pipeline'ın 7 aşaması (writer + 5 critic + editor) temperature>0 ile
örnekleme yapıyordu, seed hiç yoktu. Düzeltme: llm_service.py'de bu 7 mode
için temperature=0.0 (bkz _REVIEW_PIPELINE_MODES).

Bu script "temperature 0'a çekildi, unit test yeşil" YETERLİ DEĞİL —
kullanıcının kabul kriteri: aynı PDF'i art arda EN AZ 3 kez analiz et,
her run'ın verdict + 10 boyutun tamamının skoru + overall_readiness_score +
major/critical bulgu sayısını karşılaştır.

Gerçek API kullanır (POST /upload -> GET /status -> GET /report), dev-mode
JWT bypass ile — continuous_diversity_test.py ile AYNI desen (bkz o dosya).
Sunucunun zaten çalışıyor olması gerekir.

Çıktı: eval/review/results/temperature_zero_consistency_log.jsonl (append)
+ konsola karşılaştırma tablosu.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import jwt
import requests

BASE = "http://127.0.0.1:8420"
# 2026-08-20 devamı (seed eklendi): aynı script'i seed+temp=0 koşusu için de
# kullanabilmek üzere log dosya adı env var ile override edilebiliyor —
# iki koşu setinin sonucu birbirine karışmasın diye (bkz
# temperature_zero_seed_consistency_log.jsonl).
_LOG_NAME = os.environ.get("TZC_LOG_NAME", "temperature_zero_consistency_log.jsonl")
RESULTS_LOG = Path(__file__).parent / "results" / _LOG_NAME
POLL_INTERVAL_S = 10
TIMEOUT_S = 900
N_RUNS = 3

# gerçek dosya konumu doğrulandı (Glob/Read ile) — continuous_diversity_test.py'deki
# `C:\Users\USER\Desktop\deneme.pdf` yolu artık YANLIŞ/eski, dosya taşınmış.
PDF_PATH = Path(r"C:\Users\USER\Desktop\masaüstüson 1708\deneme.pdf")

DIMENSION_KEYS = [
    "originality",
    "importance",
    "claims_supported",
    "soundness",
    "clarity",
    "community_value",
    "contextualization",
    "citation_integrity",
    "coverage_completeness",
    "statistical_consistency",
]


def _dev_token(sub: str) -> str:
    return jwt.encode({"sub": sub, "email": f"{sub}@arbitra.local"}, "any-secret", algorithm="HS256")


# 2026-08-20 BULUNAN GERÇEK HATA: idempotency_key = sha256(dosya bytes + mode +
# language) (api/routes/review.py:83-93, _content_key), aynı (user_id, key) →
# AYNI job döner (review_service.py:289-306, BE-1). run_idx'e göre sabit
# "temp-zero-check-run-N" sub kullanmak, script'i FARKLI zamanlarda tekrar
# çalıştırınca (aynı run_idx → aynı user_id → aynı dosya → aynı key) YENİ analiz
# YAPMADAN eski job'u geri döndürüyordu (elapsed_s~1-3s, imkansız hız —
# ilk seferde bu YAKALANDI, temperature_zero_seed_consistency_log.jsonl'deki
# ilk 3 satır SİLİNMELİ/görmezden gelinmeli, gerçek değil). Fix: her invocation
# gerçekten benzersiz bir user_id alsın (run başlangıç zamanı + random) —
# idempotency scope'unu HER SEFERİNDE kaçıracak, gerçek yeni analiz tetiklenir.
def _unique_run_sub(run_idx: int) -> str:
    import random

    return f"tzc-{run_idx}-{time.time_ns()}-{random.randint(0, 999999)}"


async def run_once(run_idx: int) -> dict[str, Any]:
    result: dict[str, Any] = {"run_idx": run_idx, "run_started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    token = _dev_token(_unique_run_sub(run_idx))
    headers = {"Authorization": f"Bearer {token}"}
    t0 = time.time()

    try:
        with open(PDF_PATH, "rb") as f:
            files = {"file": (PDF_PATH.name, f, "application/pdf")}
            data = {"mode": "author", "language": "tr"}
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
        await asyncio.sleep(POLL_INTERVAL_S)

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

    findings = report.get("findings") or []
    severity_counts: dict[str, int] = {}
    for fnd in findings:
        sev = fnd.get("severity", "?")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    dim_scores = {d.get("key"): d.get("score") for d in (report.get("dimension_scores") or [])}
    ev = report.get("executive_verdict") or {}

    result["verdict"] = report.get("verdict")
    result["final_score_1_10"] = report.get("final_score")
    result["overall_readiness_score_0_100"] = ev.get("overall_readiness_score")
    result["recommended_decision"] = ev.get("recommended_decision")
    result["n_findings_total"] = len(findings)
    result["severity_counts"] = severity_counts
    result["n_major_or_critical"] = severity_counts.get("major", 0) + severity_counts.get("critical", 0)
    result["dimension_scores"] = {k: dim_scores.get(k) for k in DIMENSION_KEYS}
    result["judgment_reproducible_flag"] = (report.get("provenance") or {}).get("judgment_reproducible")
    return result


def _print_comparison(runs: list[dict[str, Any]]) -> None:
    print("\n=== KARŞILAŞTIRMA (3 run) ===")
    print(f"{'alan':<28}" + "".join(f"run{r['run_idx']:<12}" for r in runs))
    print(f"{'verdict':<28}" + "".join(f"{str(r.get('verdict')):<15}" for r in runs))
    print(f"{'overall_readiness_score':<28}" + "".join(f"{str(r.get('overall_readiness_score_0_100')):<15}" for r in runs))
    print(f"{'n_major_or_critical':<28}" + "".join(f"{str(r.get('n_major_or_critical')):<15}" for r in runs))
    print(f"{'n_findings_total':<28}" + "".join(f"{str(r.get('n_findings_total')):<15}" for r in runs))
    print()
    for key in DIMENSION_KEYS:
        vals = [r.get("dimension_scores", {}).get(key) for r in runs]
        same = len(set(vals)) == 1
        marker = "  " if same else "!!"
        print(f"{marker} {key:<25}" + "".join(f"{str(v):<15}" for v in vals))

    verdicts_same = len({r.get("verdict") for r in runs}) == 1
    scores_same = len({r.get("overall_readiness_score_0_100") for r in runs}) == 1
    dims_same = all(
        len({r.get("dimension_scores", {}).get(k) for r in runs}) == 1 for k in DIMENSION_KEYS
    )
    print("\n=== SONUÇ ===")
    print(f"verdict tutarlı: {verdicts_same}")
    print(f"overall_readiness_score tutarlı: {scores_same}")
    print(f"10 boyutun tamamı tutarlı: {dims_same}")
    if verdicts_same and scores_same and dims_same:
        print("KABUL KRİTERİ KARŞILANDI — temperature=0 fix'i 3 run boyunca tam bit-birebir tutarlı sonuç verdi.")
    else:
        print("KABUL KRİTERİ KARŞILANMADI (veya kısmen) — yukarıdaki '!!' satırlarına bak.")


async def main() -> None:
    RESULTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not PDF_PATH.exists():
        print(f"HATA: PDF bulunamadı: {PDF_PATH}")
        return

    print(f"=== {N_RUNS} run, sırayla, aynı PDF ({PDF_PATH.name}) ===")
    print(f"log: {RESULTS_LOG}\n")

    runs: list[dict[str, Any]] = []
    for i in range(1, N_RUNS + 1):
        print(f"--- run {i}/{N_RUNS} ---")
        r = await run_once(i)
        runs.append(r)
        with open(RESULTS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        if "error" in r:
            print(f"  HATA: {r['error']}")
        else:
            print(
                f"  verdict={r.get('verdict')} overall_readiness={r.get('overall_readiness_score_0_100')} "
                f"major/critical={r.get('n_major_or_critical')} elapsed={r.get('elapsed_s')}s"
            )
        print()

    ok_runs = [r for r in runs if "error" not in r]
    if len(ok_runs) < 2:
        print("Karşılaştırma yapılamıyor — en az 2 başarılı run yok.")
        return
    _print_comparison(ok_runs)


if __name__ == "__main__":
    asyncio.run(main())
