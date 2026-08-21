# F1' — PaperMind v4 End-to-End Master Plan (Backend-First, Sercan Handoff)

> **Statü**: ŞARTLI KABUL — Omer onayı 2026-04-29 (auto-mode plan onayı)
> **Karar referansı**: B-001 (papermind-app/docs/DECISIONS.md)
> **Çelişki sırası (yüksek→düşük)**: B42-045/046/047/048/049/050 (Papermind_V2/04_plan_analiz_kararlar/) > HEDEF.md > IS_PLANI.md > METHOD.md > bu plan
> **Şablon**: ARCHITECT_PROMPT_TEMPLATE §0..§18 + WhatsApp checklist (verification beklenen output gömülü + critical files kategorize + Read-only ayrı + final commitment satırı)

---

## Context (3 cümle)

PaperMind v4 = ALI advisory niş — Türkçe akademik literatür asistanı (warehouse 24.87M paper × BGE-M3 1024-d + 8/8 ESTRA + 833M edge + 504K gap matrix). Bu sprint hedefi: **30 günlük MVP slice** (HEDEF.md §1-§4: 5 ekran + 5 endpoint + 11 kabul kriteri + pilot 5 user). Handoff: Omer = frontend + UX + warehouse upload (Pinecone + Supabase), Sercan = backend implementasyon (FastAPI + Supabase + Pinecone + Redis + Celery), Claude = plan-watcher + halüsinasyon audit + verification.

---

## §0 Niş bağlamı (generic SaaS yasağı, K6)

- **Niş**: TR-native akademik literatür asistanı; rakipler (SciSpace/Consensus/Elicit/Scite/Connected Papers/Litmaps) İngilizce-only + opak skor + abstract-özeti.
- **Bizim ayrım** (HEDEF.md §6): 13 sinyal + KararBant + LVR cümle-düzey atıf + G1-G7 gate sistemi + Q_weak + MQ_Tier1 + 3-havuz RRF k=60 + CD₅ disruption + Sleeping Beauty + sentence-role.
- **Halüsinasyon-sıfır**: K1-K15 (B42-045 §12) — doğrulanmamış yıl gösterilmez, confidence<0.5 → segment `?`, LLM rank alanı yok, cümle-düzey atıf zorunlu.
- **Paralel hat**: Hat A (Papermind_V2 closure) ✅ tamam — N12b BGE-M3 24.87M Pinecone-ready, t-ESTRA 8/8 KAPANIŞ, 6 fact tablo + 2 mart hazır. Hat B (bu plan) MVP kod ve ürün.

---

## §1 Stack + karar günlüğü

