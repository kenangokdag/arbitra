# Discovery-4 — Tematik Analiz (UMAP semantik harita + cluster atribüsyonu)

> **Çift mock paradoksu:** Wired hızlı versiyon (`ThematicAnalysisPage` seeded random) + Unwired gerçek versiyon (`UMAPClusterCard` BGE-M3 1024-d UMAP). Karar: **UMAPClusterCard kazanır, ThematicAnalysisPage demote edilir.**
> **Halüsinasyon yasağı:** mevcut wired mock çağırdığı `/api/gap-heatmap` endpoint'ini misuse ediyor (gapatlas-1'in endpoint'i, theme×method değil semantik harita üretmiyor).

---

## KONUM

- **Route:** `/project/{id}/discovery-4`
- **Frontend (wired, KALDIRILACAK):** `web/src/components/project/ThematicAnalysisPage.tsx` (227 satır) `[REPO]`
  - Switch case mevcut: `case "discovery-4": return <PageShell><ThematicAnalysisPage /></PageShell>;`
- **Frontend (unwired, KANON OLACAK):** `web/src/components/UMAPClusterCard.tsx` (635+ satır) `[REPO]`
  - `zone="discovery"`, title "UMAP tematik haritası", subtitle "BGE-M3 1024-d embedding → 2D projeksiyon · Anlamsal yakınlık = harita yakınlığı", sourceBadge "BGE-M3 24.87M paper · UMAP 2D"
- **Backend:** YOK — UMAP 2D koordinatları için endpoint yok `[REPO]`
  - Wired mock `/api/gap-heatmap` (theme×method matrix; semantik harita değil — yanlış endpoint)
- **İlişkili:** discovery-1 anchor + discovery-2 topic + discovery-3 cluster_expander çıktısı

---

## MEVCUT

**Frontend WIRED (ThematicAnalysisPage 227 satır) — fake:**

- `useQuery(["gap-heatmap-themes"]) → /api/gap-heatmap?top_methods=14&top_topics=30` çağırır
- `buildClusters(topics)` — group string'inden cluster türetir, **seeded random pixel coordinates** (`cx = 80 + (i % 3) * 200 + rand() * 60`)
- `buildDots(clusters)` — her cluster etrafında **seeded random** dots (gerçek paper koordinatı değil)
- "Konunuz" pulse marker — **hard-coded `left: 51%, top: 47%`** (gerçek konum değil)
- Color mode dropdown (Tema/Yıl/Atif) — **state var, UI'a etkisi yok** (Yıl/Atif handler implement edilmemiş)
- Opacity slider — çalışıyor
- DataVizCard `badge="fact_gap_matrix M1"` — **yanıltıcı**, sayfa tematik harita değil

**Frontend UNWIRED (UMAPClusterCard 635+ satır) — gerçek tasarım:**

- d3 zoom/pan, BGE-M3 1024-d → UMAP 2D projeksiyon
- `themes`, `points`, `userTopic` interface'leri — gerçek şema
- "Anlamsal yakınlık = harita yakınlığı" subtitle — semantik anlam taşır
- Year/citation color modes muhtemelen implement edilmiş (sınıflanmış lucide ikonlar: Calendar, TrendingUp, MapPin, Target)
- DataVizCardFrame zone="discovery" — doğru atribüsyon
- sourceBadge "BGE-M3 24.87M paper · UMAP 2D" — gerçek veri kaynağı

**Backend:** YOK. Wired mock yanlış endpoint çağırıyor.

---

## ROL

Konu (discovery-2) kilitli + bibliyometrik panorama (discovery-3) görüldükten sonra **anlamsal yakınlık haritası** sayfası. Kullanıcının konusunu havuzun semantik uzayında nereye düştüğünü gösterir. Cluster'lar = tema grupları (BGE-M3 embedding üzerinde HDBSCAN/k-means); "Konunuz" marker'ı havuzdaki spesifik konum. **Insight:** "Konum şu cluster'ın kenarında — komşu cluster da ilgili" → discovery-5'e (kavram ağı) hazırlık.

