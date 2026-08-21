"""Plan docs/plans/SOUNDNESS_SEVERITY_CONTEXT_SENSITIVITY_2026-08-13.md, test
planı Adım 1: `_downgrade_design_mismatched_quant_findings()` guard'ını (LLM'e
HİÇ gitmeden) v8'in 61 STORED raporundaki gerçek Finding'lere + document_
classification'a offline uygulayıp soundness skor dağılımının ve GERÇEK insan-
soundness korelasyonunun nasıl değiştiğini hesaplar.

ÖNEMLİ (guardian bulgusu, 2026-08-13): bu "v8 canlı-koşum" veri seti (61 makale:
5 ICLR OpenReview + 6 PeerJ + 50 PeerRead) resmi `eval/review/goldset.json`
(11 girdi, Spearman≈0.42 R-3 hedefinin bağlı olduğu set) İLE AYNI ŞEY DEĞİL —
goldset'in genişletilmiş bir üst-kümesi/farklı bir çalışma seti. Bu script'in
insan-skoru kaynağı yine `load_goldset(_DEFAULT_GOLDSET)` (61 girdi de o dosyada
kayıtlı, `source` alanına göre ayrışıyor) — ama "resmi R-3 goldset'ine karşı
doğrulandı" diye SUNULMAMALI, "genişletilmiş 61-makale setine karşı" diye
çerçevelenmeli (CLAUDE.md'nin goldset-doğrulama disiplinine sadık kalmak için).

Ham veri (61 rapor JSON) repoda DEĞİL, session scratchpad'inde — bu script'i
tekrar çalıştırmak için REPORTS_DIR'i güncel bir scratchpad'e işaret etmek
gerekir (goldset_live_run_v8.py ile üretilir, PDF_PIPELINE_CALISMA_GUNLUGU.md
§40-41).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")

from api.models.review import Finding  # noqa: E402
from engine.academic._engine_base import EngineResult  # noqa: E402
from engine.academic.assessment import (  # noqa: E402
    _downgrade_design_mismatched_quant_findings,
)
from eval.review.run_eval import _DEFAULT_GOLDSET, load_goldset  # noqa: E402

REPORTS_DIR = Path(
    r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main"
    r"\3e56c8a7-1c60-4124-9a6a-0f99102f8e39\scratchpad\goldset_live_reports_v8"
)

# report_synthesis.py::RADAR_SEVERITY_PENALTY ile BİREBİR aynı değerler
# (2026-08-13'te ayrıca guardian tarafından dosya:satır ile doğrulandı,
# report_synthesis.py:79-85).
RADAR_SEVERITY_PENALTY = {
    "critical": 45.0,
    "major": 25.0,
    "moderate": 12.0,
    "minor": 5.0,
    "info": 0.0,
}

# report_synthesis.py::_DIMENSION_KEYWORD_MAP'in "methodology" kovasına giren
# GERÇEK anahtar kelimeler (basitleştirilmiş yaklaşım — tam kod yolu değil,
# sadece bu guard'ın İZOLE ETKİSİNİ görmek için; "stat"/"analysis"/"significan"
# gibi ÖNCELİKLİ statistics-kovası anahtar kelimeleri KASITLI dışarıda, gerçek
# haritadaki sıra-önceliğine yakın davranış için).
_METHODOLOGY_KEYWORDS = ("method", "sample", "technical_correct", "soundness", "rigor", "validity")


def recompute_methodology_score(findings: list[dict]) -> float:
    penalty = sum(
        RADAR_SEVERITY_PENALTY.get(f.get("severity"), 0.0)
        for f in findings
        if any(k in f.get("dimension", "") for k in _METHODOLOGY_KEYWORDS)
    )
    radar_score = max(0.0, 100.0 - penalty)
    return round(1.0 + radar_score / 100.0 * 9.0, 2)


def main() -> None:
    goldset = load_goldset(_DEFAULT_GOLDSET)
    human_soundness = {
        e.paper_id: e.human_scores.get("soundness")
        for e in goldset.entries
        if "soundness" in e.human_scores
    }

    before_scores: list[float] = []
    after_scores: list[float] = []
    before_pairs: list[tuple[float, float]] = []
    after_pairs: list[tuple[float, float]] = []
    n_triggered = 0

    for f in REPORTS_DIR.glob("*.json"):
        entry = json.loads(f.read_text(encoding="utf-8"))
        rep = entry.get("report")
        if rep is None:
            continue
        pid = entry["paper_id"]
        dc = rep.get("document_classification") or {}
        study_design = dc.get("study_design", "unknown")
        study_design_confidence = dc.get("study_design_confidence", 0.0)

        findings_raw = rep.get("findings", [])
        before = recompute_methodology_score(findings_raw)

        models = [Finding.model_validate(x) for x in findings_raw]
        er = EngineResult(findings=models, action_items=[], degraded=[])
        er2 = _downgrade_design_mismatched_quant_findings(
            er, study_design, study_design_confidence
        )
        if any(d.startswith("quant_design_mismatch:downgraded_") for d in er2.degraded):
            n_triggered += 1
        after = recompute_methodology_score([x.model_dump(mode="json") for x in er2.findings])

        before_scores.append(before)
        after_scores.append(after)
        if pid in human_soundness:
            before_pairs.append((before, human_soundness[pid]))
            after_pairs.append((after, human_soundness[pid]))

    print(f"n makale: {len(before_scores)}, guard tetiklenen: {n_triggered}")
    print(f"ONCESI en yaygin: {Counter(before_scores).most_common(1)[0]}")
    print(f"SONRASI en yaygin: {Counter(after_scores).most_common(1)[0]}")

    try:
        from scipy import stats

        n = len(before_pairs)
        be, bh = zip(*before_pairs)
        ae, ah = zip(*after_pairs)
        sp_before = stats.spearmanr(be, bh)
        sp_after = stats.spearmanr(ae, ah)
        print(f"\nn (insan-soundness-skorlu alt-kume) = {n}")
        print(f"ONCESI Spearman: r={sp_before.statistic:.4f} p={sp_before.pvalue:.4f}")
        print(f"SONRASI Spearman: r={sp_after.statistic:.4f} p={sp_after.pvalue:.4f}")
        result = {
            "n_total": len(before_scores),
            "n_triggered": n_triggered,
            "before_most_common": Counter(before_scores).most_common(1)[0],
            "after_most_common": Counter(after_scores).most_common(1)[0],
            "n_human_scored": n,
            "spearman_before": {"r": sp_before.statistic, "p": sp_before.pvalue},
            "spearman_after": {"r": sp_after.statistic, "p": sp_after.pvalue},
        }
        out = Path(__file__).parent / "soundness_guard_offline_effect_2026-08-13.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nyazildi: {out}")
    except ImportError:
        print("scipy yok, korelasyon hesaplanamadi")


if __name__ == "__main__":
    main()
