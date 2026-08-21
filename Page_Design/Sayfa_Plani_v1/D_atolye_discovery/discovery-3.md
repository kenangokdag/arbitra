# Discovery-3 — Bibliyometrik Analiz (havuz panoraması: yıl, atıf, yazar, dergi, dil)

> **Discovery batch'in tek mock'suz sayfası.** Plan-from-scratch.
> **Halüsinasyon riski yüksek:** kanıt repo'da yok; tüm kararlar `[KARAR]` etiketli, onaya tabi.
> **CitationGraphCard.tsx (zone="curation") aday DEĞİL** — yanıltıcı görünüyor ama curation zone'una bağlı; discovery-3 için sıfırdan tasarım.

---

## KONUM

- **Route:** `/project/{id}/discovery-3`
- **Frontend:** ROUTE FALLBACK — switch case **YOK**, `default → PlaceholderPage` `[REPO]`
- **Backend:** YOK — bibliometric endpoint yok `[REPO]`
- **Aday unwired component:** YOK
  - `CitationGraphCard.tsx` mevcut (465+ satır d3) ama `zone="curation"` (curation-2 İlişkili Çalışmalar için yazılmış görünüyor; bibliyometrik panorama değil) `[REPO]`
- **İlgili plan:** Yok — F9 docs'unda bibliometric sprint yok
- **Sidebar:** `nav-config.ts:66 { id: "discovery-3", label: "Bibliyometrik Analiz" }` `[REPO]`

---

## MEVCUT

**Hiçbir şey.** PlaceholderPage stub. Backend yok, mock yok, plan yok. Discovery-3 SPINE.md'de sadece label olarak duruyor.

**Veri kaynağı potansiyeli (warehouse):**

- `fact_paper_id_card` 24.86M satır — title, year, language, citations vs. metadata
- `dim_author` (varsa) — yazar metadata
- `dim_venue` (varsa) — dergi/konferans metadata
- `fact_paper_signals_13` — signals_13 abstract flags (abstract_flags_v5)
- Pinecone metadata: q_weak, method, lang, year, v_conf

V2 warehouse referans gerekirse: `~/Desktop/Papermind_V2/` (read-only, sadece veri-anlamı için).

---

## ROL

Konu (discovery-2) kilitlendikten sonra kullanıcının **alanına dair niceliksel panorama** sayfası. "Bu konuda kim çalışıyor, ne zaman, hangi dergide, hangi dilde, ne kadar ses getirmiş?" sorusunu görselleyen meta-istatistik dashboard'u. **Sentez yok, hipotez yok** — sadece havuz dağılımları. Discovery-4 tematik harita semantik yakınlığı, discovery-5 kavram ağı ilişkilendirmeyi gösterir; discovery-3 **niceliksel envanter** rolünü üstlenir.

**Rakip referansları:** Bibliometrix R paketi (yıl, lotka, h-index, KH dağılımları), VOSviewer (yazar/dergi co-occurrence), Connected Papers (graph). Discovery-3 = "hızlı Bibliometrix snapshot, web'de gömülü."

---

## PİLOT?

**HAYIR — pilot scope dışı.** Discovery-1/2 ile aynı F9+ grubu. Backend tamamen yeni; en yüksek implementation maliyeti olan discovery sayfası (yeni endpoint + service + 1-2 yeni warehouse query + ~600 LOC frontend).

---

## BAĞIMLILIK

- **Giriş:**
  - discovery-2'den topic lock sonrası (`topic_paper_id` projede kilitli)
  - Sidebar "Bibliyometrik Analiz" tıklaması
