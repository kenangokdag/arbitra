# Arbitra — Canlıya Çıkış Checklist (Render)

> Deploy hedefi: **Render** (`deploy/render.yaml`). API + managed Redis + 6 cron.
> Env referansı: `.env.production.example`. Tek doğruluk: `api/config.py`.
> Bu liste = "yazılım GO" sonrası operatör adımları (kod değil). Yazılım durumu: `docs/worldclass/STATE.md`.
>
> **2026-08-17 güncelleme (Kenan kararı, kesin):** Bu dosya ilk repo import'unda
> (`c9d873f`, 2026-07-13) "Railway seçildi" diye yazılmıştı — o zamanki
> "yerel doğrulama" da gerçek bir `docker build` DEĞİLDİ, sadece `uv sync`/
> `uvicorn` doğrudan çalıştırılmıştı (Docker imaj build'i hiç denenmedi).
> Kenan bunu inceleyip **Render**'da karar kıldı (`render.yaml` daha
> detaylı/tam: 6 servis). `railway.json` (kök + `web/`) kaldırıldı,
> `Dockerfile`/`web/Dockerfile`'daki "Railway" markası temizlendi. §3 ve §4
> aşağıda Render'a göre güncellendi.

## 0. Ön-koşul (yazılım — DONE)
- [x] Backend **880 test** yeşil · FE **249** vitest · `next build` temiz (14+ rota, /settings + /ornek-rapor dahil) · CI yeşil
- [x] Prod fail-fast kapısı doğrulandı (FRONTEND_ORIGINS boş → ProductionConfigError; dolu → boot)
- [x] Canlı uvicorn smoke: /healthz + GET /api/app/theme + Redis-yoksa degrade
- [x] KVKK: hesap silme (DELETE /api/account) + review silme + retention oto-sil (0044) hazır

