# Moat-gate / skor-tabanlı verdict kalibrasyonu — koşum kanıtları (2026-08-08)

Bu klasör, `PDF_PIPELINE_CALISMA_GUNLUGU.md` §29/§30'da anlatılan sayıların
(verdict tam isabet, tolerans, moat-gate tetikleme sayıları) tekrar
üretilebilir kanıtıdır — guardian'ın "dangling rakam" bulgusuna cevap.

## Ne var, ne yok

- `recompute_verdict_v3_score_thresholds.py` / `recompute_verdict_v4_moat_gate.py`:
  gerçek `engine.academic.report_synthesis.build_executive_verdict()`'i,
  61 makalenin **zaten var olan** (LLM'e yeniden gidilmeden) `findings`/
  `risk_radar`'ından yeniden çağıran script'ler. `REPORTS_DIR` bu makinedeki
  oturuma özgü scratchpad yolunu gösteriyor — o 61 ham rapor JSON'u (her biri
  LLM çıktısı, büyük) repoya COMMIT EDİLMEDİ, sadece bu script'lerin ürettiği
  ÖZET sayılar (`real_metrics_result_v*.json/.txt`) tutuluyor.
- `real_metrics_result_v3_score_thresholds.{json,txt}`: sadece
  `ACCEPT_READINESS_THRESHOLD`/`REJECT_READINESS_THRESHOLD` (moat-gate YOK)
  uygulanınca — %62 tam isabet, %66 tolerans.
- `real_metrics_result_v4_moat_gate.{json,txt}`: yukarıya + moat-gate
  (sadece `critical`) uygulanınca — %61 tam isabet, %66 tolerans (2/61
  makalede gate tetiklendi).

## Yeniden üretmek için

1. 61 makaleyi `assess_manuscript()`/`run_orchestration()` pipeline'ından
   geçirip her birinin `ReviewReport`'unu `{paper_id: {...}}.json` olarak
   bir klasöre yaz (bkz. session geçmişindeki `goldset_live_run*.py`
   script'leri — bunlar da repoya değil scratchpad'e yazılmıştı).
2. Bu klasördeki script'lerdeki `REPORTS_DIR`'ı o klasöre çevir.
3. Çalıştır: `python recompute_verdict_v4_moat_gate.py`.

## Bilinen sınır

Ham 61 rapor (findings + risk_radar) repoda yok — bu yüzden bu README'nin
"kanıtı" ancak script+özet-sayı seviyesinde; tam bağımsız reprodüksiyon için
goldset'i yeniden koşmak gerekir (~7.5 saat, 61×~7.5dk). `real_metrics_result_v4_moat_gate.json` içindeki `verdict_accuracy`/`dimension_agreement`
alanları `eval/review/metrics.py::evaluate()`'in ham çıktısıdır, elle
düzenlenmedi.