---

## PİLOT?

**HAYIR — pilot scope dışı.** En ağır frontend bloku (UMAPClusterCard 635+ LOC d3) + en ağır backend (UMAP 2D pre-computed warehouse). F9 sonrası faz.

---

## BAĞIMLILIK

- **Giriş:** discovery-3 sonrası (sıralı sidebar) veya direkt sidebar tıklama
- **Çıkış:** discovery-5 (kavram ağı) — cluster seçilirse "Bu cluster içinde kavram ilişkileri" geçişi `[KARAR]`
- **Backend bağımlılığı:**
  - **Yeni endpoint** `GET /api/project/{id}/umap-snapshot` — proje cluster'ının UMAP 2D koordinatları
  - **Warehouse pre-computation** — 24.87M paper × UMAP 2D koordinatı (offline batch, Colab compute) `[KARAR]`
  - HDBSCAN cluster assignment (offline batch)

---

## SAYFA YAPISI (ASCII — UMAPClusterCard'a göre yeniden)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [Atölye · Keşif] › Tematik Analiz             [Pro · UMAP cluster N=8]   │
├──────────────────────────────────────────────────────────────────────────┤
│ [DataVizCardFrame zone=discovery]                                        │
│  Title: UMAP tematik haritası                                            │
│  Subtitle: BGE-M3 1024-d → 2D · Anlamsal yakınlık = harita yakınlığı   │
│  sourceBadge: BGE-M3 24.87M paper · UMAP 2D                              │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌── SOL CLUSTER LİSTESİ (280px) ─┐ ┌── ANA CANVAS d3 zoom/pan ────────┐ │
│  │ Tema Gruplari (8)               │ │                                 │ │
│  │ ● MCDM yöntemleri    █████ 184  │ │       cluster1 ●●●●             │ │
│  │ ● Sürdürülebilirlik   ████ 142  │ │   cluster2 ●●●●●●  cluster3     │ │
│  │ ● Eğitim & akredit    ███  87   │ │              ●  ←Konunuz         │ │
│  │ ● ESG & risk          ███  76   │ │  cluster4 ●●● ★                 │ │
│  │ ● Bulanık mantık      ██   58   │ │       ●●●  cluster5             │ │
│  │ ● ML hibrit           ██   54   │ │  cluster6 ●●●●  cluster7        │ │
│  │ ● Tedarik zinciri     █    32   │ │                  ●●●            │ │
│  │ ● Diğer               ▎    19   │ │                                 │ │
│  └─────────────────────────────────┘ │                                 │ │
│                                      └─────────────────────────────────┘ │
│  Controls:                                                               │
│  Renklendir: [Tema ▾] [Yıl] [Atif]   Opasite: [▬▬▬●─] 70%               │
│  Yakınlık (zoom): ×1.0   [Reset zoom] [Konunuza fokus]                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## BOŞLUK

