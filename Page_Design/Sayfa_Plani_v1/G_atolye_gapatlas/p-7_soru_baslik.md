# p-7 · Soru & Başlık (GapAtlas)

> Tezgah: **GapAtlas · işaretler** (3.x)
> 3 mod RQ + 3 başlık adayı + özgünlük 3-API mührü + atıf projeksiyonu bandı.

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:1520-1587`
- **Sidebar:** `PaperMind_mock_v1.0.html:617`
- **Bu md:** `Page_Design/Sayfa_Plani_v1/G_atolye_gapatlas/p-7_soru_baslik.md`

## ROL
İşaretli boşluktan **3 stilde RQ** üret: temkinli (YL), dengeli (PhD), iddialı (deneyimli). Kullanıcı seçer → 3 başlık adayı + özgünlük denetimi (OpenAlex + Semantic Scholar + Pinecone semantic). 230-keyword title profile ile atıf-potansiyeli bandı [alt, üst]. Çıktı **araştırma paketi** → Authoring'e taşınır.

## BACKEND ❌ YOK (RQ + başlık endpoint hiç yok)

### Mock iddiası
- `POST /api/gapatlas/rq-title`
- LLM RQ + hipotez + matris-özgü başlık şablonu
- 3 bağımsız özgünlük denetimi: OpenAlex + Semantic Scholar + Pinecone
- 230-keyword title profile (`title_keyword_profile` data?)

### Mevcut yakın (ama bu sayfa için değil)
- `GET /api/gap-profile?method_id=&topic_id=` → `api/routes/gap_profile.py:90-150` — **tek hücre detay** endpoint (p-6 cell-detail için kullanılır, RQ üretmez)
- 6 segment dönüyor: `gap_value, depth_norm, neighbor, e_value, feasibility, publishability` (`gap_profile.py:117-124`)
- `fact_theme_year_aggregates` year trend join (`gap_profile.py:65-73`)
- ⚠ matrix_id hardcoded "M1" (`gap_profile.py:55`)

> ⚠ `gap_profile.py` p-7'nin değil, p-6'nın hücre-detay panelinin backend'i (DKEFY breakdown'ı için bkz. p-6 §AÇIK SORULAR #4)

## DB ❌ büyük çoğunluk yok
- `fact_gap_matrix` — mevcut (gap_value+breakdown)
- `fact_theme_year_aggregates` — mevcut (`gap_profile.py:68`)
- `dim_theme` — mevcut
- ❌ `golden_gap` — yok
- ❌ `research_question` — yok
- ❌ `title_proposal` — yok
- ❌ `title_keyword_profile` (230-keyword) — yok

---

## ÖNERİ: Eksik Backend Tasarımı

### 1. `0019_research_question.sql` (yeni migration)

```sql
-- golden_gap — p-6'da işaretlenen sweet spot hücreler
CREATE TABLE public.golden_gap (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id    uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  matrix_id     text NOT NULL CHECK (matrix_id ~ '^M[1-8]$'),
  axis_x        text NOT NULL,  -- topic_id
  axis_y        text NOT NULL,  -- method_id
  gap_value     numeric NOT NULL,
  marked_at     timestamptz NOT NULL DEFAULT now(),
  status        text NOT NULL DEFAULT 'marked'
                CHECK (status IN ('marked','rq_generated','authoring','archived')),
  UNIQUE (project_id, matrix_id, axis_x, axis_y)
);

-- research_question — 3-mod RQ paketi
CREATE TABLE public.research_question (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  golden_gap_id uuid NOT NULL REFERENCES public.golden_gap(id) ON DELETE CASCADE,
  mode          text NOT NULL CHECK (mode IN ('temkinli','dengeli','iddiali')),
  rq_text       text NOT NULL CHECK (char_length(rq_text) BETWEEN 20 AND 600),
  hypothesis    text,
  feasibility   text  CHECK (feasibility IN ('🟢','🟡','🔴')),
  risk          text  CHECK (risk IN ('🟢','🟡','🔴')),
  effect_band   text  CHECK (effect_band IN ('düşük','orta','orta-yüksek','yüksek')),
  is_recommended boolean NOT NULL DEFAULT false,
  generated_at  timestamptz NOT NULL DEFAULT now(),
  llm_model     text NOT NULL,
  faithfulness_pass boolean NOT NULL DEFAULT false  -- citations ⊆ pool
);

