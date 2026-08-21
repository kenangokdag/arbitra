# F3a — Mini-Plan: POST /api/search

> **STATUS: SUPERSEDED** (2026-05-04) — F8 LLM Provider Unification (DM-035..044 = DM-LLM-1..10) ile production LLM tek = **Gemini 2.5 Flash/Pro 2-tier via LiteLLM router** kanon oldu. Bu plan'daki `huggingface/tgi` + `claude-haiku-4-5` model_chain ve "Qwen draft → Claude rötuş" 2-kademeli akış **artık geçerli değil**. Aşağıdaki içerik tarihsel kayıt amaçlıdır; gerçek implementasyon F8 plan'ına bakar.
>
> Kanıt: `docs/DECISIONS.md` DM-035..044 + `docs/plans/F8_llm_provider_unification.md` + commit `2ede251` (DM-010+DM-015 drift kapatma).

> **Statü**: TASLAK — F1' master plan onayı sonrası (B-001 §16)
> **Üst plan**: `docs/plans/F1_master_plan.md` (master, çelişki üst sözdür)
> **Şablon**: ARCHITECT_PROMPT_TEMPLATE §0..§7 + WhatsApp checklist
> **Owner**: Sercan (backend code) · Claude (verify + LVR audit) · Omer (warehouse upload + onay)

---

## §0 Bağlam (3 cümle)

PaperMind v4 MVP'nin **omurga endpoint**'i — TR/EN sorgu → 5-katman pipeline (Listener→Anchor→Pool Router→Reranker→Curator) → top 10 PaperCard + faithfulness_meta + KararBant + G1-G7 gate uyarısı. Niş ayrım: jenerik vector search değil — 13 sinyal + LVR cümle-düzey atıf + halüsinasyon-sıfır (K1-K15 runtime enforce). Performans bütçesi p50 < 4s / p95 < 7s; Pinecone `papers-bgem3` 24.87M corpus üzerinden 3-havuz RRF k=60 + BGE-reranker-v2-m3 + Outlines JSON şema.

---

## §1 Karar günlüğü

