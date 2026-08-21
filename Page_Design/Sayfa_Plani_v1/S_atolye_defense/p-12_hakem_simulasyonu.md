# p-12 · Hakem Simülasyonu (Defense)

> Tezgah: **Defense · savunma** (5.x)
> 3-persona (Şüpheci · Sempatik · Yöntemci) · dergi-spesifik kalibrasyon · statcheck (Nuijten 2016) · zincir derinlik max 2.

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:1855-1926`
- **Sidebar:** `PaperMind_mock_v1.0.html:627`
- **Bu md:** `Page_Design/Sayfa_Plani_v1/S_atolye_defense/p-12_hakem_simulasyonu.md`

## ROL
Hakem tek-tip değildir. **Şüpheci** her metodolojiye saldırır, **Sempatik** kabul eder ama küçük şeyler kaşır, **Yöntemci** sadece yöntem bölümünü didikler. PaperMind 3 personayı paralel çalıştırır + **dergi-spesifik kalibrasyon** ("Sleep Medicine son 50 makalede %62 major") + **statcheck** p-değer tutarlılık (sinyal #42, Nuijten 2016). Zincir derinlik **hard-cap 2** (rakipler 5+ derinliğe gidip kullanıcıyı tüketiyor).

## BACKEND ❌ YOK
`api/routes/` listesinde `defense*` yok. Mock claims:
- `POST /api/defense/reviewer-3persona` (paralel 3-LLM zinciri · derinlik 2 hard-cap)
- `POST /api/defense/statcheck` (Nuijten 2016 — t/F → p tutarlılık)
- `GET /api/defense/journal-calibration?journal_id=`

## DB ❌ YOK
- `fact_journal_review_distribution` (dergi × son 50 makale · kabul/major/minor/red yüzdeleri) — yok
- `fact_paper_pvalue_extraction` (statcheck — sinyal #42) — yok
- `mart_reviewer_persona_template` — yok
- `dim_journal_v2` — yok (mock satır 2012)

---

## ÖNERİ: Eksik Backend

### `0024_reviewer_simulation.sql`

```sql
-- mart_reviewer_persona_template — 3 persona şablon (sabit seed)
CREATE TABLE public.mart_reviewer_persona_template (
  persona_key     text PRIMARY KEY CHECK (persona_key IN ('skeptik','sempatik','yontemci')),
  display_name    text NOT NULL,
  prompt_seed     text NOT NULL,        -- LLM system prompt
  question_focus  text[],               -- ['methodology','sample_size','validation',...]
  chain_max_depth int NOT NULL DEFAULT 2,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- fact_journal_review_distribution — dergi × kabul oran tarihçesi (son 50)
CREATE TABLE public.fact_journal_review_distribution (
  journal_id      text NOT NULL,
  window_size     int NOT NULL DEFAULT 50,
  accept_pct      real NOT NULL,        -- 0.14 = %14
  major_pct       real NOT NULL,        -- 0.62
  minor_pct       real NOT NULL,        -- 0.18
  reject_pct      real NOT NULL,        -- 0.06
  scope_keywords  text[],
  source          text NOT NULL,        -- 'sjr','clarivate','manual'
  refreshed_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (journal_id, window_size)
);

-- fact_paper_pvalue_extraction — sinyal #42 (statcheck)
CREATE TABLE public.fact_paper_pvalue_extraction (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  paper_id        text,                 -- nullable: kullanıcı tezi de buraya
  user_session_id uuid REFERENCES public.fact_user_defense_session(id) ON DELETE CASCADE,
  location_label  text NOT NULL,        -- 'Tablo 3', 'Bulgular §3.2'
  test_type       text NOT NULL CHECK (test_type IN ('t','F','chi2','r','z')),
  test_statistic  real NOT NULL,
  df1             real,                 -- t=df, F=df1, chi2=df, r=null
  df2             real,
  reported_p      real NOT NULL,
  computed_p      real NOT NULL,
  inconsistency   text NOT NULL CHECK (inconsistency IN ('green','yellow','red')),
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_pvalue_session
  ON public.fact_paper_pvalue_extraction (user_session_id);
```

### Yeni endpoint'ler

#### `POST /api/defense/reviewer-3persona`
- **In:** `{user_id, project_id, full_text, journal_id?}`
- **Out:**
  ```json
  {
    "skeptik":  {"questions":[
      {"text":"Pasif sensör validasyonu zayıf — kalibrasyon paper yok",
       "depth":1, "follow_up":null},
      {"text":"Örneklem 312 yeterli mi? (P-019 n=890)", "depth":1,
       "follow_up":{"text":"power analizi raporlanmış mı?","depth":2}},
      {"text":"Limitations 1 paragraf — yetersiz","depth":1}
    ]},
    "sempatik": {"questions":[...]},
    "yontemci": {"questions":[...]},
    "session_id": "..."
  }
  ```
- **Flow:**
  1. 3 persona prompt seed `mart_reviewer_persona_template` fetch
  2. Paralel 3 LLM call (Gemini Flash 2.0) — `asyncio.gather`
  3. **Hard-cap 2:** her question.depth ≤ 2 (LLM prompt + post-validation)
  4. Append `fact_user_defense_session.scan_results.reviewer_questions`

#### `POST /api/defense/statcheck`
- **In:** `{full_text, session_id}`
- **Out:** `{results:[{location_label, test, reported, computed, status:'green|yellow|red'}, ...], summary:{green:N, yellow:M, red:K}}`
- **Flow:**
  1. Regex extract: `t\((\d+)\)\s*=\s*([\d.]+).*?p\s*[=<]\s*([\d.]+)` (t-test)
     ve `F\((\d+),(\d+)\)\s*=\s*([\d.]+).*?p\s*[=<]\s*([\d.]+)` (ANOVA)
     ve `χ²\((\d+)\)\s*=\s*([\d.]+).*?p\s*[=<]\s*([\d.]+)` ve `r\s*=\s*([\d.]+),\s*n\s*=\s*(\d+)`
  2. Her test için `scipy.stats` ile p hesapla
  3. Karşılaştır: |reported - computed| ≤ rounding tolerance → 🟢 / yuvarlama → 🟡 / |delta| > 0.01 → 🔴
  4. Insert `fact_paper_pvalue_extraction`

#### `GET /api/defense/journal-calibration?journal_id=`
- **Out:** `{journal_id, accept_pct:0.14, major_pct:0.62, minor_pct:0.18, reject_pct:0.06, prediction:"major revision", confidence:0.71}`
- **Flow:**
  1. `fact_journal_review_distribution` fetch
  2. `prediction` = full text features (sample_n, limitations_count, statcheck_red) × `accept_pct` distribution → tahmin
  3. Cache: Redis `defense:journal_cal:{journal_id}` TTL=24h

---

## SAYFA YAPISI (ASCII)

```
┌── 12 · Hakem Simülasyonu ── 3-persona · dergi-spesifik kalibrasyon ──────┐
│ Felsefe: Hakem tek-tip değildir; 3 persona paralel + dergi spesifik.    │
│                                                                            │
│ ┌── Simülasyon · 3 persona + Sleep Medicine kalibrasyonu (Q1 IF 4.2) ──┐│
│ │ D ✓ ─ C ✓ ─ G ✓ ─ A ✓ ─ S ●   r-ESTRA cesur 0.71 · derin 0.66          ││
│ │                                                                          ││
│ │ ┌─ Şüpheci [🔴]──┐ ┌─ Sempatik [🟢]──┐ ┌─ Yöntemci [🟣]──────────┐    ││
│ │ │• Pasif sensör  │ │• Yöntem güçlü   │ │• RI-CLPM uygunluğu 🟢   │    ││
│ │ │  validasyonu    │ │  sunum net      │ │  (P-088 ✓)              │    ││
│ │ │  zayıf          │ │• Tablo 2 başlık │ │• Rastgelesi yapı        │    ││
│ │ │• Örneklem 312   │ │  belirsiz minor │ │  geçerliği test ✓ mü?   │    ││
│ │ │  (P-019 n=890)  │ │• Discussion +1  │ │  ↳ alt: χ²/CFI/RMSEA    │    ││
│ │ │  ↳ alt: power   │ │  paragraf       │ │     (derinlik 2/2)      │    ││
│ │ │     (2/2)       │ │• Yazım akıcı    │ │• Eksik veri yöntemi     │    ││
│ │ │• Limitations 1  │ │                 │ │  açık değil             │    ││
│ │ │  yetersiz       │ │                 │ │                         │    ││
│ │ └─────────────────┘ └─────────────────┘ └─────────────────────────┘    ││
│ │                                                                          ││
│ │ ┌─ 📊 statcheck ────────────┐ ┌─ 📈 Sleep Medicine kalibrasyon ────┐  ││
│ │ │ 12 p · 10 🟢 · 2 🟡       │ │ Son 50: kabul %14 · major %62 ·   │  ││
│ │ │ (T3: t(310)=2.14 → .033) │ │   minor %18 · red %6              │  ││
│ │ │ 0 🔴                      │ │ Tahmin: major revision            │  ││
│ │ └───────────────────────────┘ └────────────────────────────────────┘  ││
│ └──────────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **Üst:** Dergi seçici (Sleep Medicine / Sleep Health / J Adolesc Health · Q-band gösterimi)
- **3 sütun (mock 1880-1908):**
  - Şüpheci → border-top `#dc2626` kırmızı
  - Sempatik → border-top `#10b981` yeşil
  - Yöntemci → border-top `#7c3aed` mor
- Her sütunda 4-7 madde + zincir alt-soru italik gri (`var(--muted)`) "↳ alt soru: ... *(derinlik 2/2)*"
- **Alt sol:** statcheck şeridi (sarı bg `#fffbeb`, border `#fde68a`) — 🟢🟡🔴 sayaç
- **Alt sağ:** dergi-spesifik kalibrasyon paneli (mavi bg `#eff6ff`, border `#bfdbfe`)
- **Funnel:** Discovery ✓ Curation ✓ Gap ✓ Yazım ✓ Savunma ●

### Back (öneri)
1. Sayfa mount → `POST /reviewer-3persona` (paralel 3 LLM call)
2. Background async → `POST /statcheck` (regex extract + scipy compute)
3. Dergi seçilince → `GET /journal-calibration?journal_id=` (cache 24h)
4. Hard-cap 2: LLM prompt'ta **explicit kural** + post-process validasyon

### statcheck algoritması (Nuijten 2016)
```python
# Regex: r"t\((\d+)\)\s*=\s*([\d.]+).*?p\s*[=<]\s*([\d.]+)"
# Compute:
from scipy.stats import t as t_dist
df, t_stat, reported_p = match
computed_p = 2 * (1 - t_dist.cdf(abs(t_stat), df))  # iki yönlü

if abs(reported_p - computed_p) <= 0.005:
    status = 'green'
elif abs(reported_p - computed_p) <= 0.01:
    status = 'yellow'  # rounding
else:
    status = 'red'  # decision-altering
```

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon / Öğrenci:** kapalı
- **Araştırmacı:** açık (3-persona)
- **Profesyonel:** Gemini 2.5 Pro persona zinciri daha sofistike + journal-calibration cache miss durumunda live SJR/Clarivate query

---

## AÇIK SORULAR
1. **`fact_journal_review_distribution` veri kaynağı:** SJR/Clarivate API + manuel curated mı? Refresh frequency? (yıllık?) Bu data **çoğu dergi için public değil** — proxy gerekebilir (paper kabul tarihi - submission tarihi histogram).
2. **Persona prompt seed kararı:** Sabit metin `mart_reviewer_persona_template.prompt_seed` mi, A/B test mi? Yan etki: persona davranışı değişirse user expectation kırılır.
3. **statcheck regex eksiklikleri:** non-standard format ("p < .05", "p ns", "p = ns"), tablo içinde p-değeri varsa OCR? Markdown table parsing? Mock'ta sadece düz metin gösteriliyor.
4. **Zincir derinlik 2 hard-cap kanıt:** "rakipler 5+ derinliğe gidip tüketiyor" iddia kaynak? B-NNN kararı var mı?
5. **journal_id master listesi:** `dim_journal_v2` boyut tahmini? Sadece kullanıcının seçtiği top-10 mu, daha geniş mi?
6. **Major/minor tahmin doğruluğu:** "tahmin: major revision" çıkıyorsa ne kadar doğru? Validation set + accuracy reporting gerekli — yoksa kullanıcı yanlış güven kazanır.
7. **Dil dağılımı:** TR/EN tezler için statcheck regex aynı çalışır mı (TR'de "p değeri", "ortalama")? Locale-aware extraction?

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar Defense p-12 | `PaperMind_mock_v1.0.html` | 627 |
| 2 | p-12 page block | `PaperMind_mock_v1.0.html` | 1855-1926 |
| 3 | techspec endpoint (3persona/statcheck/journal-calibration) | `PaperMind_mock_v1.0.html` | 1864 |
| 4 | data tables (review_distribution, pvalue, persona_template) | `PaperMind_mock_v1.0.html` | 1865 |
| 5 | Wow #7 dergi-spesifik kalibrasyon | `PaperMind_mock_v1.0.html` | 1868 |
| 6 | 3 persona kart blokları | `PaperMind_mock_v1.0.html` | 1880-1908 |
| 7 | Şüpheci zincir derinlik 2/2 | `PaperMind_mock_v1.0.html` | 1886 |
| 8 | Yöntemci χ²/CFI/RMSEA alt soru | `PaperMind_mock_v1.0.html` | 1904 |
| 9 | statcheck şeridi (12 p, 10🟢, 2🟡 yuvarlama) | `PaperMind_mock_v1.0.html` | 1911-1916 |
| 10 | Sleep Medicine kalibrasyon (kabul %14 / major %62) | `PaperMind_mock_v1.0.html` | 1917-1922 |
| 11 | api/routes/ — defense* yok | `api/routes/` (ls) | — |
