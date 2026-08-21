# PaperMind Backend Protokol

> **Son güncelleme:** 2026-05-02  
> **Hedef kitle:** Sercan (deploy + monitoring)  
> **Kaynak:** `api/routes/`, `api/config.py`, `deploy/render.yaml`

---

## 1. Endpoint Listesi

| Method | Path | Açıklama | DB | Cache TTL |
|--------|------|----------|----|-----------|
| GET | `/healthz` | Sağlık kontrolü | - | - |
| POST | `/api/search` | Semantik + PMID arama | Pinecone + Supabase | 1h |
| POST | `/api/top5` | En iyi 5 konu önerisi | Pinecone | 1h |
| POST | `/api/chat` | LLM danışman (GPT-4o-mini) | - | req hash |
| GET | `/api/summarize/{task_id}` | Özet durumu | - | task_id |
| POST | `/api/summarize` | Özet görevi başlat | - | - |
| GET | `/api/paper/{paper_id}` | Makale detayı | Supabase | 1h |
| POST | `/api/enrich` | OpenAlex metadata zenginleştirme | OpenAlex API | 7d |
| GET | `/api/gap-heatmap` | Gap matrisi ısı haritası | Supabase | 1h |
| GET | `/api/gap-profile` | Tek hücre gap profili | Supabase | 1h |
| GET | `/api/connected-papers/{paper_id}` | Biblio-coupling ağı | Supabase | 1h |
| GET | `/api/reading-list` | Okuma listesi | Supabase | - |
| POST | `/api/reading-list` | Listeye ekle | Supabase | - |
| POST | `/api/notes` | Not kaydet | Supabase | - |
| GET | `/api/notes` | Notları getir | Supabase | - |
| POST | `/api/onboarding` | İlk kurulum | Supabase | - |

---

## 2. Zorunlu Ortam Değişkenleri

| Değişken | Zorunlu | Örnek / Açıklama |
|----------|---------|------------------|
| `APP_ENV` | ✓ | `production` |
| `SUPABASE_URL` | ✓ | `https://xxx.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | ✓ | `sb_publishable_...` — frontend RLS |
| `SUPABASE_SECRET_KEY` | ✓ | `sb_secret_...` — backend, RLS bypass |
| `SUPABASE_JWT_SECRET` | ✓ | Dashboard → Settings → API → JWT Secret |
| `PINECONE_API_KEY` | ✓ | Pinecone console |
| `PINECONE_INDEX_NAME` | ✓ | `papers-bgem3` |
| `OPENAI_API_KEY` | ✓ | GPT-4o-mini (B42-052) |
| `REDIS_URL` | ✓ | Render Redis internal URL |
| `OPENALEX_EMAIL` | ✓ | `dr.ofrencber@gaziantep.edu.tr` — polite pool |
| `SENTRY_DSN` | önerilen | Sentry dashboard DSN |

**İsteğe bağlı:**

| Değişken | Default | Açıklama |
|----------|---------|----------|
| `OPENAI_MODEL` | `gpt-4o-mini` | |
| `PINECONE_NAMESPACE` | `mdv1` | |
| `RATE_LIMIT_OGRENCI_PER_MIN` | `60` | İstek/dakika |
| `OPENAI_TIMEOUT_SECONDS` | `30` | Özetleme için 60 önerilir |
| `HF_ENDPOINT_URL` | `""` | Boş → GPT fallback |
| `HF_TOKEN` | `""` | HF Inference Endpoint token |

---

## 3. Deploy Adımları (Render)

1. `deploy/render.yaml` → Render dashboard "New Blueprint" ile import.
2. `sync: false` olan tüm değişkenleri manuel doldur.
3. Redis servisi otomatik oluşur (`papermind-redis`).
4. `/healthz` 200 döndükten sonra Vercel frontend'i backend URL'e yönlendir.

---

## 4. Sercan'ın Görevleri

- [ ] Render service kur (`deploy/render.yaml`)
- [ ] Tüm `sync: false` env var'ları gir
- [ ] Vercel frontend deploy + `NEXT_PUBLIC_API_URL=https://papermind-api.onrender.com`
- [ ] Custom domain bağla
- [ ] Sentry organization + DSN → `SENTRY_DSN` gir
- [ ] Grafana Cloud free tier dashboard kur
- [ ] `/healthz` kontrolü: `curl https://papermind-api.onrender.com/healthz`
- [ ] `/api/top5` Pinecone testi: gerçek sonuç geldiğini doğrula

---

## 5. Runbook Referansları

| Senaryo | Dosya |
|---------|-------|
| Supabase çöktü | `docs/runbook/supabase_down.md` |
| Pinecone erişilemiyor | `docs/runbook/pinecone_down.md` |
| HF Endpoint soğuk start | `docs/runbook/hf_endpoint_down.md` |
| Search P95 ihlali | `docs/runbook/search_p95_breach.md` |
| OpenAI / Chat çalışmıyor | `docs/runbook/chat_openai_down.md` |