| Karar | Kaynak | Etki |
|---|---|---|
| 5-katman pipeline (Listener → Anchor → Pool Router → Reranker → Curator) | B42-045 §1, ARCHITECTURE.md | `engine/` klasör yapısı |
| Pinecone `papers-bgem3` (1024-d cosine, **dense fp16**, ns=`__default__`, AWS eu-west-1; sparse Plan 2'de ayrı index) | B42-046 §2 + DM-010 + **DM-016** | `api/db/pinecone_client.py` |
| 3-havuz RRF k=60 (semantic + lexical + theme) | B42-045 §2 + ESTRA Politikası v1.1 | `api/services/pool_router.py` |
| BGE-reranker-v2-m3 (multilingual cross-encoder) | B42-045 K10 | `api/services/reranker.py` |
| Outlines + lm-format-enforcer (JSON şema) — `rank` field yasak | B42-045 K4 | `api/services/curator.py` |
| LVR_min_distance ≥ 0.7 (cümle-düzey atıf) | B42-045 K5 | `api/services/curator.py` |
| KararBant 4 sınıf: `canon` / `frontier` / `strong_evidence` / `risk` | B42-045 §4 | response shape |
| G1-G7 gate sistemi (kapı ihlali warning) | ESTRA Politikası v1.1 + B42-045 §5 | response.gate_warnings |
| Redis cache `q:{normalize(query)}:{lang}:{k}` TTL 1h | DM-006 + master §5 | `api/db/redis_client.py` |
| Tier sliding window: Öğrenci 60 req/min | B42-049 §1 + master §6.5 | `api/middleware/rate_limit.py` |
| K1 runtime guard: `year_verified=false` → response'tan `year` field düşer | B42-045 §12 K1 | curator post-process |

---

## §2 Endpoint sözleşmesi (tam OpenAPI)

```yaml
POST /api/search
content-type: application/json
authorization: Bearer <supabase_jwt>

request:
  type: object
  required: [query]
  properties:
    query:           { type: string, minLength: 3, maxLength: 512 }
    k:               { type: integer, minimum: 1, maximum: 50, default: 10 }
    language_hint:   { type: string, enum: [tr, en, null], default: null }
    include_ghost:   { type: boolean, default: false }

response 200:
  type: object
  required: [papers, faithfulness_meta, decision_band, latency_ms, pmid_match_score]
  properties:
    papers:
      type: array
      maxItems: 50
      items: { $ref: PaperCard }   # M31 (B42-045 §3) — 13 sinyal
    faithfulness_meta:
      type: object
      properties:
        jsonschema_pct:   { type: number, minimum: 0, maximum: 100 }   # her zaman 100 (C3)
        minicheck_nli:    { type: number, minimum: 0, maximum: 1 }     # ≥ 0.7 (C4)
        alce_recall:      { type: number, minimum: 0, maximum: 1 }     # ≥ 0.8 (C5)
    decision_band:
      type: string
      enum: [canon, frontier, strong_evidence, risk]
    gate_warnings:
      type: array
      items:
        type: object
        properties:
          gate_id: { type: string, enum: [G1, G2, G3, G4, G5, G6, G7] }
          severity: { type: string, enum: [info, warn, block] }
          message: { type: string }
    latency_ms:        { type: integer }
    pmid_match_score:  { type: number, minimum: 0, maximum: 1 }   # 12-segment

errors:
  422: schema_invalid                    # Pydantic validation
  401: jwt_expired | jwt_invalid
  429: quota_exceeded                    # tier %100 (Retry-After header)
  503: pinecone_unavailable              # Retry-After header
  500: pipeline_internal_error           # Sentry trace_id döner
```

PaperCard şeması (özet — B42-045 §3 M31 tam tanım):
```yaml
PaperCard:
  paper_id, pmid, title, authors[], year (year_verified=true ise), doi,
  abstract_excerpt, journal, n_cited, sentence_role_distrib,
  signals_13: { Q_weak, MQ_Tier1, CD5, sleeping_beauty, ... },
  citations_lvr[]: [{ sentence: str, paper_id: str, span: [int, int], lvr_distance: float }],
  badges: { canon | frontier | strong_evidence | risk },
  is_ghost: bool   # include_ghost=true ise GhostCard alt-küme
```

---

## §3 İmplementasyon adımları (atomik P-numara)

| P | İş | Dosya | LOC | Test |
|---|---|---|---|---|
| **P000** | Python proje setup: `pyproject.toml` (uv + minimum deps fastapi/pydantic/pytest/ruff/mypy) + `.python-version` (3.12) + `Makefile` (dev/test/lint/format/typecheck) + ruff/mypy/pytest config + .gitignore update [Council 21 plan boşluğu kapanışı, 2026-04-30] | `pyproject.toml`, `.python-version`, `Makefile` | ~150 | smoke: `uv sync` 0 error + `make lint` 0 issue + `pytest --collect-only` 0 error |
| **P001** | FastAPI bootstrap + 3 middleware (auth + rate_limit + sentry) | `api/main.py`, `api/middleware/{auth,rate_limit,sentry}.py` | ~270 | unit: middleware happy + jwt expire + rate exceed |
| **P002** | 3 db client (Supabase + Pinecone + Redis) singleton + retry | `api/db/{supabase,pinecone,redis}_client.py` | ~180 | unit: connection + retry + 503 |
| **P003** | 5-katman boş sınıf iskeleti + interface tanımları | `api/services/{listener,anchor,pool_router,reranker,curator}.py` | ~200 | unit: instantiate + abstract method check |
| **P004** | Listener — Qwen multi-query (4-6 rewrite) + LiteLLM router + **920-örneklem mini-benchmark** (4 LLM aday × 230 örneklem: Qwen2.5 + Cosmos Turkish-Gemma-9b-T1 + Cosmos Turkish-Llama-8b-Instruct + Phi-4 EN; B-006/B-007) | `api/services/listener.py` + `api/services/litellm_router.py` + `tests/quality/llm_benchmark.py` | ~250 | unit: 4-6 rewrite + TR fallback (K11); benchmark: CSV output her aday × dil × isabet skoru |
| **P005** | Anchor — PMID 12-segment partial match (D.F.S.T1.T2.T3.Y.Q.I.L.R.V) | `api/services/anchor.py` | ~140 | unit: full match + partial + wildcard `*` (K6) |
| **P006** | Pool Router — 3-havuz (semantic Pinecone **dense** / lexical BM25 / theme dim_theme_embedding) + RRF k=60 + **B-012 metadata HARD filter** (`fan_out(..., filter=None)`, Pinecone 8-field D/F/S/year/q_weak/method/lang/v_conf via `$in`/`$gte` operators — Council 24 ABC signature güncellemesi P010 öncesi yapıldı) | `api/services/pool_router.py` | ~180 | unit: 3 havuz × 50 sonuç + RRF birleşim doğru ranking + filter dict→Pinecone query çevrimi |
| **P007** | Reranker — BGE-reranker-v2-m3 (TR-EN cross-encoder) | `api/services/reranker.py` | ~100 | unit: 50 → 10 ranking + TR örneği |
| **P008** | Curator — Outlines JSON + LVR validator + K1-K15 runtime guards | `api/services/curator.py` | ~220 | unit: JSON schema 100% + LVR ≥ 0.7 + year_verified=false → year drop |
| **P009** | **Presenter** — dil-spesifik akademik sunum LLM (B-005/B-007): TR → Cosmos Turkish-Gemma-9b-T1 (ayrı endpoint), EN+ID → Qwen2.5 (anlama endpoint'i ile ortak); LiteLLM `model_list` ile route + onboarding `lang` parametresi ile branch | `api/services/presenter.py` | ~120 | unit: TR branch → Cosmos call; EN/ID branch → Qwen call; karışık dil sorgu doğal akış |
| **P010** | `/api/search` route + Pydantic schemas + Redis cache wrapper | `api/routes/search.py`, `api/models/search.py` | ~200 | integration: 200 + 422 + 401 + 429 + 503 + cache hit |

**P000 → P010 sırası katı** — her P önceki P PASS olmadan merge edilmez (master §13 commit disiplini). **Toplam 11 atomic commit, ~1960 LOC** (P000 Council 21 + P009 Presenter B-005 dahil).

---

## §4 Verification (komut + beklenen output, 6 manuel smoke senaryosu)

```bash
# S1: Unit pipeline
pytest tests/unit/ -v -k "search or listener or anchor or pool or rerank or curator"
# Beklenen: ≥30 PASS, 0 FAIL; "test_lvr_min_distance_07 PASSED" görmek

# S2: TR sorgu happy path
curl -X POST http://localhost:8000/api/search \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"query":"makine öğrenmesi tıp uygulaması","k":10,"language_hint":"tr"}'
# Beklenen: 200; len(papers)==10; faithfulness_meta.jsonschema_pct==100;
#          decision_band ∈ {canon,frontier,strong_evidence,risk};
#          her paper.citations_lvr[*].lvr_distance ≥ 0.7;
#          latency_ms < 4000

# S3: K1 yıl halüsinasyon yasağı
curl ... -d '{"query":"klasik kuram", "include_ghost": true, "k": 5}'
# Beklenen: ghost paper'larda "year" key YOK; UI placeholder hint header'da

# S4: Şema sapma reddi (422)
curl ... -d '{"query":"x", "k": 999}'   # k > 50
# Beklenen: 422 + detail.body.k.msg "Input should be less than or equal to 50"

# S5: Rate limit (429)
for i in {1..70}; do curl ... -d '{"query":"q'$i'"}' -o /dev/null -w "%{http_code}\n"; done
# Beklenen: ilk 60 → 200; sonraki → 429 + Retry-After

# S6: Cache hit ratio
# Aynı sorgu 3 kere çağır → ikinci+ çağrıda latency_ms < 100ms (Redis hit)
for i in 1 2 3; do
  curl ... -d '{"query":"derin öğrenme depresyon"}' | jq .latency_ms
done
# Beklenen: 1. çağrı ~3000ms; 2-3. çağrı < 100ms (cache hit)

# S7: 100-sorgu p50/p95 örneklem (bench)
python tests/load/bench_search.py --n 100 --query-pool tests/fixtures/queries_tr.txt
# Beklenen: p50 < 4000ms; p95 < 7000ms; error_rate < 1% (C1, C2)

# S8: Pinecone outage simülasyon
docker compose stop pinecone-mock
curl ... -d '{"query":"test"}'
# Beklenen: 503 + Retry-After + Sentry trace_id; cache hit varsa 200 fallback
```

---

## §5 Critical files

### Backend touch
- `api/main.py` (FastAPI bootstrap)
- `api/middleware/auth.py` (Supabase JWT verify) — TODO(sercan)
- `api/middleware/rate_limit.py` (Redis sliding window) — TODO(sercan)
- `api/middleware/sentry.py` (KVKK PII scrub) — TODO(sercan)
- `api/db/supabase_client.py` (singleton)
- `api/db/pinecone_client.py` (query wrapper + 3× retry) — TODO(sercan)
- `api/db/redis_client.py` (3-katlı cache helpers) — TODO(sercan)
- `api/services/listener.py` (Qwen multi-query + TR fallback K11)
- `api/services/litellm_router.py` (HF + Claude model_list) — TODO(sercan)
- `api/services/anchor.py` (PMID 12-segment match — K6)
- `api/services/pool_router.py` (3-havuz RRF k=60)
- `api/services/reranker.py` (BGE-reranker-v2-m3)
- `api/services/curator.py` (Outlines + LVR validator + K1-K15 guards)
- `api/routes/search.py` (endpoint + cache wrapper)
- `api/models/search.py` (Pydantic Request/Response/PaperCard)

### Tests touch
- `tests/unit/test_listener.py` + `test_anchor.py` + `test_pool_router.py` + `test_reranker.py` + `test_curator.py`
- `tests/integration/test_search_endpoint.py` (200 + 422 + 401 + 429 + 503 + cache)
- `tests/load/bench_search.py` (100 sorgu p50/p95)
- `tests/fixtures/queries_tr.txt` (50 TR + 30 EN + 20 karışık)

### Read-only (DOKUNMA — pre-flight Read zorunlu)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-045-MIMARI-V1.md` (5-katman + PMID + PaperCard + K1-K15)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/ENVANTER.md` (warehouse manifest — 24.87M paper)
- `~/Dataleak/facts/manifest_n12b_bge_m3.json` (Pinecone upload kanıtı)
- `~/Desktop/papermind-app/docs/plans/F1_master_plan.md` (master, çelişki üst sözdür)
- `~/Desktop/papermind-app/docs/HEDEF.md` (C1-C11)
- `~/Desktop/papermind-app/docs/DM_RULES.md` (R1-R12)

---

## §6 TODO(sercan)

### 6.1 Infrastructure
- [ ] Supabase project init + tablolar: `papers`, `dim_theme`, `users`, `user_quota` (master §5)
- [ ] Pinecone index `papers-bgem3` (1024-d cosine, **dense**, ns=`__default__`, AWS eu-west-1) — bekleyen Omer upload (DM-016, sparse Plan 2)
- [ ] Redis Render-managed namespace `q:` TTL 1h
- [ ] HF Inference Endpoint Qwen2.5-7B-Instruct AWQ + keep-alive 240s (DM-010)
- [ ] LiteLLM `model_list` config: `huggingface/tgi` + `claude-haiku-4-5`

### 6.2 Code
- [ ] P001-P009 sırasıyla atomik commit (master §13)
- [ ] Curator JSON şemasında `rank` field yasak (K4 — pytest fail-fast)
- [ ] LVR validator paper_id+span eşleşmesi zorunlu (K5)
- [ ] year_verified=false ise response'tan `year` key drop (K1)
- [ ] PMID `?` placeholder confidence<0.5 ise (K9)
- [ ] G1-G7 gate kontrol → response.gate_warnings populate

### 6.3 Tests + Quality
- [ ] Unit ≥30 PASS (listener+anchor+pool+rerank+curator + middleware)
- [ ] Integration 6 senaryo (S2-S6, S8)
- [ ] 100-sorgu bench p50<4s + p95<7s (S7)
- [ ] LVR ihlal sayısı = 0 (C8 audit script)
- [ ] K1 ihlal = 0 (C9 audit script)

### 6.4 Auth + Observability
- [ ] Supabase JWT verify + RS256 public key cache 5 dk
- [ ] Rate limit: tier-bazlı (Öğrenci 60/min) Redis sliding window
- [ ] Sentry trace_id her response (`X-Trace-Id` header)
- [ ] Sentry breadcrumb: pipeline her katman süresi (listener_ms, anchor_ms, ...)

---

## §7 Commit disiplini

- **Branch**: `feat/F2-search-skeleton`
- **Atomic commit boundary**: P001..P009 her biri ayrı commit + ayrı PR (P002 P001'siz merge edilmez)
- **Pre-flight Read**: §5 Read-only listesi + manifest_n12b_bge_m3.json + B42-045-MIMARI-V1.md
- **Test gate**: §4 verification S1-S8 PASS olmadan PR merge **YASAK**
- **Co-Authored-By**: `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` her commit footer
- **Commit message format**: `[P00X] api/search: <kısa öz>` (örn. `[P006] api/search: 3-havuz RRF k=60 implementasyon`)
- **PR template**:
  ```
  ## Summary
  - <ne yapıldı, 1-3 madde>
  ## Test plan
  - [ ] pytest unit ≥X PASS
  - [ ] curl S2 happy path 200
  - [ ] bench S7 p50<4s
  ## Verification log
  <S1-S8 çıktı yapıştır>
  ```
- **Hook bypass yasak**: pre-commit FAIL → root cause fix; `--no-verify` kullanma
- **Plan değişikliği**: bu mini-plan revize edilmeden code edit yasak (CLAUDE.md §0)

---

## §8 Önkoşullar (engelleyiciler) — GÜNCEL DURUM (2026-04-30)

### ✅ Kapanmış engelleyiciler
| Önkoşul | Statü | Kapanış kaydı |
|---|---|---|
| OPEN-001 LLM model adı | ✅ KAPALI | B-005 + B-006 + B-007 (2-katmanlı: Qwen anlama + Cosmos TR / Qwen EN+ID sunum) |
| OPEN-003 12 chip listesi | ✅ KAPALI | B42-040 entry (DI/SB/d/Ravg/RS/MQk/Ck/EDk/BC/SR/TSP/RX + 4 faz) |
| OPEN-004 Pipeline_Akis canonical | ⚠️ ŞARTLI KAPALI | B42-040+045+046 manifest yeterli; docx geldiğinde marjinal revize |
| B42-046 ŞARTLI KABUL | ✅ KAPALI | Papermind_V2/DECISIONS.md'ye yazıldı 2026-04-30 |
| Supabase project + schema_v1 migration | ✅ KAPALI | B-002 (12 tablo + 19 RLS + 9 trigger + 6 enum) |
| Supabase static facts upload | ✅ KAPALI | B-003 (562,931 satır pgvector 256-d HNSW) |
| **PaperCard + GhostCard Supabase upload** | ✅ KAPALI | B-008 (24.86M + 31.85M ≈ 28 GB) |
| **paper_satellites FK guard patch** | ✅ KAPALI | B-009 (Cell 2 + Cell 8 patch'li, Faz 2 yarın koşar) |

### ⏳ Aktif engelleyiciler (paralel akıyor — F2 P001-P005 başlamaya engel DEĞİL)
| Önkoşul | Statü | Kim | P numarası kritik |
|---|---|---|---|
| Pinecone Yol B re-upload (metadata-enriched, `embeddings_v3/papers/`) | ⏳ in-flight | Omer | **P006** (Pool Router semantic, mock client P001-P005'te) |
| HF Inference Endpoint kurulu (Qwen2.5-7B-Instruct AWQ + keep-alive 240s) | ⏳ Sercan setup | Sercan | **P004** (Listener) |
| OPEN-011 Komodo HF gated (Faz 2'ye ertelendi) | ⏳ Faz 2 | Pilot sonrası | F2 başlangıç engeli DEĞİL |

**Sonuç:** F2 P001-P005 (skeleton + middleware + db clients + listener + anchor) **HEMEN başlayabilir** — Pinecone client mock ile, P006'ya kadar Yol B upload tamamlanmalı.

---

**Final commitment**: Bu mini-plan onaylanırsa P001 commit'i `feat/F2-search-skeleton` branch'inde 24 saat içinde açılır; verification S1+S2+S5 PASS ile P001 PR mergeable olur. Tam endpoint (P001..P009) 4-5 günde curl ile çalışır (master §9 F2 süresi).
