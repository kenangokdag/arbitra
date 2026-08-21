# Runbook — Pinecone unavailable

> **Severity:** P1 (search %100 etkilenir; theme pool yedek hattı yetersiz).
> **Owner:** Sercan (BACKEND), Omer (gözlem).
> **Last reviewed:** 2026-05-01 (P015 iskelet — F2 day 3-4).

## Belirtiler

- `/api/search` 503 dönüyor (`detail: "Search temporarily unavailable — retry shortly"`).
- App log'unda `pinecone retry attempt=N/3 ... error=...` satırları zincir halinde.
- App log'unda `pinecone query failed after 3 retries` (PineconeQueryError) veya `pinecone query_async timeout` (ResilienceTimeoutError).
- p95 latency Grafana panelinde fırlamış olabilir; cache hit'ler hâlâ 200 dönerken cold path 503.

## İlk 5 dakika

1. Pinecone status sayfasını aç → bilinen incident var mı?
2. `PINECONE_API_KEY` rotate edildi mi (son 24 saatte ENV değişikliği) → `git log -- api/config.py deploy/`.
3. Index ismi `papers-bgem3` doğru mu (`PINECONE_INDEX_NAME`).
4. `mdv1` namespace'i hâlâ var mı (Pinecone console).
5. App log seviyesini DEBUG'a al ve TEK request reproduce et:
   ```bash
   curl -s -X POST http://api.../api/search -H "Authorization: Bearer $T" \
        -d '{"query":"smoke test ping","k":5}' | jq .detail
   ```

## Geçici hafifletme

- Cache TTL'i geçici olarak uzat (`CacheNamespace.QUERY` 1h → 6h) → cold path azalır, sıcak sorgular yine çalışır.
- `HybridPoolRouter` yerine `MockPoolRouter` enjeksiyonu (`api.routes.search.get_pool_router`) — ARAMAYI BOZAR ama 200 döndürür. **Sadece pilot trafiği yokken** uygulanabilir.
- Frontend'e degraded banner: "Akademik arama bakımda, sonuç gelmesi 1-2 dakika sürebilir" (F2 day 3-4 bağımlı).

## Kalıcı çözüm yolu

- Pinecone destek bileti aç (`papers-bgem3` index name + bölge).
- Outage 30 dk üzerine çıkarsa `KD-36 P065 Circuit Breaker` aktivasyonu öncelendir.
- Pilot kullanıcı sayısı arttıktan sonra: ikincil Pinecone bölgesi + read-failover (P065+).

## Eskalasyon

- 15 dk içinde çözülmezse Omer'a bildir (Telegram).
- Pilot kullanıcı varsa: Sercan + Omer ortak triage; user'a manuel "şu anda kapalı" mesajı.
