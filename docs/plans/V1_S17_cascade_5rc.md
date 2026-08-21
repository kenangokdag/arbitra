# V1-S17 — Projeye Dönüştür Kaskadı 5-RC Düzeltme Sprint'i

> **Konum:** Sprint manifest. Plan-first §0 zorunluluğu — onay sonrası koda geçilir.
> **Branch:** `feat/V1-S17-cascade-5rc` (off `main` HEAD)
> **Tip:** Çok-RC çoğul P-stage sprint (10 P-stage + R13.13 closure)
> **Tarih:** 2026-05-26 (v1.1)
> **Sahip:** Omer (PM) · Claude (kod)
> **Empirik kanıt iddiası kuralı:** R13.13 (`next build` exit 0) + `pytest` exit 0 + `vitest` exit 0 + Playwright auto-smoke.

### Değişiklik kütüğü (v1.0 → v1.1)

| # | Değişiklik | Gerekçe |
|---|------------|---------|
| 1 | KD-V1-S17-01: Stage C **BackgroundTask** + V1-S15.pre lock endpoint 202 + polling | Omer 2.b kararı |
| 2 | KD-V1-S17-03: `fact_paper_concept` YOK varsayımı — alternatif **co-citation × cosine** algoritma | Omer 4.b kararı + tablo kanıtsız |
| 3 | KD-V1-S17-04: `_FINAL_TOP_K=5` onayı | Omer 1.a kararı |
| 4 | KD-V1-S17-05 **revize**: curation-1 → `AnchorRecommendationsPage` (Anchor + ESTRA top-5); `CitationQualityPage` **authoring-4'e taşı**, mevcut `ReferenceStylePage` superset olarak değiştir | Omer "bunlar yazım tarafında olmalı burada değil" + label/içerik eşleşmesi |
| 5 | KD-V1-S17-07 (yeni): Playwright auto-smoke (Claude koşar, Omer manuel değil) | Omer 6.b kararı |
| 6 | P010 P-stage eklendi: CitationQualityPage→authoring-4 taşıma + curation-1 AnchorRecommendationsPage | (4) sonucu |
| 7 | C009 commit eklendi (P010 izole atomik commit) | (6) sonucu |

---

## §0 — BAĞLAM (kaskad anatomisi)

Omer 2026-05-26 bildirimi:
> *"projeye dönüştür dedikten sonra çapa adayı hiç çıkmıyor. bu nedenle arka planda ne sorgularsa bütün sistem o şekilde ilerliyor."*

15 semptom 5 kök nedene (RC) eşlendi (envanter kanıtları aşağıda). RC4 = cascade origin; RC1 ona bağlı, RC2/3/5 paralel.

| RC | Tanım | Kanıt (file:line) |
|----|-------|-------------------|
| **RC1** | Stage B `_FINAL_TOP_K=3` hard sınır + `signals_13` aday üstünde compute edilmiyor | `api/services/anchor_finder.py:51` · `api/services/curator.py:90-105` (Stage B çağırmıyor) |
| **RC2** | Stage B aday `title` Supabase `papers.title`'dan; lazy-mirror boşsa W-id-only dönüyor | `api/services/anchor_finder.py:191-260` · `api/services/papers_mirror.py:1-82` |
| **RC3** | Sidebar nav-config label ↔ component eşleşmesi şaşmış (curation-1 yanlış) + ConnectedPapersPage `?paper_id=` zorunlu | `web/src/lib/nav-config.ts:74` · `web/src/components/project/ConnectedPapersPage.tsx:54-77` |
| **RC4** | `cluster_expander.py` **yok** → `cluster_status='pending'` sonsuz; `ConceptNetworkPage` 20 hardcode node; Bibliometric/Thematic generic | `api/models/project.py:82` (comment) · `web/src/components/project/ConceptNetworkPage.tsx:29-83` |
| **RC5** | ConnectedPapersPage "İncele" buton href yok, dead | `web/src/components/project/ConnectedPapersPage.tsx:212-221` |

---

## §1 — HEDEF + DoD

### Hedef
Kaskad çıkış kapısını (RC4 cluster_expander) açıp, geriye doğru Stage B çıktısını zenginleştir (RC1+RC2), ileri doğru proje-aware tematik/bibliyometrik bağla (RC4), sidebar+link düzelt (RC3+RC5).

