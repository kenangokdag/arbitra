# F11 — Tek Kanal Mimarisi (Q→Çapa→Cluster→Atölye)

> **Statü:** PLAN, onay bekliyor (CLAUDE.md §0 plan-first)
> **Tarih:** 2026-05-10 sabah
> **Önceki:** F10 Phase 1 + 1.5 (demo path iskelet — fixture'larla 5 sayfa açıldı)
> **Tetik:** Omer talebi: "bağlantı yok. bahasa aradım ama ESG getirdi. her sayfa çalışır olsun. mock tasarımından çıkalım. veri projede tek kanaldan ilerleyecek."

---

## §0 Amaç

PaperMind'da **iki ayrık veri evreni** var; bugün karışık ve mock'la bulanık:

- **Vitrin (Q):** OpenAlex canlı arama, hızlı tarama (anonim erişim, max 25 makale).
- **Proje (Atölye):** Bizim warehouse — çapa makale → `cluster_expander` → ~500 makale havuzu → tüm atölye sayfaları (Keşif/Curation/Bibliyometrik/Tematik/Kavram/Gap/Yazım/Savunma) **aynı havuzdan** beslenir.

Şu an Q sayfası canlı OpenAlex'e bağlı, proje sayfaları ise her biri kendi mock fixture'ında. F10'da görsel iskelet açıldı, **veri kanalı kurulmadı**. Bu plan veri kanalını kurar:

```
Q (OpenAlex) ⟶ "Projeye Dönüştür" ⟶ Project create
                                     ↓
                            discovery-1 (Çapa onay)
                                     ↓ anchor lock
                            cluster_expander (~500 makale → project_cluster tablosu)
                                     ↓
        ┌────────────────┬──────────┴──────────┬────────────────┐
        ↓                ↓                     ↓                ↓
  discovery-2       discovery-3           discovery-4      discovery-5
  (Konu top-5)      (Bibliyometrik)       (Tematik)        (Kavram ağı)
        ↓                ↓                     ↓                ↓
        └─── tüm sonraki modüller (curation/gapatlas/authoring/defense) ───┘
                            (hepsi project_cluster'tan okur)
```

**Tek kuralı:** Bir kez çapa kilitlendi mi, proje boyunca **tek havuz** (~500 makale). Sayfa sayfa farklı bir kaynak yok.

---

## §1 Mevcut Durum (file:line kanıt — 2026-05-10)

### 1.1 Backend canlı endpoint'ler ✅

| Endpoint | Servis | Dosya:Satır |
|---|---|---|
| `POST /api/q` (OpenAlex paralel + translate) | `openalex_polite.search_papers` + `tier_gate` | `api/routes/q.py:99` |
| `POST /api/q/literature-review` (Gemini Flash) | `llm_service.call` | `api/routes/q.py:198` |
| `POST /api/project/{id}/research-area/messages` | `librarian.run` (Stage A 2-tur) | `api/routes/research_area.py:55` |
| `POST /api/project/{id}/research-area/anchor-candidates` | `anchor_finder` (HyDE→RRF→rerank, 3 aday) | `api/routes/research_area.py:84` |
| `POST /api/top5` (5-layer pipeline) | `listener+pool_router+reranker+curator` | `api/routes/top5.py:46` |
| `POST /api/project` (CRUD) | onboarding miras snapshot | `api/routes/project.py:106` |
| `GET /api/project/{id}` | RLS + manuel zırh | `api/routes/project.py:204` |

### 1.2 Backend EKSİK ❌

| Eksik | Statü | LOC tahmini |
|---|---|---|
| `cluster_expander` (anchor → ~500 makale) | F9 P096 brief panoda, NOT_IMPLEMENTED | ~280 |
| `POST .../anchor/lock` (çapayı project_anchor'a yaz + cluster_expander tetik) | YOK | ~80 |
| `GET .../bibliometric/summary` (project_cluster aggregate) | YOK | ~150 (servis ~120) |
| `GET .../topic/lock` + `POST .../topic/lock` | YOK | ~80 |
| `GET .../concept-network` (paper-paper graph) | YOK | ~200 |
| `GET .../thematic-clusters` (semantic clustering) | YOK | ~180 (gap-heatmap fixture döner şu an) |
| `POST /api/project/from-q` (Q seçim → project bootstrap) | YOK (yeni köprü) | ~120 |

### 1.3 Frontend bağlantı haritası

| Sayfa | Veri Kaynağı | Q'dan Bağ |
|---|---|---|
| `/q` (`q/page.tsx`) | ✅ `/api/q` real | — |
| `discovery-1` (`ResearchAreaConfirmPage`) | ❌ hardcoded "ESG MCDM" fixture | ❌ **YOK** |
| `discovery-2` (`TopicSuggestionPage`) | ✅ `/api/top5` real (`DEFAULT_QUERY = "MCDM cok kriterli karar verme"`) | ❌ Q sorgusu geçmiyor |
| `discovery-3` (`BibliometricSummaryPage`) | ❌ fixture (TOP_METRICS, YEAR_DIST...) | ❌ |
| `discovery-4` (`ThematicAnalysisPage`) | ⚠️ `/api/gap-heatmap` (backend de fixture) | ❌ |
| `discovery-5` (`ConceptNetworkPage`) | ❌ NODES + EDGES hardcoded | ❌ |

### 1.4 DB Şeması ✅

Migration `0015` (projects + project_chat_messages + project_anchor) + `0016` (project_cluster) DEPLOYED. Tablo hazır, sadece `cluster_expander` servisi içine yazmıyor.

```
project_anchor: project_id PK, anchor_paper_id, candidates_meta jsonb,
                rejected_anchors jsonb, locked_at, cluster_status
project_cluster: (project_id, paper_id) PK, source ('vec'|'bib'|'theme'),
                 rrf_score, q_weak, estra_score, rank_final, frozen_at
```

---

## §2 Hedef Akış (state machine)

```
[1] /q (anon veya pro)
    user: "bahasa indonesia mcdm" arar
    OpenAlex 25 makale döner
    user 5 tanesini seçer + "Literatür Özeti Üret" → review görür
    → "Projeye Dönüştür" CTA tıklar
        |
        ↓
[2] POST /api/project/from-q
    body: { q_query, q_lang, selected_paper_ids[], detected_field? }
    backend: yeni proje yaratır + Q'dan miras snapshot (q_query → project.seed_query,
             selected_paper_ids → project_seed_papers tablosu)
    döner: { project_id }
    frontend: router.push /project/{id}/discovery-1
        |
        ↓
[3] /project/{id}/discovery-1 (ResearchAreaConfirmPage)
    Açılışta:
      a) GET /api/project/{id} → seed_query + seed_papers
      b) POST .../research-area/messages turn=1 (auto-prefill seed_query)
         → librarian Stage A "anladım" 2-tur sohbet
      c) POST .../research-area/anchor-candidates → 3 anchor (HyDE→RRF→rerank)
    user: 1 anchor seçer + "Çapayı Kilitle" CTA
        |
        ↓
[4] POST /api/project/{id}/anchor/lock
    body: { anchor_paper_id }
    backend:
      a) project_anchor.upsert(anchor_paper_id, locked_at=now)
      b) cluster_expander.run(project_id) BACKGROUND JOB
         - anchor → vec havuzu (Pinecone neighbors top-200)
         - anchor → bib havuzu (citing+cited via OpenAlex top-100)
         - theme havuzu (anchor field → theme_emb cluster top-100)
         - RRF fusion k=60 → top-500
         - ESTRA scorer → rank_final
         - project_cluster tablosuna INSERT
      c) project_anchor.cluster_status = 'building' → 'ready' (job sonu)
    döner: { task_id }
    frontend: poll GET /api/project/{id}/cluster/status (1s) → ready
              → router.push /project/{id}/discovery-2
        |
        ↓
[5] /project/{id}/discovery-2 (TopicSuggestionPage)
    GET /api/project/{id}/topic/candidates
    backend: project_cluster top-5 (rank_final desc)
    user: 1 paper seçer + "Konuyu Kilitle" CTA
        |
        ↓
[6] POST /api/project/{id}/topic/lock { topic_paper_id }
    → router.push /project/{id}/discovery-3
        |
        ↓
[7-9] /discovery-3 (Bibliyometrik) + /discovery-4 (Tematik) + /discovery-5 (Kavram)
    Hepsi GET /api/project/{id}/cluster/* (project_cluster aggregate)
        - bibliometric/summary  → year_dist, lang_dist, lotka, top_authors, top_venues
        - thematic/clusters     → semantic UMAP coords + cluster labels
        - concept-network       → paper-paper RRF graph (top edges)
```

---

## §3 Kapsam — 4 Phase

| Phase | Ne | Backend | Frontend | LOC | Süre |
|---|---|---|---|---|---|
| **A** | Q→Project köprüsü + discovery-1 gerçek bağlama | `POST /api/project/from-q` + seed table migration | `ResearchAreaConfirmPage` rewrite (real backend) + Q CTA wire | ~400 | 1 gün |
| **B** | Çapa lock + cluster_expander (omurga) | `cluster_expander` servisi (P096) + `POST .../anchor/lock` + status poll | `discovery-1` lock CTA + cluster building UI + auto-redirect | ~450 | 2 gün |
| **C** | discovery-2/3 gerçek bağlama | `topic/candidates` + `topic/lock` + `bibliometric/summary` (project_cluster aggregate) | `TopicSuggestionPage` rewire + `BibliometricSummaryPage` rewrite | ~500 | 2 gün |
| **D** | discovery-4/5 + curation/gap omurga | `thematic/clusters` + `concept-network` servisleri + curation endpoint'leri | `ThematicAnalysisPage` rewire + `ConceptNetworkPage` rewrite | ~600 | 2-3 gün |

**Toplam:** ~1950 LOC, 7-8 gün full-time çalışma. Sayfa sayfa kapatma — her Phase atomic commit'lerle, build PASS empirik kanıt.

---

## §4 Phase A — Q→Project Köprüsü (1 gün)

### A.1 Backend

**Yeni migration:** `db/migrations/0019_project_seed_papers.sql`
```sql
CREATE TABLE project_seed_papers (
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  paper_id text NOT NULL,
  source_query text NOT NULL,
  source_lang text NOT NULL,  -- 'tr' | 'en' | 'id' | ...
  selected_at timestamptz DEFAULT now(),
  PRIMARY KEY (project_id, paper_id)
);

ALTER TABLE projects
  ADD COLUMN seed_query text,
  ADD COLUMN seed_lang text,
  ADD COLUMN seed_source text DEFAULT 'q';  -- 'q' | 'onboarding' | 'manual'
```

**Yeni endpoint:** `POST /api/project/from-q` (`api/routes/project.py` ekle)
```python
class ProjectFromQRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q_query: str  # max 512
    q_lang: str   # auto detected
    selected_paper_ids: list[str]  # 1-25
    detected_field: str | None = None

class ProjectFromQResponse(BaseModel):
    project_id: str
    seed_query: str
    seed_paper_count: int
```

**Servis genişletme:** `api/services/project_service.py` — `create_from_q()` (insert projects + insert project_seed_papers + RLS).

### A.2 Frontend

`web/src/app/(app)/q/page.tsx` (mevcut F3 CTA'yı değiştir):
- Mevcut: `enterProject('p1')` → router push hardcoded
- Yeni: `convertToProject()` → `apiFetch('/api/project/from-q', { q_query: submitted, q_lang: 'tr', selected_paper_ids: Array.from(selected) })` → `enterProject(response.project_id)`

`web/src/lib/navigation-context.tsx` — `enterProject` zaten `/discovery-1`'e gidiyor (F6'da değiştirildi). Değişiklik yok.

`web/src/components/project/ResearchAreaConfirmPage.tsx` — fixture sökülecek (Phase B'de):
- Bu Phase'de sadece `useProject(id)` hook ile seed_query'i göster (header'da "Q'dan: '${seed_query}' sorgusu, ${count} seçim"); fixture parsed_understanding hâlâ kalır (Phase B'de kalkar).

### A.3 DoD (Phase A)

- [ ] migration 0019 apply (psql session pooler)
- [ ] `POST /api/project/from-q` 200 + RLS + 5 unit + 2 integration test
- [ ] Q "Projeye Dönüştür" → real project create → discovery-1 açılır
- [ ] discovery-1 header'da Q'dan miras seed_query görünür
- [ ] `npm run build` PASS + `pytest -q` PASS

---

## §5 Phase B — Çapa Lock + Cluster Expander (2 gün, **omurga**)

### B.1 Backend

**Yeni servis:** `api/services/cluster_expander.py` (~280 LOC, F9 P096 brief'ten)
```python
class ClusterExpanderService:
    async def run(self, project_id: str) -> int:
        anchor = await fetch_anchor(project_id)
        # 3-havuz paralel
        vec_pool = await pinecone_neighbors(anchor.paper_id, k=200)
        bib_pool = await openalex_citing_cited(anchor.paper_id, k=100)
        theme_pool = await theme_neighbors(anchor.field, k=100)
        # RRF fusion k=60 → top-500
        fused = rrf_fuse([vec_pool, bib_pool, theme_pool], k=60, top=500)
        # ESTRA scorer
        scored = await estra_scorer.score(fused, project_id)
        # project_cluster INSERT
        await supabase.table('project_cluster').upsert([
            {project_id, paper_id, source, rrf_score, q_weak, estra_score, rank_final}
            for ... in scored
        ])
        await mark_anchor_status(project_id, 'ready')
        return len(scored)
```

**Yeni endpoint'ler:** (`api/routes/research_area.py` veya yeni `cluster.py`)
- `POST /api/project/{id}/anchor/lock` — body: `{anchor_paper_id}`; project_anchor.upsert + cluster_expander.run() background → döner `{task_id}`
- `GET /api/project/{id}/cluster/status` — döner `{status: 'building'|'ready'|'failed', count}` (Redis polling)

### B.2 Frontend

`ResearchAreaConfirmPage.tsx` — **fixture tamamen sökülür**:
- `useQuery(['research-area-messages', projectId])` ile turn 1 mesajını seed_query'le pre-fill
- `useQuery(['anchor-candidates', projectId])` ile 3 anchor real backend'den
- "Çapayı Kilitle" CTA → `useMutation(POST .../anchor/lock)` → loading "Havuz oluşturuluyor (≈30s)" + cluster status poll → ready olunca redirect /discovery-2

### B.3 DoD (Phase B)

- [ ] `cluster_expander` 6 unit + 2 integration test (Pinecone+OpenAlex mock)
- [ ] `anchor/lock` endpoint 4 unit + 1 integration
- [ ] discovery-1 sayfasında Kütüphaneci sohbeti + 3 real anchor + lock CTA → cluster build UI → auto-redirect
- [ ] project_cluster tablosunda gerçek 500 satır görünür (live smoke)

---

## §6 Phase C — discovery-2/3 Gerçek Bağlama (2 gün)

### C.1 Backend

**Yeni endpoint'ler:**
- `GET /api/project/{id}/topic/candidates` — project_cluster'tan top-5 (rank_final desc)
- `POST /api/project/{id}/topic/lock` — body: `{topic_paper_id}`; project.topic_paper_id kolon update
- `GET /api/project/{id}/bibliometric/summary` — project_cluster aggregate query (year, lang, lotka bins, top_authors, top_venues)

**Yeni servis:** `api/services/bibliometric_service.py` (~120 LOC)
```python
class BibliometricService:
    async def summary(self, project_id: str) -> BibliometricSummary:
        cluster = await fetch_cluster(project_id)  # 500 paper IDs
        papers = await supabase.table('papers').select(...).in_('id', cluster_ids)
        return BibliometricSummary(
            top_metrics=compute_top_metrics(papers),
            year_distribution=group_by_year(papers),
            language_distribution=group_by_lang(papers),
            citation_lotka=lotka_bins(papers),
            top_authors=top_n_authors(papers, n=10),
            top_venues=top_n_venues(papers, n=10),
        )
```

### C.2 Frontend

- `TopicSuggestionPage.tsx` — DEFAULT_QUERY hardcode kaldır; `useQuery(['topic-candidates', projectId])` ile gerçek backend; "Konuyu Kilitle" CTA → POST topic/lock → discovery-3
- `BibliometricSummaryPage.tsx` — fixture tamamen söküldü; `useQuery(['bibliometric', projectId])` real backend; loading skeleton + error fallback

### C.3 DoD (Phase C)

- [ ] 3 endpoint + 1 servis + test'ler PASS
- [ ] discovery-2 ve discovery-3 sayfaları project_cluster'tan canlı veri çekiyor
- [ ] Q'dan farklı sorgu (örn. "bahasa indonesia mcdm") yapsa Bibliyometrik panorama farklı sonuç gösteriyor

---

## §7 Phase D — discovery-4/5 + Sonraki Modüller (2-3 gün)

- `GET /api/project/{id}/thematic/clusters` — semantic UMAP + cluster labels (sklearn KMeans + BGE embedding cache)
- `GET /api/project/{id}/concept-network` — paper-paper RRF graph (top 100 edges)
- `ThematicAnalysisPage.tsx` rewire (gap-heatmap fixture'ı söküldü)
- `ConceptNetworkPage.tsx` rewrite (NODES/EDGES fixture söküldü)

**Sonraki modüller (curation, gapatlas, authoring, defense):** Aynı pattern — her sayfa `project_cluster`'tan okur. Phase E+ (bu plan dışı, ayrı sprint).

---

## §8 Açık Sorular

| # | Soru | Engellediği | Önerilen yön |
|---|---|---|---|
| AS-1 | Q "Projeye Dönüştür" anonim user için ne yapar? Tier kontrolü? | Phase A endpoint | DM-046 Pro tier required; anon → paywall sheet |
| AS-2 | cluster_expander ESTRA scorer hâlâ stub (NotImplementedError) — gerçek formül? | Phase B (omurga) | F8 KD-14 paralel; scorer deferred → uniform 0.5 (degraded mode), Phase E'de gerçek |
| AS-3 | OpenAlex citing/cited (bib pool) rate limit? | Phase B | polite pool (`openalex_polite.py` ✅ var) + cache |
| AS-4 | discovery-2'de DEFAULT_QUERY artık seed_query mi yoksa konu_pool aggregate mi? | Phase C | seed_query (Q'dan miras) + cluster top-5 (rank_final). Eski "free text re-query" deprecated |
| AS-5 | Q'dan seçim yapmadan "Projeye Dönüştür" tıklanırsa? | Phase A UX | CTA disabled (en az 1 seçim şart) |
| AS-6 | `discovery-1` "Değiştir" akışı — Kütüphaneci sohbeti P097'de değil burada mı? | Phase B scope | Phase B = aynı sayfada chat panel (mini); P097 P098+ ayrı |

---

## §9 Risk

| Risk | Seviye | Etki | Mitigation |
|---|---|---|---|
| cluster_expander ~30s sürer (3-havuz paralel) | ORTA | UX kötüleşir | Background job + status polling (Redis); user UI'de "havuz oluşturuluyor" animasyonu |
| Phase D çok büyük (~600 LOC frontend rewrite) | ORTA | Kapsam kayması | discovery-4/5 Phase D başında re-scope (gerekirse Phase E'ye çek) |
| ESTRA scorer hâlâ stub → cluster sıralama bozuk | DÜŞÜK | rank_final yanıltıcı | uniform 0.5 (degraded) + warn log; Phase E real scorer |
| F11 boyunca V1-S11 (translate_query) Omer paralel devam ediyor | DÜŞÜK | Branch çakışması | Her Phase ayrı branch; rebase günlük |
| Q anon user'ı "Projeye Dönüştür" tıkladığında auth yoksa | YÜKSEK | UX kırılır | Phase A'da paywall sheet açılır; auth + ücretsiz tier sonra |

---

## §10 Onay Protokolü

CLAUDE.md §0 plan-first. Onay seviyesi:

1. **Plan onayı (bu manifest):** "F11 plan onaylandı" veya "Phase A başla"
2. **Atomic commit boundary:** Her Phase için ayrı plan §3 satırındaki LOC + dosya sayısı (atomic commit'ler önceden listelenir Phase başında)
3. **Phase kapanış kanıtı (R13.13):** `npm run build` PASS + `pytest -q` PASS + browser smoke (Omer manuel)

**Önerim:** Phase A'dan başlayalım — Q→Project köprüsü 1 günde tamamlanır, demo path "bahasa aradım, ESG geldi" sorunu kalkar (artık Q'dan gelen sorgu/seçim discovery-1'de görünür). Sonra Phase B (omurga) için ayrı onay alalım — cluster_expander büyük iş.

---

## §11 Bu Plan Dışı (DEFERRED)

- Curation 5 sayfa (curation-1..5) — F12
- GapAtlas 5 sayfa (gapatlas-1..5) — F13
- Authoring 4 sayfa + Defense 6 sayfa — F14+
- ESTRA scorer gerçek implementasyon — F15
- Onboarding miras (project_seed_source='onboarding') — F16

---

## §12 Kanıt — bu plan ne kadar doğrulandı?

**Kanıt seviyesi A (bu oturumda Read/Grep ile gördüm):**
- Tüm endpoint dosyaları + LOC sayıları (Explore agent envanteri 2026-05-10)
- DB migration 0015/0016 deployed (STATE.md ✅)
- ResearchAreaConfirmPage fixture (benim yazdığım, son commit 7c65dd0)
- BibliometricSummaryPage fixture (benim yazdığım, e001a41)
- Q sayfası real /api/q (q.py:99)

**Kanıt seviyesi B (docs'ta yazılı):**
- F9 P096 cluster_expander brief panoda — `/tmp/F9_P096_executor_brief.md` (NEXT_ACTION'da referans, bu oturumda dosyayı okumadım)
- ESTRA scorer KD-14 (F8 paralel) — STATE'de geçiyor

**Kanıt seviyesi C (tahmin / training data):**
- cluster_expander LOC tahmini ~280 → STATE'de yazılı ama brief dosyasını okumadım, doğrulayamıyorum
- OpenAlex polite pool rate limit etkisi — varsayım

**Eksik doğrulama (sabah açılışta yapılacak):**
- F9 P096 brief dosyası `/tmp/F9_P096_executor_brief.md` okunmadı (tmp klasör)
- ESTRA scorer skeleton (`api/services/p008_*` veya benzeri) görülmedi
- `gap-heatmap` backend hakikaten fixture mı yoksa bir tür computation mı (kontrol edilmedi)

---

**Sıradaki adım:** Omer onayı.