## 1. Secret'ları gir (Render dashboard — render.yaml'da `sync: false` olanlar)
**⛔ Bunlar girilmezse prod BOOT ETMEZ:**
- [ ] `FRONTEND_ORIGINS` = `https://<FE_DOMAIN>` (boş → config_validation boot reddeder)
- [ ] Auth: `SUPABASE_JWKS_URL` (veya `SUPABASE_JWT_SECRET`) — en az biri
- [ ] `WAITLIST_BYPASS=false` (render.yaml'da sabit — doğrula)

**Secret (özellik için gerekli):**
- [ ] `SUPABASE_URL` · `SUPABASE_PUBLISHABLE_KEY` · `SUPABASE_SECRET_KEY`
- [ ] `GEMINI_API_KEY` (LLM çekirdeği)
- [ ] `PINECONE_API_KEY` — **hakem-değerlendirme (review) akışı için GEREKMİYOR** (2026-08-17 kod taraması: `api/routes/review.py`/`review_service.py`/`review_orchestration.py`'de hiç referans yok). Sadece eski literatür-arama uçlarında (`search.py`/`top5.py`/`workshop.py`) kullanılıyor — boş bırakılabilir, boot'u etkilemez.
- [ ] `SENTRY_DSN` (gözlem)
- [ ] `ADMIN_USER_IDS` (admin tema/işler paneli — boş = admin uçları kapalı)
- [ ] `REVIEW_SUPABASE_URL` / `REVIEW_SUPABASE_SECRET_KEY` (boş = default SUPABASE_*)

**Opsiyonel (boşsa özellik zarif pasif):**
- [ ] `ANTHROPIC_API_KEY` (LLM fallback) · `ELEVENLABS_API_KEY` (TTS)

## 2. DB migration uygula (0042 + 0043 + 0044 dahil)
`scripts/apply_migrations.sh` idempotent (schema_migrations'a bakar, uygulananı atlar).
Script `DATABASE_URL` okur (render.yaml `SUPABASE_DB_URL` diyor → aynı Postgres URL'ini `DATABASE_URL` olarak ver):
```bash
DATABASE_URL=postgresql://<user>:<pass>@<host>:5432/<db> bash scripts/apply_migrations.sh --dry-run  # önce listele
DATABASE_URL=postgresql://...                              bash scripts/apply_migrations.sh           # uygula
```
- [ ] `--dry-run` çıktısında 0042 + 0043 + 0044 sıradaki olarak görünüyor
- [ ] Apply 0 ile çıktı (0043 → admin tema kalıcılığı · 0044 → review_job.delete_after KVKK retention)
> Not: review IZOLE Supabase (REVIEW_SUPABASE_*) kullanılıyorsa, 0041/0042/**0044** o projede de uygulanmalı
> (review_job + delete_after orada). Tek Supabase ise hepsi aynı yerde.

## 3. API deploy (Render — kesin karar, 2026-08-17)
Render config repo'da HAZIR: `deploy/render.yaml` (`env: python` native buildpack — Dockerfile'ı KULLANMAZ,
`pip install uv && uv sync --frozen` → `uv run uvicorn api.main:app --port $PORT`). Web servisi + managed
Redis + 6 cron job'ın HEPSİ tek `render.yaml` içinde tanımlı.
- [ ] Render dashboard → **New → Blueprint** → bu repo'yu seç
- [ ] Render `render.yaml`'ı BULMALI — **repo kökünde DEĞİL, `deploy/render.yaml`'da** duruyor. Render Blueprint'in
      kök-dışı bir yolu otomatik bulup bulmadığı DOĞRULANMADI — bulamazsa dosyayı repo köküne taşımak (ya da
      Render'ın Blueprint ayarlarında yol belirtme seçeneğini kullanmak) gerekebilir. İlk denemede kontrol et.
- [ ] Blueprint tüm servisleri (1 web + 1 Redis + 5 cron) listeleyecek — onayla
- [ ] Secret'ları gir (Adım 1) — özellikle **FRONTEND_ORIGINS** + auth (yoksa boot reddedilir)
- [ ] Deploy → healthcheck `/healthz` 200 bekle
> Railway (railway.json + Dockerfile) DAHA ÖNCE denenmiş/yerel doğrulanmıştı (ilk commit, 2026-07-13) ama Kenan
> kararıyla TERK EDİLDİ — `railway.json` (kök + web/) repo'dan kaldırıldı, Dockerfile'lar "kullanılmıyor" notuyla
> tutuldu (yerel `docker build` ihtimaline karşı).

## 4. FE deploy (henüz seçilmedi — AÇIK)
FE için Railway config (`web/railway.json` + `web/Dockerfile`) daha önce yerel doğrulanmıştı (`next build` ✓,
`npm start` → `/` ve `/review` HTTP 200) ama Kenan kararıyla terk edildi (`web/railway.json` kaldırıldı).
**Render veya Vercel arasında henüz karar verilmedi** — CLAUDE.md ikisini de olasılık olarak anıyor, ne
`vercel.json` ne Render-static config repo'da var. Bu, backend deploy'undan AYRI, ele alınmamış bir sonraki adım.

## 5. Deploy sonrası canlı smoke (gerçek doğrulama)
- [ ] `curl https://papermind-api.onrender.com/healthz` → `{"status":"ok","env":"production"}`
- [ ] `curl https://.../api/app/theme` → tema JSON (DB satırı varsa o, yoksa default)
- [ ] FE açılıyor, ThemeProvider tema uyguluyor (gerçek tarayıcı göz testi)
- [ ] Login → bir makale yükle → review akışı uçtan uca (kokpit 3 katman render)
- [ ] `/admin/theme` (admin kullanıcıyla) → renk değiştir → kaydet → uygulanıyor
- [ ] Sentry'de boot/healthz event'leri görünüyor

## 6. Geri-alma (rollback)
- [ ] Render dashboard → önceki deploy'a "Rollback" (autoDeploy geçmişi)
- [ ] Migration geri-alma: migration'lar additive; veri-yıkıcı değil. Sorun olursa
      ilgili tabloyu manuel revert + schema_migrations satırını sil.

---
**Özet:** Adım 1 (FRONTEND_ORIGINS!) + Adım 2 (migration) zorunlu. Açık gap'ler: `render.yaml`'ın Blueprint'te
bulunup bulunmayacağı (§3, kök-dışı yol) DOĞRULANMADI; FE deploy platformu (§4) henüz seçilmedi.
