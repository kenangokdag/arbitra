# F5-S0 — `dim_field` Taksonomi Tablosu (Plan Manifest)

> **Statü:** EXECUTING — Omer "plan onaylandı" (2026-05-03); 3 atomic commit yazıldı (A: parquet PASS Drive'da; B: 0011 migration; C: seed script + polars dep). PR açma + §13 doğrulama Omer'in sonraki adımı.
> **Tarih:** 2026-05-03
> **Bağımlılık:** PROMPT #2 (FieldPicker + user_profiles.field_primary[]) ve PROMPT #3 (kullanıcı embedding) bu plan'a bağlı.
> **Faz konumu:** F5 onboarding sprint'inin önkoşul micro-faz'ı (F5-S0).

---

## §0 — Bağlam (Brain referansları)

- **K-007** (2026-05-03): `dim_field` tablosu kurulacak; warehouse'tan distinct field upload.
- **K-009** (2026-05-03): `/onboarding` tüm alanlar zorunlu; `profile_complete=true` garantili.
- **K-010** (2026-05-03): Sistem iç dili = İngilizce. Embedding/retrieval/ranking EN'de. LLM = çevirmen.
- **K-011** (2026-05-03, **revize**): DB tek dil = EN, **ileri yönlü uygulanır**. Yeni taksonomi tabloları (`dim_field` ve sonrası) yalnız `name_en`. Mevcut `dim_theme` (B-002, 2026-04-29) name_tr+name_en **muaf** — post-MVP refactor (S16 OPEN_QUESTIONS). Bu PR retroactive değişiklik yapmaz.
- **K-019** (2026-05-03): `dim_field` granularity = **OpenAlex level-1 only** (~26 satır). Subfield (~280) + topic (4500+) DAHİL DEĞİL. A4 alt sınırı `≥30` → **`≥20`** revize.
- **K-001**: 4-katman kuralı (UI niyet + data contract + endpoint imzası + veri kaynağı) — bu plan data contract + veri kaynağı katmanını sabitler; UI + endpoint PROMPT #2'ye düşer.

---

## §1 — Hedef ve scope

`/onboarding` sayfasındaki "research field" dropdown'unu besleyecek `public.dim_field` tablosunu kur ve doldur.

- **Kaynak:** Papermind_V2 warehouse `fact_paper_field.parquet` (N04D out, W-30 manifest); group-by `primary_field` (OpenAlex level-1, EN-canonical).
- **Çıktı:** Supabase'de live, RLS aktif, sorgulanabilir, idempotent yüklü tablo.
- **Boyut beklentisi:** ~26 satır (OpenAlex level-1; K-019). A4 alt sınır `≥20`, üst sınır `≤500` (savunma).

---

## §2 — Kapsam DIŞI (bu plan'da yapılmayacak)

| Madde | Nereye |
|---|---|
| Frontend `FieldPicker` komponenti | PROMPT #2 |
| `user_profiles.field_primary` text → text[] migration | PROMPT #2 |
| Runtime UI dil sunumu (LLM çeviri) + cache | PROMPT #2 + S14 OPEN_QUESTIONS |
| `dim_method`, `dim_subfield` (ayrı tablolar) | İleride; bu plan'da YOK |
| `description`, `keywords`, `parent_field_id` kolonları | İleride (gerekirse 0012) |
| Authentication akışı | O-1 ayrı görev |
| Test coverage (pytest/vitest) | Opsiyonel (prompt da öyle diyor) |
| `dim_theme` retroactive K-011 düzeltmesi | Yapılmaz; B-002 dondurulu (§11 not) |

---

## §3 — Önkoşullar + envanter (kanıtlı yollar)

### 3.1 App tarafı
- **Migration kanon dizini:** `~/Code/papermind-app/db/migrations/` (web/supabase/, api/migrations/, supabase/, api/db/migrations/ **YOK** — doğrulandı `ls`)
- **Mevcut migration'lar:** `0001_init_schema_v1.sql` … `0009_reading_status_notes.sql` (repo'da görünen son numara 0009)
- **STATE.md çelişkisi:** `0010_paper_flags_temporal` uygulandığı yazılı (B-027) ama dosya repo'da **yok** (Dashboard paste). → §10 OQ-1
- **Supabase client pattern:** `api/services/_mocks.py` + 5-katman concrete servisleri var; ama upload script için **`api/scripts/`** klasörü **YOK** → oluşturulacak (1 dizin + 1 dosya)
- **DB connection:** `.env`'de `DATABASE_URL` Session Pooler (Brain memory `project_supabase_existing_data.md` kanıtlı; Direct IPv6 çalışmaz)