### Definition of Done
- [ ] `cluster_expander.run()` real (Pinecone+lex+rerank+ESTRA) — 50 paper output, `cluster_status='ready'`
- [ ] `/api/project/{id}/cluster/expand` 200, idempotent re-run OK
- [ ] `project_papers` tablo populated (anchor_paper_id, cluster_paper_id, signals_13)
- [ ] `/api/project/{id}/concept-network` real producer
- [ ] BibliometricSummary + ThematicAnalysis proje paper_id filter
- [ ] Stage B `_FINAL_TOP_K=5` + `signals_13` her aday üstünde
- [ ] Stage B OpenAlex fallback aktif (Supabase boş W-id için)
- [ ] Sidebar curation-1 label fix
- [ ] ConnectedPapersPage paper_id picker + İncele Link aktif
- [ ] `pytest -q` exit 0 (+10..+30 PASS)
- [ ] `vitest run` exit 0 (+5..+10 PASS)
- [ ] `npx next build` exit 0 — R13.13 kanıt
- [ ] Browser smoke `/project/p1/discovery-1` → çapa kilitle → cluster expand 200 → discovery-3/4/5 dolu

---

## §2 — SCOPE (atomik P-stage'ler)

| P | Konu | Dosyalar | LOC tahmin | Test |
|---|------|----------|------------|------|
| **P001** | RC4 — cluster_expander.py iskelet | api/services/cluster_expander.py YENİ · api/models/research_area.py (ClusterExpandResponse) | ~250 | 8 unit |
| **P002** | RC4 — POST /api/project/{id}/cluster/expand route + DB persistence | api/routes/research_area.py (+endpoint) · api/services/cluster_expander.py (DB write) · 0018 migration project_papers (gerekirse) | ~120 | 3 integration |
| **P003** | RC4 — ConceptNetwork backend producer | api/services/concept_graph.py YENİ · api/routes/project_graph.py YENİ · /api/project/{id}/concept-network | ~180 | 4 unit + 1 integration |
| **P004** | RC4 — Bibliometric + Thematic project-aware | api/routes/gap_heatmap.py (project_id query param) · api/routes/bibliometric.py (varsa, yoksa stub) · FE BibliometricSummaryPage + ThematicAnalysisPage proje paper_id geçir | ~140 | 2 integration + 2 vitest |
| **P005** | RC1 — Stage B limit 3→5 + ESTRA signals_13 | api/services/anchor_finder.py (_FINAL_TOP_K=5, _signals_13 entegrasyonu) | ~30 | 2 unit |
| **P006** | RC2 — Stage B OpenAlex fallback | api/services/anchor_finder.py (papers.title boş ise `_fetch_candidate_metadata` çağır) · paylaşılan `_metadata_fallback` helper | ~70 | 3 unit |
| **P007** | RC3 — Sidebar nav-config label fix | web/src/lib/nav-config.ts (curation-1 → "Yöntem & Veri Kalitesi") · BREADCRUMB testleri update | ~10 | 1 vitest |
| **P008** | RC3 — ConnectedPapersPage paper_id picker | web/src/components/project/ConnectedPapersPage.tsx (proje anchor default + picker) | ~80 | 2 vitest |
| **P009** | RC5 — İncele Link aktif | web/src/components/project/ConnectedPapersPage.tsx:212-221 (Link href) + ResearchAreaConfirmPage paper kartlarında Detay Link | ~20 | 1 vitest |
| **P010** | RC3+ — CitationQualityPage authoring-4'e taşı + AnchorRecommendationsPage YENİ (curation-1) | web/src/app/(app)/project/[id]/[[...slug]]/page.tsx (slug remap) · web/src/components/project/AnchorRecommendationsPage.tsx YENİ · web/src/components/project/ReferenceStylePage.tsx SİL · web/src/lib/nav-config.ts (curation-1 label "Onerilen Literatur" KORUNUR) | ~180 | 3 vitest |

**Toplam:** ~1080 LOC kod + ~33 test
**Sıra (dependency):** P001 → P002 → P003 → P004 (P001 zorunlu) · P005, P006 paralel · P007, P008, P009, P010 paralel.

