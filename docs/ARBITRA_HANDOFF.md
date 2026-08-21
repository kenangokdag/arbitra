# ARBITRA (F14 Hakemlik) — Devam Notu / Handoff

> Başka makinede kaldığın yerden devam için. **Secret YOK** — sadece ne/nerede + kalan adım.
> Repo: `ofrencber/arbitra` (main). Plan: `docs/plans/F14_hakemlik_master.md`. Kararlar: `docs/DECISIONS.md §5`.

## Ne hazır (kod, doğrulanmış)
- **S1–S6 + eval** — 68 birim test PASS, FE tsc EXIT 0, ruff temiz.
  - S1 ingestion (`engine/ingestion/`), S2/S3 OpenAlex atıf motoru (`api/services/review_citation_service.py`), S4 orkestrasyon (`api/services/review_orchestration.py`), S5 servis+route+FE (`api/services/review_service.py`, `api/routes/review.py`, `web/src/app/(app)/review/`, `(admin)/`), S6 editör modu.
  - **Marka ARBITRA** (`web/src/lib/brand.ts` + `ArbitraWordmark.tsx`).
  - Eval harness: `eval/review/` (Omer N≥10 pilot-alan girdisi dolduracak).

## Canlı altyapı (kurulu)
- **Clarus Supabase** (review_job izole tablo) — project_ref `qoojmhaagwbvxjlthjaa`. Tablo açıldı + REST smoke PASS. Client: `get_review_supabase_admin` (REVIEW_SUPABASE_*). Keys: `Desktop/keys/supabase_clarus.md`.
- **GROBID** — Railway "Arbitra" projesi, CANLI: `https://grobid-production-a2c9.up.railway.app` (`/api/isalive`=true). Opsiyonel; kapalıyken PyMuPDF fallback. (`deploy/grobid/`)
- **OpenAlex** — keyless (config'de polite-pool email).
- **Railway** — proje "Arbitra" (gmail hesabı; `railway login` interaktif, token dosyası bayattı).

## Gereken env (`.env` — gitignored, secret’ler keys/'ten)
```
REVIEW_SUPABASE_URL=https://qoojmhaagwbvxjlthjaa.supabase.co
REVIEW_SUPABASE_SECRET_KEY=<Clarus service_role — supabase_clarus.md>
# Ana papermind: SUPABASE_*, PINECONE_*, REDIS_URL, GEMINI_API_KEY (veya Vertex), SUPABASE_JWKS/JWT
# GROBID: GROBID_URL=https://grobid-production-a2c9.up.railway.app
```

## Kalan adımlar
1. **Vertex (LLM) — ✅ DONE (2026-06-22, F14-S1).** Plan: `docs/plans/F14_S1_vertex_binding.md`.
   - IAM: SA `arbitra-vertex@translate-500019` → `roles/aiplatform.user` verildi; `aiplatform.googleapis.com` açıldı; SA key `Desktop/keys/translate-500019-arbitra-vertex.json` (repo dışı).
   - Kod: `LLM_PROVIDER` toggle (`api/config.py`) + `_apply_vertex_provider` (`api/services/litellm_router.py`) → `gemini/` alias'ları runtime'da `vertex_ai/`'ye map; kimlik ADC (`GOOGLE_APPLICATION_CREDENTIALS`); alias/kod değişmedi. Default `gemini` (fail-safe).
   - Doğrulandı: raw `generateContent` HTTP 200 (europe-west4) + LLMService→litellm→Vertex entegrasyon "OK" (krediden düştü) + 6 yeni unit test + tüm suite 683 PASS + ruff temiz.
   - Vertex'e geçiş: `.env` → `LLM_PROVIDER=vertex` + `GOOGLE_APPLICATION_CREDENTIALS=<SA json yolu>`.
1b. **Claude fallback — ✅ DONE (2026-06-22, F14-S2).** litellm Router `fallbacks`: Gemini/Vertex çağrısı başarısız olursa otomatik `anthropic/claude-sonnet-4-6`. Yalnız `ANTHROPIC_API_KEY` + `LLM_FALLBACK_ENABLED` iken aktif (key boşsa pasif, kırılmaz). Bug guard: `_apply_vertex_provider` yalnız `gemini/` girdilerini dönüştürür (Claude girdilerine dokunmaz). Doğrulandı: bozuk Gemini key → served_by=claude-sonnet-4-6 + 11 router testi + tüm suite 688 PASS. Key: `keys/Antrophc.rtf`.
2. **Canlı uçtan-uca smoke** — gerçek makale → parse → OpenAlex → orkestrasyon → rapor (ana papermind secret'leri gerekir).
3. **Railway deploy (api + web) — ✅ İSKELET CANLI (2026-06-22, F14-S3).** Plan: `docs/plans/F14_S3_railway_deploy.md`. Proje "Arbitra" (gmail), env production.
   - **api:** `https://api-production-88ca.up.railway.app` — `/healthz` 200. Kök `Dockerfile` (uv). LLM=gemini-key + Claude fallback.
   - **web:** `https://web-production-64ccd.up.railway.app` — `/` 200, Next.js. `web/Dockerfile` (node:24), healthcheck `/`.
   - **redis:** eklendi (REDIS_URL api'ye referans). **grobid:** mevcut.
   - **Deploy yöntemi (monorepo tuzağı):** `railway up` git kökünü context alır → kök `Dockerfile`'ı (api) build eder; `RAILWAY_DOCKERFILE_PATH` `railway up`'ta yok sayılır. web için context=`web/` gerekti → web/ git'siz temp dizine kopyalanıp oradan `railway up --service web -p <id> -e production` ile deploy edildi. **Tekrarlanabilir kalıcı çözüm:** Railway dashboard'da web servisi **Root Directory=`web`** ayarla → sonra normal `railway up`/GitHub deploy `web/`'den doğru build eder.
   - **Çözülen 2 build hatası:** (a) healthcheck eski `/healthz` kalıntısı Next'te 404 → `web/railway.json` healthcheck `/`. (b) `npm ci` "Missing @swc/helpers" → lock npm11/node24 ile üretilmiş, Dockerfile node:22(npm10) idi → **node:24-slim**.
   - **🔴 KALAN — secret'lar (review çalışması için):** Railway api Variables'a gir: `GEMINI_API_KEY`(keys/gemini.rtf) · `ANTHROPIC_API_KEY`(keys/Antrophc.rtf) · `SUPABASE_URL/_PUBLISHABLE_KEY/_SECRET_KEY/_JWKS_URL/_JWT_SECRET`(ana papermind) · `REVIEW_SUPABASE_SECRET_KEY`(keys/supabase_clarus.md) · `PINECONE_API_KEY`. Set olanlar: APP_ENV, LLM_PROVIDER=gemini, LLM_FALLBACK_ENABLED, GROBID_URL, OPENALEX_EMAIL, REVIEW_SUPABASE_URL, FRONTEND_ORIGINS(web), NEXT_PUBLIC_API_URL(web), REDIS_URL.
   - **Not:** `WAITLIST_BYPASS=true` (smoke için); public launch öncesi `false` yap. Custom domain: `railway domain` ile ekle.
4. **Canlı uçtan-uca review smoke** — secret'lar girilince: gerçek makale → web upload → status → rapor (gemini/claude + OpenAlex + Clarus + GROBID).

## Yerel çalıştırma
```
uv sync                 # deps (pymupdf, python-docx, python-multipart, google-auth dahil)
# api: uv run uvicorn api.main:app --reload
# web: cd web && npm install && npm run dev   # (npm — package-lock.json; pnpm DEĞİL)
```

## Evde / yeni makinede devam (resume)
> Repoda her şey var (S1+S2+S3 push'lu, `main`). GitHub'da OLMAYAN, evde gereken:
1. **Repo:** `git clone https://github.com/ofrencber/arbitra.git`
2. **Secret'lar — `keys/` klasörü** (repoda DEĞİL, olmamalı). Bu makinede `~/Desktop/keys/` içinde: `gemini.rtf`, `Antrophc.rtf` (Anthropic), `supabase_clarus.md`, `supabase.rtf`, `Adsız_Pinecone.rtf`, `translate-500019-arbitra-vertex.json` (Vertex SA — F14-S1'de üretildi). Evde bu klasörü senkronla (iCloud/manuel). Vertex SA key'i evde yoksa GCP'den yeniden indir (proje translate-500019, SA arbitra-vertex).
3. **`.env`** (gitignored, repoda yok) — yerel dev için yeniden oluştur. İçerik `.env.example`'da; LLM için ya `LLM_PROVIDER=gemini`+`GEMINI_API_KEY` ya da `LLM_PROVIDER=vertex`+`GOOGLE_APPLICATION_CREDENTIALS=<SA json yolu>` + `ANTHROPIC_API_KEY`.
4. **CLI'lar:** `uv` (astral), `railway` (`npm i -g @railway/cli`), opsiyonel `gcloud` (Vertex için; bu makinede `~/google-cloud-sdk`).
5. **Railway (bulutta, her yerden):** `railway login` → repo kökünde `railway link --project Arbitra`. Servisler + env zaten bulutta duruyor; deploy `railway up --service api`. **web deploy uyarısı:** monorepo context — bkz §3 "Deploy yöntemi" (Root Directory=web ayarla VEYA web'i git'siz temp dizinden deploy et).
6. **Canlı URL'ler:** api `https://api-production-88ca.up.railway.app` · web `https://web-production-64ccd.up.railway.app`. Kalan: api secret'larını gir (§3 🔴) → review uçtan uca çalışır.

## Açık riskler (master §13)
R-1..R-10 + O-1 (canlı uçtan-uca smoke yapılmadı, unit testler mock'lu) · O-5 (eval altın-set Omer dolduracak). DB pooler şifresi bayat — REST/service_role kullan, doğrudan Postgres değil.
