# Runbook — Supabase unavailable

> **Severity:** P1 (theme pool + faithfulness gate metadata + auth tümü etkilenir).
> **Owner:** Sercan (BACKEND), Omer (gözlem).
> **Last reviewed:** 2026-05-01 (P015 iskelet).

## Belirtiler

- `/api/search` 503 (`SupabaseQueryError`) veya 504 (`ResilienceTimeoutError`).
- Auth uçları (`/api/whoami`, JWT verify) 401 ya da hang.
- App log: `supabase call timeout=10.0s` veya `supabase call failed error=...`.
- `pool_router` log'unda "Theme pool failed (graceful degrade)" — semantic pool çalışırken theme pool patlıyorsa Supabase tarafı sorun.

## İlk 5 dakika

1. Supabase status sayfası → incident kontrolü.
2. Connection method:
   - **Backend (FastAPI):** `SUPABASE_URL` doğrudan; `SUPABASE_SECRET_KEY` rotate edildi mi.
   - **Colab pipeline:** Session Pooler URL kullanılır (Direct IPv6 dev'de bloke). Bu runbook backend'i kapsar.
3. Postgres-side mi REST-side mi:
   ```bash
   # PostgREST direct
   curl -s -H "apikey: $SUPABASE_PUBLISHABLE_KEY" \
        "$SUPABASE_URL/rest/v1/dim_theme?limit=1" -i | head -3
   ```
4. RLS policy son 24 saatte değişti mi (`docs/backend/SCHEMA_v1_SUPABASE_BRIDGE_DECISIONS_2026-04-29.md` + Supabase dashboard).
5. Connection limit aşımı mı: Supabase project metrics → "Pool exhaustion".

## Geçici hafifletme

- `pool_router._theme_pool` zaten graceful degrade yapıyor (boş liste döner). Search hâlâ semantic + anchor üzerinden çalışabilir.
- Auth bozuksa `APP_ENV=development` test ortamında JWT verify zayıflar — **production'da uygulama**.
- Reading list / notes uçlarına 503 dön (kullanıcı veri yazmasın → kayıp olmasın).

## Kalıcı çözüm yolu

- Supabase support ticket (project ref + saat aralığı + log snippet).
- B-003 statik fact tabloları (562K satır) zaten yüklü → restore senaryosu yok; sadece transient connection sorunu.
- Pool exhaustion ise: backend connection retry stratejisini gözden geçir, Pgbouncer parametreleri.

## Eskalasyon

- 15 dk üzerine çıkarsa Omer'a bildir.
- Yazma uçları ölü → kullanıcıya "geçici bakım" UI bandı (F2 day 3-4 bağımlı).