- **Çıkış:**
  - Yok — terminal sayfa (kullanıcı bir sonrakine sidebar'dan geçer; CTA yok)
  - Opsiyonel: "İlgili çalışmalar" kart → curation-2 ConnectedPapers
- **Backend bağımlılığı:** Yeni endpoint `GET /api/project/{id}/bibliometric/summary` ([KARAR]) + service + warehouse query.

---

## SAYFA YAPISI (ASCII)

```
┌──────────────────────────────────────────────────────────────────────┐
│ [Atölye · Keşif] › Bibliyometrik Analiz       [Pro · havuz N=240]    │
├──────────────────────────────────────────────────────────────────────┤
│ [AdvisorBanner] "Konuyla ilgili 240 makalenin nicel panoramasını    │
│  çıkardım — yıl, dil, dergi, yazarlar, atıf dağılımı."               │
├──────────────────────────────────────────────────────────────────────┤
│  ┌─── KARTLAR (top metrik özetler, 4 kolon grid) ─────────────────┐  │
│  │ Toplam   │ Medyan   │ Ortalama  │ En çok atıflanan              │ │
│  │ N=240    │ Yıl=2021 │ Atıf=42   │ "Title…" (847 atıf)          │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│  ┌─── YIL DAĞILIMI (line/bar chart) ────────────────────────────────┐ │
│  │ ▁▁▂▂▃▄▅▆▇█▆▄▃ (2010..2025)                                       │ │
│  │ Tepe: 2022 (38 paper) | Spike: 2023 ESG dalgası                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│  ┌── DİL DAĞILIMI ───┐ ┌── ATIF DAĞILIMI (Lotka style log-log) ────┐ │
│  │ EN  68%           │ │ ▆                                          │ │
│  │ TR  21%           │ │  ▆▄▃▂▁▁                                    │ │
│  │ ID   8%           │ │ x: atıf bin · y: paper sayısı              │ │
│  │ Diğer 3%          │ │ p80: atıf >100 sadece %3                  │ │
│  └───────────────────┘ └────────────────────────────────────────────┘ │
│  ┌── TOP-10 YAZAR (yatay bar) ─┐ ┌── TOP-10 DERGİ (yatay bar) ────┐  │
│  │ Liu, Y.       █████ 18 paper│ │ Expert Systems   █████ 22      │  │
│  │ Park, S.      ████  14      │ │ Omega            ████  18      │  │
│  │ Yıldız, A.    ███   11      │ │ Eur J Oper Res   ███   15      │  │
│  │ ...                          │ │ ...                             │  │
│  └──────────────────────────────┘ └────────────────────────────────┘  │
│  ┌── COĞRAFYA (chip cloud opsiyonel) ───────────────────────────────┐ │
│  │ TR · 32  US · 28  CN · 21  IR · 14  IN · 12  DE · 9  ...         │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## BOŞLUK

- **Tüm sayfa.** Ne frontend ne backend var.
- Warehouse'da yazar/dergi/coğrafya kolonu var mı bilinmiyor (V2 warehouse audit gerek)
- Atıf dağılımı `fact_paper_id_card.citations` üzerinden hesaplanabilir; yıl `year` kolonu var
- Dil `lang` kolonu Pinecone metadata'da var (B-012 patch sonrası)
- "Havuz" tanımı: discovery-1 anchor cluster_expander çıktısı mı, discovery-2 top-K paper mı, yoksa ayrı bibliometric expand mi? **[KARAR]** gerekli

---

## KARAR

**[KARAR]** Sayfa 5 görsel bloklu meta-istatistik dashboard:

1. **Top metrik kartlar (4-grid):** Toplam N · Medyan yıl · Ortalama atıf · En çok atıflanan paper (title link)
2. **Yıl dağılımı (line + bar mini chart):** 2010-2025 paper sayısı; mouse hover yıl detayı tooltip; Recharts veya d3 line
3. **Dil dağılımı (donut):** TR/EN/ID/diğer % paylar
4. **Atıf dağılımı (Lotka log-log):** y=paper sayısı, x=atıf bin (0-9, 10-49, 50-99, 100+); altta p80/p95 etiketleri
5. **Top-10 yazar + Top-10 dergi (yan yana yatay bar):** click → sadece o yazar/dergi paper'ları filter
6. **(Opsiyonel) Coğrafya chip cloud:** ülke kodu + count

**"Havuz" tanımı [KARAR]:** discovery-1'den anchor'ın **cluster_expander** çıktısı (P096 sonrası). Yani bibliyometrik analiz **proje merkez kümesi** üzerinde — discovery-2'nin top-5'inden değil. Sebep: top-5 niceliksel anlam taşımaz; cluster ~100-300 paper anlam taşır.

**Backend [KARAR]:** Tek endpoint `GET /api/project/{id}/bibliometric/summary` → büyük JSON response (5 blok birden). Cache `bibliometric:{project_id}` 24h TTL (cluster expand sonrası invalidate).

**Visualization library [KARAR]:** Recharts (Next.js + RSC uyumlu, mevcut shadcn ekosisteminde uyum). d3 sadece UMAP/Network'te (discovery-4/5).

---

## NASIL

### Frontend dosyalar

**Yeni:**

- `web/src/components/project/BibliometricSummaryPage.tsx` (~280 LOC) — 5 blok orchestrator
- `web/src/components/project/charts/YearDistributionChart.tsx` (~80 LOC) — Recharts line+bar
- `web/src/components/project/charts/LanguageDonut.tsx` (~60 LOC) — Recharts pie
- `web/src/components/project/charts/CitationLotkaChart.tsx` (~80 LOC) — Recharts log-log scatter
- `web/src/components/project/charts/TopBarList.tsx` (~70 LOC) — yatay bar (yazar+dergi reuse)
- `web/src/hooks/useBibliometric.ts` (~30 LOC) — `useQuery(["bibliometric", projectId])`

**Mevcut dosya revizyonu:**

- `web/src/app/(app)/project/[id]/[[...slug]]/page.tsx`:
  ```tsx
  case "discovery-3": return <PageShell><BibliometricSummaryPage projectId={id} /></PageShell>;
  ```
- `web/package.json` — `recharts` dependency ekle (yoksa)

### Backend (yeni)

**Yeni endpoint:** `GET /api/project/{project_id}/bibliometric/summary`

```python
class BibliometricSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    cluster_size: int                      # cluster_expander çıktı boyutu
    top_metrics: TopMetrics                # N, medyan_yil, ortalama_atif, max_atifli
    year_distribution: list[YearBin]       # [{year: 2010, count: 12}, ...]
    language_distribution: dict[str, int]  # {"en": 168, "tr": 50, "id": 18, ...}
    citation_lotka: list[CitationBin]      # [{bin: "0-9", count: 80}, ...]
    top_authors: list[TopItem]             # [{name, count}] x 10
    top_venues: list[TopItem]
    geography: dict[str, int] | None       # opsiyonel
    generated_at: datetime
```

**Service:** `api/services/bibliometric_service.py` (yeni)

1. Proje cluster paper_id listesini al (P096 cluster_expander çıktısı)
2. Supabase `fact_paper_id_card` üzerinde aggregate query: yıl GROUP BY, lang GROUP BY, atıf bin'leri
3. Yazar/dergi: `dim_author` + `dim_venue` JOIN (varsa) — yoksa paper.authors string'inden parse (kalitesiz, [KARAR])
4. Coğrafya: `dim_author.country` veya `paper.country` (varsa)
5. Redis cache: `bibliometric:{project_id}` 24h
6. Response build, return

**Warehouse audit önkoşulu:** `dim_author` + `dim_venue` tabloları gerçekten var mı? V2 warehouse'da hangi kolonlarla? Bu audit sprint başlamadan yapılır.

### Veri

- Cache: `bibliometric:{project_id}` 24h TTL Redis
- Migration gerek **yok** (varolan warehouse okuma)
- Audit gerekli: dim_author, dim_venue, paper.country kolon mevcudiyeti

---

## TIER DAVRANIŞI

**Anon:** Erişilemez.
**Pro:** Tüm bloklar aktif. Cluster size limiti yok (tek proje).
**Free:** YOK.

---

## AÇIK SORULAR

| # | Soru | Engellediği | Önerilen yön |
|---|---|---|---|
| **AS-1** | "Havuz" tanımı: cluster_expander mı top-5'in expand'i mi tüm anchor adayları mı? | Backend service + UX semantiği | **cluster_expander** (P096 çıktısı). Niceliksel anlam için ~100-300 paper gerek. `[KARAR]` |
| **AS-2** | dim_author / dim_venue / paper.country kolonu warehouse'da var mı? | Backend implementation | **Warehouse audit** sprint öncesi. Yoksa: yazar/dergi paper.authors/venue string parse (kalitesiz fallback). Coğrafya skip. `[KARAR]` |
| **AS-3** | Recharts vs d3 vs Tremor vs Visx? | Frontend dependency | **Recharts** — Next 16 RSC uyumlu, declarative, shadcn ile uyum. d3 discovery-4/5'te ağır görseller için zaten gelecek. `[KARAR]` |
| **AS-4** | Sayfa interaktivitesi (filter/drill-down) var mı? | Scope | **Hayır pilot post-MVP** — read-only dashboard. Top-10 yazar tıklamasıyla filter eklenebilir ama scope creep. Faz 2'de. `[KARAR]` |
| **AS-5** | Coğrafya chip cloud dahil mi? | Veri ihtiyacı | **Opsiyonel** — paper.country yoksa skip; varsa chip cloud (chart yok). `[KARAR]` |
| **AS-6** | "Top metrik kartlar" yerine compass/spider chart mı? | UX | **Hayır — kart** (4-grid). Spider 5+ axis'te işe yarar; 4 metrik için kart hızlı + kanonik. `[KARAR]` |

---

## TEST KAPSAMI

**Backend (yeni):**
- `tests/unit/test_bibliometric_service.py` — yıl bin, lang dist, lotka bin sayma, top-N truncate
- `tests/integration/test_bibliometric_endpoint.py` — happy path (cluster N=200), cache hit, 404 cluster yok, 401 auth
- Smoke fixture: `tests/fixtures/bibliometric_v1.json` (live cluster bir test projesi üzerinde sabitlenir)

**Frontend (yeni — Vitest):**
- `BibliometricSummaryPage.test.tsx` — 5 blok render, loading skeleton, error state
- `YearDistributionChart.test.tsx` — Recharts mount, data binding
- `LanguageDonut.test.tsx`, `CitationLotkaChart.test.tsx`, `TopBarList.test.tsx`
- `useBibliometric.test.ts` — mock 200 büyük response

---

## BU SAYFA İÇİN KARARA BAĞLANACAK DM

- **DM-XXX** Havuz tanımı: cluster_expander çıktısı (AS-1)
- **DM-XXX** Recharts dependency adoption + chart library policy
- **DM-XXX** Warehouse audit sonucu: dim_author/dim_venue varlığı
- **DM-XXX** Bibliometric endpoint sözleşmesi (BibliometricSummary schema)
- **DM-XXX** Geography/coğrafya scope kararı (opsiyonel/skip)
- **DM-XXX** Sayfa interaktivite scope (read-only pilot vs filter F2+)
