# PaperMind — Uçtan Uca Yazılım Mimarisi

> **Belge tarihi:** 2026-05-11 (v2 — workshop.py F13-S2..S11 konsolidasyonu yansıtıldı; 17 ek endpoint MEVCUT'a alındı, kalan açık 14 endpoint; engine 9 dizin MEVCUT) · **Kanıt seviyesi:** A (codebase Read/Grep + git log doğrulandı) + B (Excel + Sayfa_Plani_v2 RTF + CLAUDE.md/STATE/NEXT_ACTION yazılı kanıt) + A (Supabase Dashboard ekran kanıtı `fact_paper_disruption` canlı)
> **Kapsam:** 27 ürün sayfası + 4 mimari katman + 1 çekirdek motor (5-katman) + veri ambarı 25M corpus + ghost katmanı.
> **Amaç:** "Olan + olmayan + bitirmek için ne lazım" tek bir belgede.

---

## A. BASİT CEVAP — Ne, Nasıl, Beklenen

### A.1 Burası ne yapacak?

PaperMind akademik araştırmanın baştan sona dijital iş arkadaşıdır. Kullanıcı bir konu yazar; sistem onu adım adım literatür taramasından dergiye gönderme hazırlığına kadar götürür. Yedi büyük durak vardır:

1. **Vitrin (1)** — kullanıcı henüz hesap açmadı. Konuyu yazıyor, OpenAlex'ten 25 makale önizleme görüyor, kısa literatür özeti alıyor. Buradan "Projeye Dönüştür" butonu atölyeye geçiriyor.
2. **Keşif (2.1–2.5)** — proje açıldı. Kütüphaneci ile sohbet, çapa makale seçimi, 500 makalelik kalıcı kütüphane oluşturma, bibliyometrik / tematik / kavram ağı analizleri.
3. **Literatür (3.1–3.4)** — 500 makalenin içinden okumaya değer olanları sıralama, ilişkili çalışmalar, yöntem matrisi, akademik formatlı sentez üretme.
4. **Boşluk (4.1–4.5)** — boşluk haritası, profil, özgünlük (Funk-Owen CD index + Sleeping Beauty), gap karşılaştırma, akademik etki eğrisi.
5. **Yazım (5.1–5.4)** — yayın türü seçimi, taslak, akademik dil uyarlama, atıf stili.
6. **Savunma (6.1–6.5)** — yayın içeriği doldurma, savunma formatı, bireysel kontrol, dergi hakem simülasyonu (3 persona), jüri simülasyonu (5 persona).
7. **Yan paneller (S1, S2)** — Araştırma Defteri (sürekli erişilebilir ajanda) ve Proje Tamamlama (kapanış + öğretici geri bildirim + KVKK 3-ay imha).

Ürün vaadi tek cümle: **"Çalışıp çalışmayacağı belirsiz iddialar yerine, ölçülmüş skorlarla literatürü gezdiren ve danışmana hazır gönderen platform."** Rakipler (SciSpace, Consensus, Elicit, Scite, ResearchRabbit, Connected Papers) tek bir parçada güçlü; PaperMind bunları proje bağlamında birleştirip ESTRA + boşluk matrisi + faithfulness gate + 3-persona simülasyonlarla farklılaşır.

### A.2 Nasıl yapacak?

Üç ayağı var.

**Veri ayağı.** ~25M makaleden oluşan kendi havuz (warehouse v4, `final/` tablolar). Pinecone'da embedding, Supabase'de metadata + ESTRA + bibliyometrik fact tabloları. Ayrıca ghost katmanı (`dim_ghost_paper`) — corpus'a atıf yapan ama içeride olmayan makaleler. Vitrin sadece OpenAlex Polite Pool kullanır, corpus'a değmez. Atölye 2.1'den itibaren tamamen kendi havuza dayanır.

**Hesap ayağı.** Çekirdek motor 5 katmanlı: Listener (Qwen 2.5 anlama) → Anchor (PMID/HyDE çapa) → PoolRouter (semantic + lexical RRF) → Reranker (BGE-v2-m3) → Curator (faithfulness gate + dil-spesifik sunum). Üstüne LLM kuşağı: Gemini 2.5 Flash hızlı işler için (özet, çeviri, mikro-yorum), Gemini 2.5 Pro derin işler için (sentez, hakem persona, jüri persona). Orta katmanda Cohere rerank-3 (jüri simülasyonu için), bge-m3 embedding (cevap-skoru), ElevenLabs TTS (literatür özeti dinletisi).

**Sunum ayağı.** Next.js 16 + React 19 + Tailwind 4 frontend, FastAPI backend, Supabase Auth (magic link). Sayfa-bazlı kart kanonu D5-D6 mock'undan: Standart Yayın Kartı her yerde aynı 4 buton (Danışmana sor / Detay / Listeme ekle / Çevir ve özetle), Açık + Daraltılmış 2 versiyon. Sidebar'da S1 Araştırma Defteri kullanıcının her sayfa eylemini zaman çizelgesinde tutar. KVKK uyumu: 3 ay sonra otomatik silme (kullanıcı önceden silebilir).

### A.3 Ne bekleniyor (kabul kriterleri)

| Boyut | Hedef | Ölçüm |
|---|---|---|
| **MVP scope** | 1 ay, 5-pilot kullanıcı | F7 P074 NPS ≥ +30 |
| **Vitrin → Proje funnel** | Q sayfasında %40 conversion | Pilot ölçüm |
| **Çapa kabul oranı** | İlk turda 3 adaydan 1 seçim ≥ %60 | rejected_anchors loglarından |
| **Sentez faithfulness** | < %1 atıfsız iddia (Pydantic kapısı + retry) | `q.py:198-277` cite-verify |
| **Cevap gecikmesi (warm)** | Vitrin /api/q < 2.5 sn (P95) | Sentry latency |
| **Cold start (HF Endpoint)** | < 30 sn (Scale-to-zero 15 dk) | Endpoint metrik |
| **Tier kotası** | Anon 3/gün · authed 5/gün (Q), 10/gün (LR), 5/gün (TTS) | `tier_gate.py:56-65` |
| **KVKK retention** | 3 ay sonra otomatik imha | Cron `retention_cleanup_snapshot` (planlı) |

---

## B. MİMARİ ÖZETİ — Tek Sayfa Diyagram

```
                                                    ┌────────────────────────────┐
                                                    │   KULLANICI (TR/EN/ID)     │
                                                    └──────────────┬─────────────┘
                                                                   │
                                                  Magic Link  ┌────┴────┐  Anon
                                          (Supabase Auth)     │ /landing│  veya
                                                              └────┬────┘  Authed
                                                                   │
┌──────────────────────────────────────────────────────────────────┴───────────────────────────────────┐
│ FRONTEND  ·  Next.js 16.2  +  React 19  +  Tailwind v4  +  Zustand  +  TanStack Query  +  shadcn/ui   │
│ ──────────────────────────────────────────────────────────────────────────────────────────────────── │
│  Vitrin  ──── Atölye Kabuğu (AppShell + Sidebar 240px + Topbar Cmd+J) ──── Yan Paneller (S1, S2)     │
│   /q     ──── /project/[id]/[[...slug]]  (27 alt-sayfa, dinamik route)   ──── /reading-list, /chat   │
│   /demo  ──── ChatboxPanel (Floating Pen + AdvisorBanner)                ──── /onboarding, /search   │
│                                                                                                       │
│  Standart Yayın Kartı (kanon, D5-D6)  ·  ESTRA bar  ·  DataProvenance pill  ·  SimulationCurtain    │
└──────────────────────────────────────┬────────────────────────────────────────────────────────────────┘
                                       │  HTTPS  ·  Bearer JWT (ES256)  ·  Pydantic forbid extra
┌──────────────────────────────────────┴────────────────────────────────────────────────────────────────┐
│ BACKEND API  ·  FastAPI 0.136  +  uv 0.11  +  Python 3.12  +  Pydantic v2  +  asyncio              │
│ ──────────────────────────────────────────────────────────────────────────────────────────────────── │
│                                                                                                       │
│  api/middleware/                       api/routes/  (22 dosya)                                        │
│   - auth (JWT)                          - q.py, search.py, top5.py             (vitrin + arama)       │
│   - rate_limit (sliding 60/dk)          - project.py, research_area.py         (proje + çapa)         │
│   - sentry (KVKK PII scrub)             - chat.py, summarize.py, enrich.py     (sohbet + özet)        │
│   - tier_gate (Redis INCR)              - bibliometrics, gap_heatmap, gap_profile, connected_papers  │
│                                         - paper_detail, dim, onboarding, waitlist, tts               │
│                                         - workshop.py, diary.py                (atölye + ajanda)      │
│                                         - notes, reading_list                  (yardımcı)             │
│                                                                                                       │
│  api/services/         5-katman ABC + concrete                                                        │
│   - listener_qwen  →  anchor_finder  →  pool_router  →  reranker_bge  →  curator + faithfulness_gate │
│   - openalex_polite, librarian, cluster_expander, llm_service (LiteLLM router)                       │
│                                                                                                       │
│  api/models/   Pydantic v2 forbid-extra, structured output schemas                                    │
└─────┬─────────────────┬────────────────┬──────────────────┬──────────────────┬──────────────────────┘
      │                 │                │                  │                  │
┌─────┴────┐    ┌───────┴────────┐  ┌────┴────────┐   ┌─────┴──────┐    ┌──────┴──────┐
│ Supabase │    │   Pinecone     │  │   Redis     │   │  Storage   │    │   Sentry    │
│ Postgres │    │ Embeddings     │  │  Cache +    │   │ (Supabase) │    │  (errors +  │
│  +RLS    │    │ B-012 metadata │  │ rate-limit  │   │  signed    │    │  breadcrumb │
│          │    │  HARD filter   │  │ Q:1h        │   │  URL       │    │  PII scrub) │
│ 25M warehouse│ │  q_weak/method/│ │ SUM:24h     │   │  weekly    │    │             │
│ + RLS owner  │ │  lang/year     │ │ ENRICH:7d   │   │  refresh   │    │             │
│ scoped       │ └────────────────┘  └─────────────┘   └────────────┘    └─────────────┘
└────────────────┘
      ↑
      │
┌─────┴──────────────────────────────────────────────────────────────────────────────────┐
│ DIŞ SERVİSLER  ·  Gemini 2.5 Flash + 2.5 Pro · OpenAlex Polite · ElevenLabs · Cohere   │
│ rerank-3 · HF Inference Endpoint (Qwen2.5-7B AWQ, T4, $0.50/h, scale-to-zero 15 dk)    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## C. YATAY MİMARİ KATMANLAR

### C.1 Frontend (Next.js 16)

**Stack.** Next.js 16.2.4 (Turbopack), React 19, Tailwind v4 (`@theme` token sistemi), Zustand 5 (state), TanStack Query 5 (server state), shadcn/ui (community tier-1 atomlar override edilmiş 8-anatomi token set), Vitest (105 test passing), Lucide icon, Lora + Inter font çifti.

**Dizin yapısı.**

```
web/src/
  app/                       Next.js App Router
    (app)/                   AppShell wrapped routes
      q/page.tsx             Vitrin (939 satır)
      project/[id]/[[...slug]]/page.tsx   27 alt-sayfa dinamik
      chat/page.tsx          Tam sayfa danışman sohbeti (60 satır, ChatThread reuse)
      reading-list/page.tsx  Kütüphanem
      search/page.tsx        Makale arama (501 fixture fallback)
      onboarding/page.tsx
    landing/page.tsx         Public landing
    demo/page.tsx            Pilot demo path
  components/
    project/                 Atölye sayfa komponentleri (40+)
    layout/                  AppShell, Sidebar, Topbar, ChatboxPanel
    ui/                      Button, Card, Badge, Dialog, Sheet ... (shadcn override)
  hooks/                     useQ, useLitReview, useDiary, useTierMock, useSpeechInput
  stores/                    Zustand atomik selector pattern (HK-4 invariant)
  lib/                       api.ts (apiFetchOrFixture), auth.ts, fixtures, tokens
```

**Standart Yayın Kartı (kanon).** D5-D6-Cards.html mock. Her makale gösteriminde aynı yapı:
- Chip satırı (alan / dil / decision_band)
- Lora italik 17px başlık + Inter meta (yazar · yer · yıl · atıf)
- 3-satır abstract clamp
- ESTRA q_weak yatay bar
- 4 standart buton: **Danışmana sor · Detay · Listeme ekle · Çevir ve özetle**
- 2 versiyon: **Açık** (full, abstract+ESTRA görünür, az sayıda öneride) ve **Daraltılmış** (lite, başlık+meta, çok sayıda listede)

**Tema.** Cool-academic palette (Slate 50/100/200/300 bg + Slate 900 ink + Amber 700 accent, WCAG AAA verified). 8-anatomi token sistemi: typography (Lora display + Inter body) · palette · radius (6/10/14) · 2-katman shadow · spacing scale · transition cubic-bezier(0.16,1,0.3,1) · mikro-imza (manuscript underline) · component override (default shadcn yasak). Dark mode post-MVP.

**Mevcut sayfa-komponent eşlemesi (Excel + grep doğrulandı).**

| Sayfa | Komponent | Var/Yok |
|---|---|---|
| 1 Vitrin | `web/src/app/(app)/q/page.tsx` (939 satır) + `JourneyProgressCard.tsx` | VAR |
| 2.1 Araştırma Alanı | `ResearchAreaConfirmPage.tsx` + `SessionPage.tsx` | VAR |
| 2.2 Konu Belirleme | `TopicSuggestionPage.tsx` | VAR |
| 2.3 Bibliyometrik | `BibliometricSummaryPage.tsx` + `BibliometricSummaryPageSkeleton.tsx` | VAR |
| 2.4 Tematik | `ThematicAnalysisPage.tsx` | VAR |
| 2.5 Kavram Ağı | `ConceptNetworkPage.tsx` + `NetworkMapCard.tsx` | VAR |
| 3.1 Önerilen Literatür | `ConnectedPapersPage.tsx` + `ExtendedSummaryPage.tsx` + `DataProvenance.tsx` + `DataVizCard.tsx` | VAR (isim eşleşmesi review) |
| 3.2 İlişkili Çalışmalar | `MethodDataEthicsPage.tsx` | VAR (scope farklı, refactor adayı) |
| 3.3 Yöntem Matrisi | — | YOK (eşleşme net değil) |
| 3.4 Literatür Sentezi | `LiteratureSummaryPage.tsx` | VAR |
| 4.1 Boşluk Haritası | `GapHeatmapCard.tsx` | VAR (UI ayrı sayfa mı kart mı, review) |
| 4.2 Boşluk Profili | `GapProfilePage.tsx` | VAR |
| 4.3 Özgünlük | `DisruptionBeautyPage.tsx` | VAR |
| 4.4 Karşılaştırma | `GapComparisonPage.tsx` | VAR |
| 4.5 Akademik Etki | `SocialPulsePage.tsx` | VAR |
| 5.1 Yayın Formatı | `PublicationTypePage.tsx` + `ReferenceStylePage.tsx` | VAR |
| 5.2 Yayın Taslağı | `WritingSkeletonPage.tsx` | VAR |
| 5.3 Akademik Dil | `AcademicLanguagePage.tsx` | VAR |
| 5.4 Atıf Kılavuzu | `CitationQualityPage.tsx` | VAR |
| 6.1 İçerik Doldurma | `ThesisContentPage.tsx` | VAR |
| 6.2 Savunma Formatı | `DefenseFormatPage.tsx` | VAR |
| 6.3 Bireysel Kontrol | `IndividualFeedbackPage.tsx` | VAR |
| 6.4 Dergi Simülasyonu | `ReferenceIntegrityPage.tsx` | VAR (scope çok farklı, refactor zorunlu) |
| 6.5 Jüri Simülasyonu | `JurySimulationPage.tsx` | VAR |
| S1 Araştırma Defteri | `DiarySidebar.tsx` + `DiaryActions.tsx` + `useDiary.ts` + `NotebookPage.tsx` | VAR (sidebar tab vs sayfa-bazlı çatışması review) |
| S2 Proje Tamamlama | `ProjectClosurePage.tsx` | VAR |

**Boşluk:** 3.3 Yöntem Matrisi için ayrı UI komponenti yok (heatmap muhtemelen `GapHeatmapCard` paterninin türevi olabilir). 6.4 Dergi Simülasyonu için `ReferenceIntegrityPage.tsx` adıyla mevcut komponent var ama scope tamamen farklı (atıf bütünlüğü vs hakem simülasyonu); rename + refactor şart.

### C.2 Backend API (FastAPI)

**Stack.** FastAPI 0.136, Python 3.12.13, uv 0.11.8, Pydantic v2 (forbid-extra her endpoint), asyncio, ruff + mypy --strict, pytest (231 PASS son ölçüm).

**Endpoint envanteri (api/routes/ doğrulanmış).**

```
api/routes/
  q.py                     POST /api/q · /api/q/literature-review · /api/q2 (kilitli, V1+)
  search.py                POST /api/search
  top5.py                  POST /api/top5
  project.py               POST /api/project · GET /api/project · GET /api/project/{id}
                           POST /api/project/from-q (vitrin → atölye köprü, scope düzeltilecek)
  research_area.py         POST /api/project/{id}/research-area/messages
                           POST /api/project/{id}/research-area/anchor-candidates
                           (research-area/reset YOK; F9 plan'da)
  chat.py                  POST /api/chat (genel danışman, SSE Cosmos KD-18 plan'da)
  summarize.py             POST /api/summarize · GET /api/summarize/{id} (async)
  enrich.py                POST /api/enrich (OpenAlex zenginleştirme)
  project_bibliometrics.py POST /api/project/{id}/bibliometrics
  gap_heatmap.py           GET /api/gap-heatmap (fact_gap_matrix sorgu)
  gap_profile.py           GET /api/gap-profile/{...} (imza yenilenecek)
  connected_papers.py      GET /api/connected-papers/{paper_id} (bibcoupling top-50)
  paper_detail.py          GET /api/paper/{paper_id} · /export
  dim.py                   GET /api/fields · /api/subfields
  onboarding.py            POST /api/onboarding (V1 profil tamamlama, KVKK SHA-256)
  waitlist.py              POST /api/waitlist
  tts.py                   POST /api/tts/literature-review (ElevenLabs proxy)
  workshop.py              GET /api/workshop/maturity
                           PUT /api/workshop/manuscript/{section_type}
                           POST /api/workshop/manuscript/auto-draft
                           POST /api/workshop/paraphrase · /paraphrase-decision
                           GET /api/workshop/citation-search
                           POST /api/workshop/citation-verify · /citation-balance
                           GET /api/workshop/format-citation
  diary.py                 POST /api/diary/event · GET /api/diary/timeline
                           PATCH /api/diary/event/{id} · POST /api/diary/pre-advisor-summary
  notes.py                 GET/POST/PATCH/DELETE /api/notes
  reading_list.py          GET/POST/PATCH/DELETE /api/reading-list
```

**Middleware zinciri (api/middleware/).**

1. **Auth (Bearer JWT ES256)** — Supabase Auth, dev mode JWKS endpoint, `request.state.user_id`
2. **RateLimit (sliding window 60/dk)** — IP + user composite, Redis tabanlı
3. **Sentry init (KVKK PII scrub 5 regex)** — email, telefon, TC, IP, JWT redact
4. **TierGate (Redis INCR, günlük UTC reset)** — Anon vs authed kotalar (3 tier aynı kotada, ödeme tier V2)

**Pydantic kontratları.** Her request/response model `model_config = ConfigDict(extra="forbid")`. Structured output Gemini çağrılarında jsonschema validate, faithfulness_gate `paper_ids ⊆ corpus_paper_ids` kontrolü, sycophant kilidi (DM-049).

**Boşluk.** Atölye derinlik endpoint'lerinin önemli kısmı henüz yok: `synthesize`, `topic-proposals`, `draft-skeleton`, `defense/reviewer-3persona`, `defense/jury-question`, `defense/hyde-fanout-rerank`, `defense/answer-score`, `defense/consistency-check`, `defense/jury-decision-band`, `defense/statcheck`, `defense/journal-calibration`, `workshop/journal-suggest`, `workshop/manuscript/coherence-check`, `workshop/personal-feedback`, `workshop/originality`, `workshop/compare`, `workshop/impact-curve`, `completion/snapshot`, `feedback/project-completion`. Bölüm F'de tek liste.

### C.3 Çekirdek Motor — 5-Katman

Tüm arama / çapa / sentez işlerinin altındaki standart hat. SOLID; her katman ABC + concrete.

```
                 ┌──────────────────────────────────────────┐
   Kullanıcı     │  1. Listener  (Qwen 2.5 7B AWQ via HF)   │
   sorgusu  ──── │     - dil tespit (TR/EN/ID)              │
                 │     - parsed_query + multi_query üret    │
                 │     - LiteLLM router 3-dil               │
                 └────────────────────┬─────────────────────┘
                                      │ parsed_query, multi_query[]
                 ┌────────────────────┴─────────────────────┐
                 │  2. AnchorFinder                         │
                 │     - Stage A: Kütüphaneci sohbet (Flash)│
                 │     - Stage B: HyDE → Pinecone (sem 80)  │
                 │                + Supabase tsvector (lex 80)│
                 │                → RRF k=60 → BGE rerank 3 │
                 │     - Stage C: cluster_expander (500)    │
                 │       + ESTRA scorer + curator (bg job)  │
                 │     - rejected_anchors hafıza (project_anchor)│
                 └────────────────────┬─────────────────────┘
                                      │ anchor_paper_id, project_pool[500]
                 ┌────────────────────┴─────────────────────┐
                 │  3. PoolRouter (Hybrid)                  │
                 │     - semantic (Pinecone B-012 metadata)  │
                 │     - lexical (Supabase tsvector)         │
                 │     - theme (dim_theme_embedding)         │
                 │     - RRF fusion + HARD filter            │
                 │       (q_weak / method / lang / year)     │
                 └────────────────────┬─────────────────────┘
                                      │ candidate[]
                 ┌────────────────────┴─────────────────────┐
                 │  4. Reranker (BGE-reranker-v2-m3)        │
                 │     - lazy load (transformers + torch)    │
                 │     - CPU/MPS singleton (~700MB cold)     │
                 │     - degraded uniform 0.5 fallback       │
                 └────────────────────┬─────────────────────┘
                                      │ ranked[]
                 ┌────────────────────┴─────────────────────┐
                 │  5. Curator + FaithfulnessGate           │
                 │     - signals_13 (5 evidence + 8 placeholder)│
                 │     - decision_band (Accept/Minor/Major/Reject)│
                 │     - LVR (Linked Verification Rate) gate │
                 │     - jsonschema 100% Pydantic forbid     │
                 │     - DM-049 sycophant kilidi             │
                 │     - Presenter dil-spesifik (LiteLLM)    │
                 └────────────────────┬─────────────────────┘
                                      │ structured response
                                   Frontend
```

**Konum kanıtı.**
- `api/services/listener_qwen.py` · concrete async, HF httpx pool, cold-start retry 502/503/504/524
- `api/services/anchor_finder.py` · Stage B PASS (R13.13 kanıt), Stage C cluster_expander pending
- `api/services/pool_router.py` · `_QueryEncoder` Pinecone B-012, lexical_tsvector_pool, RRF k=60
- `api/services/reranker_bge.py` · lru_cache singleton, lazy import
- `api/services/curator.py` + `api/services/faithfulness_gate.py` · ortak servis (B-010), level=SEARCH 2-kat aktif

**Boşluk:** P096 (Stage C background job) henüz brief'te, ESTRA scorer + cluster_expander concrete kod beklenir.

### C.4 Veri Katmanı

#### C.4.1 Supabase Postgres (warehouse + uygulama)

**Migration sıralaması (db/migrations/ doğrulanmış).**

```
0001_init_schema_v1.sql              papers, dim_field, dim_subfield, ENUM, pg_trgm, dim_ghost_paper
0002_static_facts.sql                fact_paper_id_card + fact_gap_matrix
0003_paper_anchor_facts.sql          PMID anchor verileri
0004_paper_satellite_facts.sql       sentence_role + d_estra + ref_age
0005_paper_estra_temporal.sql        ESTRA: q_v3 + w_estra + velocity + **disruption (cd_5)** + **beauty (B)**
0006_paper_metadata.sql              papers metadata genişletme
0007_method_centrality.sql           fact_method_topic_affinity + fact_method_field_affinity + paper_centrality
0008_neighbor_bibcoupling.sql        fact_paper_bibcoupling_top50
0011_create_dim_field.sql            dim_field referans
0012_user_profile_fields_and_tier_refactor.sql
                                     ENUM tier (ogrenci/arastirmaci/profesyonel)
0013_create_dim_subfield.sql
0014_user_profile_subfields_bridge.sql
0015_projects_skeleton.sql           projects + project_chat_messages
                                     + project_anchor (RLS owner-only)
0016_project_cluster.sql             materialize cluster (CASCADE delete)
0017_waitlist_table.sql              Vitrin erken erişim formu
0019_project_seed_papers.sql         (vitrin seed; KARAR 2026-05-10 sonrası ölü olabilir)
0020_defense_jury_simulation.sql     5 persona seed + jury_question havuzu (F12, commit d577e5b)
0021_concept_term_arm.sql            concept_node + concept_edge (NPMI)
0025_project_progress.sql            State machine (5.1 Maturity, F13-S2 commit be32bbb)
0026_silent_learning.sql             user_silent_learning_log + user_style_profile (F13-S3 commit 2979d87)
0027_manuscript_section.sql          5 IMRaD bölüm kaydı (6.1, F13-S5)
0028_defense_session.sql             Jüri + soru havuzu + sonuçlar (6.2, F13-S6)
0029_project_event.sql               S1 Araştırma Defteri timeline (F13-S1 commit 5e28563)
0031_defense_session_individual_check.sql   defense_session.individual_check JSONB (6.3, F13-S8)
0032_defense_session_scan_results.sql       defense_session.scan_results JSONB (6.4, F13-S9)
```

**Plan / V2 migration listesi (henüz uygulanmamış, kalan):**

```
0010_paper_flags_temporal.sql        abstract_flags_v5 + temporal (24M+18M satır, 1-1.5GB)
0018 (rezerve)                       atölye tablosuna ayrılabilir
0022_extended_affinity.sql           3 türetilmiş affinity tablo (lift+transpose)
0023_gap_matrix_calibration.sql      fact_gap_matrix.matrix_confidence_calibrated
0030_completion.sql                  dim_project +3 kolon, dim_feedback, snapshot tablo (S2, F13-S14)
```

**JSONB politikası (DM kararı: küçük şemalı sürekli değişen veri JSONB tabloya bölünmez).**

```
project_anchor.candidates_meta            (rejected anchors hafızası)
user_profiles.metadata.gap_targets        (4.2 gap target listesi)
defense_session.individual_check          (6.3 makale/tez checklist)
defense_session.scan_results.reviewer_3persona  (6.4 hakem sonuçları)
defense_session.scan_results.statcheck    (6.4 p-value uyumsuzluk)
defense_session.scan_results.jury_session (6.5 jüri tepki+skor+decision band)
```

**Veri ambarı boyutu (Excel kanıt B + STATE.md).**

- Kendi havuz: ~25M makale (warehouse v4 final/ tablolar; N18 PASS)
- Supabase mirror (papers tablosu): bugün 0 satır (lazy fill, B-012 sonrası)
- `fact_paper_bibcoupling_top50`: parquet 643M satır
- `fact_gap_matrix`: 504,436 satır (canlı Supabase doğrulandı, 0002 migration)
- `fact_paper_disruption` (Funk-Owen CD-index): **canlı Supabase** (0005 migration, Dashboard kanıt — örnek satır W1000067951 / 2015 / n_a=1 / n_i=0 / n_j=579199 / cd_5)
- `fact_paper_beauty` (Sleeping Beauty B-coefficient): canlı Supabase (0005 migration)
- `fact_paper_velocity`: hesaplı (0005 migration)
- Plan V2 büyük tablolar (henüz uygulanmadı): `fact_paper_disrupted_refs` ~750M (CD raw refs), `fact_paper_yearly_citations` ~250-375M, `fact_gap_matrix_temporal` (1-2 hafta pipeline)

#### C.4.2 Pinecone

- Index: corpus 25M embedding
- B-012 metadata patch (Omer Colab in-flight): `q_weak / method / lang / year / D / F / S / v_conf` HARD filter
- Plan: Plan 1 `filter=None` tolere; Plan 2'de zorunlu

#### C.4.3 Redis

```
Cache namespaces:
  q:           1 saat   (vitrin OpenAlex sonuç)
  sum:         24 saat  (özetler)
  enrich:      7 gün    (enrichment)
  ghost:       7 gün vs 90 gün (DM-006 master vs L1; OPEN-006 açık)
  rate:        1 gün    (tier gate INCR)
```

#### C.4.4 Storage (Supabase Storage)

- Yükleme dosyaları (Word, PDF), defense audio, completion PDF report
- Cron `signed_url_refresh` her Pazartesi 02:00 (S2 plan)

### C.5 Dış Servisler

| Servis | Kullanım | Maliyet | Cold start |
|---|---|---|---|
| **Gemini 2.5 Flash** | Vitrin LR, mikro-yorum, librarian sohbet, hakem persona | düşük | yok |
| **Gemini 2.5 Pro** | 3.4 sentez, 5.2 topic+draft, 5.3 paraphrase, 6.2 jury question | orta | yok |
| **OpenAlex Polite Pool** | Vitrin /api/q, enrich, jury member paper listesi (6.2) | bedava | rate limit |
| **HF Inference Endpoint** | Qwen2.5-7B-Instruct-AWQ vLLM v0.18.1, T4 GPU eu-west-1 | $0.50/h | scale-to-zero 15 dk |
| **ElevenLabs** | TTS literature review dinleti (vitrin) | dakika ücretli | yok |
| **Cohere rerank-3** | 6.5 jüri HyDE-fanout-RRF rerank | düşük | yok |
| **bge-m3 embed** | 6.5 cevap embed → kanıt-kapsam skoru | self-hosted | lazy load |
| **Sentry** | Hata + breadcrumb (KVKK PII scrub) | ücretsiz tier yeterli | yok |
| **Supabase Auth** | Magic link (Sercan e-mail provider seçimi) | bedava | yok |
| **Pytrends** | 4.5 Google Trends 24h cache + rate limit | bedava | rate limit |

---

## D. DİKEY SAYFA MİMARİSİ — 27 Sayfa

Her sayfa için `[felsefe · nasıl · backend · frontend · veri · LLM · boşluk]` yapısı. Excel sheet'lerinden + RTF kanıtlardan damıtıldı.

### D.0 Genel Kurallar (orkestralama)

Tüm sayfalara hâkim 5 ilke (`Sayfa_Plani_v2/0_genel_kurallar.rtf`):

1. **Vitrin/Proje ikiliği** — Vitrin OpenAlex (her tür yayın), Proje BİZİM HAVUZ (kaliteli ~25M).
2. **Rakip kıyas** — her sayfada 3 soru: bizim güçlü olduğumuz, rakibin güçlü olduğu, fayda-maliyete kaçırdığımız.
3. **4 persona** — danışman / öğrenci / jüri / hakem her adımda sorulur.
4. **Sayfa disiplini** — kabarık olmasın, eğitici-doyurucu olsun.
5. **Veri ambarı envanteri** — sayfa-bazlı 3'lü eşleme: veri ambarı / backend / frontend; üçü hizalanmadan kapalı sayılmaz.

### D.1 Vitrin (1)

- **Felsefe.** Hesapsız kullanıcı için vanilla literatür özeti. ESTRA / validator / ghost / persona / kavram ağı imzaları burada gösterilmez. Vitrin bir vaattir, kanıt değil; "Projeye Dönüştür" CTA'sının değerini büyütür.
- **Nasıl.** Kullanıcı sorgusu Gemini Flash ile İngilizce'ye çevrilir; OpenAlex Polite Pool çift dil paralel sorgu; 25 makale dedup + cited_by_count desc. Seçilen makalelerden Flash sentez. Atölyeye sadece `{alan, alt-alan, konu}` taşınır (2026-05-10 KARAR, Omer).
- **Backend.** `api/routes/q.py` 295 satır, 3 endpoint, `_Q_LIMIT=25`, `_ANON_PAPER_LIMIT=3`. TierGate Redis. `api/services/openalex_polite.py` retry envelope.
- **Frontend.** `web/src/app/(app)/q/page.tsx` 939 satır, `useQ` + `useLitReview` hooks, `JourneyProgressCard`, `useTierMock` localStorage.
- **Veri.** Bizim corpus DEĞİL; sadece OpenAlex. `0017_waitlist_table` dolu erken erişim formu için.
- **LLM.** Flash × 1 (~5K in / 1K out). ElevenLabs TTS opsiyonel.
- **Boşluk.** (a) `convertToProject()` hâlâ `paper_id` listesi gönderiyor; KARAR sonrası `{field, subfield, topic, lang}` payload'a refactor şart. (b) Vitrin sentezinden field/subfield/topic çıkarımı LLM mi parse mı manuel mi - karar bekliyor. (c) `0019_project_seed_papers` migration ölü mü (silinsin mi) - DM kararı.

### D.2 Atölye Keşif (2.1 – 2.5)

#### D.2.1 Araştırma Alanı — Çapa Belirleme

- **Felsefe.** Projenin DNA'sı. Çapa = proje boyunca tüm modülleri hizalayan akademik referans noktası. Stage A 2-tur Kütüphaneci sohbet, Stage B HyDE → 3 çapa adayı, Stage C 500 komşu + ESTRA + curator.
- **Nasıl.** Vitrin'den `{alan, alt-alan, konu}` Stage A girdisi; Flash librarian. Stage B: HyDE → Pinecone(80) + Supabase tsvector(80) → RRF k=60 → BGE rerank → top-3. Çapa seçimi → Stage C arka planda.
- **Backend.** `api/routes/research_area.py` 2 endpoint (messages + anchor-candidates). `api/services/anchor_finder.py` (P095 KAPANDI). `api/services/librarian.py` (P094 KAPANDI). `reset` endpoint YOK.
- **Frontend.** `ResearchAreaConfirmPage.tsx` + `SessionPage.tsx`.
- **Veri.** `project_chat_messages` + `project_anchor` (0015). `project_anchor.candidates_meta` JSONB persist EKSİK.
- **LLM.** Flash 5-8 çağrı (~3K/çağrı), Pro 1.
- **3 dokunuş önerisi (RTF).** "Anladığım kadarıyla" kartı (parsed_understanding geri yansıma) · "Niye bu paper?" mikro-açıklama (3 paralel Flash batch ~600ms) · Reset hafıza wire-up (`reset` endpoint + rejected_anchors append).
- **Boşluk.** `reset` endpoint, `candidates_meta` persist, P096 background job.

#### D.2.2 Konu Belirleme

- **Felsefe.** Çapa makro, konu mikro. 1-2 ek çapa seçimine izin; ısrar etmezse 500 yayın varsayılan kütüphane olarak kilitleniyor.
- **Nasıl.** Stage C çıktısı (cluster_expander) + ESTRA + ilk 25 kart. Kullanıcı 1-2 ek çapa seçerse cluster yenilenir; yoksa 500 yayın `project_pool` tablosuna kalıcı.
- **Backend.** Endpoint listelenmemiş (RTF'de geçmiyor); muhtemelen `project_bibliometrics` veya yeni bir `project/{id}/topic/finalize` gerekecek.
- **Frontend.** `TopicSuggestionPage.tsx`.
- **LLM.** Flash sadece kart özetlerinde (lazy).
- **Boşluk.** Endpoint adı + kontratı net değil; planlanacak.

#### D.2.3 Bibliyometrik Analiz

- **Felsefe.** Sayısal kanıtla "alan nerede, kim baskın, nereye gidiyor?" PaperMind'ın asıl yetkin olduğu alan. ★ CD-index, ◆ Sleeping Beauty rozetler ön-hesaplı.
- **Nasıl.** Saf SQL aggregation; LLM yok. `fact_paper_id_card + dim_author + dim_journal + fact_paper_velocity` JOIN. Bar chart, histogram, badge.
- **Backend.** `POST /api/project/{id}/bibliometrics` (`project_bibliometrics.py:63`).
- **Frontend.** `BibliometricSummaryPage.tsx` + `BibliometricSummaryPageSkeleton.tsx` (V1-S13 polish KAPANDI).
- **LLM.** Yok (anlık, 200ms hedef).
- **Boşluk.** Yok (tamamlanmaya en yakın atölye sayfası).

#### D.2.4 Tematik Analiz

- **Felsefe.** Ham UMAP+HDBSCAN değil, "senin çapan şu temada burada konumlanıyor". 3 dominant tema sabit.
- **Nasıl.** `dim_theme_embedding` cosine eşleşme + project_pool ağırlık. Radar/scatter ile çapa-içi konum.
- **Backend.** Endpoint listelenmemiş (eklenecek).
- **Frontend.** `ThematicAnalysisPage.tsx`.
- **LLM.** Yok.
- **Boşluk.** Endpoint kontratı.

#### D.2.5 Kavram Ağı

- **Felsefe.** Concept-concept (Connected Papers paper-paper'dan farklı). NPMI eş-anma + betweenness centrality. KeyBERT + 11-kategori ontoloji (FLD/CON/THR/MTD/...).
- **Nasıl.** `concept_node` + `concept_edge` (0021 migration) önceden hesaplı. D3 force-graph.
- **Backend.** Endpoint listelenmemiş.
- **Frontend.** `ConceptNetworkPage.tsx` + `NetworkMapCard.tsx`.
- **LLM.** Yok.
- **Boşluk.** Endpoint, "kavram tıklayınca paper listesi" etkileşim katmanı.

### D.3 Literatür (3.1 – 3.4)

#### D.3.1 Önerilen Literatür

- **Felsefe.** Okuma alanı, karar alanı değil. Çapa kararı 2.1-2.2'de verildi; burada sıralı 25/50/100 gösterim. ESTRA q_weak descending.
- **Backend.** `connected_papers.py:77`, `paper_detail.py:56,109`, `enrich.py:56`.
- **Frontend.** `ConnectedPapersPage.tsx` + `ExtendedSummaryPage.tsx` + `DataProvenance` + `DataVizCard`.
- **LLM.** Sadece kullanıcı isteğinde (özet/çeviri).
- **Boşluk.** Komponent adı 3.1 ile uyumsuz (Connected Papers 3.2'ye ait); rename adayı.

#### D.3.2 İlişkili Çalışmalar (Connected Papers + Ghost)

- **Felsefe.** Connected Papers dengi + bizim corpus'a atıf yapan dış (ghost) makaleler. Rakipte yok.
- **Nasıl.** `fact_paper_bibcoupling_top50` (643M parquet) project_pool top-50 komşu. D3 force-graph.
- **Backend.** Endpoint listelenmemiş.
- **Frontend.** `MethodDataEthicsPage.tsx` (scope farklı, refactor adayı).
- **Veri.** V2 `dim_ghost_paper` aktif olunca tam görünüm.
- **Boşluk.** Endpoint + komponent rename + ghost katmanı.

#### D.3.3 Yöntem Matrisi

- **Felsefe.** 7-tag çapraz matris (Metod × Konu/Kavram/Alan). Elicit %20 metod gösteriyor; matris yok.
- **Nasıl.** `fact_paper_metod` heatmap. Dropdown X/Y eksen.
- **Backend.** Endpoint listelenmemiş.
- **Frontend.** Eşleşme net değil.
- **Boşluk.** `0022_extended_affinity` migration plan; UI komponenti (`MethodMatrixPage.tsx` adıyla yeni eklenecek).

#### D.3.4 Literatür Sentezi

- **Felsefe.** Atölye sentezi (vitrin Q1'in derin versiyonu). 25 paper, kullanıcı dilinde, ≥1 paper/cümle, faithfulness rozet.
- **Backend.** `POST /api/workshop/synthesize` **MEVCUT** (F13-S11-P001, commit fed7de9). `/api/summarize` ayrı (async paper özet, farklı amaç).
- **Frontend.** `LiteratureSummaryPage.tsx`.
- **LLM.** Pro 1 (~10K in / 2K out).
- **Boşluk.** Yok (endpoint canlı). UI bağlama review.

### D.4 Boşluk (4.1 – 4.5)

#### D.4.1 Boşluk Haritası

- **Felsefe.** M1-M8 boşluk formülü (0.25D + 0.20K + 0.20E + 0.15F + 0.20Y). Üç heatmap (Metod×Kavram, Konu×Kavram, Metod×Konu). Rakipte yok.
- **Backend.** `GET /api/gap-heatmap` (`gap_heatmap.py:181`) — 504,436 satır canlı.
- **Frontend.** `GapHeatmapCard.tsx`.
- **Boşluk.** `0023_gap_matrix_calibration` (matrix_confidence_calibrated). V2: `fact_gap_matrix_temporal`.

#### D.4.2 Boşluk Profili

- **Felsefe.** Bir gap hücresine zoom — son 5 yıl trendi, komşuluk, ESTRA, **yorumlanabilir dil**.
- **Backend.** `GET /api/workshop/gap/{matrix_id}/{axis_x}/{axis_y}` YOK; mevcut `/api/gap-profile` imzası farklı.
- **Frontend.** `GapProfilePage.tsx`.
- **LLM.** Flash 1 (~3K in / 500 out).
- **Veri (KARAR).** `0024_user_gap_targets` migration REDDEDİLDİ; `user_profiles.metadata.gap_targets` JSONB tercih.
- **Boşluk.** Endpoint imza fix + JSONB persist wire.

#### D.4.3 Özgünlük Değerlendirmesi

- **Felsefe.** ★ Funk-Owen CD-index + ◆ Sleeping Beauty B-coefficient. Subjektif değil ölçülebilir.
- **Backend.** `GET /api/workshop/originality` YOK.
- **Frontend.** `DisruptionBeautyPage.tsx`.
- **LLM.** Lazy Flash kart başına (~1K in / 100 out).
- **Veri.** V2 büyük tablolar `fact_paper_disrupted_refs` (~750M) + `fact_paper_yearly_citations` (~250-375M).
- **Boşluk.** Endpoint + V2 tablolar pipeline.

#### D.4.4 Çalışma Karşılaştırma

- **Felsefe.** 5 eksen (Risk · Yıkıcılık · Bakir alan · Sleeping Beauty · Yayınlanabilirlik) yan yana.
- **Backend.** `POST /api/workshop/compare` YOK.
- **Frontend.** `GapComparisonPage.tsx`.
- **LLM.** Flash N+1 (~2K in / 200 out).

#### D.4.5 Akademik Etki Eğrisi

- **Felsefe.** Akademik + popüler trend çift mercek. ★/◆ rozetlerin ana görüntüleme yeri.
- **Backend.** `GET /api/workshop/impact-curve` YOK.
- **Frontend.** `SocialPulsePage.tsx`.
- **Dış.** Pytrends 24h cache.
- **Boşluk.** Endpoint + summary_cache (Redis 24h TTL).

### D.5 Yazım (5.1 – 5.4)

#### D.5.1 Yayın Formatı (Maturity Gate)

- **Felsefe.** "Danışmana Gitmeden Evvel" kapısı. Önceki adım çıktıları checklist; tümü ✓ olunca akademik özet üretilir.
- **Backend.** `GET /api/workshop/maturity` VAR (workshop.py içinde). `POST /api/workshop/advisor-summary` YOK.
- **Frontend.** `PublicationTypePage.tsx` + `ReferenceStylePage.tsx`.
- **Veri.** `0025_project_progress` (state machine, MEVCUT).
- **LLM.** Pro 1 (4-5 paragraf, PDF/MD export).
- **Boşluk.** `advisor-summary` endpoint.

#### D.5.2 Yayın Taslağı

- **Felsefe.** 3 konu kartı (3-mod RQ stilleri: temkinli/dengeli/iddialı). LLM halüsinasyonu değil; gap+metod+sentez üstünden hesap.
- **Backend.** `topic-proposals` + `draft-skeleton` YOK.
- **Frontend.** `WritingSkeletonPage.tsx`.
- **LLM.** Pro 2 (~5K in / 2K out).

#### D.5.3 Akademik Dil & Üslup

- **Felsefe.** TR/EN/ID dilbilgisi farkları. Sessiz öğrenme: `user_silent_learning_log` 30-gün → `user_style_profile`.
- **Backend.** `POST /api/workshop/paraphrase` + `paraphrase-decision` VAR (workshop.py içinde — son sprint'te eklendi).
- **Frontend.** `AcademicLanguagePage.tsx`.
- **Veri.** `0026_silent_learning` MEVCUT.
- **Engine.** `engine/style/{tr,en,id}.json` PLAN.
- **Cron.** `user_style_profile_update` her gece 02:00.
- **LLM.** Pro 1/cümle (~500 in / 500 out).
- **Boşluk.** Engine style JSON dosyaları.

#### D.5.4 Atıf Stil Kılavuzu

- **Felsefe.** Hiçbir atıf icat edilemez (`paper_ids ⊆ corpus_paper_ids` kapısı). Eski/yeni atıf dengesi danışman gözüyle.
- **Backend.** `citation-search` + `citation-verify` + `format-citation` + `citation-balance` **MEVCUT** (F13-S4, commit 2555758).
- **Frontend.** `CitationQualityPage.tsx`.
- **Engine.** `engine/citation/{apa,vancouver,ieee,chicago,mla}.py` 5 stil **MEVCUT** (F13-S4 commit 2555758). `engine/dictionary/{tr,en,id}.json` PLAN.
- **LLM.** Flash 1-2 (~2K in / 500 out).
- **Boşluk.** 3 dil sözlük JSON dosyaları.

### D.6 Savunma (6.1 – 6.5)

#### D.6.1 Yayın İçeriği Doldurma

- **Felsefe.** Simülasyon içerik üzerinde çalışır; Emerald 5-bölüm (intro/methods/findings/discussion/conclusion). Min 3/5 dolu olmadan "Simülasyonu Başlat" pasif.
- **Backend.** `manuscript` GET/PUT/quality-check/auto-draft VAR (workshop.py).
- **Frontend.** `ThesisContentPage.tsx`.
- **Veri.** `0027_manuscript_section` PLAN.
- **LLM.** Flash + Pro 2 (~5K in / 1K out).
- **Boşluk.** `0027` migration apply.

#### D.6.2 Savunma Formatı

- **Felsefe.** Sahte simülasyon zayıf; jüri üyelerinin gerçek paper'larından soru havuzu. Stanford-style 2-derinlik zincir.
- **Backend.** `defense/generate-questions` + `defense/suggest-jury` YOK.
- **Frontend.** `DefenseFormatPage.tsx`.
- **Veri.** `0028_defense_session` PLAN.
- **LLM.** Pro N_jüri (~5K in / 2K out).

#### D.6.3 Bireysel Kontrol

- **Felsefe.** Statik yönlendirme + dinamik checklist hibrit. Makale dalında SJR + scope match top-5 dergi öneri.
- **Backend.** `journal-suggest` + `coherence-check` + `personal-feedback` YOK.
- **Frontend.** `IndividualFeedbackPage.tsx`.
- **Veri.** `defense_session.individual_check` JSONB **MEVCUT** (0031 migration, F13-S8).
- **Engine.** `engine/checklist/{makale,tez}_{tr,en}.json` PLAN.
- **LLM.** Flash 3 (~3K in / 500 out).

#### D.6.4 Dergi Simülasyonu

- **Felsefe.** 3-persona paralel hakem (Şüpheci / Sempatik / Yöntemci) + statcheck (Nuijten 2016 p-value tutarlılık) + dergi kalibrasyon (son 50 makale review distribution). Zincir derinlik hard-cap 2 (rakip 5+ derinlik = kullanıcı tükenir).
- **Backend.** `defense/reviewer-3persona` (workshop.py:580) + `defense/statcheck` (workshop.py:598) + `defense/journal-calibration` (workshop.py:613) **MEVCUT** (F13-S9 workshop.py konsolide, 2026-05-11 çalışıyor).
- **Frontend.** `ReferenceIntegrityPage.tsx` (scope çok farklı, RENAME + REFACTOR zorunlu).
- **Veri.** `defense_session.scan_results.{reviewer_3persona,statcheck}` JSONB **MEVCUT** (0032 migration, F13-S9).
- **Engine.** `engine/personas/journal/{skeptik,sempatik,yontemci}.json` + `engine/statcheck/multilingual.json` + `engine/journals/review_distribution.json` **MEVCUT** (disk'te VAR, 2026-05-11).
- **LLM.** Flash × 3 paralel (~5K in / 1K out).

#### D.6.5 Jüri Simülasyonu

- **Felsefe.** 4-5 jüri eş zamanlı, 60 sn timer, başkan destekleyici. **Bizim imza:** HyDE → fan-out → RRF → rerank zinciri arka planda canlı kanıt çeker; kullanıcı cevabı bge-m3 embed → multi-dim rubric kanıt-kapsam skoru → jüri tepkisi (satisfied/probing/dissatisfied) + depth-2 alt-soru. Tutarlılık taraması (LLM second-pass) çelişen cevap çiftleri.
- **Backend.** `defense/jury-question` (workshop.py:635, F12 B.1 commit 0cb0ada) + `defense/hyde-fanout-rerank` (workshop.py:653) + `defense/answer-score` (workshop.py:671) + `defense/consistency-check` (workshop.py:686) + `defense/jury-decision-band` (workshop.py:704) **HEPSİ MEVCUT** (workshop.py konsolide, 2026-05-11 çalışıyor).
- **Frontend.** `JurySimulationPage.tsx` (cinematic curtain D17 açılış; F12 commit 5b476f7 ile Page rewrite + thinking model + JSON prose-strip).
- **Veri.** `defense_session.scan_results.jury_session` JSONB (0032 migration). 5 persona seed **MEVCUT** (0020 migration, F12 commit d577e5b).
- **Engine.** `engine/personas/jury/{canli,anti_tez,yontemci,dis_disiplin,pratisyen}.json` + `engine/jury/reaction_thresholds.json` **MEVCUT** (disk'te VAR; pilot validation κ ≥ 0.7 hala kalibre edilecek).
- **LLM.** Flash × 7+ (~3K in / 500 out) + Cohere rerank-3 (HyDE fanout).
- **Boşluk.** Endpoint zinciri kapandı; kalan iş: reaction threshold pilot validation (Cohen κ ≥ 0.7 için 20+ kullanıcı oturumu) + cinematic curtain D17 frontend animasyon.

### D.7 Yan Paneller (S1, S2)

#### D.7.1 Araştırma Defteri (sidebar tab)

- **Felsefe.** PaperMind doğrusal değil iteratif; her sayfa eylemi (Ajandama Kaydet / Danışmana Sor / Kütüphaneme Ekle) timeline'a yazılır. 3 hafta önce işaretlediği açık event "hâlâ açık" hatırlatması.
- **Backend.** `diary/event` + `diary/timeline` + `diary/event/{id}` PATCH + `diary/pre-advisor-summary` HEPSİ VAR (`diary.py`).
- **Frontend.** `DiarySidebar.tsx` + `DiaryActions.tsx` + `useDiary.ts` VAR. `NotebookPage.tsx` mevcut ama scope farklı (sayfa-bazlı notebook vs sidebar tab).
- **Veri.** `0029_project_event` MEVCUT.
- **Cron.** `diary_weekly_digest` Pazartesi 10:00 + `diary_monthly_email` her ay 1, 09:00 (TZ).
- **LLM.** Flash 1 (~2K in / 300 out).
- **Boşluk.** `NotebookPage` vs `DiarySidebar` çatışması — refactor adayı.

#### D.7.2 Proje Tamamlama

- **Felsefe.** Sadece kapanış değil — başarılı/geliştirilmeli her adıma akademik öğretici çıktı + mezun ileri-adım önerileri (yayın yolu, sonraki proje) + 5-soru kullanıcı geri bildirim. KVKK 3 ay otomatik silme.
- **Backend.** `completion/snapshot` + `feedback/project-completion` YOK. `reading-list` GET/POST/PATCH/DELETE VAR (S2 user library temeli).
- **Frontend.** `ProjectClosurePage.tsx`.
- **Veri.** `0030_completion` PLAN: `dim_project +3 kolon (completed_at, tier_at_completion, deletion_due_at)` + `dim_feedback` + `project_completion_snapshot`. V2: `mart_completion_health` admin dashboard.
- **Engine.** `engine/completion/badge_thresholds.json` + `oneri_kuralı.json` + `badge_calculator.py` + `oneri_skorlayici.py` + `yorum_prompts/{adim}.txt` (8 adım × Flash sistem prompt) PLAN.
- **Cron.** `retention_cleanup_snapshot` her gün 03:00 + `nps_rollup_daily` her gün 04:00 + `signed_url_refresh` Pazartesi 02:00.
- **LLM.** Flash × 11 (8 yorum + 3 öneri, ~5K in / 200 out).

---

## E. ÇAPRAZ-KESEN KONULAR

### E.1 Kimlik & Yetki

- **Auth:** Supabase Auth magic link (Sercan e-mail provider seçimi pending). JWT ES256 P-256 (HS256 legacy revoke 2026-04-30).
- **Tier:** ENUM `ogrenci / arastirmaci / profesyonel` (`0012` migration), default `ogrenci`. Anon DB'de yok. Mock 5-tier T0-T4 eski (revize ayrı iş).
- **TierGate:** Redis INCR günlük UTC reset; 3 authed tier aynı kotada (KD-V1-S5-03: ödeme tier V2'de ayrışır).
- **RLS:** her project_* tablosuna owner-only. Service-role bypass eder; bu nedenle defansif `eq("user_id", uid)` zırh her route + service'te (K-031).

### E.2 KVKK & Gizlilik

- Sentry breadcrumb PII scrub (5 regex: email, telefon, TC, IP, JWT).
- `0030` migration `deletion_due_at` + cron `retention_cleanup_snapshot` (3 ay sonra soft+hard delete).
- Onboarding KVKK SHA-256 (e-mail hash, plain saklanmaz).

### E.3 Faithfulness & Sycophant Kilidi (DM-049)

- **Pydantic forbid extra** her request/response.
- **Faithfulness gate** ortak servis (`api/services/faithfulness_gate.py`, B-010): jsonschema 100% + LVR (Linked Verification Rate) placeholder 0.85.
- **paper_ids ⊆ corpus_paper_ids** kontrol (5.4 atıf + 3.4 sentez).
- **Sycophant kilidi:** "Yapalım" denmiş olsa bile 3-kontrol uygulanır; ham skor reddedilir, LLM yorumu skor üstünde.

### E.4 Gözlemlenebilirlik

- **Sentry** errors + breadcrumb (KVKK scrub).
- **Runbook iskeleti** (`docs/runbook/`): pinecone_down, supabase_down, hf_endpoint_down, search_p95_breach.
- **Test envanteri:** backend 231 PASS son ölçüm; frontend Vitest 105 PASS (V1-S13 sonrası).
- **Build PASS Empirik Kanıt** (R13.13): `next build` exit 0 + son 3 satır log her sprint closure'unda zorunlu.

### E.5 Cron / Batch

```
gece 02:00 — user_style_profile_update      (silent learning aggregate)
gece 02:00 — signed_url_refresh             (Storage URL renew, Pazartesi)
gece 03:00 — retention_cleanup_snapshot     (KVKK 3 ay imha)
gece 04:00 — nps_rollup_daily               (dim_feedback → mart_nps_daily)
hafta 10:00 — diary_weekly_digest           (21+ gün açık event uyarı)
ay 1, 09:00 — diary_monthly_email           (aylık özet maili, kullanıcı TZ)
```

### E.6 Hesap Tabanı (DM Kararları, B serisi)

Tüm B-NNN kararlar `docs/DECISIONS.md`'de. Mimariye direkt etkili olanlar:
- B-010 `faithfulness_gate` ortak servis.
- B-014 Hibrit workflow (lokal commit + push timing Omer kontrolünde).
- B-018 Backend Senaryo B + pseudocode-first + Pinecone-bağımsız parçalar concrete.
- DM-046 Tier 2-katman canon.
- DM-049 Sycophant kilidi.
- DM-052 Q sayfası 3/20/50 chip + ranking + "Literatür Özeti Oluştur" CTA.
- 2026-05-10 KARAR (Omer): Vitrin → Proje sadece `{alan, alt-alan, konu}` taşır; paper_id YASAK.

---

## F. MİMARİ BOŞLUK — Tek Liste

Aşağıdaki tablo "kusursuz" mimariye giden net açıkları toplar. Statü `YOK` = endpoint/komponent/migration henüz yok; `KISMEN` = var ama scope/imza eşleşmiyor; `RENAME` = mevcut komponent yanlış adla bağlanmış.

### F.1 Backend endpoint açıkları (öncelik sırasıyla)

> **Not (2026-05-11 ikinci senkron):** workshop.py F13-S2..S11 konsolidasyonu ile 17 ek endpoint MEVCUT konumuna geçti (working tree, hepsi çalışıyor). Önceki "28 kalan" listesinden 17 satır KAPANDI bölümüne taşındı. **Kalan açık:** 14 endpoint.

| # | Endpoint | Sayfa | Statü | LOC tahmini |
|---|---|---|---|---|
| 1 | `POST /api/project/{id}/research-area/reset` | 2.1 | YOK | ~90 |
| 2 | `GET /api/workshop/originality` | 4.3 | YOK | ~100 |
| 3 | `POST /api/workshop/compare` | 4.4 | YOK | ~160 |
| 4 | `GET /api/workshop/impact-curve` | 4.5 | YOK | ~140 |
| 5 | `GET /api/workshop/gap/{matrix_id}/{x}/{y}` | 4.2 | KISMEN (mevcut `/api/gap-profile` imzası farklı) | ~100 |
| 6 | `POST /api/workshop/manuscript/coherence-check` | 6.3 | YOK | ~140 |
| 7 | ~~`POST /api/completion/snapshot`~~ | S2 | ✅ MEVCUT (completion.py:56, F13-S13) | — |
| 8 | ~~`POST /api/feedback/project-completion`~~ | S2 | ✅ MEVCUT (completion.py:75, F13-S13) | — |
| 9 | `POST /api/project/{id}/topic/finalize` | 2.2 | YOK (RTF'den çıkarsama) | ~120 |
| 10 | `POST /api/project/{id}/thematic-analysis` | 2.4 | YOK | ~140 |
| 11 | `POST /api/project/{id}/concept-network` | 2.5 | YOK | ~140 |
| 12 | `POST /api/project/{id}/related-works` (ghost) | 3.2 | YOK | ~180 |
| 13 | `POST /api/project/{id}/method-matrix` | 3.3 | YOK | ~120 |
| 14 | `POST /api/project/from-q` payload refactor | 1 → 2.1 | KISMEN (paper_id → field+subfield+topic) | ~50 |

**KAPANDI (referans, 31 endpoint):**

*F11-F12 (vitrin → atölye köprüsü + jüri simülasyonu, 6 endpoint):*
- ✅ `POST /api/project/from-q` payload — F11 Phase A
- ✅ `POST /api/defense/jury-question` (workshop.py:635) — F12 B.1 commit 0cb0ada
- ✅ `POST /api/defense/hyde-fanout-rerank` (workshop.py:653) — F12 6.5 konsolide
- ✅ `POST /api/defense/answer-score` (workshop.py:671) — F12 6.5
- ✅ `POST /api/defense/consistency-check` (workshop.py:686) — F12 6.5
- ✅ `POST /api/defense/jury-decision-band` (workshop.py:704) — F12 6.5

*F13-S1 (araştırma defteri, 4 endpoint):*
- ✅ `POST /api/diary/event` (diary.py:63) + `GET /api/diary/timeline` (:77) + `PATCH /api/diary/event/{id}` (:97) — commit cab5ffc
- ✅ `POST /api/diary/pre-advisor-summary` (diary.py:112) — commit 8dfd228

*F13-S2 (yayın formatı + maturity, 3 endpoint):*
- ✅ `GET /api/workshop/maturity` (workshop.py:139) — commit ccf15b6
- ✅ `PUT /api/workshop/progress` (workshop.py:156) — commit 9619992
- ✅ `POST /api/workshop/advisor-summary` (workshop.py:171) — commit 1ed907e

*F13-S3 (akademik dil, 2 endpoint):*
- ✅ `POST /api/workshop/paraphrase` (workshop.py:196) + `paraphrase-decision` (:216) — commit 4095340

*F13-S4 (atıf stil, 4 endpoint):*
- ✅ `GET /api/workshop/citation-search` (workshop.py:242) + `POST citation-verify` (:255) + `GET format-citation` (:265) + `POST citation-balance` (:280) — commit 2555758

*F13-S5 (yayın taslağı, 2 endpoint, workshop.py konsolide):*
- ✅ `POST /api/workshop/topic-proposals` (workshop.py:319) — 5.2
- ✅ `POST /api/workshop/draft-skeleton` (workshop.py:339) — 5.2

*F13-S6 (yayın içeriği doldurma, 4 endpoint, workshop.py konsolide):*
- ✅ `GET /api/workshop/manuscript` (workshop.py:367) — 6.1
- ✅ `PUT /api/workshop/manuscript/{section_type}` (workshop.py:381) — 6.1
- ✅ `POST /api/workshop/manuscript/quality-check` (workshop.py:403) — 6.1
- ✅ `POST /api/workshop/manuscript/auto-draft` (workshop.py:421) — 6.1

*F13-S7 (savunma formatı, 3 endpoint, workshop.py konsolide):*
- ✅ `POST /api/workshop/defense/session` (workshop.py:442) — 6.2
- ✅ `POST /api/workshop/defense/generate-questions` (workshop.py:457) — 6.2
- ✅ `GET /api/workshop/defense/suggest-jury` (workshop.py:479) — 6.2

*F13-S8 (bireysel kontrol, 4 endpoint):*
- ✅ `GET /api/workshop/checklist` (workshop.py:497) — 6.3
- ✅ `PUT /api/workshop/individual-check` (workshop.py:511) — 6.3
- ✅ `GET /api/workshop/journal-suggest` (workshop.py:537) — 6.3
- ✅ `POST /api/workshop/personal-feedback` (workshop.py:552) — 6.3

*F13-S9 (dergi simülasyonu, 3 endpoint):*
- ✅ `POST /api/defense/reviewer-3persona` (workshop.py:580) — 6.4
- ✅ `POST /api/defense/statcheck` (workshop.py:598) — 6.4
- ✅ `GET /api/defense/journal-calibration` (workshop.py:613) — 6.4

*F13-S11 (literatür sentezi, 1 endpoint):*
- ✅ `POST /api/workshop/synthesize` (workshop.py:296) — commit fed7de9

*F13-S13 (proje tamamlama, 2 endpoint):*
- ✅ `POST /api/completion/snapshot` (completion.py:56) — 8+3 Flash paralel
- ✅ `POST /api/feedback/project-completion` (completion.py:75) — 5-soru form

**Toplam tahmini (güncel):** Kalan 14 endpoint için ~1700 LOC backend + her endpoint için 4-8 unit + 1-3 integration test (toplam ~70-90 yeni test). 31 KAPANDI endpoint zaten test_*.py kapsamında.

### F.2 Frontend komponent açıkları

| # | Komponent / Sayfa | Sayfa | Statü | İş |
|---|---|---|---|---|
| 1 | `ReferenceIntegrityPage` | 6.4 | RENAME (scope farklı) | Rename `JournalReviewerSimulationPage` + içerik refactor (3-persona panel) |
| 2 | `MethodDataEthicsPage` | 3.2 | REFACTOR | RelatedWorks (ghost) UI'a dönüştür |
| 3 | `ConnectedPapersPage` | 3.1 | RENAME | RecommendedLiteraturePage'e taşı; Connected Papers 3.2'ye |
| 4 | `MethodMatrixPage` (yeni) | 3.3 | YOK | Heatmap + dropdown XY + tıklamalı paper listesi |
| 5 | `DiarySidebar` vs `NotebookPage` | S1 | ÇATIŞMA | Sidebar tab kanonu — NotebookPage refactor adayı |
| 6 | `convertToProject()` payload refactor | 1 → 2.1 | KISMEN | `{field, subfield, topic, lang}` payload + selected_paper_ids SİL |
| 7 | "Anladığım kadarıyla" kartı | 2.1 | YOK | parsed_understanding hidrate kart + Düzelt CTA |
| 8 | "Niye bu paper?" mikro-açıklama | 2.1 | YOK | 3 paralel Flash batch ~600ms gerekçe satırı |
| 9 | Standart Yayın Kartı 4-buton kanonu | tüm sayfa | KISMEN | `<PaperCardOpen>` + `<PaperCardLite>` reusable; mevcut `PaperCard` rebrand |
| 10 | Cinematic curtain D17 | 6.5 | YOK | Dramatik açılış sequence (varsa SimulationCurtain reuse) |

### F.3 Veri / Migration açıkları

> **Not (2026-05-11 senkron):** Aşağıdaki tablodan KAPANDI 5 migration çıkarıldı: 0020 (F12 d577e5b), 0025 (F13-S2 be32bbb), 0026 (F13-S3 2979d87), 0027 (F13-S5), 0028 (F13-S6), 0029 (F13-S1 5e28563), 0031 (F13-S8), 0032 (F13-S9).

| # | Migration / JSONB | Statü | Notu |
|---|---|---|---|
| 1 | `0010_paper_flags_temporal.sql` | PLAN | abstract_flags_v5 + temporal (24M+18M satır, 1-1.5GB) |
| 2 | `0018` rezerve | PLAN | Atölye tablosuna kullan |
| 3 | `0019_project_seed_papers` | KARAR BEKLİYOR | Vitrin için ölü; tutulsun mu silinsin mi (DM kararı) |
| 4 | `0022_extended_affinity` | PLAN | 3 türetilmiş affinity tablo |
| 5 | `0023_gap_matrix_calibration` | PLAN | matrix_confidence_calibrated |
| 6 | `0030_completion` | PLAN | dim_project +3 kolon, dim_feedback, snapshot (S2 F13-S14) |
| 7 | `project_anchor.candidates_meta` JSONB persist | EKSİK | anchor_finder yazma kodu yok |
| 8 | `user_profiles.metadata.gap_targets` | PLAN | 4.2 gap target listesi |
| 9 | V2: `dim_ghost_paper` enrichment | V2 | OpenAlex metadata taşıma (0001'de tablo MEVCUT, doldurma V2) |
| 10 | V2: `fact_paper_disrupted_refs` (~750M) | V2 | 1-2 hafta pipeline (cd_5 raw refs; cd_5 skoru zaten 0005'te canlı) |
| 11 | V2: `fact_paper_yearly_citations` (~250-375M) | V2 | Pipeline |
| 12 | V2: `fact_gap_matrix_temporal` | V2 | Zaman serisi gap |
| 13 | V2: `mart_completion_health` view | V2 | Admin dashboard |

**KAPANDI (referans):**
- ✅ `0020_defense_jury_simulation` — F12 commit d577e5b (5 persona seed, 6.5)
- ✅ `0025_project_progress` — F13-S2 commit be32bbb (5.1 Maturity)
- ✅ `0026_silent_learning` — F13-S3 commit 2979d87 (5.3 Akademik Dil)
- ✅ `0027_manuscript_section` — F13-S5 (6.1)
- ✅ `0028_defense_session` — F13-S6 (6.2)
- ✅ `0029_project_event` — F13-S1 commit 5e28563 (S1 Diary)
- ✅ `0031_defense_session_individual_check` — F13-S8 (6.3)
- ✅ `0032_defense_session_scan_results` — F13-S9 (6.4)

### F.4 Engine / Konfigürasyon açıkları

> **2026-05-11 senkron:** Engine dosyalarının çoğu disk'te VAR. Sadece S2 completion engine + 4.3 config eşikleri PLAN.

**MEVCUT (disk'te VAR — `ls engine/` doğrulandı 2026-05-11):**
```
engine/style/{tr,en,id}.json                  ✅ 5.3 dil kuralları
engine/citation/{apa,vancouver,ieee,chicago,mla}.py   ✅ 5.4 (F13-S4 2555758)
engine/dictionary/{tr,en,id}.json             ✅ 5.4 synonym fallback
engine/checklist/{makale,tez}_{tr,en}.json    ✅ 6.3 bireysel kontrol (4 dosya)
engine/personas/journal/{skeptik,sempatik,yontemci}.json    ✅ 6.4
engine/statcheck/multilingual.json            ✅ 6.4 p-value regex
engine/journals/{review_distribution,seed}.json   ✅ 6.4 top-50 dergi profil
engine/personas/jury/{canli,anti_tez,yontemci,dis_disiplin,pratisyen}.json   ✅ 6.5
engine/jury/reaction_thresholds.json          ✅ 6.5 (κ ≥ 0.7 pilot kalibrasyon kalır)
```

**PLAN (henüz yok):**
```
engine/completion/{badge_thresholds.json, oneri_kuralı.json,
                   badge_calculator.py, oneri_skorlayici.py,
                   yorum_prompts/{adim}.txt × 8}    S2 (F13-S14)
config/originality_thresholds (JSON/.env)     4.3 disruption + beauty eşik
```

### F.5 Cron / Batch açıkları

Yukarıdaki E.5 listesi planlı; hiçbiri henüz çalışmıyor. Celery setup (F3 sprint) önkoşul.

### F.6 Çapraz dış bağımlılık

- **HF Inference Endpoint:** `papermind-qwen` çalışıyor (eu-west-1, $0.50/h, scale-to-zero 15 dk). Cosmos TR sunum ayrı endpoint pilotta karar.
- **B-012 Pinecone metadata patch:** Omer Colab'da in-flight (Plan 1 tolere `filter=None`, Plan 2 zorunlu).
- **METHOD §1:** Omer paylaşması bekleniyor (F4 frontend skeleton önkoşulu).
- **Sercan handoff:** MiniCheck NLI fine-tune indir + ALCE recall implementation (faithfulness_gate); Sentry org+project; Render+Vercel+DNS; magic-link e-mail provider.

---

## G. TAMAMLAMA YOL HARİTASI — 3 Sprint Önerisi

> Mimari "kusursuz" hale gelmek için bağımlılık sırasıyla. Plan-first kuralı (CLAUDE.md §0): her sprint başında mini Plan Manifest + explicit onay.

### G.1 Sprint 1 — "Vitrin → Atölye köprüsü temizlenir + 2.x atölye keşfi tamamlanır"

**Süre:** 5-7 gün · **LOC:** ~2200 backend + ~1400 frontend

1. **F11 Phase A** — `convertToProject()` payload refactor (`{field, subfield, topic, lang}`) + `from-q` endpoint imza güncelleme + `0019_project_seed_papers` karar.
2. **F9 P096** — Stage C `cluster_expander` background job + ESTRA scorer + curator concrete (~280 LOC). Bağımlılık: P095 ✅ + B-012 patch.
3. **`research-area/reset` endpoint + candidates_meta JSONB persist** (~90 LOC + anchor_finder.run() append).
4. **2.1 üç dokunuş:** "Anladığım kadarıyla" kartı + "Niye bu paper?" mikro-açıklama + Reset hafıza UI.
5. **2.2 endpoint** `topic/finalize` + project_pool kalıcı kayıt (~120 LOC).
6. **2.4 + 2.5 endpoint** thematic-analysis + concept-network (~280 LOC).
7. **3.1 + 3.2 + 3.3 komponent rename + refactor** (RecommendedLiterature / RelatedWorks (ghost) / MethodMatrix yeni komponent).

**Çıktı:** Vitrin → Proje funnel temiz; 2.x atölye keşfi end-to-end çalışır; Standart Yayın Kartı kanonu kullanılır hale gelir.

### G.2 Sprint 2 — "Boşluk + Yazım + Atıf çalışır hale gelir"

**Süre:** 7-10 gün · **LOC:** ~2800 backend + ~1200 frontend

1. **3.4 `synthesize`** — atölye sentezi (Pro 1 LLM, faithfulness gate; ~180 LOC).
2. **4.1 boşluk haritası kalibrasyon** — `0023_gap_matrix_calibration` migration + UI polish.
3. **4.2 + 4.3 + 4.4 + 4.5 endpoint** — gap-profile imza fix + originality + compare + impact-curve (~500 LOC).
4. **5.1 advisor-summary endpoint** + maturity gate UI bağlama.
5. **5.2 topic-proposals + draft-skeleton** (~270 LOC).
6. **5.3 paraphrase-decision wire** + `engine/style/{tr,en,id}.json`.
7. **5.4 engine/citation parser** 5 stil + `engine/dictionary` 3 dil + UI 4 buton karar (eski-yeni denge histogramı).

**Çıktı:** Boşluk → Karar → Yazım zinciri end-to-end. Atıf halüsinasyon kapısı aktif.

### G.3 Sprint 3 — "Savunma simülasyonları + S1/S2 paneller + KVKK retention"

**Süre:** 10-14 gün + 14 gün pilot · **LOC:** ~3500 backend + ~1800 frontend

1. **6.1 manuscript** — `0027_manuscript_section` migration apply + 5 IMRaD form.
2. **6.2 jury formatı** — `0028_defense_session` migration + `defense/generate-questions` + `suggest-jury`.
3. **6.3 bireysel kontrol** — engine/checklist + journal-suggest endpoint + dergi top-5 SJR match.
4. **6.4 dergi simülasyonu** — `ReferenceIntegrityPage` rename + 3-persona endpoint + statcheck + journal calibration. Engine personas + statcheck regex + review_distribution JSON.
5. **6.5 jüri simülasyonu** — 5 endpoint zinciri (jury-question + hyde-fanout-rerank + answer-score + consistency-check + decision-band). Cinematic curtain D17. Engine 5 persona + reaction_thresholds (pilot validate Cohen κ ≥ 0.7).
6. **S1 Diary Sidebar refactor** (NotebookPage çatışması çöz) + cron diary_weekly + diary_monthly.
7. **S2 completion** — `0030_completion` migration + snapshot endpoint (8+3 Flash paralel) + feedback form + cron retention_cleanup + nps_rollup + signed_url_refresh.
8. **F7 Quality + Pilot** — Sentry tam entegrasyon, Docker, HF, Vercel + 5 pilot 14 gün NPS ölçüm.

**Çıktı:** PaperMind MVP V1 tamamlanmış. C1-C11 kabul kriterleri test edilebilir.

### G.4 V2 (Pilot sonrası)

- `dim_ghost_paper` aktif + 3.2 ghost katmanı tam görünüm.
- `fact_paper_disrupted_refs` ~750M + `fact_paper_yearly_citations` ~250-375M pipeline (1-2 hafta).
- `fact_gap_matrix_temporal` zaman serisi gap.
- Ödeme tier ayrışması (Free/Pro+ DM-046'nın tersine eski 2-katman).
- Dark mode (KD-22).
- `mart_completion_health` admin dashboard.

---

## H. RİSKLER & AÇIK SORULAR

### H.1 Halüsinasyon riski (Claude'un kendi içkapı)

1. **Excel ile codebase arasında zaman gecikmesi.** Excel `workshop.py` ve `diary.py` endpoint'lerini "YOK" listeliyor; codebase grep'te VAR (workshop.py: maturity, manuscript PUT/POST, paraphrase, citation-search/verify/format/balance; diary.py: event POST + timeline GET + event PATCH + pre-advisor-summary). Excel kanonik değil; kod kanonik. **Bu mimari belgesinde codebase verisi öne alındı.**
2. **0019_project_seed_papers ölü mü.** Karar bekliyor. Bu belge "DM kararı bekliyor" kaydı.
3. **`0024_user_gap_targets` REDDEDİLDİ → JSONB.** Doğrulama Excel sheet 16'dan; codebase'te eklenmemiş, onaylı.
4. **`anchor_finder.py` rejected_anchors yazma.** RTF kanıt: "anchor_finder.py içinde rejected_anchors geçmiyor — Grep doğrulandı". Bu belgede doğrulamadım; kanıt seviyesi B (RTF'den).

### H.2 Karar bekleyen mimari noktalar

| # | Soru | Engellediği |
|---|---|---|
| 1 | `0019_project_seed_papers` tutulsun mu silinsin mi | F11 Phase A |
| 2 | Vitrin LR çıktısından field/subfield/topic nasıl çıkarılsın (LLM / parse / manuel) | F11 Phase A |
| 3 | `paywall` modalı V1'de bağlansın mı (KD-V1-S5-03) | Sprint 1 öncesi |
| 4 | Vitrin'den gelen field/subfield/topic Stage A'yı atlasın mı yoksa sentetik turn 0 olarak yazılsın mı | Sprint 1 task 4 |
| 5 | Stage C tetikleme: 2.1'de ÇAPA SEÇ anında mı 2.2 girişinde mi | Sprint 1 task 2 |
| 6 | Card aksiyonları V1'de hangileri (4 standart vs alt küme) | Standart Yayın Kartı kanonu |
| 7 | OPEN-005 Top 5 onay margin eşiği (default 0.7) | F5 P050 chat clarify |
| 8 | OPEN-006 Ghost cache TTL (7d vs 90d) | F3d enrichment + F6 P060 |
| 9 | C11 NPS hedefi (≥+30 vs ≥+50) | F7 P074 |
| 10 | Pilot süresi (14 vs 21 gün) | F7 |

### H.3 Dış engelleyici

- **B-012 Pinecone metadata patch koşum** — Omer Colab in-flight; bitince Sprint 1 task 2 başlayabilir.
- **HF Endpoint Cosmos TR** — Qwen TR yeterli mi, pilotta karar; yetersizse ayrı endpoint $0.50/h ek.
- **Sercan handoff** — MiniCheck NLI fine-tune + Sentry + Render+Vercel+DNS + magic-link.

---

## I. SÖZLÜK

| Kısaltma | Açılım |
|---|---|
| **ESTRA** | 7-boyut paper kalitesi skoru (q_weak / cd_5 / beauty / pagerank / ...) |
| **HyDE** | Hypothetical Document Embeddings — soruyu sahte cevap olarak embed edip ara |
| **RRF** | Reciprocal Rank Fusion — birden fazla ranked listeyi birleştir (k=60) |
| **BGE** | BAAI General Embedding — bizim reranker modeli (BGE-reranker-v2-m3) |
| **CD-index** | Funk-Owen Consolidating-Disrupting (★ yıkıcılık) |
| **Sleeping Beauty** | Ke 2015, B-coefficient (◆ gecikmiş keşif) |
| **NPMI** | Normalized Pointwise Mutual Information (kavram eş-anma) |
| **ARM** | Association Rule Mining (kavram-kavram lift) |
| **Ghost paper** | Bizim corpus'a atıf yapan ama corpus dışında kalan makale |
| **Stage A/B/C** | Çapa belirleme: Sohbet → HyDE+RRF+rerank → cluster_expander |
| **Faithfulness gate** | jsonschema 100% + LVR + paper_ids subset; sycophant kilidi |
| **Decision band** | Accept/Minor/Major/Reject hakem kararı |
| **DataProvenance** | Veri kaynağı şeffaflık pill (kaynak / N / hesaplama / güncellik / kanıt A-B-C) |
| **D5/D6/D17** | Mockup ID'leri — Cards, ChatThread, SimulationCurtain |
| **B-NNN, KD-NNN, DM-NNN** | DECISIONS.md'deki karar / Bilinen Borç / Düzeltme Memo numaraları |

---

## J. KAPANIŞ

Bu belge `Page_Design/Sayfa_Plani_v2/` 28 RTF + `PaperMind_Mimari.xlsx` 30 sheet + `api/routes/` 22 dosya + `web/src/components/project/` 40+ komponent + `db/migrations/` 22 migration üstünden damıtıldı. "Olan + olmayan + bitirmek için ne lazım" tek belgede.

**Sıradaki adım (Omer kararı):**
1. Sprint 1 plan manifest yazılsın mı (CLAUDE.md §0 — onay sonrası kod).
2. F11 Phase A (vitrin → proje köprü temizliği) Sprint 1'in 1. işi olarak başlasın mı.
3. 2.1 sayfasında 3 dokunuş Sprint 1'e dahil mi yoksa F12 Phase B'ye mi.

Bu üç soruya cevap geldiğinde Sprint 1 Plan Manifest'i `docs/plans/F11_vitrin_proje_koprusu_ve_kesif.md` olarak yazılır.

---

*Belge sahibi: PaperMind mimari. Versiyon: v1 — 2026-05-10.*
