# F3d — Mini-Plan: POST /api/enrichment

> **Statü**: TASLAK — F1' master plan onayı sonrası (B-001 §16)
> **Üst plan**: `docs/plans/F1_master_plan.md`
> **Şablon**: ARCHITECT_PROMPT_TEMPLATE §0..§7 + WhatsApp checklist
> **Owner**: Sercan (backend code) · Claude (K1 yıl audit + OpenAlex contract verify) · Omer (TTL OPEN-006)

---

## §0 Bağlam (3 cümle)

Ghost paper enrichment — `dim_ghost_paper` v1.2'deki 31.85M referans-only paper'ın eksik metadata'sı (year, doi, journal, abstract) **on-demand** OpenAlex `/works/{id}` endpoint'inden (.edu.tr polite pool) çekilir, K1 enforce ile `year_verified=true` etiketlenip Supabase'e write-back edilir, Redis 7d cache'lenir. Niş ayrım: jenerik metadata fetch değil — K1 hallucination yasağı runtime guard (`year_verified=false` ise UI'a hiç düşmez, "Klasik kaynak (yıl yükleniyor)" placeholder), DM-005 dar kullanım (sadece okuma önerisi sayfası "ek öneri" olarak) ve B42-045 K8 (`n_corpus_citers ≥ 3` filtresi). Async (Celery) çünkü OpenAlex 100K req/gün polite pool + tek paper ~400ms.

---

## §1 Karar günlüğü

| Karar | Kaynak | Etki |
|---|---|---|
| OpenAlex (.edu.tr polite pool) birincil + Semantic Scholar fallback | DM-009 | `api/services/enrichment_fetch.py` |
| 7-gün Redis cache (master §3) — DM-006 90 günden indirildi | master §3 + OPEN-006 | `enrich:` namespace |
| Async (202 + task_id), Celery + Redis broker (paralel /summarize ile) | master §4.4 | task queue |
| Write-back `dim_ghost_paper` Supabase tablo + audit `enrichment_log` | master §5 | DB schema |
| K1 enforce: response'ta `year_verified` flag; false ise UI'ye `year` field gönderilmez | B42-045 §12 K1 | curator post-process |
| K8 filter: `n_corpus_citers < 3` ghost'lar enrichment için 422 reddet | B42-045 K8 | route guard |
| Depth 1 (sadece bu ghost) vs depth 2 (ghost + first-degree neighbors) | master §4.4 | iş yükü kontrol |
| Polite pool: User-Agent `mailto:dr.ofrencber@gaziantep.edu.tr` | OpenAlex docs + DM-009 | HTTP client header |
| Rate limit: OpenAlex 100K/gün → API tarafı 80 req/sec sürekli üst sınır | DM-009 | semaphore |
| KVKK: ghost metadata çekilirken sadece bibliyografi (title/year/doi/abstract) — yazar e-postası yok | POLICIES.md | scrub |

---

## §2 Endpoint sözleşmesi (tam OpenAPI)

```yaml
POST /api/enrichment
content-type: application/json
authorization: Bearer <supabase_jwt>

request:
  type: object
  required: [ghost_id]
  properties:
    ghost_id:  { type: string, pattern: "^GHOST_OA_W[0-9]+$" }
    depth:     { type: integer, enum: [1, 2], default: 1 }

response 202:
  type: object
  properties:
    task_id:   { type: string, format: uuid }
    eta_s:     { type: integer }                      # depth=1: ~5s; depth=2: ~30s
    poll_url:  { type: string }                       # /api/enrichment/{task_id}

GET /api/enrichment/{task_id}:
response 200:
  type: object
  properties:
    status:    { type: string, enum: [queued, running, done, failed] }
    ghost:     { $ref: GhostCard, nullable: true }    # status=done
    error:     { type: string, nullable: true }
    progress:  { type: number }
    cached:    { type: boolean }                      # Redis 7d hit

GhostCard (özet — B42-045 M51 tam tanım):
  type: object
  required: [ghost_id, title, year_verified, n_corpus_citers]
  properties:
    ghost_id:           { type: string }
    title:              { type: string }
    year:               { type: integer, nullable: true }       # K1 — sadece year_verified=true ise dolu
    year_verified:      { type: boolean }                       # K1 enforce
    doi:                { type: string, nullable: true }
    journal:            { type: string, nullable: true }
    abstract:           { type: string, nullable: true }        # OpenAlex inverted_index decode
    authors:            { type: array, items: { type: string } }
    n_corpus_citers:    { type: integer, minimum: 3 }           # K8
    triage_priority:    { type: string, enum: [high, mid, low] }
    enriched_at:        { type: string, format: date-time }
    source:             { type: string, enum: [openalex, semantic_scholar, none] }

errors:
  404 ghost_not_found                  # dim_ghost_paper'da yok
  422 schema_invalid | k8_violated     # n_corpus_citers < 3
  429 quota_exceeded
  503 openalex_rate_limit + retry_after
```

---

## §3 İmplementasyon adımları (atomik P-numara)

| P | İş | Dosya | LOC | Test |
|---|---|---|---|---|
| **P024** | OpenAlex polite pool HTTP client + 80 req/s semaphore | `api/services/openalex_client.py` | ~120 | unit: header doğru + 429 retry-after honor |
| **P025** | Semantic Scholar fallback client | `api/services/semantic_scholar_client.py` | ~80 | unit: OpenAlex 503 → S2 dener |
| **P026** | Enrichment fetcher (depth 1 + 2 + abstract inverted_index decode) | `api/services/enrichment_fetcher.py` | ~140 | unit: depth=1 + depth=2 (5 neighbor) |
| **P027** | Ghost curator: K1 (year_verified) + K8 filter + KVKK scrub | `api/services/ghost_curator.py` | ~100 | unit: year=null → year_verified=false; n<3 reject |
| **P028** | `/api/enrichment` route + GET poll | `api/routes/enrichment.py` + `api/models/enrichment.py` | ~150 | integration: 202 + poll done |
| **P029** | Celery task: fetch → curator → write-back + Redis cache | `api/workers/tasks/enrichment_task.py` | ~120 | integration: end-to-end < 60s (depth=1) |
| **P030** | `enrichment_log` audit trail | `db/migrations/0004_enrichment.sql` | ~50 | unit: log row her fetch sonrası |

---

## §4 Verification (komut + beklenen output, 6 manuel smoke senaryosu)

```bash
# S1: Unit enrichment pipeline
pytest tests/unit/ -v -k "enrichment or ghost_curator or openalex"
# Beklenen: ≥15 PASS; "test_year_verified_false_no_year_in_response PASSED"

# S2: Depth=1 happy path
TASK=$(curl -X POST http://localhost:8000/api/enrichment \
  -H "Authorization: Bearer $JWT" \
  -d '{"ghost_id":"GHOST_OA_W1234567","depth":1}' | jq -r .task_id)
# Beklenen: 202 + eta_s ≤ 10

curl http://localhost:8000/api/enrichment/$TASK
# t=0s:  {"status":"queued"}
# t=2s:  {"status":"running","progress":0.5}
# t=5s:  {"status":"done","ghost":{...},"progress":1,"cached":false}

# S3: K1 year_verified enforce
echo $RESPONSE | jq '.ghost | {year_verified, year}'
# Beklenen 1 (OpenAlex'te yıl var): {"year_verified": true, "year": 2018}
# Beklenen 2 (yıl bulunamadı):     {"year_verified": false, "year": null}

# S4: K8 violation reject
curl ... -d '{"ghost_id":"GHOST_OA_W_LOW_CITERS"}'   # n_corpus_citers=1
# Beklenen: 422 + body {error: "k8_violated", n_corpus_citers: 1, threshold: 3}

# S5: Cache hit (7d Redis)
curl ... -d '{"ghost_id":"GHOST_OA_W1234567"}'   # 2. çağrı
TASK2=$(... task_id)
curl /api/enrichment/$TASK2
# Beklenen: status=done IMMEDIATELY + cached=true + latency_ms < 100

# S6: OpenAlex 503 → Semantic Scholar fallback
docker compose stop openalex-mock
TASK=$(curl ... -d '{"ghost_id":"GHOST_OA_W999"}' | jq -r .task_id)
curl /api/enrichment/$TASK
# Beklenen: status=done + ghost.source == "semantic_scholar"

# S7: Ghost not found
curl ... -d '{"ghost_id":"GHOST_OA_W_DOES_NOT_EXIST"}'
# Beklenen: 404 + body {error: "ghost_not_found"}

# S8: Depth=2 (5 neighbor)
TASK=$(curl ... -d '{"ghost_id":"GHOST_OA_W1234567","depth":2}' | jq -r .task_id)
# Beklenen: eta_s ≤ 30; poll status=done içinde 6 ghost (1 ana + 5 neighbor) write-back

# S9: KVKK scrub audit
curl ... -d '{"ghost_id":"GHOST_OA_W_WITH_AUTHOR_EMAIL"}'
# Beklenen: response.ghost'ta yazar e-postası YOK (OpenAlex'te varsa scrub edilmiş)
```

---

## §5 Critical files

### Backend touch
- `api/routes/enrichment.py`
- `api/models/enrichment.py` (Request + GhostCard)
- `api/services/openalex_client.py` (polite pool)
- `api/services/semantic_scholar_client.py` (fallback)
- `api/services/enrichment_fetcher.py` (depth 1/2)
- `api/services/ghost_curator.py` (K1 + K8 + KVKK)
- `api/workers/tasks/enrichment_task.py`
- `api/db/redis_client.py` (extension: `enrich:` namespace 7d)
- `db/migrations/0004_enrichment.sql` (enrichment_log)

### Tests touch
- `tests/unit/test_openalex_client.py` + `test_ghost_curator.py`
- `tests/integration/test_enrichment_celery.py` (S2-S6)
- `tests/quality/test_k1_audit.py` (50 ghost × enrich → year_verified=true ihlal=0)

### Read-only
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-045-MIMARI-V1.md` (M51 GhostCard + K1 + K8)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/ENVANTER.md` (`dim_ghost_paper` 31.85M)
- `~/Desktop/papermind-app/docs/plans/F1_master_plan.md`
- `~/Desktop/papermind-app/docs/POLICIES.md` (KVKK scrub)
- `~/Desktop/papermind-app/docs/DM_RULES.md`

---

## §6 TODO(sercan)

### 6.1 Infrastructure
- [ ] OpenAlex User-Agent header `mailto:dr.ofrencber@gaziantep.edu.tr`
- [ ] HTTPX async client + connection pool 50
- [ ] Semaphore 80 req/s (OpenAlex polite pool soft cap)
- [ ] Celery worker (F3c'den ortak)
- [ ] Redis `enrich:` namespace TTL 7d (OPEN-006 onayı sonrası net)

### 6.2 Code
- [ ] P024-P030 sırasıyla atomik commit
- [ ] OpenAlex `/works/{id}` response → GhostCard mapping
- [ ] Inverted index abstract decode (OpenAlex format)
- [ ] K1 enforce: OpenAlex'te yıl varsa `year_verified=true`; yoksa `year=null` + flag false
- [ ] K8 guard: route'ta dim_ghost_paper.n_corpus_citers < 3 → 422
- [ ] KVKK scrub: yazar e-posta + ORCID id (hash'sız) drop
- [ ] Write-back: `dim_ghost_paper` UPDATE + `enrichment_log` INSERT atomic txn

### 6.3 Tests + Quality
- [ ] Unit ≥15 PASS
- [ ] Integration S2-S6, S8-S9 PASS
- [ ] K1 audit script (50 ghost × enrich) → ihlal=0
- [ ] OpenAlex rate-limit retry test (3× exponential backoff)

### 6.4 Auth + Observability
- [ ] JWT verify
- [ ] Rate limit: tier-bazlı (Öğrenci 20 enrich/saat)
- [ ] Sentry breadcrumb: openalex_ms, fallback_ms, curator_ms
- [ ] OpenAlex API quota counter (Grafana panel — 100K/gün)

---

## §7 Commit disiplini

- **Branch**: `feat/F3-enrichment-openalex`
- **Atomic commit**: P024..P030 ayrı commit + ayrı PR
- **Pre-flight Read**: §5 listesi
- **Test gate**: §4 S1-S9 PASS olmadan merge **YASAK**
- **Co-Authored-By**: Claude Opus 4.7
- **Commit message**: `[P0XX] api/enrichment: <kısa>` (örn. `[P027] api/enrichment: K1+K8 ghost curator`)

---

## §8 Önkoşullar — GÜNCEL DURUM (2026-04-30)

### ✅ Kapanmış
| Önkoşul | Kapanış |
|---|---|
| `dim_ghost_paper` Supabase upload | ✅ B-008 (31,855,437 satır + triage_priority + JSONB topic_profile) |
| Supabase static facts | ✅ B-003 |

### ⏳ F3a + F3c bağımlı
| Önkoşul | Statü |
|---|---|
| F3a P002 (Redis client) merge | ⏳ F3a PR |
| F3c P017 (Celery app) merge | ⏳ F3c PR (worker setup ortak — B grubu birleşim refactor) |

### ⏳ Aktif engelleyiciler
| Önkoşul | Statü | Kim |
|---|---|---|
| OPEN-006 cache TTL ghost (7d default, F6 öncesi netleşir) | ⏳ | Omer F6 öncesi |
| OpenAlex polite pool e-posta header verify (`mailto:dr.ofrencber@gaziantep.edu.tr`) | ⏳ | Sercan |
| Supabase migration `0007_enrichment.sql` (enrichment_log) | ⏳ | F3d P030 |

---

**Final commitment**: F3c Celery infra hazır olunca P024..P030 2-3 günde curl ile end-to-end PASS.
