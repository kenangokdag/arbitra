"""F14 — sürekli, çok-alanlı/çok-study_design uçtan uca test döngüsü.

AMAÇ: pipeline'ın tek bir makaleyle değil, farklı disiplin ve study_design
kombinasyonlarında TUTARLI çalıştığını göstermek — tek seferlik manuel deneme
DEĞİL, tekrar tekrar çalıştırılabilir bir test seti (Kenan, 2026-08-14 talebi).

Gerçek API'yi kullanır (POST /upload -> GET /status -> GET /report), dev-mode
JWT bypass ile (api/middleware/auth.py case 3 — imza doğrulanmıyor). Sunucunun
zaten çalışıyor olması gerekir: `uvicorn api.main:app --host 127.0.0.1 --port 8420`.

Her koşum, `results/continuous_diversity_log.jsonl` dosyasına BİR SATIR olarak
EKLENİR (append, üzerine yazmaz) — böylece zaman içinde tutarlılık izlenebilir.
Her satır: paper_id, çalıştırma zamanı, verdict, final_score, degraded_features
(hangi guard/downgrade tetiklendi), document_classification, elapsed_s, hata
(varsa).

KAPSAM DÜRÜSTLÜĞÜ (2026-08-14 tespiti): mevcut yerel PDF havuzunda (61-goldset +
retraction-candidate'ler) HİÇ qualitative veya mixed_methods sınıflı makale yok
(sadece computational_modeling=53, quantitative=6, theoretical=1, unknown=1
gözlendi — bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md §"diversity test" notu). Bu script
QUALITATIVE_PLOS girdisini YENİ, gerçek, açık-erişimli (CC BY) bir PLOS ONE
makalesiyle kapatıyor; MIXED_METHODS için henüz doğrulanmış gerçek bir yerel PDF
YOK — bkz. TEST_CASES altındaki not.
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import jwt
import requests

BASE = "http://127.0.0.1:8420"
RESULTS_LOG = Path(__file__).parent / "results" / "continuous_diversity_log.jsonl"
POLL_INTERVAL_S = 10
TIMEOUT_S = 900


@dataclass
class TestCase:
    case_id: str
    pdf_path: str
    expected_study_design_hint: str  # önceden bilinen/varsayılan sınıflandırma, sadece etiketleme amaçlı
    discipline_hint: str


TEST_CASES: list[TestCase] = [
    TestCase("deneme_education_quant", r"C:\Users\USER\Desktop\deneme.pdf", "quantitative", "eğitim bilimleri"),
    TestCase("peerj_4181_quant", r"C:\Users\USER\Desktop\goldset_pdfs\peerj-4181.pdf", "quantitative", "biyoloji/sağlık (PeerJ)"),
    TestCase("peerj_cs3113_quant", r"C:\Users\USER\Desktop\goldset_pdfs\peerj-cs-3113.pdf", "quantitative", "bilgisayar bilimi (PeerJ CS)"),
    TestCase("openreview_odjMSBSWRt_quant", r"C:\Users\USER\Desktop\goldset_pdfs\openreview_odjMSBSWRt.pdf", "quantitative", "ML (OpenReview)"),
    TestCase("peerread_iclr2017_398_theoretical", r"C:\Users\USER\Desktop\goldset_pdfs_v2\peerread_iclr2017_398.pdf", "theoretical", "ML/CS (PeerRead ICLR2017)"),
    TestCase("pied_physics_compmodel", r"C:\Users\USER\Desktop\goldset_pdfs\14224_PIED_Physics_Informed_Ex.pdf", "computational_modeling", "fizik/mühendislik (physics-informed ML)"),
    TestCase(
        "plos_qualitative_sierra_leone",
        r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main\3e56c8a7-1c60-4124-9a6a-0f99102f8e39\scratchpad\qualitative_plos_0294391.pdf",
        "qualitative",
        "halk sağlığı (PLOS ONE, gerçek nitel görüşme çalışması, DOI 10.1371/journal.pone.0294391)",
    ),
    # 2026-08-14 genişletme: sistematik derleme/meta-analiz, mixed_methods,
    # mühendislik disiplini eklendi (gerçek, açık-erişim PLOS ONE makaleleri).
    TestCase(
        "plos_meta_analysis_sport_education",
        r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main\3e56c8a7-1c60-4124-9a6a-0f99102f8e39\scratchpad\meta_analysis_sport_education_0331228.pdf",
        "meta_analysis/systematic_review",
        "beden eğitimi/spor bilimleri (PLOS ONE, gerçek meta-analiz, DOI 10.1371/journal.pone.0331228)",
    ),
    TestCase(
        "plos_mixed_methods_covid_returntoclass",
        r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main\3e56c8a7-1c60-4124-9a6a-0f99102f8e39\scratchpad\mixed_methods_covid_returntoclass_0279813.pdf",
        "mixed_methods",
        "halk sağlığı/eğitim (PLOS ONE, gerçek sequential explanatory mixed-methods çalışma, DOI 10.1371/journal.pone.0279813)",
    ),
    TestCase(
        "plos_engineering_sustainability",
        r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main\3e56c8a7-1c60-4124-9a6a-0f99102f8e39\scratchpad\engineering_sustainability_0294421.pdf",
        "quantitative",
        "mühendislik eğitimi (PLOS ONE, gerçek ampirik çalışma, DOI 10.1371/journal.pone.0294421)",
    ),
    # 2026-08-15: Güzel sanatlar/tasarım boşluğu kapatıldı — International
    # Journal of Design (ijdesign.org, CC BY 4.0) gerçek ampirik bir tasarım
    # araştırması makalesi bulundu (etkileşimli cihaz + anksiyeteli bağlanma
    # üzerine deneysel çalışma).
    TestCase(
        "ijdesign_anxious_attachment_device",
        r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main\3e56c8a7-1c60-4124-9a6a-0f99102f8e39\scratchpad\design_anxious_attachment_4907.pdf",
        "quantitative",
        "tasarım araştırması/etkileşim tasarımı (International Journal of Design, gerçek deneysel çalışma, Vol 18(2) 2024)",
    ),
]


def _dev_token(sub: str) -> str:
    return jwt.encode({"sub": sub, "email": f"{sub}@arbitra.local"}, "any-secret", algorithm="HS256")


def _extract_guard_signals(report: dict) -> list[str]:
    """report.evidence_pack.degraded_features + report.action_plan vb. içinden
    guard/downgrade tetiklenme izlerini çıkar (string prefix eşleşmesiyle,
    assessment.py'deki gerçek sabitlere karşı — icat değil, kod referansı:
    engine/academic/assessment.py::_downgrade_design_mismatched_quant_findings,
    engine/academic/assessment.py::_downgrade_ungrounded_citation_findings)."""
    signals: list[str] = []
    ep = report.get("evidence_pack") or {}
    degraded = ep.get("degraded_features") or []
    for d in degraded:
        if "quant_design_mismatch" in d or "citation_integrity_grounding" in d or "downgrad" in d:
            signals.append(d)
    return signals


async def run_case(case: TestCase) -> dict:
    result: dict = {
        "case_id": case.case_id,
        "pdf_path": case.pdf_path,
        "expected_study_design_hint": case.expected_study_design_hint,
        "discipline_hint": case.discipline_hint,
        "run_started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    pdf_file = Path(case.pdf_path)
    if not pdf_file.exists():
        result["error"] = f"PDF bulunamadı: {case.pdf_path}"
        return result

    token = _dev_token(f"continuous-test-{case.case_id}")
    headers = {"Authorization": f"Bearer {token}"}
    t0 = time.time()

    try:
        with open(pdf_file, "rb") as f:
            files = {"file": (pdf_file.name, f, "application/pdf")}
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
            pass  # geçici ağ hatası — döngü devam eder, TIMEOUT_S sınırı zaten var
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

    dc = report.get("document_classification") or {}
    result["verdict"] = report.get("verdict")
    result["final_score"] = report.get("final_score")
    result["n_findings"] = len(report.get("findings") or [])
    result["study_design_actual"] = dc.get("study_design")
    result["study_design_confidence"] = dc.get("study_design_confidence")
    result["document_type"] = dc.get("document_type")
    result["guard_signals"] = _extract_guard_signals(report)
    return result


async def main():
    RESULTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    print(f"=== {len(TEST_CASES)} test case, sirayla calistiriliyor ===")
    print(f"log dosyasi: {RESULTS_LOG}")
    print()
    for case in TEST_CASES:
        print(f"--- {case.case_id} ({case.discipline_hint}, beklenen study_design={case.expected_study_design_hint}) ---")
        r = await run_case(case)
        with open(RESULTS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        if "error" in r:
            print(f"  HATA: {r['error']}")
        else:
            print(f"  verdict={r.get('verdict')} final_score={r.get('final_score')} "
                  f"study_design_actual={r.get('study_design_actual')} "
                  f"guard_signals={r.get('guard_signals')} elapsed={r.get('elapsed_s')}s")
        print()
    print("=== bitti ===")


if __name__ == "__main__":
    asyncio.run(main())
