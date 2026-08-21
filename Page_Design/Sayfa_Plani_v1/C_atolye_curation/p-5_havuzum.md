# p-5 · Havuzum (Curation)

> Tezgah: **Curation · seçer** (2.x)
> 6 raf · rol-aware · validator çift mühür · r-ESTRA paper-bazında uyum · "Boşluk × bu paper" inverted lookup.

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:1361-1439`
- **Sidebar:** `PaperMind_mock_v1.0.html:613`
- **Bu md:** `Page_Design/Sayfa_Plani_v1/C_atolye_curation/p-5_havuzum.md`

## ROL
Curation çıktısının ev'i. 6 rafta paper diz (Temel/Ampirik/Yöntem/Sarsıcı/Cephe/Dışla). Sistem rol önerir, kabul/değiştir. Tıkla → TR mini-çeviri (2 satır), alıntı kopyala. Sonunda APA/RIS/BibTeX/DOCX export. **Çift mühür** (RCR×FCR×SJR), **r-ESTRA paper-uyum %**, **"→ G1 M3" boşluk-doldurma rozeti** her kart üstünde.

## BACKEND ⚠ kısmen var (mock vs gerçek büyük uçurum)

### Mevcut
- `GET /api/reading-list` → liste (`reading_list.py:32-36`)
- `POST /api/reading-list` → ekle, in-memory (`reading_list.py:39-52`)
- `PATCH /api/reading-list/{item_id}` → status/notes update (`reading_list.py:55-75`)
- `DELETE /api/reading-list/{item_id}` → sil (`reading_list.py:78-86`)
- Status enum: `want_to_read|reading|finished|skipped` (`models/reading_list.py:14`)

### ⚠ KRİTİK: Store **in-memory** (`reading_list.py:26-29`)
> _"MVP in-memory store; restart'ta veri sifirlanir. Pilot oncesi Supabase'e gecis zorunlu."_ (KD-36)
>
> P035 sonrası asyncpg + Supabase RLS gerekli — şu an yok.

### ⚠ Mock-backend uyumsuzluğu (büyük)
| Mock iddiası | Gerçek backend |
|---|---|
| 6 raf rol enum (Temel/Ampirik/Yöntem/Sarsıcı/Cephe/Dışla) | YOK — sadece 4 status (want/reading/finished/skipped) |
| `POST /api/curation/role-suggest` | ❌ route YOK |
| `POST /api/translate` (EN→TR 2 satır cache) | ❌ route YOK |
| Validator API (iCite RCR · Dimensions FCR · SCImago SJR) | ❌ entegrasyon YOK |
| `POST /api/gapatlas/paper-fill-preview` | ❌ route YOK |
| `paper_role` tablo | ❌ DB'de yok |
| `paper_translation_cache` tablo | ❌ DB'de yok |
| `paper_annotation` tablo | ❌ DB'de yok |
| `user_style_profile` (r-ESTRA) | ❌ DB'de yok |
| `project_pool` tablo | ❌ DB'de yok (sadece `project_cluster` 0016'da) |

## DB ❌ büyük çoğunluk yok
- **Tek mevcut store:** `_store: dict[str, ReadingListItem]` Python in-memory (`reading_list.py:28`)
- **Supabase taraf:** Migration yok. Öneri: `0018_curation_pool.sql` (aşağıda)

---

## ÖNERİ: Eksik Backend Tasarımı

### 1. `0018_curation_pool.sql` (yeni migration)

```sql
-- project_pool — proje × paper × rol
CREATE TABLE public.project_pool (
  project_id    uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  paper_id      text NOT NULL,
  role          text NOT NULL DEFAULT 'unassigned'
                CHECK (role IN ('temel','ampirik','yontem','sarsici','cephe','disla','unassigned')),
  role_suggested text  CHECK (role_suggested IN ('temel','ampirik','yontem','sarsici','cephe','disla')),
  added_from    text   CHECK (added_from IN ('connected','q','search','manual')),
  status        text NOT NULL DEFAULT 'want_to_read'
                CHECK (status IN ('want_to_read','reading','finished','skipped')),
  notes         text DEFAULT '',
  added_at      timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, paper_id)
);

-- paper_translation_cache — TR mini-özet 2 satır
CREATE TABLE public.paper_translation_cache (
  paper_id      text NOT NULL,
  lang          text NOT NULL CHECK (lang IN ('tr','en','id')),
  summary_2line text NOT NULL,
  source_model  text NOT NULL,  -- 'gemini-flash-2.0' vs.
  generated_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (paper_id, lang)
);

