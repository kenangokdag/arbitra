# Runbook — Search p95 latency breach

> **Severity:** P2 (servis ayakta ama kullanıcı algılanan yavaşlık → pilot bozar).
> **Hedef SLO:** p95 < 8s (Plan F2 §17 — Curator hariç pipeline 7s, Curator 1s tolerans).
> **Owner:** Sercan + Omer.
> **Last reviewed:** 2026-05-01 (P015 iskelet).

## Belirtiler

- Grafana latency panelinde p95 > 8s (5 dk pencere).
- Sentry'de `slow request` traces.
- App log: `pinecone retry attempt=2/3` zincir halinde — single request retry'larda zaman yiyor.
- `gate_warnings` "G3 düşük taban" + "G4 eksik metadata" sıklığı arttı (pool sonuçları zayıflıyor).

## İlk 5 dakika

1. Latency hangi katmandan geliyor — request log'unda `latency_ms` field'ı var mı, breakdown alınabilir mi (P017+ instrumentation gerekli, F2 day 4'te eklenmedi).
   - Geçici proxy: per-request `time.monotonic()` log, hangi `await` uzun sürdü.
2. Cache hit oranı ne — Redis `INFO stats` `keyspace_hits` / `keyspace_misses`.
   - %30 altında ise warm-up scriptini tetikle (P058+).
3. Pinecone retry attempt sayısı — `app.log | grep "pinecone retry" | wc -l`.
4. HF endpoint cold-start mı — `app.log | grep "HF cold start"`.
5. Embedding encode süresi — BGE-M3 CPU'da yavaşlar; `EMBEDDING_DEVICE` `mps` veya `cuda` set edildi mi (deploy env).

## Geçici hafifletme

- Pinecone `top_k` parametresini geçici düşür (50 → 30) — fan_out hızlanır, sonuç kalitesi az düşer.
- LiteLLM presenter timeout 30→15 — Curator yavaş ise erken degrade.
- Redis cache TTL'i 1h → 6h: tekrar eden sorgu hızlanır.
- `RERANKER_BATCH_SIZE=8` doğru mu — bge-reranker CPU'da 16+ batch yavaşlatır.

## Kalıcı çözüm yolu

- Per-stage latency instrumentation (P017+ Plan F3a sonrası): `pipeline_stage_seconds` Prometheus histogram.
- HF endpoint warm-keepalive interval kısalt (`HF_KEEPALIVE_INTERVAL_SECONDS` 240 → 180).
- Embedding cache (Faz 3+ KD-37): aynı sub_query 1 saat TTL.

## Eskalasyon

- p95 > 12s 10 dk üst üste → Omer'a Telegram + Sercan ortak triage.
- Pilot kullanıcılar varsa: feature flag ile premium-only, free tier rate-limit aşağı (60 → 20 req/min).
