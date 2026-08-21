# F14-S3 — Railway Deploy (API + web), Gemini-key + Claude fallback (Plan Manifest)

> Handoff Adım 3. Karar: **API + web birlikte** Railway'de; LLM = **gemini-key + Claude fallback** (Vertex'i ertele, dosya jimnastiği yok). Master: `docs/plans/F14_hakemlik_master.md`.
> Kanıt: A = bu oturumda Read/grep. render.yaml (Render) referans alınır, Railway'e çevrilir.

## §0 — AMAÇ
papermind-app'i (api FastAPI + web Next.js + Redis) Railway'de canlıya almak; ARBITRA review akışı uçtan uca çalışsın. GROBID zaten Railway'de canlı (`grobid-production-a2c9`).

## §1 — MEVCUT DURUM (kanıt A)
- `deploy/render.yaml`: tam servis+env spec'i (web/api/redis/6 cron). Railway'e otomatik taşınmaz.
- App boot lazy: ML (torch/BGE/reranker) `BGE_WARMUP_ENABLED=false` ile yüklenmez; Pinecone/Supabase `lru_cache` lazy (`api/db/*`). Eksik secret boot'u çökertmez. **(A)**
- web: Next.js 16, **npm** (`web/package-lock.json`; handoff "pnpm" yanlış). Scripts: `build`=`next build`, `start`=`next start`. API base = build-time `NEXT_PUBLIC_API_URL` (`web/src/lib/api.ts:3` + review-api/tts-api/paper). **(A)**
- Redis: `api/middleware/rate_limit.py`, `tier_gate.py`, `api/db/redis_client.py` — hepsi graceful-degrade (yoksa cache/rate-limit kapanır, app çalışır). **(A)**
- railway CLI **kurulu değil**. **(A)**
- deps ağır: torch>=2.4, transformers, sentence-transformers, pinecone (`pyproject.toml:24-35`) → imaj büyük (~2GB), build uzun. **(A)**

