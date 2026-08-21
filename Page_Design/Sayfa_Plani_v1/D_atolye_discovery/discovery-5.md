# Discovery-5 — Kavram Ağı (ARM N08 lift & confidence: kavram-yöntem ilişkileri)

> **Çift mock paradoksu (discovery-4 paterni):** Wired hard-coded versiyon (`ConceptNetworkPage` 20-NODE TOPSIS örneği) + Unwired gerçek versiyon (`NetworkMapCard` ARM N08 lift+confidence). Karar: **NetworkMapCard kazanır, ConceptNetworkPage demote edilir.**
> **Halüsinasyon yasağı:** wired mock backend yok — TÜM veri komponent içinde sabit (TOPSIS, AHP, MCDM... 20 node + 29 edge örneği).

---

## KONUM

- **Route:** `/project/{id}/discovery-5`
- **Frontend (wired, KALDIRILACAK):** `web/src/components/project/ConceptNetworkPage.tsx` (349 satır) `[REPO]`
  - Switch case mevcut: `case "discovery-5": return <PageShell><ConceptNetworkPage /></PageShell>;`
  - 20 NODE + 29 EDGE **hard-coded**, backend yok
- **Frontend (unwired, KANON OLACAK):** `web/src/components/project/NetworkMapCard.tsx` (773+ satır) `[REPO]`
  - `zone="discovery"`, title "Terim ag haritasi — Birlikte gecis", subtitle "ARM (Association Rule Mining) ile cikarilmis yontem x konu iliskileri", sourceBadge "ARM N08 — lift & confidence"
- **Backend:** YOK — ARM N08 endpoint yok `[REPO]`
- **İlişkili:** N08 = signals_13 anahtarlarından biri (B42-... ARM kanonu)

---

## MEVCUT

**Frontend WIRED (ConceptNetworkPage 349 satır) — demonstrasyon mock:**

- 20 NODE: TOPSIS, AHP, MCDM, Fuzzy, VIKOR, ELECTRE, PROMETHEE, BWM, Entropy, CRITIC, DEA, ML, Regression, SEM, Factor, Sustainability, ESG, Supply, Risk, Education
- 4 cluster: 0 (MCDM çekirdek), 1 (Ağırlık metodları), 2 (İstatistik/ML), 3 (Uygulama alanları)
- 29 EDGE: lift 1.2-3.1, confidence 0.28-0.85 hard-coded
- SVG edge layer (lift→strokeWidth, confidence→stroke-opacity), absolute-positioned node div'leri (cluster color background)
- Hover: connected node highlight + edge highlight (E8A157 amber)
- Click: selectedNode + sağ panel "Bağlı terimler Top 5" lift/conf liste
- Min lift slider 1.0-3.0
- Etiket toggle (Eye/EyeOff icon)
- Küme dropdown — **handler yok, filter etmiyor**
- DataVizCard `badge="ARM N08 — lift & confidence"` — **yanıltıcı**, gerçek N08 yok

**Frontend UNWIRED (NetworkMapCard 773+ satır) — gerçek tasarım:**

- d3 force simulation (muhtemelen — d3 import + ZONE_CONFIG mevcut)
- DataVizCardFrame ortak kabuk (d24-d29 paterni)
- ZoneId tipi: `discovery | curation | gapatlas | authoring | defense` — sayfa zone'a uygun atribüsyon
- "ARM (Association Rule Mining) ile cikarilmis" — gerçek warehouse veri kaynağı
- sourceBadge "ARM N08 — lift & confidence" — N08 fact tablosu

**Backend:** YOK. Wired mock backend hiç çağırmıyor, NetworkMapCard mock veri gömülü olabilir (henüz tam okunmadı).

---

## ROL

