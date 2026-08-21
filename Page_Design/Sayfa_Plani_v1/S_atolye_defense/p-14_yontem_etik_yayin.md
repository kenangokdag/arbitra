# p-14 · Yöntem & Etik & Yayın (Defense)

> Tezgah: **Defense · final stop** (5.x son durağı)
> 3 kapı: statcheck full · etik checklist · top-10 dergi semantik scope eşleme · gönderim paketi.

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:2002-2067`
- **Sidebar:** `PaperMind_mock_v1.0.html:629`
- **Bu md:** `Page_Design/Sayfa_Plani_v1/S_atolye_defense/p-14_yontem_etik_yayin.md`

## ROL
Akış son durağı. Tez/makale teslim edilmeden önce **3 kapı**: yöntem-tutarlılık (statcheck full report), etik (KVKK + IRB beyanları), yayın stratejisi (top-10 dergi eşleme · scope/IF/kabul oranı/açık erişim politikası). Bu kapılar geçilmeden gönderme — saç çıkartmama protokolü. **Top-10 semantik scope eşleme** ayırıcı: rakipler keyword match yapar; PaperMind tez metnini bge-m3 vector ile dergi scope vector'üne kosinüs benzerliği ile eşler.

## BACKEND ❌ YOK
`api/routes/` listesinde `defense*` yok. Mock claims:
- `POST /api/defense/statcheck-full` (S2'deki statcheck'in full-report versiyonu)
- `POST /api/defense/ethics-check`
- `POST /api/defense/journal-match` (semantik scope match + Q-band + IF + kabul oranı sıralama)

## DB ❌ YOK
- `fact_paper_pvalue_extraction` — p-12'de önerilen (paylaşılan)
- `dim_journal_v2` (Q-band · IF · scope vector) — yok
- `fact_journal_acceptance_rate` — yok
- `mart_user_authoring_session` — p-9'da önerilen

---

## ÖNERİ: Eksik Backend

### `0026_journal_publish.sql`

```sql
-- dim_journal_v2 — dergi master (scope vector + Q + IF)
CREATE TABLE public.dim_journal_v2 (
  journal_id      text PRIMARY KEY,         -- ISSN-bazlı
  display_name    text NOT NULL,
  q_band          text CHECK (q_band IN ('Q1','Q2','Q3','Q4','unranked')),
  impact_factor   real,
  if_year         int,
  scope_keywords  text[],
  scope_embedding vector(1024),             -- bge-m3 (pgvector ext)
  open_access     text CHECK (open_access IN ('full','hybrid','closed')),
  avg_response_days int,
  publisher       text,
  source_provider text NOT NULL,            -- 'sjr','clarivate','manual'
  refreshed_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_journal_q_if
  ON public.dim_journal_v2 (q_band, impact_factor DESC);

-- fact_journal_acceptance_rate — kabul oran tarihçesi
CREATE TABLE public.fact_journal_acceptance_rate (
  journal_id      text NOT NULL REFERENCES public.dim_journal_v2(journal_id) ON DELETE CASCADE,
  year            int NOT NULL,
  acceptance_pct  real NOT NULL,
  total_submissions int,
  source          text NOT NULL,
  PRIMARY KEY (journal_id, year)
);

-- fact_user_submission_package — gönderim paketi snapshot
CREATE TABLE public.fact_user_submission_package (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  project_id      uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  defense_session_id uuid REFERENCES public.fact_user_defense_session(id),
  ethics_passed   boolean NOT NULL DEFAULT false,
  statcheck_red_count int NOT NULL DEFAULT 0,
  selected_journal_id text REFERENCES public.dim_journal_v2(journal_id),
  cover_letter_text text,
  package_pdf_path text,                    -- Supabase Storage URL
  package_zip_path text,
  generated_at    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);
```

### Yeni endpoint'ler

#### `POST /api/defense/statcheck-full`
- **In:** `{user_id, project_id, defense_session_id}`
- **Out:**
  ```json
  {
    "rows": [
      {"location":"Tablo 2","test":"t(310)=3.41","reported":".001","computed":".0007","status":"green"},
      {"location":"Tablo 3","test":"t(310)=2.14","reported":".034","computed":".033","status":"yellow","reason":"rounding"},
      {"location":"Tablo 4","test":"F(2,309)=8.92","reported":".0001","computed":".0002","status":"green"},
      {"location":"Şekil 3","test":"χ²(1)=4.18","reported":".04","computed":".041","status":"green"},
      {"location":"Bulgular §3.2","test":"r=.31, n=312","reported":".001","computed":"2.5e-08","status":"red","reason":"decision_altering"}
    ],
    "summary": {"green":3, "yellow":1, "red":1, "fix_required": true}
  }
  ```
- **Flow:** p-12 statcheck çağrısının full-report versiyonu — `fact_paper_pvalue_extraction` filter `user_session_id = :defense_session_id`

#### `POST /api/defense/ethics-check`
- **In:** `{user_id, project_id, full_text}`
- **Out:**
  ```json
  {
    "checklist": [
      {"key":"irb_approval","label":"IRB onay belirtildi","status":"present","evidence":"§Etik Beyanı, par 1"},
      {"key":"data_sharing","label":"Veri paylaşım beyanı","status":"missing"},
      {"key":"kvkk","label":"KVKK aydınlatma (TR projesi için)","status":"present"},
      {"key":"conflict_of_interest","label":"Çıkar çatışması beyanı","status":"present"},
      {"key":"contribution_statement","label":"Katkı beyanı (CRediT)","status":"missing"}
    ],
    "all_passed": false,
    "missing_count": 2
  }
  ```
- **Flow:** Regex + LLM hybrid — bölüm başlıkları "Etik Beyanı / Ethics Statement / Data Availability" tara, içerik LLM ile sınıflandır

#### `POST /api/defense/journal-match`
- **In:** `{full_text, top_k:10, filters?:{q_band:["Q1"], oa?:string}}`
- **Out:**
  ```json
  {
    "matches": [
      {"journal_id":"...","name":"Sleep Medicine","q":"Q1","if":4.2,"scope_match":0.91,"acceptance":0.14,"response_days":68,"oa":"hybrid"},
      {"journal_id":"...","name":"Sleep Health","q":"Q1","if":3.7,"scope_match":0.87,"acceptance":0.22,"response_days":52,"oa":"hybrid"},
      ...10 row
    ]
  }
  ```
- **Flow:**
  1. Tez full text → bge-m3 embed (1024-dim)
  2. `dim_journal_v2.scope_embedding` × tez embed → cosine
  3. Filter: q_band, oa (varsa)
  4. Sort: scope_match × IF × (1 - acceptance penalty) — composite score
  5. Top-10 dön

#### `POST /api/defense/submission-package`
- **In:** `{user_id, project_id, defense_session_id, selected_journal_id}`
- **Out:** `{package_url:"https://...zip", cover_letter:"...", statcheck_pdf_url:"..."}`
- **Flow:**
  1. Pre-check: `ethics_passed=true` AND `statcheck_red_count=0` AND `selected_journal_id != null` → değilse 400 "kapılar açık değil"
  2. Cover letter LLM-generate (selected journal'a göre)
  3. PDF render (full text + statcheck rapor)
  4. ZIP → Supabase Storage upload
  5. Insert `fact_user_submission_package`

---

## SAYFA YAPISI (ASCII)

```
┌── 14 · Yöntem & Etik & Yayın ── statcheck · top-10 dergi · final stop ───┐
│ Felsefe: 3 kapı geçilmeden teslim yok — saç çıkartmama protokolü.       │
│                                                                            │
│ ┌── Simülasyon · 3 final kapı (akış sonu) ──────────────────────────────┐│
│ │ D ✓ ─ C ✓ ─ G ✓ ─ A ✓ ─ S ✓                                           ││
│ │                                                                          ││
│ │ ┌─[① statcheck]─[② etik]─[③ dergi]──── [① aktif] ──────────────────┐││
│ │ │ ┌─ statcheck full ─────────────────────────────────────────────────┐│││
│ │ │ │ konum   | test          | rapor p | gerçek p | durum             ││││
│ │ │ ├─────────┼───────────────┼─────────┼──────────┼────────────────── ││││
│ │ │ │ Tablo 2 | t(310)=3.41   |  .001   |  .0007   | 🟢                ││││
│ │ │ │ Tablo 3 | t(310)=2.14   |  .034   |  .033    | 🟡 yuvarlama      ││││
│ │ │ │ Tablo 4 | F(2,309)=8.92 |  .0001  |  .0002   | 🟢                ││││
│ │ │ │ Şekil 3 | χ²(1)=4.18    |  .04    |  .041    | 🟢                ││││
│ │ │ │ §3.2 ●  | r=.31, n=312  |  .001   |  .0000   | 🔴 tutarsız       ││││
│ │ │ └─────────────────────────────────────────────────────────────────┘│││
│ │ │ ⚠ 1 tutarsızlık: r=.31 n=312 → gerçek p=2.5e-08; raporda .001       │││
│ │ │ [Düzelt →] (metni güncelle)                                         │││
│ │ └─────────────────────────────────────────────────────────────────────┘││
│ │                                                                          ││
│ │ ┌── Top-10 dergi · semantik scope eşleme ────────────────────────────┐││
│ │ │ dergi             | Q  | IF  | scope | kabul% | gün | OA          │││
│ │ │ Sleep Medicine    | Q1 | 4.2 | 0.91 🟢|  14   |  68 | hibrit      │││
│ │ │ Sleep Health      | Q1 | 3.7 | 0.87 🟢|  22   |  52 | hibrit      │││
│ │ │ J Adolesc Health  | Q1 | 5.1 | 0.74 🟡|  18   |  94 | hibrit      │││
│ │ │ J Sleep Research  | Q1 | 3.4 | 0.81 🟡|  28   |  45 | tam         │││
│ │ │ Pediatrics        | Q1 | 8.0 | 0.62  |   8   | 110 | hibrit      │││
│ │ └─────────────────────────────────────────────────────────────────────┘││
│ │                                                                          ││
│ │ [📦 Gönderim paketi indir (PDF + cover letter + statcheck rapor)]     ││
│ └──────────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **3 sekme bar:** ① statcheck (aktif `var(--defense)` bg) · ② etik · ③ dergi
- **Statcheck tablosu:** mock 2033-2046 — kolon: konum/test/rapor p/gerçek p/durum, son satır (§3.2) kırmızı text — "Düzelt" butonu inline
- **Top-10 dergi tablosu:** mock 2050-2061 — sticky header, scope-uyum yeşil/sarı/kırmızı, Pediatrics row gri (uyum düşük) `var(--muted)`
- **Final buton:** Tam genişlik (`width:100%`), `var(--defense)` bg, beyaz text "📦 Gönderim paketi indir (PDF + cover letter + statcheck rapor)"
- **Funnel:** Discovery ✓ Curation ✓ Gap ✓ Yazım ✓ Savunma ✓ (final stop ✓)

### Back (öneri)
1. Sayfa mount → paralel: `POST /statcheck-full` + `POST /ethics-check` + `POST /journal-match`
2. Sekme switch → ilgili veri zaten cached
3. "Düzelt" buton → A2 sayfasına derin-link `?fix_pvalue=§3.2&suggested=p<.001`
4. "Gönderim paketi indir" → `POST /submission-package` → 3-kapı pre-check → ZIP URL döner

### Top-10 sıralama formülü (öneri)
```python
composite_score = (
    0.50 * scope_match               # semantik öncelik
    + 0.20 * (impact_factor / max_if)
    + 0.15 * (1 - acceptance_pct)    # düşük kabul = prestij ama risk
    + 0.10 * (1 - response_days/180) # hızlı yanıt bonus
    + 0.05 * (open_access == 'full' ? 1 : open_access == 'hybrid' ? 0.5 : 0)
)
```

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon:** kapalı tamamen
- **Öğrenci:** statcheck-full + ethics-check (sadece self-review için)
- **Araştırmacı:** + journal-match (Pinecone sorgusu maliyetli)
- **Profesyonel:** + submission-package (PDF rendering + LLM cover letter) + Gemini 2.5 Pro

---

## AÇIK SORULAR
1. **`dim_journal_v2.scope_embedding` üretimi:** Hangi metin embed edilecek — dergi "aim & scope" sayfası, son 50 paper özeti, başlık+abstract concatenation? Refresh frequency (yıllık? quartal?)
2. **`fact_journal_acceptance_rate` veri kaynağı:** Yine SJR/Clarivate; çoğu dergi public değil → proxy gerekecek (submission/decision date histogramı yoksa fallback değer ne?)
3. **Cover letter LLM kalitesi:** Standart format mı (journal-specific template + tez özet), yoksa free-form mu? Kullanıcı düzenleyebilmeli mi?
4. **PDF render:** WeasyPrint mı, ReportLab mı, browser-side print-to-PDF mi? Tablo + figür + matematik (LaTeX) render desteği?
5. **Etik checklist regex eksikliği:** "Etik Beyanı" başlığı yoksa LLM bölüm sınıflandırma yapmalı — tutarlılık nasıl ölçülecek?
6. **Top-10 sıralama formülü ağırlıkları (0.5/0.2/0.15/0.10/0.05):** Mock'ta yok, B-NNN kararı yok. Kullanıcı slider ile ayarlayabilsin mi? Sadece kullanıcı "high IF / open access / fast response" prefi seçsin?
7. **Pediatrics gri satır:** mock'ta `color:var(--muted)` ile düşük scope-uyum gösterilmiş. Threshold (0.65?) net değil — composite_score < threshold ise dim düşür kuralı yazılmalı.
8. **"Düzelt" buton hedefi:** `r=.31, n=312` için doğru `p` ne? `2*1−normal_cdf(r×sqrt(n−2)/sqrt(1−r²))` → r→t→p formülü gerekiyor. Auto-suggest mi, sadece konum link mi?

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar Defense p-14 | `PaperMind_mock_v1.0.html` | 629 |
| 2 | p-14 page block | `PaperMind_mock_v1.0.html` | 2002-2067 |
| 3 | techspec endpoint (statcheck-full/ethics/journal-match) | `PaperMind_mock_v1.0.html` | 2011 |
| 4 | data tables (pvalue_extraction, dim_journal_v2, acceptance_rate) | `PaperMind_mock_v1.0.html` | 2012 |
| 5 | Wow ayırt edici: 3 final kapı + semantik scope match | `PaperMind_mock_v1.0.html` | 2015 |
| 6 | 3 sekme bar (statcheck/etik/dergi) | `PaperMind_mock_v1.0.html` | 2026-2030 |
| 7 | Statcheck tablosu (5 satır + §3.2 🔴) | `PaperMind_mock_v1.0.html` | 2032-2046 |
| 8 | "Düzelt" butonu inline | `PaperMind_mock_v1.0.html` | 2045 |
| 9 | Top-10 dergi matrisi (Sleep Medicine 0.91 ... Pediatrics 0.62) | `PaperMind_mock_v1.0.html` | 2049-2061 |
| 10 | Final buton "Gönderim paketi indir" | `PaperMind_mock_v1.0.html` | 2064 |
| 11 | api/routes/ — defense* yok | `api/routes/` (ls) | — |