**P010 detay:**
- `CitationQualityPage` 4 paneli (citation-search/verify/format/balance) zaten `ReferenceStylePage`'in format-only fonksiyonunun SUPERSET'i — `ReferenceStylePage` sil, `CitationQualityPage` authoring-4'e yerleştir (label "Atif & Stil Kilavuzu" eşleşiyor).
- `CitationQualityPage.tsx:20` yorumu güncelle: "F13-S3.5 — authoring-4 (5.4 Atıf & Stil Kılavuzu) — taşındı V1-S17 / 2026-05-26".
- curation-1 ("Önerilen Literatür") YENİ component: `AnchorRecommendationsPage` — `cluster_status='ready'` ise `project_papers` top-5'i `PaperCard compact` ile listele; pending ise spinner + 5s polling.
- Sidebar label "Onerilen Literatur" KORUNUR (gerçek "önerilen literatür" sayfası bu oldu, v1.0 KD-V1-S17-05'in label revize önerisi iptal).

---

## §3 — KD KARARLAR (yeni)

### KD-V1-S17-01 — cluster_expander algoritma (v1.1 REVİZE — BackgroundTask)
**Karar:** Stage C **fastapi.BackgroundTasks** içinde çalışır; V1-S15.pre lock endpoint **202 Accepted** döner; FE polling `/api/project/{id}/cluster/status` 5s interval.

Algoritma:
1. Pinecone vec(anchor_embedding) top-200
2. Supabase lexical(anchor_title_tsv + abstract_keywords) top-200
3. RRF k=60 merge → top-100
4. `is_suspicious=false` HARD filter (Stage B ile aynı)
5. BGE-reranker-v2-m3 → top-50
6. Her aday için `signals_13` compute (curator._signals_13'i reuse)
7. DB persist: `project_papers` (project_id, paper_id, anchor_paper_id, rank, signals_13 jsonb)
8. UPDATE `research_areas SET cluster_status='ready', cluster_completed_at=NOW()`

**Why:** Stage B'nin tam aynası ama "anchor-seed" üzerinden + final top-K 50; BGE-reranker singleton zaten Stage B'de pinned, Stage C tek shot ~3-5s — kullanıcı bekletmez (lock endpoint 202 + poll UX).
**How to apply:** Stage C asla LLM çağırmaz (HyDE Stage B'de kullanıldı, burada gerekmez); maliyet minimize. Hata yutma yasak — `cluster_status='failed'` + `cluster_error` jsonb (HK-1).

### KD-V1-S17-02 — project_papers tablosu schema
**Karar:** Yeni migration `0018_project_papers.sql` — anchor_paper_id FK + cluster paper_id + signals_13 jsonb + rank int.
**Why:** Phase B/C bağlantı tablosu; gelecek discovery sayfaları bu üzerinden okur.
**How to apply:** Migration'ın çelişip çelişmediği `db/migrations/` listesi ile P002 başında doğrulanır (halüsinasyon ihtimali).

### KD-V1-S17-03 — concept_graph veri kaynağı (v1.1 REVİZE — fact_paper_concept YOK)
**Karar:** `fact_paper_concept` tablosu mevcut değil; alternatif algoritma:
1. **Node kaynağı:** `project_papers` üstünden `papers.abstract` TF-IDF top-20 keyword (sklearn `TfidfVectorizer` `max_features=20`, ngram (1,2), TR+EN stopword)
2. **Edge ağırlığı:** keyword `i` ile `j` arasındaki **co-citation cosine** — birlikte geçtiği paper kümesi `S_i ∩ S_j` / `√(|S_i|·|S_j|)`
3. **Filter:** cosine ≥ 0.15 (mock 30 edge ~ orta yoğunluk)
4. Cache: `concept_graph` jsonb kolonu `research_areas` üstünde (HK-5 migration audit P003 başında)

**Why:** Stage C zaten paper havuzunu doldurur (KD-01); concept graph = türetilmiş katman, ayrı tablo gereksiz. TF-IDF + co-citation = standart (Small 1973 SIGIR).
**How to apply:** `fact_paper_concept` aramaya gerek YOK; P003 başında SADECE `research_areas` migration kontrol et — concept_graph jsonb yoksa migration 0019 yaz.

### KD-V1-S17-04 — Stage B `_FINAL_TOP_K=5` (v1.1 ONAYLI)
**Karar:** 3 → 5 (Omer 1.a kararı).
**Why:** UX şikayeti somut ("sadece 3 makale"); reranker'ın top-5'i top-3 ile aynı kaliteli (rerank cost +66% ama tek-shot).
**How to apply:** F9 plan manifestine "1.2 revize" not düşülür. >5 olursa BGE-reranker latency budget breach riski (rerank cold-start ~700MB).

### KD-V1-S17-05 — curation-1 yerleşim (v1.1 REVİZE — taşıma + yeni page)
**Karar (Omer 5.b + "bunlar yazım tarafında olmalı"):**
- `CitationQualityPage` curation-1'den **authoring-4'e taşı** (page.tsx slug remap)
- `ReferenceStylePage` SİL — `CitationQualityPage`'in "format" paneli zaten superset (4 stil + bulk kopyala + BibTeX, ReferenceStylePage tek-stil format-only)
- curation-1'e YENİ `AnchorRecommendationsPage` — anchor + ESTRA top-5 listesi (`project_papers` rank=1..5, `PaperCard compact`)
- Sidebar label `"Onerilen Literatur"` KORUNUR — gerçek içerik artık önerilen literatür

**Why:**
- `CitationQualityPage.tsx:20` yorumu kendisi authoring tarafına aittiğini söylüyor (label "Atif & Stil Kilavuzu" eşleşmesi)
- ReferenceStylePage'in fonksiyonu CitationQualityPage'in "Tek atıfı formatla" paneliyle birebir kapsanıyor — ayrı tutmak ölü kod
- curation-1 (önerilen literatür) için doğal eşleşme = anchor'ın getirisi (cluster top-5)

**How to apply:**
- `page.tsx`:
  - `case "curation-1": return <PageShell><AnchorRecommendationsPage /></PageShell>;` (CitationQualityPage YERİNE)
  - `case "authoring-4": return <PageShell><CitationQualityPage /></PageShell>;` (ReferenceStylePage YERİNE)
- `AnchorRecommendationsPage.tsx` YENİ: anchor `cluster_status` GET → `pending`/`failed`/`ready` 3-yol render; `ready` ise `GET /api/project/{id}/papers?rank_max=5` → `PaperCard compact` list
- `ReferenceStylePage.tsx` SİL + lazy import satırı sil
- Vitest: yeni `AnchorRecommendationsPage.test.tsx` (3 state)

### KD-V1-S17-06 — OpenAlex fallback eşik
**Karar:** Supabase `papers.title` NULL veya boş ("") ise OpenAlex `_fetch_candidate_metadata` tek-paper çağır.
**Why:** RC2 kanıt: anchor_finder.py:249 `title = row.get("title") or ""` → boş kalıyor.
**How to apply:** Latency ekleyici; OpenAlex 100K/gün polite pool — paralel batch (gather) ile minimize.

### KD-V1-S17-07 — Browser smoke (v1.1 YENİ — Playwright auto)
**Karar (Omer 6.b):** Claude `npx playwright test tests/e2e/cascade_smoke.spec.ts` koşar; manuel browser yok.
**Why:** Auto mode + R13.13 build PASS sonrası HEAD smoke; Omer manuel adım istemiyor.
**How to apply:**
- `web/tests/e2e/cascade_smoke.spec.ts` YENİ — 1 senaryo: `/project/p1/discovery-1` → çapa kilitle → 202 + status polling → ready → `/project/p1/discovery-5` ConceptNetwork node count > 5 + `/project/p1/curation-1` Anchor Recs 5 kart
- Playwright config zaten varsa reuse; yoksa C009 commit'ine ekle (`@playwright/test` devDep)

---

## §4 — ATOMIC COMMIT BOUNDARY (§R7)

| Commit | İçerik | Atomicity test |
|--------|--------|----------------|
| C001 | P001 cluster_expander.py iskelet + 8 unit | `pytest tests/test_cluster_expander.py -q` PASS |
| C002 | P002 route + DB migration + 3 integration | `pytest tests/integration/test_cluster_expand.py -q` PASS |
| C003 | P003 concept_graph + route + 5 test | `pytest tests/test_concept_graph.py tests/integration/test_concept_network.py -q` PASS |
| C004 | P004 bibliometric/thematic project-aware | `pytest tests/integration/test_gap_heatmap_project.py -q` + `vitest run` PASS |
| C005 | P005+P006 Stage B limit+ESTRA+OpenAlex | `pytest tests/test_anchor_finder.py -q` PASS |
| C006 | P007 sidebar label fix + vitest | `vitest run nav-config.test.ts` PASS |
| C007 | P008+P009 ConnectedPapersPage paper_id flow + İncele Link | `vitest run ConnectedPapersPage.test.tsx` PASS |
| C008 | P010 CitationQualityPage→authoring-4 taşı + AnchorRecommendationsPage YENİ + ReferenceStylePage SİL | `vitest run AnchorRecommendationsPage.test.tsx` PASS |
| C009 | Playwright cascade_smoke.spec.ts + docs (STATE.md, NEXT_ACTION, V1_S17 closure) | `npx playwright test cascade_smoke` exit 0 |

Plan dışı edit denenirse **STOP** + plan revize (§R7).

---

## §5 — PIPELINE KANIT (file:line — A kanıt seviyesi)

| İddia | Kanıt | A/B/C |
|-------|-------|-------|
| anchor_finder `_FINAL_TOP_K=3` | `api/services/anchor_finder.py:51` | A |
| anchor_finder reranker `_signals_13` çağırmıyor | `api/services/anchor_finder.py:310-315` (sadece score) | A |
| curator `_signals_13` fonksiyonu var | `api/services/curator.py:90-105` | A |
| cluster_expander.py YOK | grep `cluster_expander` → `api/models/project.py:82` comment only | A |
| ConceptNetworkPage hardcoded | `web/src/components/project/ConceptNetworkPage.tsx:29-83` | A |
| ConnectedPapersPage `paperId = params.get("paper_id") ?? ""` | `web/src/components/project/ConnectedPapersPage.tsx:54-56` | A |
| ConnectedPapersPage "İncele" buton href yok | `web/src/components/project/ConnectedPapersPage.tsx:212-221` | A |
| Sidebar curation-1 label "Onerilen Literatur" | `web/src/lib/nav-config.ts:74` | A |
| page.tsx curation-1 → CitationQualityPage | (envanter raporu §1 tablo) | A |
| anchor_finder title source Supabase | `api/services/anchor_finder.py:206-211` | A |
| /api/search OpenAlex enrichment | `api/routes/search.py:114-148` `_fetch_candidate_metadata` | A |
| F9 P096 cluster_expander queued | `docs/plans/V1_S15_pre_anchor_lock.md:37-38` (OUT bölümü) | A |

Doğrulanmamış / B kanıt:
- `project_papers` tablosu **mevcut mu** → P002 başında migrations/0018* var mı diye kontrol; yoksa migration yaz.
- `fact_paper_concept` schema → P003 başında kontrol; yoksa concept_graph algoritması revize.

---

## §6 — R13 COUNCIL (plan-time)

**Alan:** Backend (Stage B/C, Pinecone, Supabase) + Frontend (sidebar, ConnectedPapers).
**Alan sahibi (BAĞLAYICI):** Backend = Sercan post-hoc · Frontend = Omer (lead bos)

| # | Üye | Oy | Gerekçe | Notu |
|---|-----|----|---------|----|
| 1 | Halüsinasyon Avcısı | 🟡 | `project_papers` ve `fact_paper_concept` schema kanıtsız — P002/P003 başında runtime kontrol gerekli (HK-5). | Migration audit önce |
| 2 | Akademik İsabet | 🟢 | RRF (Cormack 2009) + BGE-reranker-v2-m3 + ESTRA reuse, Stage B ile birebir akademik isabet. | — |
| 3 | Fayda-Maliyet | 🟡 | ~900 LOC + 2 yeni migration + 1 yeni Pinecone fan-out (anchor seed) — büyük sprint; ama kaskadın kökü kapanıyor. | 9 P-stage tek sprint ağır, atomik commit zinciri buna izin veriyor |
| 4 | Daha İyisi Var Mı? | 🟢 | F9 §75 P096 spec'i 2026-05-06 zamanı yazıldı; halen geçerli (BGE-reranker-v2-m3 2025 sürümü production'da). | — |
| 5 | Global Çözüm | 🟢 | Pinecone tüm corpus üstünde, dil-agnostik (BGE-M3 multilingual), tüm proje paterni. | — |
| 6 | Son Kullanıcı Avukatı | 🟢 | Kaskad çıkışı = kullanıcının "bütün sistem yanlış ilerliyor" şikayetinin kökünü kapatıyor. | — |
| **A1** | **Backend (post-hoc Sercan)** | 🟡 | OpenAlex fallback latency'si Stage B'yi şişirebilir (her boş paper için +500ms); batch + asyncio.gather zorunlu. | P006 batch impl gözden geçir |
| **A2** | **Frontend (Omer)** | 🟢 | Sidebar label fix + paper_id picker küçük cerrahi, regress riski düşük. | — |

**Sonuç:** YELLOW 3 → Omer hakem kararı (plan onayı şartı).
**Empirik test:** P002 başında migration audit + P003 başında `fact_paper_concept` schema kontrolü ZORUNLU; FAIL → plan revize.

---

## §7 — HK-1..HK-7 (halüsinasyon kod-seviyesi)

| HK | Uygulama bu sprint'te |
|----|----------------------|
| HK-1 | `ClusterExpandResponse`, `ConceptNetworkResponse` Pydantic `extra="forbid"` zorunlu |
| HK-2 | `cluster_expander.py` sabit yorumları: `# kaynak: fact_paper_quality_v3.q_weak (Stage B reuse)`, `# RRF k=60: Cormack 2009 SIGIR`, `# top-50: F9 §75 P096 spec` |
| HK-3 | Pinecone canlı smoke — `tests/fixtures/cluster_expand_v1.json`; OpenAlex fallback smoke — `tests/fixtures/openalex_anchor_fallback.json` |
| HK-4 | Runtime assertion: `assert cluster_status in {"pending","ready","failed"}`, `assert len(candidates) <= 50` |
| HK-5 | Migration manifest verify — `0018_project_papers.sql` apply öncesi `db/migrations/` ls + numara çakışma kontrolü |
| HK-6 | mypy --strict; `Any` leak yasak (signals_13 jsonb için `dict[str, float]` typed) |
| HK-7 | Test seed `random.seed(42)`; `tests/fixtures/cluster_expand_v1.json` deterministic |

---

## §8 — R13.13 BUILD KANIT (closure öncesi)

Sprint kapanışında zorunlu:
```
$ pytest -q
=== N passed in Ts ===  ← exit 0

$ cd web && vitest run
=== Test Files M passed (M) ===  ← exit 0

$ cd web && npx next build
✓ Compiled successfully
✓ Generating static pages (X/X)  ← exit 0
```
Son 3 satır log NEXT_ACTION + STATE'e copy-paste edilecek.

---

## §9 — AÇIK SORULAR + HALÜSİNASYON RİSKLERİ

### Açık sorular (v1.1 — Omer onayı sonrası tüm 6 madde kapalı)
1. ✅ `_FINAL_TOP_K=5` — Omer 1.a (KD-04)
2. ✅ Stage C BackgroundTask 202+polling — Omer 2.b (KD-01)
3. ✅ project_papers var (Omer 3); kolon schema P002 başında runtime audit
4. ✅ fact_paper_concept YOK → TF-IDF + co-citation cosine alternatif (KD-03)
5. ✅ curation-1 = AnchorRecommendationsPage; CitationQualityPage→authoring-4 (KD-05); ReferenceStylePage silinir
6. ✅ Playwright auto-smoke (Claude koşar — KD-07)

### Halüsinasyon riskleri
- `fact_paper_concept` tablosu schema iddiası **kanıtsız** → P003 başında `\d+ fact_paper_concept` zorunlu (Read migration files); yoksa concept_graph algoritması "co-citation × cosine" gibi alternatif.
- `project_papers` migration numarası **0017 reserved waitlist** (CLAUDE.md §6). 0018 önerildi ama mevcut sıra 0018-0027 arası "atölye sayfaları için öneri" (apply edilmemiş). Numara çakışması P002 başında kontrol.
- BGE-reranker-v2-m3 cold-start ~700MB; Stage C ayrı endpoint'te çalışsa singleton (lru_cache) — Stage B ile aynı reranker instance reuse.

---

## §10 — UYUM SİNYALİ CHECKLIST (executor için)

Plan v1.1 zorunlu doğrulama (executor başlamadan önce her madde tickli olmalı):
- [ ] `_FINAL_TOP_K=3` `api/services/anchor_finder.py:51`'de var (5'e çıkar)
- [ ] `_signals_13` fonksiyonu `api/services/curator.py:90`'da var
- [ ] `cluster_expander.py` `api/services/` altında YOK (yazılacak)
- [ ] `ConceptNetworkPage.tsx:29-83` hardcoded NODES/EDGES dizileri var
- [ ] `ConnectedPapersPage.tsx:212-221` button (Link değil)
- [ ] `nav-config.ts:74` "Onerilen Literatur" string'i var (KORUNUYOR)
- [ ] `db/migrations/` listesinde mevcut numara — 0018+ kontrol
- [ ] `web/src/app/(app)/project/[id]/[[...slug]]/page.tsx:97,114` CitationQualityPage curation-1'de, ReferenceStylePage authoring-4'te (taşınacak)
- [ ] `CitationQualityPage.tsx:20` yorum "authoring-3" yanlış (authoring-4 olacak)

Executor eski versiyonu okumuşsa **STOP** — bu plan **v1.1**, v1.0 deprecated.

---

## §11 — RİSK + GERİ ÇEKİLME (rollback)

| Risk | İndikatör | Geri çekme |
|------|-----------|------------|
| Stage C BGE-reranker OOM (Stage B + Stage C aynı reranker singleton 700MB×2) | uvicorn worker memory > 1.5GB | Stage C'yi BackgroundTask'a al (V1-S15.pre kararının tersi, 202 + polling) |
| Pinecone `filter=None` Stage C'de gevşek (B-012 metadata patch koşumu hala duruyor) | İrrelevant cluster aday | KD-V1-S17-01'e `filter={"is_suspicious": False}` ekle (Pinecone B-012 patch sonrası) |
| project_papers migration apply prod-blocking | Supabase Dashboard rejection | Migration rollback + DB-less in-memory cache (Redis 24h) fallback |
| OpenAlex fallback rate-limit 429 | Stage B latency p95 > 6s | Fallback'ı tüm boş paper için tek batch'te değil, top-3 enrich'le sınırla |
| Sidebar label korunuyor — riski yok | — | (v1.1 label revize iptal) |
| ReferenceStylePage silindi ama bağlı test/route varsa kırılır | `pytest`/`vitest` red | P010 başında `grep "ReferenceStylePage"` zorunlu — bağlantı varsa CitationQualityPage'in format paneline yönlendir |

---

## §12 — DEĞER ZİNCİRİ (somut son kullanıcı)

| Önce | Sonra |
|------|-------|
| Çapa kilitledim → sayfa donuyor / "pending" görüyorum | Çapa kilitlerken cluster fan-out tetiklenir; 50 makale anchor altında dolar |
| Discovery-5 Kavram Ağı = 20 hardcoded MCDM düğümü | Proje papers'larından üretilen 20 concept + 30 edge real graph |
| Discovery-3/4 generic gap-heatmap (tüm corpus) | Proje paper_id filter — sadece bu projeye özel themes×methods |
| Stage B 3 aday + sadece W-id | Stage B 5 aday + her aday için Q/M/Δ5/R chip + title/abstract dolu |
| ConnectedPapers "İncele" → ölü buton | İncele → /paper/{id} detay sayfası açılır |
| curation-1 "Önerilen Literatür" → 4-panelli atıf aracı (içerik label'a uymuyor) | curation-1 → anchor + ESTRA top-5 (gerçek önerilen literatür); CitationQualityPage authoring-4'e taşındı (kendi label'ına eşleşti) |
| authoring-4 "Atif & Stil Kilavuzu" = tek-stil format-only (ReferenceStylePage) | 4-panelli tam atıf toolkit'i (CitationQualityPage) |

---

## §13 — POST-CLOSURE PERSİSTENS

- `docs/STATE.md` başlık paragrafı V1-S17 KAPANDI ✅ + commit hash zinciri + R13.13 kanıt
- `docs/NEXT_ACTION.md` lean-back pointer revize
- `docs/SPRINT_HISTORY.md` append entry
- Bu plan manifest §8 R13.13 build kanıt slot doldurulur (closure öncesi)
- Memory güncelle:
  - `project_papermind_current.md` revize (cluster_expander kapsam dışı → kapsam içi)
  - V1-S17 closure memory yaz: `project_papermind_cascade_5rc_closed_2026-05-26.md`

---

## §14 — ONAY

> **Plan onayı YOKSA Edit/Write yasak — §0 absolute.**
> Onay metni: "V1-S17 onaylıyorum" veya "V1-S17 başla" (R1).
> Onay sonrası: P001 → P002 → ... → P009 → C008 closure.

---