Tematik harita (discovery-4) konunun semantik konumunu gösterir; **kavram ağı** ise **kavramlar arası ilişkilendirmeyi** gösterir. ARM N08: havuzdaki paper'larda hangi terim çiftleri sıkça birlikte geçer (lift > 1 = anlamlı birliktelik, confidence = koşullu olasılık). Insight: "Senin konun TOPSIS — ama TOPSIS+Fuzzy ve TOPSIS+Sustainability güçlü birliktelikler; bunları araştırmaya değer." Discovery-4 (semantik yakınlık) tamamlayıcı; discovery-5 (kavram birlikteliği) farklı sinyal.

---

## PİLOT?

**HAYIR — pilot scope dışı.** Discovery-4 ile aynı F9+ frontend grubu. ARM N08 backend offline batch gerekir.

---

## BAĞIMLILIK

- **Giriş:** discovery-4 sonrası (sıralı sidebar) veya direkt sidebar tıklama
- **Çıkış:** Yok — terminal sayfa
- **Backend bağımlılığı:**
  - **Yeni endpoint** `GET /api/project/{id}/concept-network` — proje cluster'ı için ARM N08 lift+confidence çıkarımı
  - **Warehouse pre-computation** — fact_term_arm_n08 tablosu (offline batch ARM mining)
  - Term extraction sözlüğü — `dim_term` (varsa) veya text mining

---

## SAYFA YAPISI (ASCII — NetworkMapCard'a göre)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [Atölye · Keşif] › Kavram Ağı                  [Pro · 124 terim, 408 bağ]│
├──────────────────────────────────────────────────────────────────────────┤
│ [DataVizCardFrame zone=discovery]                                        │
│  Title: Terim ağ haritası — Birlikte geçiş                               │
│  Subtitle: ARM ile çıkarılmış yöntem × konu ilişkileri                   │
│  sourceBadge: ARM N08 — lift & confidence                                │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌── ANA CANVAS d3 force ─────────────────────┐ ┌── SAĞ PANEL (280px) ─┐ │
│  │                                             │ │ Seçili: TOPSIS      │ │
│  │      ●AHP                                   │ │ Cluster: MCDM       │ │
│  │   ●MCDM ─── ●TOPSIS ─── ●Fuzzy             │ │ Frekans: 184        │ │
│  │      │       │                              │ │                     │ │
│  │      └─ ●VIKOR ─── ●ELECTRE                │ │ Bağlı terimler T5:  │ │
│  │                                             │ │ ● Fuzzy lift 2.5    │ │
│  │   ●Sustainability ─── ●ESG ─── ●Risk       │ │ ● MCDM   lift 3.1   │ │
│  │       │                          │          │ │ ● AHP    lift 2.8   │ │
│  │       └────● Supply ────●Education          │ │ ● VIKOR  lift 2.5   │ │
│  │                                             │ │ ● ESG    lift 1.7   │ │
│  └─────────────────────────────────────────────┘ └─────────────────────┘ │
│  Controls:                                                               │
│  Min lift: [▬▬▬●─] 1.0   ☑ Etiketler   Küme: [Tüm kümeler ▾]            │
│  [Reset zoom] [Konuna fokus]                                             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## BOŞLUK

