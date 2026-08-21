# Runbook — HF Inference Endpoint down (Listener / Curator)

> **Severity:** P1 (Listener boş sub_query → arama anlamsızlaşır; Curator placeholder döner).
> **Owner:** Sercan (BACKEND).
> **Last reviewed:** 2026-05-01 (P015 iskelet).

## Belirtiler

- App log: `HF endpoint exhausted retries=4 last_err=HTTPStatusError`.
- App log: `LiteLLM presenter timeout` veya cold-start hatası.
- `/api/search` 200 dönebilir ama papers boş, `gate_warnings` doluya yakın → çıktı kalitesi anlık çöküş.
- HF dashboard endpoint statüsü "Initializing" / "Failed" / "Stopped".

## İlk 5 dakika

1. HF endpoint URL doğru: `HF_ENDPOINT_URL` env (Settings).
2. HF token expired mı: `curl -s -H "Authorization: Bearer $HF_TOKEN" $HF_ENDPOINT_URL` → 401 ise rotate.
3. Endpoint Scale-to-Zero'dan uyanırken cold-start ~30-60s — `HF_COLD_START_RETRIES=4` + `HF_KEEPALIVE_INTERVAL_SECONDS=240` doğru çalışıyor mu (uvicorn keep-alive task).
4. Model ID değişti mi: `HF_MODEL_ID` (`Qwen/Qwen2.5-7B-Instruct-AWQ`) — endpoint config'inde hâlâ yüklü mü.
5. Quota / billing — HF account → usage panel.

## Geçici hafifletme

- Listener fail → MockListener inject (search.py `get_listener` DI swap). Sub_query rewrite olmaz, kullanıcı sorgusu aynen geçer; sonuç kalitesi düşer ama servis ayakta kalır.
- Curator fail → OutlinesCurator zaten partial graceful (faithfulness gate placeholder döner). Banner ekleyip "AI özeti şu anda kapalı, sadece skoru gösteriyoruz" diye işaretle.
- LiteLLM presenter timeout → `LITELLM_TIMEOUT_SECONDS` geçici olarak 30→60s.

## Kalıcı çözüm yolu

- HF endpoint logs (HF console) → OOM / GPU error / quota.
- `HF_KEEPALIVE_INTERVAL_SECONDS` cold-start frekansını az tutuyor mu — pilot trafiği yoksa endpoint donuyor olabilir.
- Pilot başlamadan: alt-domain / ikinci endpoint olarak yedek (P070+ kararı).

## Eskalasyon

- HF model paged-attention regression olasılığı varsa Sercan'a Hugging Face support thread aç.
- 30 dk üstünde fail → Omer'a Telegram, pilot trafiği varsa kullanıcıya manuel uyarı.