| Katman | Teknoloji | Karar kaynağı | Çelişki çözümü |
|---|---|---|---|
| **Frontend** | Next.js 16 (App Router + Turbopack default + async PageProps) + React 19 + TypeScript 5+ | DM-013 (2026-04-29, A-evidence + context7 v16.2.2 stable) | B42-050 §11 "15" eski; DM-013 son söz |
| **Stil** | Tailwind v4 + CSS variable theming + 4-zone palet (B42-050 §1) | B42-050 §1.1-1.4 | — |
| **Komponent** | shadcn/ui FULL custom (default sıfır) + Tiptap (Defter, MVP-sonrası) | B42-050 §11 | — |
| **Tipografi** | Crimson Pro (display) + Lora (body, serif ayrışımı) + Geist Sans (UI) + Geist Mono (PMID) | B42-050 §2 (OFL ücretsiz) | — |
| **State** | TanStack Query (server) + Zustand (client) + RHF + Zod | B42-047 A1-A4 | — |
| **Animasyon** | Framer Motion (interaktif) — Google Flow perde MVP-**sonrası** (Faz 3) | B42-050 §7.2 OPEN-DD1 | MVP'de perde YOK |
| **Backend** | FastAPI 0.110+ + Pydantic v2 (Python 3.12) | DM-003, IS_PLANI F2 | — |
| **DB** | Supabase (Postgres 15 + Auth + Storage + RLS, EU region KVKK) | DM-003 | schema_v1, B42-048 9 schema MVP'de **5 endpoint kapsamı**na indirildi (§5'te 11 tablo listesi) |
| **Vector** | Pinecone serverless (`papers-bgem3` index, 1024-d cosine, **dense fp16**, 24.87M vektör, namespace=`__default__`, AWS eu-west-1; sparse Plan 2'de ayrı index — DM-016) | B42-046 §2 + DM-010 + DM-016 | Omer upload eder, Sercan client wrapper yazar |
| **Cache** | Redis (Upstash) — 3-katlı (query→result + paper_id→enrichment + user→tier+quota) | DM-006 | TTL: query 1h, paper 24h (DM-006 90 günden indirildi MVP için), user 5min |
| **LLM (anlama — B-005)** | Qwen2.5-7B-Instruct AWQ (HF Endpoint, multilingual, Apache 2.0) — query rewrite + EN paper okuma + JSON şema + faithfulness | DM-003, DM-010, **B-005** | — |
| **LLM (sunum — B-005 + B-006 + B-007)** | Dil-spesifik (kullanıcının onboarding seçimine göre): TR → `ytu-ce-cosmos/Turkish-Gemma-9b-T1` (Gemma Terms ✅, ayrı endpoint) — F2 P004'te Cosmos Turkish-Llama-8b-Instruct-v0.1 yan-yana pilot; EN → Qwen2.5 (anlama endpoint'i ile ortak, ek maliyet $0; F2 P004 sonrası Phi-4 14B MIT swap aday); ID → Qwen2.5 (anlama endpoint'i ile ortak, ek maliyet $0; **B-007: Komodo-Instruct HF'te YOK halüsinasyon yakalandı, R12 recovery, Qwen2.5 multilingual baseline'a geri**; Faz 2 A/B aday SeaLLMs-v3-7B-Chat / Sailor2 / Komodo community SFT — OPEN-011) | **B-005 + B-006 + B-007** | OPEN-008 (post-MVP A/B), OPEN-011 (ID Faz 2 A/B) |
| **LLM (TR akademik rötuş)** | Anthropic Claude Haiku 4.5 (yedek faithfulness fallback) | DM-003 | — |
| **LLM router** | LiteLLM (`huggingface/tgi` provider + Claude `model_list`) | DM-015 | — |
| **Worker** | Celery + Redis broker | DM-003 | /summarize + /enrichment async |
| **Reranker** | BGE-reranker-v2-m3 (multilingual cross-encoder) | B42-045 K10 | — |
| **JSON enforcement** | Outlines + lm-format-enforcer (rank alanı yasak — K4) | B42-045 K4 | — |
| **Faithfulness gate** | MiniCheck NLI ≥ 0.7 + ALCE citation-recall ≥ 0.8 + JSON %100 | C3-C5, R9 | — |
| **External** | OpenAlex (.edu.tr polite pool) + Semantic Scholar fallback | DM-009 | — |
| **Deploy** | Vercel (frontend) + Render Docker (backend ALWAYS-restart) + Supabase (managed) + Pinecone (managed) + HF (Scale-to-Zero + 240s keep-alive) | DM-013 (Next 16) + DM-014 (Render) | — |
| **Monitoring** | Sentry (KVKK PII scrub) + Prometheus + Grafana Cloud (free) | F7 | — |

**Çözülen çelişki kaydı**: B42-050 §11'de "Next.js 15" geçiyor; DM-013 (2026-04-29 A-evidence) "Next.js 16" ile kapattı. Bu plan DM-013'ü takip eder.

---

## §2 Mimari katmanlar (warehouse → API → UI)

```
┌─────────────────────────────────────────────────────────────────┐
│  VERİ HAVUZU (Hat A ✅ — read-only)                             │
│  ~/Dataleak/facts/                                              │
│  ├─ fact_paper_id_card v1.2 (24.87M × 15) PaperCard             │
│  ├─ dim_ghost_paper v1.2 (31.85M × 16) GhostCard                │
│  ├─ fact_paper_embedding_bge_m3 (24.87M × 1024-d) → Pinecone    │
│  ├─ fact_paper_sentence_role (24.87M × 13)                      │
│  ├─ fact_theme_year_aggregates v4 (53.9K × 15, t-ESTRA 8/8)     │
│  ├─ fact_gap_matrix v2 (504K × 13)                              │
│  ├─ dim_theme_embedding (4516 × 256-d)                          │
│  └─ mart_cocitation_pair (2.45B × 5) + mart_bibcoupling (2.39B) │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Omer upload (Pinecone + Supabase)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ONLINE STORE                                                   │
│  ├─ Pinecone papers-bgem3 (dense, namespace=__default__) DM-016 │
│  ├─ Supabase schema_v1 (11 tablo MVP — §5)                      │
│  └─ Redis (3-katlı cache)                                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI engine/ — 5-KATMAN + PRESENTER (B-005)                          │
│  Listener → Anchor → Pool Router → Reranker → Curator → Presenter        │
│   (Qwen)    (PMID)   (3-havuz RRF)  (BGE-v2-m3)  (Outlines+LVR)  (TR Cosmos / EN Qwen / ID Sea-Lion) │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────┬───────┴───────┬───────────┬─────────┐
        ▼          ▼               ▼           ▼         ▼
   /api/search  /api/chat  /api/summarize  /api/    /api/
                                          enrichment reading-list
        │          │               │           │         │
        └──────────┴───────────────┴───────────┴─────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Next.js 16 web/ — 5 EKRAN (E1-E5)                              │
│  E1 onboarding | E2 chat | E3 top-5 onay | E4 search | E5 detail│
└─────────────────────────────────────────────────────────────────┘
```

---

## §3 Endpoint envanteri (MVP — 5 endpoint)

| # | Endpoint | Method | Auth | Cache | İşlev | p50 / p95 hedefi |
|---|---|---|---|---|---|---|
| **1** | `/api/search` | POST | JWT | Redis 1h | Sorgu → 5-katman → top 10 paper + faithfulness_meta + KararBant + gate uyarısı | <4s / <7s |
| **2** | `/api/chat` | POST (SSE) | JWT | yok | Kütüphaneci LLM diyalog → multi-turn → IntentPMID extraction → konu kilit | first-token <2s |
| **3** | `/api/summarize` | POST | JWT | Redis 24h | Paper özet (on-demand, Celery → HF Qwen → Claude TR rötuş) | async, <30s wallclock |
| **4** | `/api/enrichment` | POST | JWT | Redis 7d | Ghost paper OpenAlex enrichment (.edu.tr polite pool) → write-back dim_ghost_paper | async, <60s |
| **5** | `/api/reading-list` | GET/POST/PATCH/DELETE | JWT | yok | M52 user_reading_list CRUD (RLS) | <500ms |

**MVP-sonrası ek endpoint envanteri (B42-048 9 kalem yol haritası — §15)**:
`/api/topic-suggest`, `/api/topic-lock` (B42-049), `/api/simulate` (B42-047 §5.5), `/api/notify`, `/api/export` (B42-048 §6).

---

## §4 Endpoint kontratları (özet — tam OpenAPI per-endpoint mini-plan'da)

### 4.1 POST /api/search
```
request: {
  query: string,                  # TR/EN/karışık
  user_id: uuid,                  # JWT'den
  k: int = 10,                    # 1-50
  language_hint?: "tr"|"en"|null,
  include_ghost?: bool = false
}
response: {
  papers: PaperCard[],            # 24.87M corpus + opt. ghost
  faithfulness_meta: { jsonschema_pct, minicheck_nli, alce_recall },
  decision_band: "canon"|"frontier"|"strong_evidence"|"risk",
  gate_warnings: G1G7Warning[],   # G1-G7 kapı ihlali
  latency_ms: int,
  pmid_match_score: float
}
errors:
  422 schema_invalid
  401 jwt_expired
  429 quota_exceeded                # tier %100
  503 pinecone_unavailable + retry_after
```

### 4.2 POST /api/chat (SSE)
```
request: { session_id?: uuid, message: string, user_id: uuid }
response: SSE stream
  event: token        data: { delta: string }
  event: intent_pmid  data: { pmid_segments: PartialPMID }
  event: clarify      data: { question: string, options: string[] }  # margin altı
  event: lock         data: { topic_id: uuid, lock_state: "accepted" }
  event: done         data: { latency_ms: int }
errors: 422, 401, 429
```

### 4.3 POST /api/summarize
```
request: { paper_id: string, mode: "abstract"|"detailed", user_id: uuid }
response (sync 202): { task_id: uuid, eta_s: int }
response (poll GET /api/summarize/{task_id}): { status: "queued"|"running"|"done"|"failed", summary?: SummaryDoc, error?: string }
errors: 404 paper_not_found, 422, 429
```

### 4.4 POST /api/enrichment
```
request: { ghost_id: string, depth: 1|2 = 1, user_id: uuid }
response (202 async): { task_id: uuid, eta_s: int }
errors: 404 ghost_not_found, 422, 429, 503 openalex_rate_limit
```

### 4.5 /api/reading-list
```
GET    /api/reading-list                  → ReadingItem[]
POST   /api/reading-list { paper_id, note }
PATCH  /api/reading-list/{id} { note?, tags? }
DELETE /api/reading-list/{id}
errors: 404, 422, 401
```

---

## §5 Veri havuzu mapping (her endpoint hangi tablo / index)

| Endpoint | Pinecone | Supabase tablolar | Redis key | OpenAlex |
|---|---|---|---|---|
| `/api/search` | `papers-bgem3` (dense, ns=`__default__`) | `papers` (mirror PaperCard partial), `dim_theme`, `users`, `user_quota` | `q:{normalize(query)}:{lang}:{k}` 1h | — |
| `/api/chat` | (gerek yok) | `chat_sessions`, `chat_messages`, `users`, `topic_locks` | session_id state | — |
| `/api/summarize` | (paper komşuluk için opt.) | `papers`, `summary_cache` | `sum:{paper_id}:{mode}` 24h | — |
| `/api/enrichment` | — | `dim_ghost_paper` (write-back), `enrichment_log` | `enrich:{ghost_id}` 7d | OpenAlex `/works/{id}` |
| `/api/reading-list` | — | `user_reading_list` (RLS) | yok | — |

**Supabase schema_v1 — MVP'de 11 tablo (B42-048 9 schema'dan tier/lifecycle/notif çıkarılmış)**:
```
1.  papers              (mirror fact_paper_id_card partial cols)
2.  dim_theme           (mirror dim_theme partial)
3.  users               (auth.users foreign key)
4.  user_profiles       (tier + lang + field_of_study)
5.  chat_sessions
6.  chat_messages
7.  topic_locks         (B42-049, MVP'de basitleştirilmiş 3-state)
8.  user_reading_list   (RLS — M52)
9.  summary_cache       (paper_id → SummaryDoc + LVR_meta)
10. enrichment_log      (ghost_id → OpenAlex fetch audit)
11. user_quota          (LLM token + req sliding window)
```
B42-048 9 schema → **MVP-sonrası**: `projects`, `dataset_link_registry`, `ethics_rule_tree`, `notifications`, `llm_quota` (separated).