### 3.2 Warehouse tarafı (§A1 envanter SONUÇ — 2026-05-03)

**Notebook dizinleri:**
- `~/Desktop/PaperMind_V2/01_aday_notebooks/` (development)
- `~/Desktop/PaperMind_V2/02_production_notebooks/` (kanonik)
- `~/Desktop/PaperMind_V2/06_scripts/` (script kanon — prompt'un yazdığı `02_scripts/` boş)

**4 aday değerlendirmesi:**

| # | Notebook | Anahtar hücre | Çıktı | Verdict |
|---|---|---|---|---|
| 04 | `04_N04A_v5_alan_mapping` | H2: `dim_alan_komsuluk` A01..A20 (Türk YÖK kodları); H3: `dim_field_to_alan.parquet` bridge | `fact_paper_alan.parquet` | ❌ REJECT — Türk lokal taksonomi, K-010 ihlal |
| 05 | `05_N04B_a1_taksonomi_v2` | H2: `WEAK_REVIZE = {'M11':[], ...}` metod weak-keyword | metod config | ❌ REJECT — metod, field değil |
| 12 | `12_N04B_a7_inference` | H6: `OUT = FACTS / 'fact_paper_metod.parquet'` | metod inference | ❌ REJECT — metod, field değil |
| **16** | **`16_N04D_fact_paper_field`** | **H4: paper × theme (primary) → field/subfield/domain** | **`fact_paper_field.parquet`** | ✅ **ACCEPT — birincil kaynak** |

**Schema kanıtı (kaynak: N04D H7 manifest_W30.json payload, kanıt A):**
```json
"output": {
  "fact_paper_field": "<DRIVE_ROOT>/facts/fact_paper_field.parquet",
  "cols": 4,
  "schema": ["paper_id", "primary_field", "primary_subfield", "primary_domain"]
}
```

**Yedek (cross-check):** `dim_theme.parquet` (4516 satır × `field_name+subfield_name`, N04A H3 kanıt) — distinct ≈ 26 verecektir; ama paper_count agg için papers join gerek → ek iş. **N04D zaten paper×field bridge** olduğu için tek adım yeterli.

**Pinecone metadata cross-check:** `mdv1` namespace 8-meta `D/F/S/year/q_weak/method/lang/v_conf` — `F = field` zaten dağıtıldı (B-012 KAPANDI 2026-05-01); ortak kaynak doğrulaması.

**Output dizini:** `~/Desktop/PaperMind_V2/03_outputs/` **YOK** — A3'te `mkdir -p` ile oluşturulacak.

### 3.3 Mevcut Supabase envanteri
`~/Desktop/PaperMind_Supabase_Envanter.xlsx` (34 tablo, 2026-05-03) — **`dim_field` YOK** (Brain memory `project_supabase_phase3.md` kanıtlı).

---

## §4 — 7-kontrol (R2 / DM_RULES)

| K | Soru | Cevap |
|---|---|---|
| K1 | **Literatür** | OpenAlex Field/Subfield (5 + 26 = 31 level-0+1; topic'lerle 250+) sektörde standart. SciSpace/Consensus benzer taksonomi kullanıyor. ✅ |
| K2 | **Halüsinasyon** | Field değeri kaynağı **kanıtlandı** (Pinecone metadata `F`, B-012). Notebook ismi 4 aday — final seçim §A1 envanter sonrası, **uydurmuyorum**. Migration numarası AÇIK (OQ-1). |
| K3 | **Fayda-maliyet** | ~150 LOC + 1 saat (parquet extract + migration + script). Postgres ek <1MB. Net pozitif. ✅ |
| K4 | **Daha kolayı** | Alternatif: hardcoded `OPENALEX_FIELDS = [...]` enum frontend'de. RED — global çözüm değil, bakım pahalı, K-007 ihlal. ✅ tablo doğru. |
| K5 | **Son kullanıcı** | Onboarding'de field seçimi → ESTRA-R kişiselleştirme + Pinecone metadata HARD filter (B-012 `F` field) → arama relevansı doğrudan artar. ✅ |
| K6 | **Rakip** | SciSpace dropdown'u var (~60 alan); Consensus tag-based; Elicit free-text (zayıf). Bizimki structured + EN-canonical → multilang LLM render avantajı. ✅ |
| K7 | **Lokal/global** | Tablo 25M corpus + tüm dil + tüm onboarding tier'larında çalışır. Global. ✅ K-011 uyumlu. |

**Sonuç:** 7/7 GREEN. **OQ-1 (migration numarası)** yalnız taktik açıklık.

---

## §5 — R13 Council (zorunlu, R13.3)

**Alan:** Backend + Veri (warehouse → DB)
**Alan sahibi (BAĞLAYICI):** Sercan (Backend Lead — schema + migration + RLS); Frontend Lead **boş** (post-hoc onay açık iş).

| # | Üye | Beklenen oy | Olası RED gerekçesi |
|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟡 → OQ-1 cevaplanmadan GREEN değil | "0010 mu 0011 mi?" repo state vs STATE.md çelişkisi |
| 2 | Akademik İsabet | 🟢 | OpenAlex resmi taksonomi, kanıt A |
| 3 | Fayda-Maliyet | 🟢 | <1MB + ~150 LOC, net pozitif |
| 4 | Daha İyisi Var Mı? | 🟢 | Hardcoded enum reddedildi (K7) |
| 5 | Global Çözüm | 🟢 | EN-canonical + LLM runtime çeviri (K-010) |
| 6 | Son Kullanıcı Avukatı | 🟢 | Onboarding adım 1 — friction-free dropdown |
| **A** | **Sercan (Backend, BAĞLAYICI)** | **YELLOW olası** | RLS only-authenticated SELECT + service_role write — sade, prod uygun. UNIQUE name_en field çakışması riski (Computer Science vs CS) — §10 OQ-2. |

**Karar kuralı:** OQ-1 + OQ-2 cevaplanınca Council yeniden toplanır; sonuç plan §18'e işlenir.

---

## §6 — Atomic commit boundary (R7) — KİLİTLİ

**3 atomic commit, sıralı:**

| # | Slice | Dosyalar | Test/kanıt |
|---|---|---|---|
| 1 | **A** Warehouse extract | `~/Desktop/PaperMind_V2/06_scripts/extract_dim_field.py` (yeni) + `~/Desktop/PaperMind_V2/03_outputs/dim_field_seed.parquet` (data, repo'ya commit edilmez — Drive yerel) | A4 smoke verdict PASS print + Top-30 göz testi PASS verdict (Omer onayı) |
| 2 | **B** Migration + Schema | `~/Code/papermind-app/db/migrations/0011_create_dim_field.sql` | psql apply log + `\d public.dim_field` çıktı + RLS verify |
| 3 | **C** Upload script | `~/Code/papermind-app/api/scripts/__init__.py` + `~/Code/papermind-app/api/scripts/seed_dim_field.py` + `~/Code/papermind-app/pyproject.toml` (polars dep eklenir — parquet read için) | İlk çalıştırma N satır insert; ikinci çalıştırma 0 yeni satır + 0 hata (idempotent) |

> **Not:** Plan-time atomic boundary. Plan dışı dosya edit denemesi → R7 STOP, plan revize.
> Slice A veri çıktısı (`dim_field_seed.parquet`) Drive'da yaşar, repo'da değil; B+C app repo'sunda atomic commit olur.

---

## §7 — Mimari kararlar (DM-NNN proposal)

**DM-XXX (yeni — onay sonrası numarası atanır):** `dim_field` taksonomi tablosu, K-011 ilk uygulayıcı (yalnız `name_en`).

- **Primary key:** `field_id text` — slug formundan türetilmiş (`re.sub(r'[^a-z0-9]+', '_', name_en.lower()).strip('_')`); deterministik + idempotent upsert için PK olarak slug değil türev kimlik tercih edildi (slug ayrı UNIQUE kalır; isim değişirse field_id korunur — gelecek-uyumlu).
- **`name_en` UNIQUE:** Prompt şartı. Riski OQ-2'de (eşadlı field çakışması).
- **`paper_count_total integer DEFAULT 0`:** Warehouse'tan dolu; `int` (bigint değil) çünkü 25M < INT32 max.
- **RLS:** `authenticated` SELECT only; service_role write (mevcut migration konvansiyonu `0001`'le birebir).
- **`updated_at` trigger:** `public.set_updated_at` mevcut helper kullanılır (0001'de tanımlı), prompt'taki SQL bu konvansiyona göre revize edilir (DEFAULT now() yerine BEFORE UPDATE trigger).
- **`IF NOT EXISTS`:** Mevcut `0001`'de YOK; konvansiyona uyum için **kaldırılır**. (Migration zaten transactional ve `schema_migrations` tarafından idempotent koruma altında.)

---

## §8 — Test stratejisi

| Kapı | Yöntem | Eşik |
|---|---|---|
| A4 smoke | Polars/DuckDB assert (4 invariant: 30≤N≤500 + non-null + min_len≥2 + uniqueness) | PASS |
| Schema doğrulama | `\d public.dim_field` + information_schema | 6 kolon, name_en NOT NULL, slug UNIQUE |
| RLS verify | Anon role ile SELECT → 0 satır veya permission denied | PASS |
| Idempotency | Script ikinci çalıştırma | 0 yeni satır, 0 hata |
| K-011 lint | `name_(?!en)[a-z]{2}|i18n|_tr$|_translation` regex | 0 match |
| Göz testi | Top-10 by paper_count_total | Akademik anlam ifade ediyor |

**pytest/vitest:** Kapsam dışı (prompt opsiyonel). Sercan post-hoc PR review batch'inde ekleyebilir.

---

## §9 — Risk + halüsinasyon kayıt (HK-1..HK-7)

| HK | Uygulanması |
|---|---|
| HK-1 Pydantic forbid | Upload script DTO `extra="forbid"` (parquet → pydantic model bypass'a izin yok) |
| HK-2 Sayı kaynağı kod yorumunda | `# kaynak: <notebook>.<cell>` her threshold için |
| HK-3 Empirik kanıt | Migration apply çıktısı + smoke verdict snapshot fixture |
| HK-4 Runtime assertion | Upload öncesi `assert df['name_en'].n_unique() == df.shape[0]` |
| HK-5 Manifest verify | Parquet row count + schema check öncesi upsert |
| HK-6 No `Any` leak | mypy strict (api/scripts altı strict mode) |
| HK-7 Reproducibility | Slug regex deterministik; seed gerekmez (no randomness) |

---

## §10 — AÇIK SORULAR (KAPALI — Omer karar verdi 2026-05-03)

| # | Soru | Karar |
|---|---|---|
| OQ-1 | 0010 dosya repo'da yok; yeni migration 0010 mı 0011 mi? | ✅ **0011** (collision güvenliği; 0010 backfill ayrı PR — S17 OPEN_QUESTIONS) |
| OQ-2 | UNIQUE name_en collision stratejisi | ✅ **(d) field-only, OpenAlex level-1 sadece** (~26 satır); subfield/topic dahil değil; A4 ≥30 → ≥20 (K-019) |
| OQ-3 | Notebook hücre vs ayrı script | ✅ **Ayrı script `06_scripts/extract_dim_field.py`** (review temiz, atomic commit boundary saf) |
| OQ-4 | paper_count_total kaynağı | ✅ **`fact_paper_field.parquet` group-by primary_field** (N04D out, tek adım) |

**Yeni açık sorular (göz testi sonrası kontrol):**
- **OQ-G1** (göz testi gate): Top-30 tablosunda **>50 satır** gelirse → subfield karışmış, `level` filter eklenmeli (durup düzelt)
- **OQ-G2:** **<20 satır** → A4 FAIL, kaynak yetersiz, plan revize
- **OQ-G3:** TR/lokal isimler karışırsa → K-010 ihlal, durup düzelt

---

## §11 — K-010/K-011 uyum kontrolü (Omer cümlesi, 2026-05-03)

> **K-011 ileri yönlü uygulanır.** Yeni `dim_field` yalnız `name_en` taşır. Mevcut `dim_theme` (B-002, 2026-04-29) `name_tr+name_en` **muaf** — post-MVP refactor (S16 OPEN_QUESTIONS). Bu PR retroactive değişiklik yapmaz.

- **`dim_field`:** ✅ K-011 uyumlu — yalnız `name_en` (kolon adlarında `_tr/_id/_lang/i18n` YOK).
- **`dim_theme`:** muaf, dondurulu, S16'da yeniden değerlendirilir.
- **Lint adımı (§13 SQL #4):** Yalnız `dim_field` üzerinde; `dim_theme` muaf.

---

## §12 — Kabul kriterleri (8/8 PASS zorunlu — prompt §Kabul)

1. `dim_field_seed.parquet` 30-500 satır, A4 smoke PASS
2. Migration uygulandı; `\d public.dim_field` doğru schema
3. RLS aktif; anon SELECT 0 satır / permission denied
4. `SELECT count(*) FROM dim_field;` ≥ 30
5. Upload ikinci çalıştırma idempotent (row count sabit, 0 hata)
6. `count(*) WHERE name_en IS NULL = 0`
7. Top-10 by paper_count_total makul akademik alanlar (göz testi)
8. K-011 regex lint = 0 match

---

## §13 — Doğrulama SQL (PR'a yapıştırılır)

```sql
-- 1. Schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='public' AND table_name='dim_field'
ORDER BY ordinal_position;

-- 2. RLS politikaları
SELECT polname, polcmd, polroles::regrole[]
FROM pg_policy WHERE polrelid='public.dim_field'::regclass;

-- 3. Veri sağlığı
SELECT count(*) AS total, count(DISTINCT name_en) AS unique_names FROM public.dim_field;
SELECT name_en, slug, paper_count_total
FROM public.dim_field ORDER BY paper_count_total DESC LIMIT 10;

-- 4. K-011 ihlal kontrolü
SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='dim_field'
  AND column_name ~ '(name_(?!en)[a-z]{2}|i18n|_tr$|_translation)';
-- beklenen: 0 satır
```

---

## §14 — PR açıklaması iskeleti

- Plan manifest yolu: `docs/plans/F5_S0_dim_field_taxonomy.md`
- 7-kontrol özeti (her madde 1 satır — §4'ten kopya)
- Doğrulama SQL çıktıları (yapıştır)
- A4 smoke verdict çıktısı
- OQ-1..OQ-4 cevap özeti (Omer kararı)
- Kapsam dışı liste (§2 kopya)

---

## §15 — Commit mesajı (her commit için ayrı)

**Commit 1 (A):**
```
feat(warehouse): extract dim_field seed parquet (K-007/K-010)

- Source: <seçilen notebook> distinct (name_en, paper_count_total)
- Output: ~/Desktop/PaperMind_V2/03_outputs/dim_field_seed.parquet
- Smoke A4 PASS: <N> rows, non-null, len≥2, unique
```

**Commit 2 (B):**
```
feat(supabase): add dim_field migration <NNNN> (K-011)

- Single-language schema: name_en only (no _tr/_id/_lang)
- RLS: authenticated SELECT, service_role write
- Indexes: slug, paper_count_total DESC

Refs: BRAIN K-007/K-010/K-011 · DECISIONS B-NNN
```

**Commit 3 (C):**
```
feat(api): idempotent dim_field seed upload script

- Upsert via service_role on conflict=field_id
- Slug derivation: lower + non-alnum→_ + dashify
- Second run: 0 new rows, 0 errors

Refs: plans/F5_S0_dim_field_taxonomy.md
```

---

## §16 — Tahmini efor

| Slice | LOC | Süre |
|---|---|---|
| A Warehouse extract | ~50 (script yoluna gidilirse) veya ~30 (notebook hücre) | ~30 dk |
| B Migration SQL | ~40 | ~15 dk |
| C Upload script | ~80 | ~45 dk |
| OQ-1..OQ-4 cevaplama + plan revize | — | ~15 dk |
| **Toplam** | **~150 LOC** | **~2 saat** |

---

## §17 — Karar günlüğü (DM-NNN proposal)

**DM-XXX:** `dim_field` K-011 ilk uygulama (yalnız name_en); UI çevirisi runtime LLM. PR onayında DECISIONS.md'ye atanır (R6.2, Omer onayı sonrası).

---

## §18 — §Council toplanma kayıt yeri

OQ-1..OQ-4 cevaplanınca buraya §Council toplantı tablosu eklenecek (R13.4 + R13.9 alan sahibi BAĞLAYICI satırı zorunlu).

---

## §A2 — Extract kodu (UNBLOCKED ✅, 2026-05-03)

**Statü:** ✅ UNBLOCKED — Schema + Top-30 + GATE PASS, Omer onayı (§A1.5 kanıt).

**Manifest payload kanıtı (N04D H7):** `schema = ['paper_id', 'primary_field', 'primary_subfield', 'primary_domain']` — kolon adı **`primary_field`** (level-1).

**Önerilen extract (göz testi PASS sonrası kilitlenir):**

```python
# kaynak: ~/Dataleak/facts/fact_paper_field.parquet (N04D H7 manifest schema)
import polars as pl
from pathlib import Path

DRIVE_ROOT = Path.home() / 'Dataleak'  # Colab: /content/drive/MyDrive/Dataleak
SRC = DRIVE_ROOT / 'facts' / 'fact_paper_field.parquet'
OUT = Path('~/Desktop/PaperMind_V2/03_outputs/dim_field_seed.parquet').expanduser()
OUT.parent.mkdir(parents=True, exist_ok=True)

# HK-5 schema kanıtı pre-flight
schema = pl.scan_parquet(SRC).collect_schema()
assert 'primary_field' in schema.names(), f'primary_field kolonu yok! schema={schema}'

# group-by extract (K-019 level-1 only)
df = (pl.scan_parquet(SRC)
        .group_by('primary_field')
        .agg(pl.len().alias('paper_count_total'))
        .filter(pl.col('primary_field').is_not_null())
        .filter(pl.col('primary_field').str.len_chars() >= 2)
        .rename({'primary_field': 'name_en'})
        .sort('paper_count_total', descending=True)
        .collect())

df.write_parquet(OUT)
```

## §A4 — Smoke verdict (REVİZE: ≥20, K-019)

```python
assert 20 <= df.shape[0] <= 500, f'satır {df.shape[0]} aralık dışı'
assert df['name_en'].is_not_null().all(), 'NULL var'
assert df['name_en'].str.len_chars().min() >= 2, 'kısa isim var'
assert df['name_en'].n_unique() == df.shape[0], 'duplicate var'
print(f'PASS A4 — {df.shape[0]} satır')
```

---

## §A1.5 — Dış oturum çıktı kaydı (PASS, 2026-05-03 Omer onaylı)

```
============================================================
SCHEMA (collect_schema)
============================================================
  paper_id                        String
  primary_field                   String
  primary_subfield                String
  primary_domain                  String

============================================================
GROUP-BY primary_field — TOP 30
============================================================
Toplam distinct field: 26

primary_field                                          paper_count_total
---------------------------------------------------------------------------
Medicine                                                       5,943,324
Engineering                                                    3,362,141
Social Sciences                                                2,133,052
Biochemistry, Genetics and Molecular Biology                   1,804,453
Agricultural and Biological Sciences                           1,262,177
Environmental Science                                          1,226,658
Computer Science                                               1,209,184
Materials Science                                              1,002,576
Physics and Astronomy                                            879,119
Psychology                                                       774,332
Arts and Humanities                                              588,467
Business, Management and Accounting                              574,120
Health Professions                                               547,311
Chemistry                                                        523,269
Neuroscience                                                     490,045
Economics, Econometrics and Finance                              473,802
Earth and Planetary Sciences                                     436,152
Mathematics                                                      346,145
Immunology and Microbiology                                      331,696
Energy                                                           222,438
Decision Sciences                                                201,552
Dentistry                                                        152,350
Nursing                                                          142,199
Pharmacology, Toxicology and Pharmaceutics                       110,243
Chemical Engineering                                              84,711
Veterinary                                                        45,429

============================================================
GATE VERDICT
============================================================
  ✅ PASS — 26 satır (20 ≤ N ≤ 50 beklendi)
  ✅ K-010 — TR karakter yok
```

**Verdict özeti (Omer onaylı):** Schema = OpenAlex ASJC level-1 dağılımı; "Chemical Engineering" Engineering'den ayrı (OpenAlex sınıflama), "Physics and Astronomy" birleşik — tablo bunları olduğu gibi alır, sorun yok.

### Nokta-prompt (kayıt için saklanır — gelecek ihtiyaç)

> **Hedef:** Schema kanıtı + Top-30 göz testi çıktısı al, plan §A2/§A4 kilitlemesi için.
> **Yer:** Colab notebook (yeni hücre, çalıştırma) veya lokal Python (`~/Dataleak` mount edilmişse).
> **Çıktı:** Aşağıdaki print blokları → bu plan'a yapıştırılır → Omer onayı.

```python
# === dim_field schema + göz testi (N04D fact_paper_field.parquet) ===
import polars as pl
from pathlib import Path

# Path setup (Colab vs lokal otomatik)
try:
    from google.colab import drive
    if not Path('/content/drive/MyDrive').exists():
        drive.mount('/content/drive', force_remount=False)
    DRIVE_ROOT = Path('/content/drive/MyDrive/Dataleak')
except ImportError:
    DRIVE_ROOT = Path.home() / 'Dataleak'

SRC = DRIVE_ROOT / 'facts' / 'fact_paper_field.parquet'
assert SRC.exists(), f'YOK: {SRC}'
print(f'Source: {SRC}')
print(f'Size:   {SRC.stat().st_size / 1024 / 1024:.1f} MB')

# === EK KOŞUL 1 — SCHEMA KANITI ===
print()
print('=' * 60)
print('SCHEMA (collect_schema)')
print('=' * 60)
schema = pl.scan_parquet(SRC).collect_schema()
for name, dtype in schema.items():
    print(f'  {name:30s}  {dtype}')

# === EK KOŞUL 2 — GÖZ TESTİ (Top-30 + count) ===
print()
print('=' * 60)
print('GROUP-BY primary_field — TOP 30')
print('=' * 60)
df = (pl.scan_parquet(SRC)
        .group_by('primary_field')
        .agg(pl.len().alias('paper_count_total'))
        .filter(pl.col('primary_field').is_not_null())
        .filter(pl.col('primary_field').str.len_chars() >= 2)
        .sort('paper_count_total', descending=True)
        .collect())

print(f'Toplam distinct field: {df.shape[0]}')
print()
print(f'{"primary_field":50s}  {"paper_count_total":>20s}')
print('-' * 75)
for row in df.head(30).iter_rows(named=True):
    print(f'{row["primary_field"][:50]:50s}  {row["paper_count_total"]:>20,}')

# === GATE VERDICT ===
print()
print('=' * 60)
print('GATE VERDICT')
print('=' * 60)
n = df.shape[0]
if n < 20:
    print(f'  ❌ FAIL — {n} < 20 (K-019 alt sınır), kaynak yetersiz')
elif n > 50:
    print(f'  ⚠️  WARN — {n} > 50, subfield karışmış olabilir; level filter gerekebilir')
else:
    print(f'  ✅ PASS — {n} satır (20 ≤ N ≤ 50 beklendi)')

# K-010 ihlal ön-tarama (TR/lokal isim algılama)
import re
suspects = [r for r in df['primary_field'].to_list() if re.search(r'[ğüşıöçĞÜŞİÖÇ]', str(r))]
if suspects:
    print(f'  ❌ K-010 ihlal — TR karakterli isim(ler): {suspects[:5]}')
else:
    print(f'  ✅ K-010 — TR karakter yok')
```

**Çıktı 3 blokta** (schema / top-30 / verdict) Omer'e döner. PASS + 26 civarı satır + EN-canonical → §A2 kilitlenir, §A3'e geçilir. WARN/FAIL → plan revize.

---

**KOD YAZIMI:** Bu plan onaylanmadan **tek satır kod yazılmaz** (R1, mutlak).

**Sonraki adım:**
1. ⏳ Omer §A1.5 nokta-prompt'u dış Colab oturumuna verir
2. ⏳ Schema + Top-30 + verdict çıktısı bu plan'a yapıştırılır
3. ⏳ Omer "plan onaylandı" der → §A3/§B/§C atomic commit yazımına geçilir
4. ⏳ PR aç → Omer kontrol → 8/8 PASS → merge
5. ⏳ Sonra `0010_paper_flags_temporal` backfill ayrı PR (S17 OPEN_QUESTIONS)