-- paper_annotation — kullanıcı not (paper-spesifik)
CREATE TABLE public.paper_annotation (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  project_id    uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  paper_id      text NOT NULL,
  body          text NOT NULL CHECK (char_length(body) BETWEEN 1 AND 4000),
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- user_style_profile — r-ESTRA 7-boyut hedef vektörü (kullanıcı stil profili)
CREATE TABLE public.user_style_profile (
  user_id       uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  cesur         numeric CHECK (cesur BETWEEN 0 AND 1),
  derin         numeric CHECK (derin BETWEEN 0 AND 1),
  -- ek 5 boyut (canon/teorik/empirik/methodol/replikasyon)
  updated_at    timestamptz NOT NULL DEFAULT now()
);
```

### 2. Yeni route'lar

#### `POST /api/curation/role-suggest`
- **In:** `{project_id, paper_ids:list[str]}`
- **Out:** `list[{paper_id, role_suggested, confidence, rationale}]`
- **Flow:** Gemini Flash 2.0 — paper başlık/abstract + ESTRA radar girdi olarak alır → 6 rolden birini öner. Cache: `curation:role:{paper_id}:30d`. Faithfulness gate: rationale içindeki paper_id citation `paper_ids` ⊆ input.

#### `POST /api/curation/role-confirm`
- **In:** `{project_id, paper_id, role}`
- **Out:** updated `project_pool` row
- DB: `UPDATE project_pool SET role=:role WHERE (project_id,paper_id)=(...)`

#### `POST /api/translate`
- **In:** `{paper_id, target_lang:'tr'|'en'|'id', max_lines:2}`
- **Out:** `{summary_2line, source_lang, cached:bool}`
- **Flow:** `paper_translation_cache` lookup → yoksa Gemini Flash 2.0 (paper abstract → 2-satır summary) → upsert → return

#### `GET /api/curation/passport-batch?paper_ids=...`
- **In:** comma-separated paper_ids (max 50)
- **Out:** `list[PassportItem{paper_id, rcr, fcr, sjr, cd, uzzi, w_estra:7d, role, role_suggested, fills_gap_cell:str|null}]`
- **Flow:** join `fact_paper_quality_v3` + `fact_paper_w_estra` + `project_pool` (rol) + öneri G1 lookup (`fills_gap_cell` — bkz. p-6)

#### `POST /api/gapatlas/paper-fill-preview` (cross-page p-6)
- **In:** `{project_id, paper_id}`
- **Out:** `{fills_cell:str|null, M_index:int, contribution_score:float}`
- **Flow:** Paper'ın 8-matris hücrelerinden hangisini en çok doldurduğunu hesapla — `gap_heatmap` cell vector'üyle paper ESTRA radar cosine.

#### `GET /api/curation/export?project_id=&format=apa|ris|bibtex|docx`
- **Out:** dosya download
- **Flow:** `project_pool` filter `role != 'disla' AND status != 'skipped'` → sırasıyla biçim render

### 3. Validator entegrasyonu (Wow #1)

Üç bağımsız kaynak çift-mühür için:
- **iCite RCR:** NIH Open Citation Collection API (`https://icite.od.nih.gov/api/pubs?pmids=...`)
- **Dimensions FCR:** Dimensions API (auth gerekli, paid). Alt: OpenAlex `cited_by_count` proxy.
- **SCImago SJR:** Statik dump CSV (yıllık güncellenir) → `dim_journal_sjr` tablo lookup.

Mühür kuralı: 3 kaynak da uyumlu (sapma %10 altında) → 🟢 yeşil. 1 sapma → 🟡 sarı + chip "RCR sapma".

---

## SAYFA YAPISI (ASCII)

```
┌── 5 · Havuzum ─────── 6 raf · rol-aware · çift mühür ────────────────┐
│ Felsefe: topladıklarım rol-rafa diz, tıkla oku, alıntıla, dışa aktar. │
│ Tek sayfa.                                                            │
│                                                                       │
│ Bu sayfada: 6 raf · rol önerisi (kabul/değiştir) · TR mini-çeviri    │
│ · alıntı kopyala · APA/RIS/BibTeX/DOCX export.                       │
│                                                                       │
│ ┌── Simülasyon · 6 raf  (23 paper · doygunluk %72) ───────────────┐  │
│ │  D ✓ ─ C ● ─ G ─ A ─ S        r-ESTRA cesur 0.71               │  │
│ │                                                                  │  │
│ │  [Temel·6] [Ampirik·9] [Yöntem·4] [Sarsıcı·2] [Cephe·1] [Dışla·1]│  │
│ │                                                                  │  │
│ │  □ P-019 · Blue light suppression and sleep onset (2020)         │  │
│ │     1,847 atıf · r-ESTRA %88 · M3-Yöntem boşluğu doldurur        │  │
│ │     [Ampirik] [RCR×FCR×SJR 🟢] [★ CD 0.42] [→ G1 M3]            │  │
│ │                                                                  │  │
│ │  □ P-046 · Pre-2010 melatonin baseline (2008, uyandı 2020)       │  │
│ │     1,289 atıf · r-ESTRA %72 · M5-Bağlam boşluğu doldurur        │  │
│ │     [Temel] [🟢] [◆ B 8.7] [→ G1 M5]                             │  │
│ │                                                                  │  │
│ │  □ P-053 · Atypical biomarker model (2022)                       │  │
│ │     89 atıf · r-ESTRA %94 ⚡ · M7-Atılım boşluğu doldurur         │  │
│ │     [Sarsıcı] [🟡 RCR sapma] [◇ Uzzi 92%] [→ G1 M7]              │  │
│ │                                                                  │  │
│ │  ── Seçili: P-019 · okuyucu ──                                  │  │
│ │  ┌──────────────────────────────────────────────────────────┐   │  │
│ │  │ TR ÖZET (2 satır)                                        │   │  │
│ │  │ "Akşam saatlerinde mavi ışık maruziyetinin melatonin    │   │  │
│ │  │  baskılaması yoluyla uyku başlangıcını ortalama 31 dk    │   │  │
│ │  │  geciktirdiği bulundu. Etki yaşa bağlı (12-15 daha güçlü)│  │  │
│ │  │ [⇄ EN'e dön] [📋 alıntıla] [📌 anotasyon] [↓ APA]       │   │  │
│ │  └──────────────────────────────────────────────────────────┘   │  │
│ └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **6 raf chip:** Temel (`#1e3a8a`) · Ampirik (`#047857`) · Yöntem (`#0891b2`) · Sarsıcı (`#b91c1c`) · Cephe (`#7c2d12`) · Dışla (gri) — sayaç sağda
- **Sürükle-bırak:** kart raf-arası taşınabilir → `PATCH /api/curation/role-confirm`
- **Paper kart:** title + atıf + r-ESTRA % + boşluk-doldurma şerit + 4 rozet (rol · çift mühür · ★◆◇ · gap-link)
- **Okuyucu paneli (alt):** seçili paper'ın TR/EN 2-satır özet + 4 buton (EN'e dön · alıntıla · anotasyon · ↓APA)
- **Funnel + r-ESTRA:** üst sağ
- **Doygunluk şeridi:** "23 paper · doygunluk %72" (kapsama / 6-raf hedef)