## §2 — SERVİS TOPOLOJİSİ (Railway projesi "Arbitra", mevcut)
1. **api** — FastAPI. Build: uv. Start: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`. Health: `/healthz`.
2. **web** — Next.js. Build: `npm ci && npm run build` (NEXT_PUBLIC_API_URL build-arg). Start: `npm start -- -p $PORT`.
3. **redis** — Railway Redis eklentisi → `REDIS_URL` api'ye inject.
4. **grobid** — zaten canlı, dokunma.

## §3 — OLUŞTURULACAK CONFIG (repo)
- `Dockerfile` (api) — python:3.12-slim + uv + `uv sync --frozen` + uvicorn. (nixpacks+uv kırılgan; Dockerfile deterministik.)
- `web/Dockerfile` — node:22-slim, `npm ci`, `ARG NEXT_PUBLIC_API_URL`, `npm run build`, `npm start`. `next.config.ts`'e `output: "standalone"` eklenebilir (imaj küçültür) — opsiyonel.
- `railway.json` (api, kök) + `web/railway.json` — her servis kendi Dockerfile'ını işaret eder; `healthcheckPath=/healthz` (api).
- `.dockerignore` — `.venv`, `node_modules`, `.git`, `.env`, `web/.next` (imaj şişmesin).

## §4 — ENV MATRİSİ (Railway dashboard / CLI — secret'lar repoya GİRMEZ)
**api:**
- APP_ENV=production · APP_LOG_LEVEL=INFO · WAITLIST_BYPASS=false
- `LLM_PROVIDER=gemini` · `GEMINI_API_KEY`(secret) · `LLM_FALLBACK_ENABLED=true` · `ANTHROPIC_API_KEY`(secret)
- SUPABASE_URL/PUBLISHABLE_KEY/SECRET_KEY/JWKS_URL/JWT_SECRET (secret)
- REVIEW_SUPABASE_URL=`https://qoojmhaagwbvxjlthjaa.supabase.co` · REVIEW_SUPABASE_SECRET_KEY (secret, Clarus service_role)
- PINECONE_API_KEY(secret) + INDEX/NAMESPACE/DIM/METRIC (render.yaml değerleri) — *review yolu için zorunlu değil; diğer endpointler için*
- GROBID_URL=`https://grobid-production-a2c9.up.railway.app`
- OPENALEX_EMAIL=`dr.ofrencber@gaziantep.edu.tr`
- REDIS_URL ← Railway redis (otomatik)
- SENTRY_DSN(secret) · ADMIN_USER_IDS(prod allowlist) · `FRONTEND_ORIGINS=https://<web-domain>` (CORS, R-? — web URL'i belli olunca)

**web (build-time):**
- `NEXT_PUBLIC_API_URL=https://<api-domain>` — **build arg**; api domain'i önce belirlenmeli.

## §5 — SIRA (deploy adımları)
1. Config dosyalarını yaz (S3a, bende — bloker'sız).
2. railway CLI kur (bende, gcloud gibi).
3. **Omer:** `railway login` (interaktif). Proje "Arbitra"yı seç/bağla.
4. Redis servisi ekle (`railway add` veya dashboard).
5. api servisini deploy et (`railway up` veya GitHub bağla) → api domain al (`railway domain`).
6. web env `NEXT_PUBLIC_API_URL=<api domain>` set → web deploy → web domain al.
7. api'ye `FRONTEND_ORIGINS=<web domain>` set (CORS) → api redeploy.
8. Secret'ları gir (env matrisi).
9. Smoke: `GET /healthz` 200 · web yüklenir · review upload→status→report uçtan uca.

## §6 — UYGULAMA YETKİSİ
- S3a (config dosyaları) + CLI kurulumu: bloker'sız, onay sonrası bende.
- Adım 3-9: **Omer-kararı/geri-dönülmez** (deploy, domain, canlı secret, ödeme-etkili). Ben hazırlar + komutları veririm; `railway login` ve canlıya basma **sende** (veya "sen bas" dersen unilateral yapmam, komutu veririm).

## §7 — RİSK
- R-1: torch imajı büyük → build timeout/Railway plan. Mitigasyon: `.dockerignore`, slim base, gerekirse `output: standalone`. Build uzunsa plan yükselt.
- R-2: `NEXT_PUBLIC_API_URL` build-time gömülür → api domain'i web build'inden ÖNCE sabitlenmeli (Adım 5→6 sırası kritik). Yanlış sırada web yanlış API'ye gider.
- R-3: CORS — `FRONTEND_ORIGINS` boşsa prod'da cross-origin reddedilir (config.py:27 fail-closed). web domain'i set edilmeli.
- R-4: Bellek — ilk gerçek search/rerank isteği BGE+reranker (~1GB) yükler; review yolu LLM+OpenAlex (hafif). review için sorun yok; search ağır endpoint plan boyutu ister.
- R-5: Ana Supabase migration durumu — review_job (Clarus) açık ✅; ana DB şema prod'da hazır mı doğrulanmalı (ayrı iş).
- R-6: DB pooler şifresi bayat (handoff) → REST/service_role kullan, doğrudan Postgres değil.

## §8 — DoD
- `GET https://<api>/healthz` → 200.
- web ana sayfa render + `NEXT_PUBLIC_API_URL` doğru API'ye gidiyor (network tab).
- ARBITRA review: gerçek makale upload → status ilerleme → rapor döner (LLM gemini/claude, OpenAlex, Clarus).
- "Çalışıyor" demeden önce hepsini canlı URL'de gör (itiraf protokolü).

## §9 — REFERANS
- `deploy/render.yaml` (env kaynağı) · `api/main.py` (boot/lifespan) · `api/config.py` (env) · `web/src/lib/api.ts` (NEXT_PUBLIC_API_URL) · handoff §"Kalan adımlar 3"
