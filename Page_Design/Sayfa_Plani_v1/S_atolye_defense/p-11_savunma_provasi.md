# p-11 · Savunma Provası (Defense)

> Tezgah: **Defense · savunma** (5.x)
> Atıfsız iddia · zayıf iddia · **G1 ters-bakış** (boşluk hâlâ açık mı?) · 90g window.

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:1797-1852`
- **Sidebar:** `PaperMind_mock_v1.0.html:626`
- **Bu md:** `Page_Design/Sayfa_Plani_v1/S_atolye_defense/p-11_savunma_provasi.md`

## ROL
Yazılan metni kendi gözüyle okumak yetmez — **hakem gözü** gerekir. A1/A2'deki atıfsız iddia motoru burada **tüm metin düzeyinde panoramik** taranır. **G1 ters-bakış** ayırıcıdır: kullanıcı G1'de "şu RQ boşlukta" demişti, sistem 30g sonra Savunma'ya gelinen anda son 90g'da yayınlanmış paper'ları yeniden taraİr ve "**P-117 Şubat 2026'da yayınlandı, RQ'nun bir kısmını kapatmış olabilir**" der. Akademide gerçek bir risk (tez teslim edilirken aynı anda başkası yayınlar) — kimse otomatize etmiyor.

## BACKEND ❌ YOK
`api/routes/` listesinde `defense*` yok. Mock claims:
- `POST /api/defense/full-text-scan` (atıfsız + zayıf + makro uyarı)
- `GET /api/defense/gap-still-open?rq_id=` (G1 ters-bakış — `fact_paper_gap_v3` yeniden bakar)
- `POST /api/defense/argument-graph` (cümleler arası iddia zinciri)

## DB ❌ YOK
- `fact_user_defense_session` (savunma çıktısı snapshot) — yok
- `fact_paper_publication_recent` (90g window — boşluk kapanma kontrolü) — yok
- `fact_paper_gap_v3` mevcut mu? `db/migrations/` içinde `gap_v3` olarak adlandırılmış table henüz **yok** (mevcut M1/M7/M8 matrix'leri `fact_paper_gap` üzerinden çalışıyor — gap_heatmap.py).

---

## ÖNERİ: Eksik Backend

### `0023_defense_session.sql`

```sql
-- fact_user_defense_session — savunma snapshot (full-text scan + ters-bakış sonucu)
CREATE TABLE public.fact_user_defense_session (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  project_id      uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  authoring_session_id uuid REFERENCES public.fact_user_authoring_session(id),
  full_text       text NOT NULL,
  scan_results    jsonb NOT NULL,  -- {atifsiz:[...], zayif:[...], makro:[...]}
  gap_still_open  jsonb NOT NULL,  -- {rq_id, new_papers_90d:[...], partial_close:bool}
  argument_graph  jsonb,           -- {nodes:[cumle_idx], edges:[(i,j,relation)]}
  r_estra_cesur   real,            -- savunmasal gerileme tespiti
  r_estra_derin   real,
  r_estra_tarafsiz real,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_defense_session_user_recent
  ON public.fact_user_defense_session (user_id, created_at DESC);

-- fact_paper_publication_recent — 90g window (Wow #1 inverted lookup)
CREATE TABLE public.fact_paper_publication_recent (
  paper_id        text PRIMARY KEY,
  published_at    date NOT NULL,
  rq_match_score  real,           -- RQ embedding × paper embedding cosine
  closes_methods  text[],         -- ['RI-CLPM', 'aktigrafi', 'pasif sensör'] altkümeleri
  source          text NOT NULL CHECK (source IN ('openalex','semantic_scholar','arxiv'))
);

CREATE INDEX idx_pub_recent_date_rq
  ON public.fact_paper_publication_recent (published_at DESC)
  WHERE published_at >= now() - interval '90 days';
```

### Yeni endpoint'ler

#### `POST /api/defense/full-text-scan`
- **In:** `{user_id, project_id, full_text, authoring_session_id?}`
- **Out:**
  ```json
  {
    "atifsiz": [{"sentence_idx":1, "text":"...nedensel yönlülüğü ortaya koymuştur",
                 "severity":"high", "reason":"observational_data"}],
    "zayif": [{"sentence_idx":4, "text":"politika sonuçları doğurur",
               "severity":"medium", "type":"unsupported_claim"}],
    "makro": [{"section":"limitations", "issue":"<3 limitations",
               "expected_min":3, "found":1}],
    "session_id": "..."
  }
  ```
- **Flow:**
  1. Full text → cümle splitting (regex + spaCy sentencizer)
  2. Her cümle → A1/A2 ortak motor (atıfsız tespiti — paylaşılan kod)
  3. Zayıf iddia: gözlemsel veri + nedensel iddia kalıbı (`/nedensel|kanıtla|ortaya koy/` × `/observational|cross-sectional/`)
  4. Makro: limitations <3 paragraf, methods → results geçişi yok, discussion → conclusion atlama
  5. Snapshot `fact_user_defense_session.scan_results`

#### `GET /api/defense/gap-still-open?rq_id=&days=90`
- **Out:**
  ```json
  {
    "rq_id": "...",
    "still_open": false,
    "partial_close": true,
    "new_papers": [
      {"paper_id":"P-117","published":"2026-02-15","title":"...",
       "closes_methods":["RI-CLPM"], "remaining":["pasif sensör"]},
      {"paper_id":"P-119","published":"2026-03-08","title":"...",
       "closes_methods":["aktigrafi"], "remaining":["RI-CLPM"]},
      {"paper_id":"P-121","published":"2026-04-22","title":"...",
       "closes_methods":[], "design":"cross_sectional"}
    ],
    "warning": "P-117 boşluğun yöntem ayağını kısmen kapatmış",
    "suggested_action": "Tartışmaya 'P-117 ile farkımız: pasif sensör + RI-CLPM kombinasyonu' cümlesi ekle"
  }
  ```
- **Flow:**
  1. RQ embedding fetch (`fact_research_question`)
  2. `fact_paper_publication_recent` filter `published_at >= now() - 90d`
  3. RQ × paper cosine + `closes_methods` set intersection
  4. RQ method seti = {pasif sensör, RI-CLPM}; paper closes = {RI-CLPM} → **partial_close**
  5. Cache: Redis `defense:gap_still_open:{rq_id}:{days}` TTL=6h

#### `POST /api/defense/argument-graph`
- **In:** `{full_text}`
- **Out:** `{nodes:[{idx, text, type:'claim|evidence|warrant'}], edges:[{from, to, rel:'supports|contradicts|elaborates'}]}`
- **Flow:** Gemini Flash 2.0 prompt — Toulmin argument structure → graph

---

## SAYFA YAPISI (ASCII)

```
┌── 11 · Savunma Provası ── atıfsız iddia · ters-bakış G1 ────────────────┐
│ Felsefe: Hakem gözü gerekir; cümle düzeyinde sürtünme + G1 ters-bakış. │
│                                                                          │
│ ┌── Simülasyon · tam metin tarama + G1 ters-bakış (12 sf · 47 cümle) ─┐│
│ │ D ✓ ─ C ✓ ─ G ✓ ─ A ✓ ─ S ●   r-ESTRA cesur 0.71 ↓.03                ││
│ │                                                                        ││
│ │ ┌── 🔄 G1 ters-bakış · boşluk hâlâ açık mı? ────────────────────────┐││
│ │ │ RQ "pasif sensör + RI-CLPM" boşluğu (M3 [3,8] altın)              │││
│ │ │ son 90g yeni 3 paper:                                              │││
│ │ │ • P-117 (Şubat 2026)  RI-CLPM ✓  pasif sensör ✗                   │││
│ │ │ • P-119 (Mart 2026)   aktigrafi ✓  RI-CLPM ✗                      │││
│ │ │ • P-121 (Nisan 2026)  kesitsel                                     │││
│ │ │ ⚠ P-117 yöntem ayağını kısmen kapatmış —                           │││
│ │ │   "P-117 ile farkımız: pasif sensör + RI-CLPM kombinasyonu" ekle. │││
│ │ │ [P-117'yi tartışmaya enjekte et →]                                 │││
│ │ └────────────────────────────────────────────────────────────────────┘││
│ │                                                                        ││
│ │ ┌── tartışma · paragraf 3 ──────────────┐ ┌── 5 sürtünme noktası ──┐││
│ │ │ "Çalışmamız ergenlerde ekran-uyku    │ │ ① "nedensel yönlülüğü   │││
│ │ │  ilişkisinde nedensel yönlülüğü       │ │   ortaya koymuştur" —   │││
│ │ │  ortaya koymuştur." [ERR ●]           │ │   gözlemsel için fazla  │││
│ │ │                                       │ │   iddialı (cümle 1)     │││
│ │ │ "Mevcut literatür özbildirim odaklı   │ │ ② Atıfsız: "politika    │││
│ │ │  çalışmaların ötesine geçmektedir     │ │   sonuçları doğurur"    │││
│ │ │  [P-019]." [WARN ▲]                   │ │ ③ P-117 referansı eksik │││
│ │ │                                       │ │ ④ Methods→Results geçiş│││
│ │ │ "Pasif sensör verisi gözlemsel        │ │ ⑤ Limitations 1 par     │││
│ │ │  düzeyde nedensel çıkarım sağlar      │ │   (≥3 beklenir)         │││
│ │ │  [P-088]." [OK ✓]                     │ │                         │││
│ │ │                                       │ │                         │││
│ │ │ "...politika sonuçları doğurur."[ERR●]│ │                         │││
│ │ └───────────────────────────────────────┘ └─────────────────────────┘││
│ └────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **Sol:** Tam metin önizleme (atıfsız altı çizik · zayıf iddia turuncu · G1-onay yeşil — `.sent.err/.sent.warn/.sent.ok` mock CSS)
- **Sağ üst:** **G1 ters-bakış paneli** — mavi-açık bg `#eff6ff`, border `#bfdbfe`, başlık mono small-caps, son 90g yeni paper sayısı + buton "P-117'yi tartışmaya enjekte et" (`#1d4ed8`)
- **Sağ alt:** Hakem-gözü özet — 5 sürtünme noktası, daire-numaralı liste (① ② ③ ④ ⑤)
- **Funnel:** `Discovery ✓ Curation ✓ Gap ✓ Yazım ✓ Savunma ●`
- **r-ESTRA cesur ↓.03:** savunmasal gerileme tespiti — bu sayfada izlenir

### Back (öneri)
1. Sayfa mount → A3 akademize tam metin yüklenir → `POST /full-text-scan`
2. Paralel: `GET /gap-still-open?rq_id=` (her aktif RQ için)
3. Buton "enjekte et" → S2'ye geçişte hakem simülasyonuna girdi olarak kullanılır
4. r-ESTRA cesur skoru `<0.7` ise "savunmasal gerileme" uyarı

### Wow #1 inverted lookup tetikleyici
- **Trigger:** Savunma sayfası mount + RQ_id mevcut + 30g geçmiş (G1 timestamp - now > 30d)
- **Kanıt:** mock satır 1810 "kullanıcı G1'de 'şu RQ boşlukta' demişti; sistem 30 gün sonra Savunma'ya gelinen anda 'P-117 Şubat 2026'da yayınlandı...' der"

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon / Öğrenci:** kapalı (Defense profesyonel ihtiyaç + LLM maliyet)
- **Araştırmacı:** açık (full-text scan + G1 ters-bakış)
- **Profesyonel:** + Gemini 2.5 Pro argument-graph daha hassas (cümleler arası warrant tespiti)

---

## AÇIK SORULAR
1. **`fact_paper_publication_recent` veri kaynağı:** OpenAlex daily harvest (90g) mu, Semantic Scholar API mu, hibrit mi? `pipelines/` altında günlük cron gerekecek.
2. **`closes_methods` etiketleme:** paper title+abstract → method extract NER veya LLM ile? Hangi schema? (current: hardcoded 6 method bucket)
3. **30g G1 trigger:** "kullanıcı G1'e ne zaman bastı" timestamp'i `fact_user_gapatlas_session` benzeri bir tablodan gelecek — bu tablo da yok (p-7'de önerilmişti).
4. **Wow #1 false positive riski:** P-121 "kesitsel" → kapatmaz; P-117 "RI-CLPM ✓" → kısmen kapatır. Bu sınıflandırma %95+ doğrulukta olmazsa kullanıcıya yanlış paniğe sebep olur. Validasyon protokolü?
5. **Argüman graph kullanım:** Mock'ta sadece techspec'te bahsediyor, simülasyon görünmüyor — sayfa render'da nerede? (sürtünme noktası genişletme?)
6. **r-ESTRA cesur ↓.03 hesaplama:** A3 → S1 arasındaki delta nasıl ölçülür? Belirgin agresif iddia kelime sayısı mı?
7. **5 sürtünme limit:** mock'ta sabit 5; gerçekte daha fazla varsa "top-5 by severity" mi, sayfalandırma mı?

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar Defense p-11 | `PaperMind_mock_v1.0.html` | 626 |
| 2 | p-11 page block | `PaperMind_mock_v1.0.html` | 1797-1852 |
| 3 | techspec endpoint | `PaperMind_mock_v1.0.html` | 1806 |
| 4 | data tables (gap_v3, publication_recent, defense_session) | `PaperMind_mock_v1.0.html` | 1807 |
| 5 | Wow #1 inverted lookup açıklama | `PaperMind_mock_v1.0.html` | 1810 |
| 6 | Δ revize: G1 ters-bakış paneli yeni | `PaperMind_mock_v1.0.html` | 1811 |
| 7 | G1 ters-bakış simülasyon (P-117/P-119/P-121) | `PaperMind_mock_v1.0.html` | 1822-1829 |
| 8 | Tartışma paragraf 3 (.sent.err/.warn/.ok) | `PaperMind_mock_v1.0.html` | 1832-1838 |
| 9 | 5 sürtünme noktası | `PaperMind_mock_v1.0.html` | 1840-1847 |
| 10 | api/routes/ — defense* yok | `api/routes/` (ls) | — |