- **Wired mock hard-coded** — TOPSIS örneği herkesin projesinde aynı; gerçek terimler yok
- **Backend yok** — ARM N08 endpoint, term extraction, cluster mining yok
- **NetworkMapCard 773 LOC orphan** — yeniden yazma israf olur
- **Küme dropdown filter handler yok** (mevcut wired mock'ta da yok)
- **N08 = signals_13 anahtarı** ama warehouse'da `fact_term_arm` tablosu var mı **doğrulanmamış** — V2 audit gerek

---

## KARAR

**[KARAR]** discovery-4 paterniyle aynı çözüm:

1. **`ConceptNetworkPage.tsx` SİL** — hard-coded TOPSIS örneği kanon değil (her projede aynı = yanıltıcı).
2. **`NetworkMapCard.tsx` ADOPT** — `web/src/components/project/ConceptNetworkPageV2.tsx` veya benzer'e taşınır + projectId prop + useQuery veri kaynağı.
3. **Switch case güncellenir:** `case "discovery-5": return <PageShell><ConceptNetworkPageV2 projectId={id} /></PageShell>;`
4. **Backend yeni:** `GET /api/project/{id}/concept-network` → ARM N08 lift+confidence + nodes + edges
5. **Warehouse offline batch:** ARM mining (apriori veya FP-growth) cluster paper'ları üzerinde — terim extraction (TF-IDF + n-gram + filter stopwords) → ARM (min_support=0.05, min_confidence=0.3) → fact_term_arm_n08 tablosu.

**Term extraction kaynağı [KARAR]:** Title + abstract noun phrases (spaCy + custom domain dict). Pre-existing `signals_13` N08 hesabında zaten yapılmış olabilir — V2 warehouse audit önkoşulu.

**Filter scope [KARAR]:** ARM N08 sadece **proje cluster'ı** üzerinde rerun olur (havuz çok büyük; cluster ~100-300 paper anlamlı ARM süresi). Cache 24h proje başına.

**Edge görünüm [KARAR]:** lift → stroke-width (1-4 px linear), confidence → stroke-opacity (0.2-0.9 linear). Bu mevcut wired mock paterniyle uyumlu (KARAR netliği için tekrarlandı).

---

## NASIL

### Frontend dosyalar

**Sil:**
- `web/src/components/project/ConceptNetworkPage.tsx` (hard-coded TOPSIS örneği — kanon değil)

**Adopt + revize:**
- `web/src/components/project/NetworkMapCard.tsx` → `ConceptNetworkPageV2.tsx` rename + projectId prop + useQuery + d3 force layout (mevcut)

**Yeni:**
- `web/src/hooks/useConceptNetwork.ts` (~40 LOC) — `useQuery(["concept-network", projectId])`, staleTime 1h

**Mevcut dosya revizyonu:**
- `web/src/app/(app)/project/[id]/[[...slug]]/page.tsx` — switch case güncelleme

### Backend (yeni)

**Yeni endpoint:** `GET /api/project/{project_id}/concept-network`

```python
class ConceptNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    term_id: str            # normalized lowercase, ASCII, dash-joined
    label: str              # display: "TOPSIS", "Fuzzy AHP"
    cluster_id: int         # ARM-derived community (Louvain veya HDBSCAN over edge graph)
    frequency: int          # cluster paper'larda toplam geçiş

class ConceptEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str             # term_id
    target: str
    lift: float = Field(ge=0.0)
    confidence: float = Field(ge=0.0, le=1.0)

class ConceptNetworkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    nodes: list[ConceptNode]
    edges: list[ConceptEdge]
    user_term_id: str | None    # topic paper'dan extract edilen primary term
    generated_at: datetime
```

**Service:** `api/services/concept_network_service.py` (yeni)

1. Cluster paper_id listesini al (P096 cluster_expander)
2. fact_term_arm_n08 tablodan paper_id IN (cluster) ile filter (eğer pre-computed varsa) VEYA on-demand ARM rerun (cluster küçükse <500 paper)
3. Edge'leri lift desc sırala, top-N (default 200) — UI overload önler
4. Cluster_id atama: Louvain community detection edge graph üzerinde
5. user_term_id: topic paper title+abstract → primary noun phrase (Gemini Flash mini-call veya frequency-based)
6. Cache: `concept-net:{project_id}` 24h
7. Response build, return

### Veri (yeni warehouse + offline batch)

**Migration `0022_fact_term_arm_n08.sql`:**

```sql
create table fact_term_arm_n08 (
  cluster_id int not null,         -- proje cluster_id veya global cluster
  term_a text not null,
  term_b text not null,
  lift real not null,
  confidence real not null,
  support real not null,
  computed_at timestamptz not null default now(),
  primary key (cluster_id, term_a, term_b)
);
create index idx_n08_cluster on fact_term_arm_n08 (cluster_id);
create index idx_n08_lift on fact_term_arm_n08 (lift desc);
```

**Migration `0023_dim_term.sql`:**

```sql
create table dim_term (
  term_id text primary key,        -- normalized lowercase
  label text not null,             -- display
  category text,                   -- method | concept | application | other
  frequency_global int not null
);
```

**Offline batch (Colab Pro+):**
1. Cluster paper'lardan title+abstract → spaCy noun phrase extraction → `dim_term` populate
2. ARM apriori (mlxtend veya efficient-apriori) cluster paper'ları üzerinde, min_support=0.05, min_confidence=0.3
3. Top-200 edge per cluster bulk upload `fact_term_arm_n08`
4. Sprint başında 1 kez global N08; sonra incremental sadece yeni cluster'lar için (~5-10 dk her proje sonrası)

---

## TIER DAVRANIŞI

**Anon:** Erişilemez.
**Pro:** Tüm özellikler. Lift/confidence eşik default sabit.
**Free:** YOK.

---

## AÇIK SORULAR

| # | Soru | Engellediği | Önerilen yön |
|---|---|---|---|
| **AS-1** | NetworkMapCard rename + adopt mı sıfırdan mı? | Frontend implementation | **Rename + adopt** — discovery-4 paterniyle aynı; 773 LOC d3 force büyük yatırım. `[KARAR]` |
| **AS-2** | ARM rerun on-demand mı offline batch mi? | Backend perf | **Hibrit:** global N08 (24.87M) ağır → offline. Proje cluster'ı küçük (<500 paper) → on-demand ARM (~5-10s). `[KARAR]` |
| **AS-3** | Term extraction yöntemi (spaCy / KeyBERT / TF-IDF)? | Backend implementation | **spaCy noun phrase + custom domain dict** — pre-existing N08 pattern (varsa). KeyBERT alternatif daha kaliteli ama yavaş. `[KARAR]` |
| **AS-4** | Cluster atama (edge graph community)? | Backend implementation | **Louvain** — networkx implement, hızlı, kanonik. `[KARAR]` |
| **AS-5** | Min lift/confidence default eşik? | UX | lift ≥ 1.5, confidence ≥ 0.4 default. UI'da slider ile ayarlanabilir. `[KARAR]` |
| **AS-6** | Edge sayı kapağı (top-N)? | UX overload | top-200 edge default. Daha fazlası canvas okunaksız. `[KARAR]` |
| **AS-7** | user_term_id (topic paper'dan primary term) yöntem? | UX | **Frequency-based** — topic paper title+abstract noun phrase'lerinden cluster'da en sık geçen ilk; LLM mini-call gerek yok. `[KARAR]` |

---

## TEST KAPSAMI

**Backend (yeni):**
- `tests/unit/test_concept_network_service.py` — top-N edge sort, cluster Louvain, user_term lookup, cache
- `tests/integration/test_concept_network_endpoint.py` — happy path, 404, cache hit, on-demand ARM trigger
- Smoke: `tests/fixtures/concept_network_v1.json`

**Frontend (yeni — Vitest):**
- `ConceptNetworkPageV2.test.tsx` — render, d3 force mount, hover/click, slider behavior
- `useConceptNetwork.test.ts` — mock 200/404
- Visual regression (Playwright F2+) — d3 force layout pixel diff

---

## BU SAYFA İÇİN KARARA BAĞLANACAK DM

- **DM-XXX** ConceptNetworkPage demote + NetworkMapCard adopt (çift mock çözümü, discovery-4 paterni)
- **DM-XXX** ARM N08 hibrit strateji (global offline + cluster on-demand)
- **DM-XXX** Warehouse 2 yeni tablo (fact_term_arm_n08 + dim_term)
- **DM-XXX** Term extraction yöntemi (spaCy noun phrase + domain dict)
- **DM-XXX** Cluster atama Louvain
- **DM-XXX** Default lift/confidence eşikleri ve top-N edge kapağı