-- title_proposal — 3 başlık adayı
CREATE TABLE public.title_proposal (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  research_question_id  uuid NOT NULL REFERENCES public.research_question(id) ON DELETE CASCADE,
  title                 text NOT NULL CHECK (char_length(title) BETWEEN 10 AND 250),
  -- Özgünlük 3-API mührü
  openalex_seal         text CHECK (openalex_seal IN ('🟢','🟡','🔴')),
  openalex_match_count  int,
  s2_seal               text CHECK (s2_seal IN ('🟢','🟡','🔴')),
  s2_max_sim            real,
  pinecone_seal         text CHECK (pinecone_seal IN ('🟢','🟡','🔴')),
  pinecone_max_sim      real,
  pinecone_neighbor_id  text,  -- en yakın paper_id
  -- Atıf projeksiyonu
  citation_lower        int,
  citation_median       int,
  citation_upper        int,
  keyword_profile_score real,  -- 230-keyword title profile cosine
  generated_at          timestamptz NOT NULL DEFAULT now()
);

-- title_keyword_profile — 230-keyword referans (yıllık güncel)
CREATE TABLE public.title_keyword_profile (
  keyword       text PRIMARY KEY,
  weight        real NOT NULL,  -- citation-velocity weighted
  last_seen_year int NOT NULL
);
```

### 2. Yeni endpoint'ler

#### `POST /api/gapatlas/mark-gap` (p-6 → p-7 köprü)
- **In:** `{project_id, matrix_id, axis_x, axis_y, gap_value}`
- **Out:** `golden_gap` row
- Idempotent: UNIQUE constraint (project_id, matrix, x, y)

#### `POST /api/gapatlas/rq-title`
- **In:** `{golden_gap_id, modes:["temkinli","dengeli","iddiali"], generate_titles:true}`
- **Out:**
  ```json
  {
    "research_questions": [
      {"id":"...", "mode":"temkinli", "rq_text":"...", "hypothesis":"...",
       "feasibility":"🟢", "risk":"🟢", "effect_band":"düşük"},
      ...3 entry
    ],
    "recommended_mode": "dengeli",
    "title_proposals": [
      {"title":"...", "openalex_seal":"🟢", "s2_seal":"🟢",
       "pinecone_seal":"🟡", "pinecone_max_sim":0.81, "pinecone_neighbor_id":"P-019",
       "citation_lower":34, "citation_median":58, "citation_upper":87,
       "keyword_profile_score":0.62},
      ...3 entry
    ]
  }
  ```
- **Flow:**
  1. `golden_gap` + matris-özgü template fetch (M1=Konu×Yöntem template, M3=Yöntem×Örneklem, ...)
  2. **LLM call (Gemini Flash 2.0):** prompt içinde proje pool top-12 paper özet + işaretli hücre tarif → 3 mod RQ + hipotez üret
  3. **Recommended seçimi:** RQ'lar arası feasibility+risk+effect ağırlıklı skor → en yüksek olan ✓
  4. **Başlık şablonu:** her RQ için matris başlık template'inden 3 varyasyon
  5. **Özgünlük denetimi (paralel 3 API çağrı):**
     - **OpenAlex:** `/works?search=<title>&per-page=5` → exact match count
     - **Semantic Scholar:** `/graph/v1/paper/search?query=<title>&limit=5` → cosine sim
     - **Pinecone:** title embedding (text-embedding-3-small veya bge) → top-1 in `papers` index
  6. **Mühür kuralı:** count==0 ve sim<0.7 → 🟢; sim ∈ [0.7, 0.85) → 🟡; sim≥0.85 veya count>0 → 🔴
  7. **Atıf projeksiyonu:** title cosine × `title_keyword_profile` → 5-yıl atıf [P10, P50, P90] OpenAlex aggregate
  8. **Faithfulness gate (Pydantic):** RQ içindeki her paper_id citation `golden_gap.project_id` pool'una dahil mi?

#### `POST /api/gapatlas/research-package-finalize`
- **In:** `{research_question_id, title_proposal_id}` (kullanıcı seçimi)
- **Out:** Authoring'e geçişe hazır paket
- DB: `golden_gap.status = 'authoring'`, push URL `/p-8?package_id=`

### 3. Cache stratejisi
- `rq-title:{golden_gap_id}:{model_hash}` → TTL 30g (LLM expensive, gap stable)
- `originality:{title_hash}` → TTL 7g (API rate limit)
- `keyword_profile:current` → TTL 24h (yıllık güncel ama stabil)

---

## SAYFA YAPISI (ASCII)

```
┌── 7 · Soru & Başlık ── 3 mod RQ + özgünlük 3 API ─────────────────────┐
│ Felsefe: boşluktan araştırma sorusuna ve başlığa.                     │
│                                                                        │
│ 3 mod öneri (temkinli/dengeli/iddialı), 3 başlık adayı,               │
│ özgünlük 3 API mührü, 230-keyword atıf bandı.                         │
│                                                                        │
│ ┌── Simülasyon · 3-mod RQ + başlık (M3[3,8] altın) ────────────────┐ │
│ │  D ✓ ─ C ✓ ─ G ● ─ A ─ S                                          │ │
│ │                                                                    │ │
│ │  ┌── RQ · TEMKİNLİ (YL) ─────────────────────────────────────┐    │ │
│ │  │ "Pasif sensör verisi kullanılarak ergenlerde akşam ekran │    │ │
│ │  │  maruziyetinin uyku başlangıç süresine etkisi nasıl      │    │ │
│ │  │  değişir?"                                                │    │ │
│ │  │  uygulanabilirlik 🟢 · risk 🟢 · etki düşük              │    │ │
│ │  └───────────────────────────────────────────────────────────┘    │ │
│ │  ┌── RQ · DENGELİ (PhD) · ÖNERİLEN ✓ ───────────────────────┐    │ │
│ │  │ "RI-CLPM çerçevesinde, pasif sensörle ölçülen akşam      │    │ │
│ │  │  ekran maruziyeti, ergenlerde uyku gecikmesini           │    │ │
│ │  │  özbildirim ölçümlerinden farklı bir şekilde mi öngörür?"│    │ │
│ │  │  uygulanabilirlik 🟢 · risk 🟡 örneklem · etki orta-yüksek│   │ │
│ │  └───────────────────────────────────────────────────────────┘    │ │
│ │  ┌── RQ · İDDİALI ─────────────────────────────────────────┐     │ │
│ │  │ "Pasif sensör tabanlı RI-CLPM, ekran-uyku ilişkisinin   │     │ │
│ │  │  nedensel yönünü, mevcut özbildirim çalışmalarının      │     │ │
│ │  │  raporladığı yönü tersine çevirir mi?"                  │     │ │
│ │  │  uygulanabilirlik 🟡 · risk 🔴 reddi yüksek · etki yüksek│    │ │
│ │  └─────────────────────────────────────────────────────────┘     │ │
│ │                                                                    │ │
│ │  3 başlık adayı · özgünlük denetimi                               │ │
│ │  ┌──────────────────────────────────────────────────────────┐     │ │
│ │  │ "Passive screen exposure and sleep onset in adolescents: │     │ │
│ │  │  an RI-CLPM design"                                      │     │ │
│ │  │  OpenAlex 🟢 0 · S2 🟢 0 · Pinecone 🟡 sim 0.81 (P-019) │     │ │
│ │  │  Atıf projeksiyonu (5 yıl)  ▓▓▓▓▓▓░░░░  62%             │     │ │
│ │  │  [34, 87] medyan 58 · 230-keyword profile               │     │ │
│ │  └──────────────────────────────────────────────────────────┘     │ │
│ │  ┌──────────────────────────────────────────────────────────┐     │ │
│ │  │ "RI-CLPM evidence for actigraphy-measured screen time    │     │ │
│ │  │  on teen sleep latency"                                  │     │ │
│ │  │  OpenAlex 🟢 · S2 🟢 · Pinecone 🟢 sim 0.74              │     │ │
│ │  │  ▓▓▓▓▓░░░░░  54% · [28, 71] medyan 47                   │     │ │
│ │  └──────────────────────────────────────────────────────────┘     │ │
│ │  ┌──────────────────────────────────────────────────────────┐     │ │
│ │  │ "Reverse causality reconsidered: passive sensors..."     │     │ │
│ │  │  OpenAlex 🔴 1 · S2 🟡 sim 0.78 · Pinecone 🔴 sim 0.91   │     │ │
│ │  │  ⚠ Benzer başlık var (2023, sim 0.91) — yeniden yaz     │     │ │
│ │  └──────────────────────────────────────────────────────────┘     │ │
│ │                                                                    │ │
│ │  [ Araştırma paketini Authoring'e taşı → ]                        │ │
│ └────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **3 RQ kartı:** beyaz arka, içlerinde italik metin + 3 sinyal (uygulanabilirlik 🟢🟡🔴 / risk / etki bandı). **Önerilen** olan gapatlas yeşil border + ✓
- **3 başlık kartı:** title + 3 mühür chip (OpenAlex/S2/Pinecone) + atıf bar + [alt, üst] aralık + medyan
- **Özgünlük çakışması:** 🔴 ise altta uyarı kutusu kırmızı + "yeniden yaz öner"
- **CTA:** "Araştırma paketini Authoring'e taşı →" (gapatlas yeşil, full-width)
- **Funnel:** D ✓ · C ✓ · G ● · A · S

### Back
- LLM (Gemini Flash 2.0): RQ + hipotez (3 mod paralel)
- 3-API paralel `asyncio.gather`: OpenAlex search · S2 search · Pinecone vector
- 230-keyword profile cosine → atıf projeksiyonu band
- Faithfulness gate: Pydantic validator `citations ⊆ project_pool.paper_ids`

### Veri akışı
1. p-6 "★ İşaretle" → `POST /api/gapatlas/mark-gap` → `golden_gap` row → push `/p-7?gap_id=`
2. Mount → `POST /api/gapatlas/rq-title` (1 çağrı, 3 RQ + 3 başlık dön)
3. Render: 3 RQ kartı + önerilen highlight + 3 başlık kartı + mühür rozeti
4. Kullanıcı seçer (1 RQ + 1 başlık) → "Authoring'e taşı" → `POST /api/gapatlas/research-package-finalize` → push `/p-8?package_id=`

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon:** kapalı
- **Öğrenci:** RQ üretimi günde 5 çağrı (LLM-pahalı)
- **Araştırmacı:** günde 50 çağrı
- **Profesyonel:** sınırsız + Gemini 2.5 Pro (özgünlük tahmini daha hassas)
- **Cache:** golden_gap stable → 30g cache (yeniden çağrı tekrar maliyet doğurmaz)

---

## AÇIK SORULAR
1. **Faithfulness gate Q1 deseni:** RQ içinde paper_id citation gerekli mi yoksa free-text mi? Mock'ta inline citation görünmüyor; gate uygulamak için karar gerek.
2. **Matris-özgü başlık şablonu** ne? Her M1-M8 için template kütüphanesi yazılacak — repo'da yok.
3. **230-keyword title profile** veri kaynağı: ne sıklıkla güncellenir? Pipeline?
4. **Özgünlük 3-API maliyet:** Pinecone embedding pahalı (text-embedding-3-small $0.02/M token). Cache hit ratio kritik.
5. **OpenAlex rate limit:** 100k/gün ücretsiz → batch dikkatli olmalı.
6. **`golden_gap` ↔ `gap_signal` ayrımı:** p-6'daki not'tan farklı mı? Karar.
7. **Başlık L10n:** mock'ta İngilizce başlık + TR RQ. Vitrin Q1 sorgu dilinde dönüyordu — atölyede karışık mı?
8. **Başlık L=10-250 char limit** kararı (B-NNN)?
9. **`research_question.is_recommended` tek satır mı row'larda flag mi?** Tek `recommended_mode` enum + 3 row → daha temiz.

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar GapAtlas p-7 | `PaperMind_mock_v1.0.html` | 617 |
| 2 | p-7 page block | `PaperMind_mock_v1.0.html` | 1520-1587 |
| 3 | techspec back/front/data | `PaperMind_mock_v1.0.html` | 1526-1532 |
| 4 | 3-mod RQ kartı | `PaperMind_mock_v1.0.html` | 1544-1558 |
| 5 | 3 başlık + özgünlük + atıf | `PaperMind_mock_v1.0.html` | 1561-1582 |
| 6 | Authoring'e taşı CTA | `PaperMind_mock_v1.0.html` | 1584 |
| 7 | gap_profile.py (p-6 cell-detail, p-7 değil) | `api/routes/gap_profile.py` | 90-150 |
| 8 | matrix_id "M1" hardcoded | `api/routes/gap_profile.py` | 55 |
| 9 | 6 segment (DKEFY breakdown) | `api/routes/gap_profile.py` | 117-124 |
| 10 | `fact_theme_year_aggregates` | `api/routes/gap_profile.py` | 65-73 |
| 11 | `dim_theme` label | `api/routes/gap_profile.py` | 77-87 |
| 12 | Q1/Q3 faithfulness gate canon | `Page_Design/Sayfa_Plani_v1/_envanter_felsefe.md` | §11 |