- **Wired mock fake** — seeded random dots, `/api/gap-heatmap` misuse, color mode handler yok
- **UMAPClusterCard hiç bağlanmamış** — switch'te yok, dosya orphan duruyor
- **Backend yok** — UMAP 2D endpoint, cluster assignment, "Konunuz" konum hesabı yok
- **Warehouse pre-compute eksik** — 24.87M paper × UMAP 2D batch işi yapılmamış (Pinecone embedding'den UMAP fit_transform Colab gerek)

---

## KARAR

**[KARAR]** Çift mock paradoksu çözümü:

1. **`ThematicAnalysisPage.tsx` SİL** — fake seeded random + yanlış endpoint çağrısı; kanon değil. Switch case `discovery-4` kalır ama component değişir.
2. **`UMAPClusterCard.tsx` ADOPT** — `web/src/components/project/UMAPThematicPage.tsx` veya benzer'e taşınır + projectId prop kabul edecek şekilde wrap. Mevcut hardcoded mock veri (`generateMockUMAPData()` benzeri) `useQuery` sonucuyla replace edilir.
3. **Switch case güncellenir:** `case "discovery-4": return <PageShell><UMAPThematicPage projectId={id} /></PageShell>;`
4. **Backend yeni:** `GET /api/project/{id}/umap-snapshot` → cluster atributu + paper koordinatları + userTopic konumu
5. **Warehouse offline batch:** 24.87M paper UMAP 2D fit_transform (BGE-M3 1024-d → UMAP 2D, n_neighbors=15, min_dist=0.1) + HDBSCAN cluster assignment (min_cluster_size=50). **Tek seferlik batch**, sonra incremental update.

**Cluster atribüsyonu [KARAR]:** HDBSCAN. Reason: paper sayısı belirsiz (her proje farklı havuz boyutu), HDBSCAN k seçimi gerektirmez. K-means alternatif: k=8 sabit, kullanıcı algılaması daha sade ama gerçek kümelenmeyi yakalamayabilir. **HDBSCAN tercih**, fallback k-means k=8.

**"Konunuz" marker konum [KARAR]:** Topic paper'ın UMAP 2D koordinatı doğrudan. Eğer topic paper havuzda yoksa (off-manifold), embedding'den UMAP transform (lazy) ile anlık projeksiyon — fallback "yakın 5 paper centroid".

**Color modes:**
- **Tema:** cluster_id → 8 renk (Tableau-10 paleti)
- **Yıl:** year → linear gradient blue→amber (eski → yeni)
- **Atıf:** citations → log-scale gradient gri→koyu mor (az → çok)

---

## NASIL

### Frontend dosyalar

**Sil:**
- `web/src/components/project/ThematicAnalysisPage.tsx` (mevcut wired mock — kanon değil) — silinir veya reference olarak korunur (`.bak`)

**Adopt + revize:**
- `web/src/components/UMAPClusterCard.tsx` → `web/src/components/project/UMAPThematicPage.tsx` rename + projectId prop + `useQuery` veri kaynağı
- Mevcut hardcoded `generateMockUMAPData()` → API call

**Yeni:**
- `web/src/hooks/useUMAPSnapshot.ts` (~40 LOC) — `useQuery(["umap-snapshot", projectId])`, staleTime 1h

**Mevcut dosya revizyonu:**
- `web/src/app/(app)/project/[id]/[[...slug]]/page.tsx` — switch case güncelleme (yukarıdaki KARAR §3)

### Backend (yeni)

**Yeni endpoint:** `GET /api/project/{project_id}/umap-snapshot`

```python
class UMAPPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paper_id: str
    x: float
    y: float
    cluster_id: int
    year: int | None
    citations: int | None

class UMAPCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cluster_id: int
    label: str            # LLM-generated cluster label (Gemini Flash + top-5 paper title)
    color: str            # "#4C78A8" Tableau palette assignment
    paper_count: int
    centroid: tuple[float, float]

class UMAPSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    points: list[UMAPPoint]              # cluster paper'ları (filtered)
    clusters: list[UMAPCluster]
    user_topic: UMAPPoint                # topic paper'ın koordinatı
    generated_at: datetime
```

**Service:** `api/services/umap_service.py` (yeni)

1. Cluster paper_id listesini al (P096 cluster_expander çıktısı)
2. Warehouse'dan `fact_paper_umap_2d` tablosunda paper_id → (x, y, cluster_id) join (yeni tablo)
3. Cluster label'ları: `dim_umap_cluster` (LLM-pre-generated; offline batch)
4. user_topic: topic paper_id'nin (x, y) koordinatı — havuzda yoksa lazy projeksiyon
5. Redis cache: `umap:{project_id}` 1h TTL
6. Response build, return

### Veri (yeni warehouse tabloları + offline batch)

**Migration `0020_fact_paper_umap_2d.sql`:**

```sql
create table fact_paper_umap_2d (
  paper_id text primary key,
  x real not null,
  y real not null,
  cluster_id int not null,
  computed_at timestamptz not null default now()
);
create index idx_umap_cluster on fact_paper_umap_2d (cluster_id);
```

**Migration `0021_dim_umap_cluster.sql`:**

```sql
create table dim_umap_cluster (
  cluster_id int primary key,
  label text not null,
  color text not null,
  centroid_x real not null,
  centroid_y real not null,
  paper_count int not null,
  computed_at timestamptz not null default now()
);
```

**Offline batch (Colab Pro+ × 3, BGE-M3 mevcut):**
1. Pinecone'dan tüm 24.87M paper embedding fetch (chunk 10K) — ~3-4h
2. UMAP fit_transform (n_neighbors=15, min_dist=0.1) — ~6-8h tek A100
3. HDBSCAN cluster_assignment (min_cluster_size=50)
4. Cluster label generation: her cluster için top-5 paper title → Gemini Flash → label (1-2 token TR)
5. Bulk upload Supabase
6. Tek seferlik batch (incremental update F2+ kararı)

---

## TIER DAVRANIŞI

**Anon:** Erişilemez.
**Pro:** Tüm özellikler. Cluster boyutu sınırı yok.
**Free:** YOK.

---

## AÇIK SORULAR

| # | Soru | Engellediği | Önerilen yön |
|---|---|---|---|
| **AS-1** | UMAPClusterCard rename mı yoksa silip yeniden mi? | Frontend implementation | **Rename + adopt** — 635 LOC d3 zoom/pan büyük yatırım, sıfırdan yazma israf. `[KARAR]` |
| **AS-2** | UMAP fit_transform offline batch ne zaman koşulur? | Backend + warehouse | **F2 başında** Colab. Backend canlı olmadan frontend test edilemez. `[KARAR]` |
| **AS-3** | Cluster label LLM mi sabit metni mi? | Backend service | **LLM** — Gemini Flash, offline batch, sabitlenir (ucuz, cache'lenir). `[KARAR]` |
| **AS-4** | Color mode (Tema/Yıl/Atıf) defaults? | UX | **Tema** default. `[KARAR]` |
| **AS-5** | "Konunuz" marker fallback (paper havuzda yoksa)? | Backend service | Lazy projeksiyon — Pinecone embed lookup → UMAP transform → koordinat. Yoksa: yakın 5 paper centroid. `[KARAR]` |
| **AS-6** | discovery-4 → discovery-5 cluster geçişi (cluster click ile filter)? | UX scope | Pilot post-MVP — cluster click only highlight; F2+'da discovery-5'e cluster filter geçişi. `[KARAR]` |

---

## TEST KAPSAMI

**Backend (yeni):**
- `tests/unit/test_umap_service.py` — cluster filter, user_topic lookup, cluster label fetch
- `tests/integration/test_umap_endpoint.py` — happy path, 404 cluster yok, cache hit
- Smoke: `tests/fixtures/umap_snapshot_v1.json` (test projesi üzerinde sabitlenir)

**Frontend (yeni — Vitest):**
- `UMAPThematicPage.test.tsx` — render, d3 zoom mount, cluster list interaction, color mode switch
- `useUMAPSnapshot.test.ts` — mock 200/404
- Visual regression (Playwright F2+) — d3 canvas pixel diff

---

## BU SAYFA İÇİN KARARA BAĞLANACAK DM

- **DM-XXX** ThematicAnalysisPage demote + UMAPClusterCard adopt (çift mock çözümü)
- **DM-XXX** UMAP+HDBSCAN offline batch sprint timing
- **DM-XXX** Warehouse 2 yeni tablo (fact_paper_umap_2d + dim_umap_cluster)
- **DM-XXX** Cluster label LLM generation policy
- **DM-XXX** "Konunuz" off-manifold fallback algoritması
- **DM-XXX** Color mode default (Tema)
