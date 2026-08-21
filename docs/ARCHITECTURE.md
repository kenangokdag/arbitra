# ARCHITECTURE.md — PaperMind App MVP Mimari

> **Statü:** v0.1 skeleton (2026-04-29). F2 sonunda donar.
> **Referans:** B42-045 (5-katman + PMID 12-segment + PaperCard + GhostCard) + B42-040 (12 chip) + ESTRA Politikası v1.1

---

## 1. ÜST KATMAN — sistem haritası

```
┌─────────────────────────────────────────────────────────────────────┐
│  KULLANICI KATMANI — Next.js 16 (web/) — Turbopack + async params   │
│  - Onboarding (8 input anket)                                       │
│  - Kütüphaneci sohbet (multi-turn dialog, SSE stream)               │
│  - Top 5 paper onay (PMID match)                                    │
│  - Arama sonuç (KararBant + GateUyari)                              │
│  - Paper detay (13 sinyal + 12 chip + NedenPanel engineer-mode)     │
│  - Tema sayfası                                                     │
│  - Okuma önerisi (corpus + ghost ek)                                │
│  - Reading list                                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               ↕ (HTTPS + JWT)
┌─────────────────────────────────────────────────────────────────────┐
│  API KATMANI — FastAPI (api/)                                       │
│  Routes:                                                            │
│  - /api/search          POST, 5-katman entry                        │
│  - /api/summarize       single + multi paper                        │
│  - /api/chat            kütüphaneci dialog (SSE)                    │
│  - /api/reading-list    M52                                         │
│  - /api/enrichment      ghost on-demand (OpenAlex)                  │
│  - /api/auth            Supabase JWT                                │
│  - /healthz                                                         │
│                                                                     │
│  Middleware: rate_limit (Redis), auth (JWT), observability,sentry   │
│  Workers: Celery (summarize_task, enrichment_task)                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               ↕
┌─────────────────────────────────────────────────────────────────────┐
│  ENGINE KATMANI — Saf core (engine/)                                │
│                                                                     │
│  ┌─ Listener ──────────────────────────────────────────────────┐   │
│  │  Qwen multi-query rewrite + 3-yol intent (explicit/silent/  │   │
│  │  default) + IntentPMID extraction                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─ Anchor ────────────────────────────────────────────────────┐   │
│  │  Top 3-10 paper, 12-segment PMID match + margin gate +      │   │
│  │  3-katlı fallback (clarification card)                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─ Pool Router ───────────────────────────────────────────────┐   │
│  │  3-havuz: Çekirdek (alan-kilit) / Komşu (bibcoup+cocite+    │   │
│  │  citation+same-shelf) / Uzak (bridge) — RRF k=60            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─ Reranker ──────────────────────────────────────────────────┐   │
│  │  BGE-reranker-v2-m3, K=50/200/500 tier-bazlı                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─ Curator ───────────────────────────────────────────────────┐   │
│  │  Outlines + lm-format-enforcer JSON şema, rank alanı YOK    │   │
│  │  Cümle-düzey atıf (LVR), faithfulness 3-katlı               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ESTRA: w (offline) + d (offline R/E) + t (offline tema×yıl) +     │
│         c (online PageRank) + s (online hybrid) + r/m (online)     │
│  Gates: G1 retraction / G2 predatory / G3 düşük taban / G4 eksik  │
│         metadata / G5 çok yeni / G6 MQ floor / G7 disiplin         │
│  Chip Library: B42-040 12 chip + 4 freeze faz (DETAY OPEN-003)     │
│  LVR Validator: her cümle paper_id+span ile doğrulanır             │
└──────────────────────────────┬──────────────────────────────────────┘
                               ↕
┌─────────────────────────────────────────────────────────────────────┐
│  VERİ + LLM KATMANI                                                 │
│                                                                     │
│  Pinecone (24M corpus BGE-M3 1024-d Float16 dense, DM-016)         │
│  Postgres / Supabase (auth + memory + state + consent)              │
│  Redis Upstash (L1 cache + Celery broker)                          │
│  HuggingFace Inference Endpoint (Qwen / YTU LLM, Scale-to-Zero)    │
│  Anthropic Claude Haiku (sadece son akademik TR rötuş)              │
│  OpenAlex API (.edu.tr polite pool, ghost on-demand)                │
│  Semantic Scholar API (fallback)                                    │
│  Drive (read-only warehouse referansı: M31 PaperCard, M51 Ghost,   │
│         t-ESTRA, w-ESTRA, d-ESTRA, gap_matrix, sentence_role,      │
│         centrality, beauty, disruption, velocity, ref_age,         │
│         interdisc, method×topic, bibcoupling top-50, cocite mart)  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. AKIŞ — kullanıcı arama yaparsa

```
1. Kullanıcı sorgu yazar (TR/EN/mixed)
2. Frontend → POST /api/search
3. Middleware: auth + rate_limit + observability
4. Engine.Listener: query → 4-6 alt-sorgu + IntentPMID
5. Engine.Anchor: PMID 12-segment match → top 3-10 anchor paper
6. Engine.PoolRouter: Çekirdek + Komşu + Uzak havuz → top 500 (RRF k=60)
7. Engine.Reranker: BGE-v2-m3 → top 50
8. Engine.Curator: top 10 + Outlines JSON + LVR + faithfulness gate
9. Cache lookup (L1 Redis hash(query+model+version))
10. LLM call (HF Endpoint) → streaming SSE
11. Response: results[] + pmid_intent + faithfulness_meta + latency_ms
12. Frontend render: PaperCard + KararBant + GateUyari (G1-G7) + ChipLibrary
```

**Hedef p50:** <4s end-to-end. **Hedef p95:** <7s.

---

## 3. AKIŞ — kullanıcı paper detay isterse (özet talebi) [2026-04-30 revize]

```
1. Kullanıcı paper kartına tıklar → /calisma-masasi/paper/[pmid]
2. Frontend Zustand store'dan PaperCard'ı okur (search response'undan)
   - 13 sinyal + 12 chip + KararBant + GateUyari ZATEN var, ek API ÇAĞRISI YOK
3. Frontend render: PaperCard + KararBant + 12 chip + NedenPanel (engineer-mode)
4. Kullanıcı "Detay özet ver" tıklar (opsiyonel — abstract zaten görünür)
5. Frontend → POST /api/summarize {paper_id, mode: "detailed"}
6. Cache lookup (Redis 24h hash)
7. Cache miss → Celery task → LiteLLM (Qwen draft → Claude Haiku TR rötuş)
8. Quality gate (jsonschema=100% + MiniCheck NLI ≥0.7 + ALCE recall ≥0.8)
9. LVR validator (cümle-düzey atıf paper_id+span ≥0.7)
10. K1 yıl scrub (year_verified=false → response'tan year drop)
11. Cache yaz (Supabase summary_cache + Redis 24h)
12. Frontend poll → 200 + SummaryDoc
```

**Önemli:** `/api/papers/{id}` ayrı endpoint **YOK**. Master plan §3'teki 5 endpoint MVP scope'una sadık kalındı; detail sayfası client-side cache pattern'i ile çalışır.

---

## 4. GHOST PAPER FLOW (on-demand)

```
1. Kullanıcı reading-list veya recommendation'da ghost paper görür
2. Ghost kart: PMID + Q_proxy + indegree (M51 GhostCard'tan, ÖNCEDEN var)
3. Kullanıcı "Detay özet" butonuna tıklar
4. Frontend → POST /api/enrichment {ghost_id}
5. Cache lookup (L1 Redis 90 gün → L2 Postgres 1 yıl)
6. Cache miss → OpenAlex API call (.edu.tr polite pool)
7. Cevap: abstract + kaynakça + DOI + OpenAlex link
8. Cache yaz (3-katlı)
9. Frontend render: ek "Detay özet" paneli
```

---

## 5. KARAR BANDI (UX — ESTRA P1)

Kullanıcıya **skor değil bant** gösterilir:

| Bant | Tetikleyici |
|---|---|
| **Canon** | d-ESTRA R yüksek + Q_weak yüksek + venue_tier Q1/Q2 |
| **Frontier** | d-ESTRA E yüksek + velocity_pct yüksek + age < 3yr |
| **Kuvvetli kanıt** | MQ_Tier1_claimed yüksek + sentence_role RES yoğun |
| **Risk** | G1-G7 herhangi gate tetiklendi (retracted / predatory / suspicious) |

"Neden?" tıklarsa NedenPanel açılır → 13 sinyal + chip detay (engineer-mode).

---

## 6. GÜVENLİK + KVKK

- Auth: Supabase JWT
- Rate limit: Redis sliding window (anonim 10 req/dk, login 60 req/dk)
- PII scrub: Sentry middleware (email/token/orcid maskeli)
- Consent: `fact_consent_event` SCD-2 + cascade-delete API
- LLM call audit: `fact_llm_call` (input hash + token + cost)
- Veri lokasyonu: Supabase EU region (KVKK uyumlu)

---

## 7. MİMARİ KARARLAR — GÜNCEL DURUM (2026-04-30)

### Kapanmış kararlar (B-005..B-009)
- ✅ **OPEN-001** LLM model — KAPALI (B-005 + B-006 + B-007): 2-katmanlı mimari, anlama Qwen2.5 + sunum dil-spesifik (TR Cosmos Turkish-Gemma-9b-T1 ayrı endpoint, EN+ID Qwen2.5 anlama endpoint'i ile ortak)
- ✅ **OPEN-003** B42-040 12 chip — KAPALI (B42-040 entry): DI/SB/d/Ravg/RS/MQk/Ck/EDk/BC/SR/TSP/RX + 4 fazlı freeze + 7-renk palet + sabit slot sırası
- ⚠️ **OPEN-004** Pipeline_Akis.docx — ŞARTLI KAPALI: B42-040 + B42-045 + B42-046 manifest-seviyesi yazılı yeterli; docx geldiğinde marjinal revize
- ✅ **B42-046** Backend Aşama 1 ŞARTLI KABUL — Papermind_V2/DECISIONS.md'ye yazıldı
- ✅ **B-008** Faz 1 PaperCard (24,862,232) + GhostCard (31,855,437) Supabase upload tamam (~28 GB)
- ✅ **B-009** paper_satellites notebook FK guard patch hazır (Faz 2 yarın koşar)

### Hâlâ açık (F2 başlangıç engelleyicisi DEĞİL)
- ⏳ **OPEN-005** Top 5 onay margin eşiği (F5'te netleşir, default 0.7 ile başla)
- ⏳ **OPEN-006** Cache TTL ghost (F6'da netleşir, 7d default)
- ⏳ **OPEN-007** Pilot 5 user (F7'de netleşir)
- ⏳ **OPEN-011** ID sunum LLM Faz 2 A/B test (Qwen2.5 baseline pilot doğrulaması sonrası)
- ⏳ **METHOD §1** Akademik Mekanlar mekan modeli (F4 frontend skeleton öncesi)

### F2 başlangıç engelleyicisi (paralel akıyor)
- ⏳ **Pinecone Yol B re-upload** (metadata-enriched, in-flight Omer)
- ⏳ **HF Inference Endpoint kurulumu** (Qwen2.5 + keep-alive 240s, Sercan)

### Yeni endpoint kararı (master plan §3 ile uyum)
- 🔧 **`/api/papers/{id}` ayrı endpoint YOK** — Detail sayfası `/api/search` response'undaki PaperCard verisini Zustand cache'inden okur (client-side); ek özet için `/api/summarize` (mode=detailed) kullanılır. ARCHITECTURE.md §3 akışı bu pattern ile revize edildi.

---

## 8. F2 SONRASI MİMARİ DONDURUR

F2 (Backend Slice 1) bittikten sonra bu dosya **v1.0 dondurulur**. Sonraki değişiklikler yeni B42-NNN benzeri DM-NNN kararıyla yapılır.
