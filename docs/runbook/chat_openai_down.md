# Runbook — Chat / OpenAI unavailable

> **Severity:** P2 (chat + summarize + language analysis + jury simulation etkilenir; search/gap çalışmaya devam eder).
> **Owner:** Sercan (key rotate), Omer (gözlem).
> **Last reviewed:** 2026-05-02 (B42-052 GPT-4o-mini).

## Belirtiler

- `/api/chat` yanıt dönüyor ama `delta` = K11 template (örn. "Hazırlanıyor...") — gerçek yanıt değil.
- `/api/summarize` (POST) görev oluşturuyor ama GET patlıyor veya uzun sürüyor.
- App log: `OpenAI chat failed (K11 fallback): ...` veya `OpenAI summarize failed`.
- Kullanıcı: "Danışman yanıt vermiyor" / "Özet gelmiyor."

## İlk 5 dakika

1. OpenAI status: `status.openai.com` → aktif incident mi.
2. API key geçerli mi:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY" | jq '.data[0].id'
   ```
3. Rate limit aşımı mı (HTTP 429): log'da `429 Too Many Requests`.
4. `OPENAI_MODEL=gpt-4o-mini` Render env var'da set edilmiş mi.
5. Timeout sorunuysa: `OPENAI_TIMEOUT_SECONDS` 30s — büyük özetlerde düşük olabilir, 60s dene.

## Geçici hafifletme

- K11 fallback zaten aktif: `/api/chat` template yanıt döner, uygulama çökmez.
- `/api/summarize` için: `task_id` üretiyor ama `delta` boş kalıyorsa UI "hazırlanıyor" durumunda kalır.
- Kullanıcıya UI'de "LLM geçici olarak devre dışı — sonuçlar kısıtlı" bandı göster (F2 sprint UI banner).

## Kalıcı çözüm yolu

- OpenAI key rotate: Render → Environment → `OPENAI_API_KEY` güncelle → "Manual Deploy".
- Rate limit ise: usage tier yüksel veya istek kuyruğu ekle (KD-32 Celery sprint).
- Uzun vadeli: HF Inference Endpoint (`HF_ENDPOINT_URL` + `HF_TOKEN`) fallback — `chat.py` içinde `_call_hf_chat()` varsa devreye alınır.

## Eskalasyon

- 30 dk üzerine çıkarsa Omer'a bildir.
- OpenAI incident ise: HF endpoint'i sıcak tutmak için `HF_KEEPALIVE_INTERVAL_SECONDS=240` ping'i kontrol et.