---

## §6 Domain rules + sınırlar (kurallar)

### 6.1 K1-K15 halüsinasyon yasakları (B42-045 §12 — runtime enforce)
- **K1**: doğrulanmamış yıl gösterilmez (`year_verified=false` → UI'da yer tutucu "Klasik kaynak (yıl yükleniyor)"); APA referans sadece year_verified=true ile yazılır.
- **K2**: tahmini segment `?` placeholder.
- **K3**: boş veriyle tam referans yok.
- **K4**: LLM rank alanı yok (Curator JSON şemasında `rank` field yasak).
- **K5**: cümle-düzey atıf zorunlu (LVR_min_distance ≥ 0.7 + paper_id+span gerekli).
- **K6**: PMID 12-segment sabit format `D.F.S.T1.T2.T3.Y.Q.I.L.R.V`.
- **K7**: year_upper_bound arka plan, year_verified UI.
- **K8**: ghost `n_corpus_citers ≥ 3`.
- **K9**: confidence<0.5 → segment `?`.
- **K10**: BGE-M3 ana, BGE-reranker-v2-m3 reranker.
- **K11**: TR FAIL fallback hazır.
- **K12**: ağırlıklar bootstrap, LightGBM Aşama 3 kalibre.
- **K13**: eval 330 stratified zorunlu (faz 7).
- **K14**: pilot N=20 yeter, Faz 2 N≥150.
- **K15**: tek doğruluk kaynağı manifest>docx>envanter>state>memory.

### 6.2 Tier limit (B42-049 §1) — MVP'de Öğrenci-only başlar
- **Öğrenci** (MVP default): 1 proje, 50K LLM token/ay, sınırlı follow-up
- **Araştırmacı / Profesyonel / Takım**: MVP-sonrası
- Quota %80 → uyarı banner; %100 → LLM endpoint disable, kalıp özellikler etkilenmez

### 6.3 Topic-lock state machine (B42-049 §2.1) — MVP'de basitleştirilmiş
- MVP: `suggested → accepted → released` (review_due/grace MVP-sonrası)
- `accepted_at = now()`, `released_at` manuel "konu bırak" ile

### 6.4 Performance budget
- API container CPU 2 cores, RAM 4GB
- Pinecone query top_k ≤ 200 (RRF k=60)
- LLM context max 8K token (Qwen baseline)
- Redis memory ≤ 256MB (LRU)

### 6.5 Security checklist
- Supabase RLS her tabloda (user_id = auth.uid())
- JWT verify middleware her endpoint
- ORCID hash+salt, KVKK VERBİS kayıt Beta öncesi
- Rate limit: tier-bazlı sliding window (Öğrenci 60 req/min, vb.)
- LLM input sanitize (prompt injection guard)
- Sentry scrub (PII patterns, API keys)

---

## §7 Frontend page-API map

| Ekran (HEDEF.md §2) | Route | Endpoint çağrıları | State | Loading | Error |
|---|---|---|---|---|---|
| **E1 Onboarding** | `/onboarding` | POST `/api/users/onboarding` (1 kez, profil kaydet) | RHF + Zod | skeleton form | inline field error |
| **E2 Kütüphaneci** | `/kutuphaneci` | POST `/api/chat` SSE | Zustand chat store | typing indicator | chat bubble error + retry |
| **E3 Top-5 onay** | `/kutuphaneci/dogrula` (modal) | (chat çıktısı, no extra call) | Zustand | — | — |
| **E4 Arama** | `/kutuphane/arama/[query_id]` | POST `/api/search` (TanStack Query) | TanStack cache | shimmer 5 PaperCard | "Arama başarısız, tekrar dene" + retry |
| **E5 Detay** | `/calisma-masasi/paper/[pmid]` | GET `/api/papers/{pmid}` (cache 24h) + on-demand POST `/api/summarize` | TanStack | skeleton + 13 sinyal placeholder | "Özet üretilemedi" + retry |
| **+ Reading list** | `/kutuphane/okuma-listesi` | CRUD `/api/reading-list` | TanStack mutation | optimistic | toast error |

**MVP-sonrası 25 alt-sayfa (B42-047) yol haritası** — §15.

---

## §8 Başarı metrikleri (HEDEF.md §4 — C1-C11)

| # | Kriter | Hedef | Ölçüm |
|---|---|---|---|
| C1 | Arama p50 latency | <4s | 100 sorgu medyan |
| C2 | Arama p95 latency | <7s | aynı |
| C3 | JSON şema validation | %100 | Outlines + lm-format-enforcer |
| C4 | MiniCheck NLI | ≥0.7 | 100 yanıt cümle ortalama |
| C5 | ALCE citation-recall | ≥0.8 | aynı |
| C6 | Cache hit ratio | ≥%70 | Redis stats 7d |
| C7 | HF endpoint warm ratio | ≥%95 | keep-alive ping log |
| C8 | LVR_min_distance ihlal | %0 | her cümle paper_id+span ile |
| C9 | K1 ihlali (yıl tahmini) | %0 | runtime fail |
| C10 | Pilot user sorgu/hafta | ≥50 | Supabase event |
| C11 | Pilot NPS | ≥+30 | hafta-2 anket |

**MVP "tamam" demek**: C1-C9 her zaman PASS, C10-C11 pilot 2 hafta sonunda PASS.

---

## §9 Implementasyon faz sırası (yeniden sıralanmış — backend dominant)

| Faz | İş | Süre | Önkoşul | Çıktı |
|---|---|---|---|---|
| **F1' Master Plan** (bu dosya) | Omer onayı | 1 gün | METHOD §1 + B42-046 | DECISIONS B-001 entry + 5 mini-plan |
| **F2 Backend Skeleton + /api/search slice** | FastAPI app + 5-katman + Pinecone client + 1 endpoint çalışır | 4-5 gün | F1' onay + Pinecone upload + Supabase schema_v1 | curl 200 + p50<4s |
| **F3 Backend kalan 4 endpoint** | /chat /summarize /enrichment /reading-list | 4-5 gün | F2 PASS | 5 endpoint çalışır + integration test |
| **F4 Frontend Skeleton + E4 Arama** | Next.js 16 + 4-zone palet + PaperCard fiş + arama sayfası | 3-4 gün | F2 PASS | curl yerine UI'dan arama |
| **F5 E1 Onboarding + E2 Chat + E3 Top-5** | RHF + SSE + IntentPMID flow | 4-5 gün | F3 PASS | tam akış: onboarding → chat → search |
| **F6 E5 Detay + Summarize + Ghost** | paper detay + on-demand özet + ghost enrichment | 4-5 gün | F4+F5 PASS | tam ürün akışı |
| **F7 Quality + Deploy + Pilot** | 3-katlı faithfulness + Sentry + Docker + HF deploy + 5 pilot user | 3-4 gün | F6 PASS | MVP HAZIR |

**Toplam: 23-32 gün** (IS_PLANI 28-35 gün ile uyumlu, frontend planlama fazını master'a entegre ettik için 4-5 gün kazanım).

---

## §10 Critical files (kategorize)

### Backend (touch — `~/Desktop/papermind-app/api/`)
- `api/main.py` (yeni, FastAPI app + middleware bootstrap, ~80 LOC)
- `api/middleware/auth.py` (yeni, Supabase JWT verify, ~60 LOC) — TODO(sercan)
- `api/middleware/rate_limit.py` (yeni, Redis sliding window, ~80 LOC) — TODO(sercan)
- `api/middleware/sentry.py` (yeni, init + scrub, ~50 LOC) — TODO(sercan)
- `api/db/supabase_client.py` (yeni, singleton, ~40 LOC)
- `api/db/pinecone_client.py` (yeni, query wrapper + retry, ~80 LOC) — TODO(sercan)
- `api/db/redis_client.py` (yeni, 3-katlı cache helpers, ~60 LOC) — TODO(sercan)
- `api/services/listener.py` (yeni, Qwen multi-query 4-6 rewrite, ~120 LOC)
- `api/services/anchor.py` (yeni, PMID 12-segment match, ~140 LOC)
- `api/services/pool_router.py` (yeni, 3-havuz RRF k=60, ~180 LOC)
- `api/services/reranker.py` (yeni, BGE-v2-m3, ~100 LOC)
- `api/services/curator.py` (yeni, Outlines + LVR validator, ~200 LOC)
- `api/services/presenter.py` (yeni, **B-005** dil-spesifik akademik sunum LLM — Curator yapısal çıktıyı kullanıcının seçtiği dile çevirir; LiteLLM `model_list` içinden cosmos-tr-sunum / qwen-en-sunum / sealion-id-sunum route eder, ~120 LOC)
- `api/services/litellm_router.py` (yeni, Qwen primary + Claude fallback, ~80 LOC) — TODO(sercan)
- `api/routes/search.py` (yeni, ~150 LOC)
- `api/routes/chat.py` (yeni, ~120 LOC, SSE)
- `api/routes/summarize.py` (yeni, ~140 LOC, Celery)
- `api/routes/enrichment.py` (yeni, ~100 LOC, Celery + OpenAlex)
- `api/routes/reading_list.py` (yeni, ~80 LOC, RLS CRUD)
- `api/models/*.py` (Pydantic request/response schemas)
- `api/workers/celery_app.py` + `api/workers/tasks/*.py` — TODO(sercan)

### Frontend (touch — `~/Desktop/papermind-app/web/src/`)
- `web/package.json` (yeni — Next.js 16.x + React 19 + dependencies)
- `web/next.config.ts` + `web/tsconfig.json` + `web/tailwind.config.ts`
- `web/src/styles/globals.css` (4-zone CSS variable palet, B42-050 §1.4)
- `web/src/app/layout.tsx` (root layout, font load Lora + Crimson + Geist)
- `web/src/app/onboarding/page.tsx` (E1)
- `web/src/app/kutuphaneci/page.tsx` (E2)
- `web/src/app/kutuphane/arama/[query_id]/page.tsx` (E4)
- `web/src/app/calisma-masasi/paper/[pmid]/page.tsx` (E5)
- `web/src/components/PaperCard.tsx` (kütüphane fişi, B42-050 §5)
- `web/src/components/Banner.tsx` (el-yazısı not, B42-050 §3)
- `web/src/components/Button.tsx` (4-sınıf, B42-050 §4)
- `web/src/components/KararBant.tsx` + `GateUyari.tsx` + `ChipRozet.tsx`
- `web/src/lib/api.ts` (TanStack Query + fetch wrapper + auth header)
- `web/src/lib/supabase.ts` (client init)
- `web/src/lib/zustand-stores/*.ts` (chat store, query store)

### Tests (touch)
- `tests/unit/test_listener.py` + `test_anchor.py` + `test_pool_router.py` + `test_reranker.py` + `test_curator.py`
- `tests/integration/test_search_endpoint.py` + `test_chat_sse.py` + `test_summarize_celery.py`
- `tests/e2e/test_search_p95.py` (Playwright)
- `tests/load/test_search_concurrency.py` (Locust, 50 concurrent user, 5 dk)

### Docs (touch)
- `docs/plans/F1_master_plan.md` (bu plan, master)
- `docs/plans/F3a_search.md` (Sercan mini-plan, ARCHITECT_PROMPT_TEMPLATE §0..§7)
- `docs/plans/F3b_chat.md`
- `docs/plans/F3c_summarize.md`
- `docs/plans/F3d_enrichment.md`
- `docs/plans/F3e_reading_list.md`
- `docs/backend/api_kontrat.md` (5 endpoint × tam OpenAPI schema)
- `docs/backend/pipeline_akis.md` (5-katman akış detay)
- `docs/backend/chip_library_spec.md` (12 chip — OPEN-003 sonrası)
- `docs/STATE.md` (her faz sonrası güncelle)
- `docs/SPRINT_HISTORY.md` (P-numara log)
- `docs/DECISIONS.md` (B-NNN entry)

### Read-only (DOKUNMA — pre-flight Read zorunlu)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/CLAUDE.md` (canon protokol)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/STATE.md` (warehouse closure)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/DECISIONS.md` (B42-045/046/047/048/049/050 dondurulmuş)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-045-MIMARI-V1.md` (5-katman + PMID + PaperCard + GhostCard)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-047-FRONTEND-IA.md` (25 alt-sayfa)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-048-BACKEND-NEW-ASSETS.md` (9 schema)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-049-PROJECT-LIFECYCLE.md` (4 tier + lifecycle)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-050-DESIGN-DIRECTION.md` (4-zone + tipografi)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/ENVANTER.md` (warehouse manifest)
- `~/Desktop/papermind-app/docs/HEDEF.md` (MVP scope sınırı)
- `~/Desktop/papermind-app/docs/DM_RULES.md` (R1-R12 + DM-001..DM-015)
- `~/Desktop/papermind-app/docs/ARCHITECTURE.md` (5-katman + ESTRA + chip)
- `~/Desktop/papermind-app/docs/POLICIES.md` (KVKK + privacy)
- `~/Desktop/papermind-app/reference/*` (Papermind_V2 warehouse özet)
- `~/Dataleak/facts/*` (warehouse output, write yok — sadece Pinecone+Supabase'e upload)

---

## §11 TODO(sercan) — handoff iş tanımı

Sercan'ın yapacağı işler **per-endpoint mini-plan dosyalarında** (F3a-F3e) detaylı; bu master'da özet:

### 11.1 Infrastructure (faz F2 baseline)
- [ ] Supabase project init + schema_v1 migration (11 tablo MVP — §5)
- [ ] RLS policy her tabloda (`user_id = auth.uid()` pattern)
- [ ] Pinecone index `papers-bgem3` 1024-d cosine (Omer upload eder, Sercan client wrapper yazar)
- [ ] Redis Render-managed (3-katlı namespace: `q:`, `sum:`, `enrich:`, `user:`)
- [ ] Celery + Redis broker config
- [ ] HF Inference Endpoint (Qwen2.5-7B-Instruct AWQ, Scale-to-Zero, keep-alive 240s)
- [ ] LiteLLM router (Qwen primary + Claude fallback, cost-aware)
- [ ] Sentry init + KVKK PII scrub patterns
- [ ] Rate limit middleware (tier-bazlı, Redis sliding window)

### 11.2 Code (faz F2-F3)
- [ ] `api/main.py` FastAPI bootstrap
- [ ] 3 middleware (auth + rate_limit + sentry)
- [ ] 3 db client (supabase + pinecone + redis)
- [ ] 5-katman engine (listener + anchor + pool_router + reranker + curator)
- [ ] 5 endpoint route
- [ ] Celery worker + 2 task (summarize + enrichment)
- [ ] Pydantic schemas (request/response her endpoint)
- [ ] LVR validator (Curator içinde, K5 enforce)
- [ ] K1-K15 runtime guards (her endpoint çıkışında check)

### 11.3 Tests (her commit yeşil olmalı)
- [ ] Unit test her servis (≥1 happy path + ≥1 fail path)
- [ ] Integration test her endpoint (200 + 422 + 401 + 429)
- [ ] E2E test arama akışı (Playwright)
- [ ] Load test 50 concurrent user (Locust, 5 dk, p95<7s)

### 11.4 Deploy (F7)
- [ ] Dockerfile + docker-compose.yml
- [ ] Render service (backend) + env var setup
- [ ] Vercel deploy (frontend) — Omer
- [ ] Supabase migration up production
- [ ] HF Endpoint warm ratio monitor
- [ ] Sentry alert kuralları + Grafana dashboard

---

## §12 Verification harness (her faz için PASS kriteri — beklenen output gömülü)

```bash
# F2 Backend skeleton (P001 sonrası)
cd ~/Desktop/papermind-app/api && pytest tests/unit/ -v
# Beklenen: 0 fail, ≥10 PASS, "Listener test_multi_query_4_rewrites PASSED" görmek

# F2 /api/search slice (P008 sonrası)
curl -X POST http://localhost:8000/api/search \
  -H "Authorization: Bearer $JWT" \
  -d '{"query":"makine öğrenmesi tıp uygulaması","k":10}'
# Beklenen: 200 + papers[10] + faithfulness_meta + decision_band ∈ {canon,frontier,strong_evidence,risk}
# Beklenen: latency_ms < 4000 (p50) — 100 sorgu örnekleminde

# F2 K1 enforcement
curl -X POST .../search -d '{"query":"...", "include_ghost": true}'
# Beklenen: ghost paper kartında "year" field YOK; "Klasik kaynak (yıl yükleniyor)" placeholder

# F4 Frontend baseline (build)
cd web && npm run build
# Beklenen: 0 type error + 0 lint error + Lighthouse score ≥90 (Performance + Accessibility)

# F5 E2 chat SSE
curl -N -X POST .../chat -d '{"message":"yapay zeka ile depresyon tedavisi"}' -H "Accept: text/event-stream"
# Beklenen: stream "event: token" ile başlar, en az 1 "event: intent_pmid", final "event: done"

# F6 E5 summarize end-to-end
curl -X POST .../summarize -d '{"paper_id":"W123", "mode":"detailed"}'
# Beklenen: 202 + task_id; poll → status: done <30s; summary cited (LVR ✓)

# F7 Quality gate (3-katlı faithfulness)
python tests/quality/run_eval.py --n 100
# Beklenen: jsonschema_pct=100, minicheck_avg≥0.7, alce_recall≥0.8

# F7 Load test
locust -f tests/load/test_search_concurrency.py --users 50 --spawn-rate 5 --run-time 5m
# Beklenen: p50<4000ms, p95<7000ms, error rate <1%

# F7 K9 ihlal sayısı (runtime fail enforced)
python tests/quality/run_k9_audit.py --sample 1000
# Beklenen: 0 ihlal (runtime fail count = 0)
```

---

## §13 Commit disiplini

- **Branch**: `feat/F<N>-<slug>` (örn. `feat/F2-search-skeleton`)
- **Atomic commit boundary**: her P00X bir commit (P001 main+middleware, P002 5-katman boş sınıf, P003 listener, P004 anchor, ...)
- **Pre-flight Read**: Sercan/Claude her commit öncesi §10 Read-only listesinde geçen dosyaları okur (manifest_*.json + DECISIONS.md + HEDEF.md + DM_RULES.md)
- **Test gate**: §12 verification PASS olmadan PR merge **YASAK**
- **Co-Authored-By**: Claude Opus 4.7 (her commit footer)
- **PR template**: `## Summary` 3 madde + `## Test plan` ✅ checklist + verification çıktı log
- **Commit message format**: `[P001] api: FastAPI bootstrap + 3 middleware`
- **Hook bypass yasak**: `--no-verify` kullanma; hook FAIL ise root cause fix

---

## §14 Açık karar noktaları (engelleyiciler)

| OPEN | Soru | Kim | Engellediği faz |
|---|---|---|---|
| ~~OPEN-001~~ | ~~LLM model kesin adı~~ | **KAPALI 2026-04-30 (B-005)** — 2-katmanlı: anlama Qwen2.5 + sunum Cosmos/Qwen/Sea-Lion | KAPATILDI |
| **OPEN-008** | MVP-sonrası LLM A/B test (Phi-4 14B EN sunum aday + Cosmos TR pilot doğrulama) | Pilot sonrası | F7 sonrası |
| **OPEN-011** | Sea-Lion v3-8b lisans doğrulama (HF model card "Apache mı, MIT mi?" kontrol) | Omer / Sercan | F2 P004 mini-benchmark öncesi |
| **OPEN-003** | 12 chip listesi tam (chip_library_spec.md için) | Omer | F2 |
| **OPEN-004** | Pipeline_Akis canonical (1 dosya seç) | Omer paylaşacak | F1' onay sonrası |
| **OPEN-005** | Top 5 onay margin eşiği (E3, hangi pmid_match_score altı) | Omer | F5 |
| **OPEN-006** | Ghost cache TTL (7d default kabul mu?) | Omer | F6 |
| **OPEN-007** | Pilot 5 user kim (akademisyen network) | Omer | F7 |
| **B42-046** | Backend Aşama 1 ŞARTLI KABUL (Papermind_V2 DECISIONS) | Omer | F2 |
| **METHOD §1** | Akademik Mekanlar mekan modeli onayı | Omer | F4 frontend |

**Kritik path**: OPEN-001 + OPEN-003 + OPEN-004 + B42-046 → F1' onay sonrası 24 saat içinde cevap gerekir, yoksa F2 başlayamaz.

---

## §15 İleri vizyon yol haritası (MVP-sonrası)

| Faz | Süre | Kapsam | Karar referansı |
|---|---|---|---|
| **MVP** (bu sprint) | 30 gün | 5 ekran + 5 endpoint + pilot 5 user | HEDEF.md, bu plan |
| **Faz 2 — Discovery + Curation tezgâhları** | 6-8 hafta | B42-047 §1 Discovery (5 alt-sayfa) + §2 Curation (5 alt-sayfa) + topic-suggest endpoint + topic-lock 3-state machine + Connected Papers viz | B42-047, B42-048 §2, B42-049 §2.1 |
| **Faz 3 — Defense + Simülasyon Odası** | 8-10 hafta | B42-047 §5 Defense (6 alt-sayfa) + Simulation Room (CrewAI multi-agent) + Google Flow perde reveal + advisor-rescue chat | B42-047 §5.5, B42-050 §7 |
| **Faz 4 — Authoring + Defter** | 4-6 hafta | B42-047 §4 Authoring (4 alt-sayfa) + Tiptap Defter cilt-sırtı sidebar + 📌 Nota ekle context capture + export DOCX/PDF | B42-047 §A4, B42-048 §6 |
| **Faz 5 — Tier upgrade + billing** | 4 hafta | B42-049 4 tier (Araştırmacı/Profesyonel/Takım Çalışması) + Stripe/iyzico billing + Multi-user simülasyon (jüri provası) | B42-049 §1, OPEN-LC5 |
| **Faz 6 — Lifecycle + notification** | 2-3 hafta | B42-049 topic-lock state machine full (review_due/grace/released) + cron + 12 trigger notification + e-posta | B42-049 §2-§4 |
| **Faz 7 — Gap Atlas + ESTRA viz** | 6-8 hafta | B42-047 §3 Gap Atlas (5 alt-sayfa) + UMAP + ESTRA radar + 504K gap matrix viz + arxiv watch + Google Trends | B42-047 §3 |

**Toplam ileri vizyon**: ~6-9 ay MVP-sonrası. Tüm fazlar bu master plan üzerine inşa olur — backend kontratları MVP'de baseline atılır, frontend `/(app)/` route grupları MVP-sonrası fazlarda doldurulur.

---

## §16 Per-endpoint mini-plan paketi (Sercan teslim)

5 dosya, her biri ARCHITECT_PROMPT_TEMPLATE §0..§7 + WhatsApp checklist şablonuyla:

```
docs/plans/
├── F3a_search.md       # POST /api/search — 5-katman + Pinecone + Redis + LVR
├── F3b_chat.md         # POST /api/chat SSE — Listener + IntentPMID + topic-lock
├── F3c_summarize.md    # POST /api/summarize — Celery + HF + Claude TR rötuş
├── F3d_enrichment.md   # POST /api/enrichment — OpenAlex polite pool + write-back
└── F3e_reading_list.md # CRUD /api/reading-list — RLS + Supabase
```

**Her mini-plan içeriği** (kompakt, ~150-250 satır):
- §0 Bağlam (3 cümle, niş + halüsinasyon-sıfır)
- §1 Karar günlüğü (DM-NNN + B42-NNN referans)
- §2 Endpoint sözleşmesi (tam OpenAPI)
- §3 İmplementasyon adımları (atomik P-numara)
- §4 Verification (komut + beklenen output, 6 manuel smoke senaryosu)
- §5 Critical files (Backend touch + Tests touch + Read-only)
- §6 TODO(sercan) (auth/rate/log/cache/etc.)
- §7 Commit disiplini (atomic boundary + branch + co-author)

---

## §17 Final commitment

Plan onaylandı (2026-04-29 auto-mode):

1. ✅ **Bu plan** `~/Desktop/papermind-app/docs/plans/F1_master_plan.md` olarak kopyalandı (DM-013 Next 16 + 11-tablo düzeltmesi ile)
2. ✅ **DECISIONS.md** entry: `B-001 ŞARTLI KABUL 2026-04-29 — End-to-End Master Plan (Backend-First)`
3. ⏳ **5 mini-plan dosyası** F3a-F3e Claude tarafından yazılıyor (bu sprint)
4. ⏳ **Sercan brief**: 5 mini-plan + ARCHITECT_PROMPT_TEMPLATE §0-§7 + Read-only listesi teslim edilecek
5. ⏳ **F2 başlangıç koşulu**: OPEN-001 + 003 + 004 + B42-046 cevap + Pinecone upload + Supabase project init
6. **Atomic commit P001**: `feat/F2-search-skeleton` branch + `api/main.py + 3 middleware` (yeşil pytest ile)
7. **F2 SHIP kriteri**: §12 verification çıktısı 7 satır PASS + STATE.md güncel + SPRINT_HISTORY entry

---

## §18 Verification — bu plan dosyasının kendisi (kalite kapısı)

| Kontrol | Sonuç |
|---|---|
| HEDEF.md §1-§4 ile uyumlu (5 ekran + 5 endpoint + C1-C11) | ✓ |
| DM_RULES R1 (plan-first) ile uyumlu | ✓ |
| B42-045/047/048/049/050 dondurulmuş kararlar referans + uyumlu | ✓ |
| DM-013 Next.js 16 ile hizalı (master draft "15" düzeltildi) | ✓ |
| DM-014 Render backend host hizalı | ✓ |
| DM-015 LiteLLM router hizalı | ✓ |
| Sercan handoff için ARCHITECT_PROMPT_TEMPLATE §0-§7 yapısı | ✓ |
| K1-K15 halüsinasyon yasakları runtime enforce edilmiş | ✓ |
| Generic SaaS reflexi yok — niş bağlam (TR-akademik, ALI advisory) §0'da | ✓ |
| MVP scope (5 endpoint) + ileri vizyon (B42-047 25 sayfa) ayrılmış | ✓ |
| Verification beklenen output gömülü (§12, 7 senaryo) | ✓ |
| Critical files kategorize + Read-only ayrı | ✓ |
| TODO(sercan) handoff bölümü mevcut | ✓ |
| Açık karar noktaları net (§14) — engelleyiciler işaretli | ✓ |

---

**Son söz**: Bu plan, Omer'in "veri havuzundan kullanıcı deneyimine kadar her şeyi planlayalım, backend sağlam kurgu, kurallar/sınırlar/başarı değerleri" talebine cevap. Onay sonrası 5 mini-plan + DECISIONS B-001 entry + Sercan brief 1-2 günde teslim. F2 backend skeleton 4-5 günde curl ile çalışır.