### Back (mevcut + öneri)
1. Mount → `GET /api/reading-list` _(mevcut, in-memory)_ veya `GET /api/curation/pool?project_id=` _(öneri)_
2. Pool dönüşü → `GET /api/curation/passport-batch?paper_ids=...` _(öneri)_ — rol/sinyal/gap-link batch
3. Rol önerisi yoksa: `POST /api/curation/role-suggest` _(öneri)_ — Gemini Flash background
4. Kart click → `POST /api/translate?paper_id=...&target=tr` _(öneri)_ — 2-satır
5. Anotasyon → `POST /api/curation/annotation` _(öneri)_
6. Export → `GET /api/curation/export?project_id=&format=apa` _(öneri)_

### Veri akışı
- Anchor seçildiğinde p-4 → "sepete at" → `POST /api/curation/pool` (paper batch insert into `project_pool`)
- Background: role-suggest queue worker → 6 rolden bir öneri, kullanıcı kabul/değiştir
- TR çeviri lazy: kart açıldığında istek → cache hit %85 hedef

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon:** kapalı
- **Öğrenci:** havuz 50 paper / proje, basic mühür, çeviri 100/gün
- **Araştırmacı:** havuz 100 paper, validator çift-mühür, çeviri 250/gün
- **Profesyonel:** havuz 200 paper + Gemini 2.5 Pro (uzun bağlam · 10+ paper batch rol önerisi) + sınırsız çeviri

---

## AÇIK SORULAR
1. **In-memory → Supabase geçiş** ne zaman? Plan KD-36 dedi, hâlâ yok. F-N planı?
2. **6 rol enum** kararı (B-NNN) var mı? Mock'ta sabit; backend'e kanonize edilmeli.
3. **Validator API maliyeti:** Dimensions paid; ücretsiz proxy (OpenAlex `cited_by_count`) yeterli mi?
4. **r-ESTRA paper-uyum %** formülü: paper.w_estra vektörü vs user_style_profile vektörü cosine? Karar nerede?
5. **"Boşluk × bu paper" inverted lookup** (Wow #1) — gap_heatmap M-cell vektörünü paper ESTRA ile cosine? Eşik?
6. **Doygunluk %72** nasıl hesaplanır? 6 raf × hedef-min mi? Karar?
7. **APA/RIS/BibTeX/DOCX export** kütüphane (pylatex/citeproc-py)? Yeni service module gerek.
8. **Çoklu proje desteği:** reading-list global; project_pool proje-spesifik. Geçişte data migration?

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar Curation 2 sayfa · p-5 | `PaperMind_mock_v1.0.html` | 611-613 |
| 2 | p-5 page block | `PaperMind_mock_v1.0.html` | 1361-1439 |
| 3 | techspec back/front/data | `PaperMind_mock_v1.0.html` | 1367-1373 |
| 4 | 6 raf chip + sayaç | `PaperMind_mock_v1.0.html` | 1386-1393 |
| 5 | Paper kart (rol+mühür+gap) | `PaperMind_mock_v1.0.html` | 1395-1424 |
| 6 | TR özet okuyucu paneli | `PaperMind_mock_v1.0.html` | 1426-1436 |
| 7 | reading-list endpoint (4 op) | `api/routes/reading_list.py` | 32-86 |
| 8 | In-memory store uyarı (KD-36) | `api/routes/reading_list.py` | 26-29 |
| 9 | Status enum 4-değerli | `api/models/reading_list.py` | 14 |
| 10 | Pydantic forbid + 64-char paper_id | `api/models/reading_list.py` | 17-29 |
