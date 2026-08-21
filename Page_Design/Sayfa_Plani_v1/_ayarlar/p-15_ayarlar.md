# p-15 · Ayarlar

> Tezgah: **SİSTEM** (genel)
> 3 sekme: Profil · Bildirim & Veri · Veri Sağlığı L6 (DQ ledger).

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:2073-2134`
- **Sidebar:** `PaperMind_mock_v1.0.html:632`
- **Bu md:** `Page_Design/Sayfa_Plani_v1/_ayarlar/p-15_ayarlar.md`

## ROL
Ayarlar bir "kontrol kutusu" değildir; **kullanıcı-sistem sözleşmesinin görünür yüzü**'dür. KVKK + veri sağlığı + AI'ın kullanıcıdan ne öğrendiği. Üç kapı: kim olduğun (profil), neyi paylaştığın (bildirim & veri), sistemin sana ne kadar güvenebildiği (**veri sağlığı L6 = DQ ledger**). Ayırt edici: rakipler veri ambarı sağlığını kullanıcıdan saklar; PaperMind 30 warehouse tablosu × refresh tarihi × kapsama × hata sayısı × güven skorunu **şeffaflaştırır**.

## BACKEND ⚠ KISMEN VAR
`api/routes/onboarding.py` mevcut → profil yazımı (3-tier enum, field 1-3, subfield bridge, ORCID SHA-256). Mock'taki diğer endpointler **YOK**:

| Endpoint | Durum |
|---|---|
| `POST /api/onboarding` | ✓ var (`onboarding.py:54`) |
| `GET /api/settings/profile` | ❌ yok |
| `POST /api/settings/data-export` | ❌ yok (KVKK export) |
| `GET /api/settings/dq-ledger` | ❌ yok |
| `DELETE /api/settings/account` | ❌ yok (KVKK silme) |
| `GET /api/settings/silent-ledger?days=30` | p-10'da önerilmiş (paylaşılan) |
| `GET /api/settings/sycophant-history` | p-10'da önerilmiş (paylaşılan) |

## DB ⚠ KISMEN VAR
- `auth.users` + `user_profiles` (tier enum, ORCID hash) — ✓ var (`0012_user_profile_fields_and_tier_refactor.sql`)
- `user_profile_fields` (1-3 alan bridge) — ✓ var (`0012`)
- `user_profile_subfields` bridge — ✓ var (`0014_user_profile_subfields_bridge.sql`)
- `dim_user_v3` — ❌ yok (mock 2083 var-saymış; gerçekte `user_profiles` + bridge tablo var)
- `fact_user_consent_log` (KVKK aydınlatma onay tarihçesi) — ❌ yok
- `fact_warehouse_dq_ledger` (30 warehouse tablosu × refresh × hata × güven) — ❌ yok

**Tier modeli net:** DB 3-tier enum (`0012` K-013): `ogrenci` / `arastirmaci` / `profesyonel`, default `ogrenci`. Anon = giriş yapmamış (DB satırı yok). Mock'taki eski T0-T4 5-tier görsel revize edildi.

---

## ÖNERİ: Eksik Backend

### `0027_settings_dq_consent.sql`

```sql
-- fact_user_consent_log — KVKK aydınlatma onay tarihçesi
CREATE TABLE public.fact_user_consent_log (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  consent_type    text NOT NULL CHECK (consent_type IN ('kvkk_aydinlatma','data_processing','llm_use','marketing')),
  consent_version text NOT NULL,         -- '2026-04-12-v1'
  granted         boolean NOT NULL,
  granted_at      timestamptz NOT NULL DEFAULT now(),
  revoked_at      timestamptz,
  ip_hash         text,                  -- audit (SHA-256)
  user_agent_hash text
);

CREATE INDEX idx_consent_user_type
  ON public.fact_user_consent_log (user_id, consent_type, granted_at DESC);

-- fact_warehouse_dq_ledger — sinyal: 30 tablo × günlük refresh
CREATE TABLE public.fact_warehouse_dq_ledger (
  table_name      text NOT NULL,
  layer           text NOT NULL CHECK (layer IN ('L0','L1','L2','L3','L4','L5','L6')),
  refreshed_at    timestamptz NOT NULL,
  row_count       bigint NOT NULL,
  error_count_7d  int NOT NULL DEFAULT 0,
  coverage_pct    real CHECK (coverage_pct BETWEEN 0 AND 1),
  trust_score     real NOT NULL CHECK (trust_score BETWEEN 0 AND 1),
  last_error_msg  text,
  PRIMARY KEY (table_name, refreshed_at)
);

CREATE INDEX idx_dq_table_recent
  ON public.fact_warehouse_dq_ledger (table_name, refreshed_at DESC);

-- mart_warehouse_dq_summary — UI'da görünen son satır (her tablo için en güncel)
CREATE MATERIALIZED VIEW public.mart_warehouse_dq_summary AS
SELECT DISTINCT ON (table_name)
  table_name, layer, refreshed_at, row_count, error_count_7d, coverage_pct, trust_score, last_error_msg
FROM public.fact_warehouse_dq_ledger
ORDER BY table_name, refreshed_at DESC;

-- Account silme talebi (KVKK 30g grace period)
CREATE TABLE public.user_account_deletion_request (
  user_id       uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  requested_at  timestamptz NOT NULL DEFAULT now(),
  scheduled_at  timestamptz NOT NULL,    -- requested_at + 30d
  cancelled_at  timestamptz,
  executed_at   timestamptz
);
```

### Yeni endpoint'ler

#### `GET /api/settings/profile`
- **Out:**
  ```json
  {
    "user_id":"...","email_hash":"...","tier":"profesyonel",
    "fields":[{"field_id":"PSY","position":1},...],
    "subfields":[{"subfield_id":"...","field_id":"PSY"},...],
    "language_pref_ui":"tr",
    "orcid_present": true,
    "consent_state":{
      "kvkk_aydinlatma":{"granted":true,"version":"2026-04-12-v1","granted_at":"..."},
      "llm_use":{"granted":true},
      "marketing":{"granted":false}
    },
    "r_estra_snapshot": {"cesur":0.71,"derin":0.66,"tarafsiz":0.69}
  }
  ```
- **Flow:** RLS `auth.uid() = user_id`, `user_profiles` + bridge JOIN

#### `POST /api/settings/data-export` (KVKK export)
- **In:** `{format:'json'|'pdf'|'both'}`
- **Out:** `{export_id:"...", url:"https://...gz", expires_at:"..."}` (24h pre-signed URL)
- **Flow:**
  1. Tüm kullanıcı verisi: profile + projects + chat_messages + reading_list + authoring_session + jury_session + style_log + consent_log
  2. JSON pretty + (opsiyonel) PDF render
  3. gzip → Supabase Storage upload (private bucket, 24h TTL)

#### `GET /api/settings/dq-ledger`
- **Out:**
  ```json
  {
    "rows":[
      {"table":"fact_paper_quality_v3","layer":"L4","refreshed_at":"2026-05-08","row_count":12400000,"error_7d":0,"trust":0.97},
      {"table":"fact_paper_w_estra","layer":"L4","refreshed_at":"2026-05-08","row_count":12100000,"error_7d":0,"trust":0.95},
      {"table":"fact_paper_bibcoupling_top50","layer":"L4","refreshed_at":"2026-05-07","row_count":643000000,"error_7d":2,"trust":0.88},
      ...30 row
    ],
    "summary":{"avg_trust":0.92, "errors_7d":3, "tables_total":30}
  }
  ```
- **Flow:** `mart_warehouse_dq_summary` direkt fetch; ETL job (cron) ledger'ı günlük doldurur

#### `DELETE /api/settings/account` (KVKK silme — 30g grace)
- **In:** `{confirm_phrase:"hesabımı sil"}` (anti-misclick)
- **Out:** `{scheduled_at:"...", cancellable_until:"..."}`
- **Flow:**
  1. Insert `user_account_deletion_request` with `scheduled_at = now() + 30d`
  2. 30g sonra cron → cascade DELETE (auth.users → tüm bağlı tablolar)
  3. Kullanıcı `POST /api/settings/account-cancel-deletion` ile geri alabilir

---

## SAYFA YAPISI (ASCII)

```
┌── 15 · Ayarlar ── profil · bildirim & veri · veri sağlığı L6 ────────────┐
│ Felsefe: Sözleşmenin görünür yüzü; KVKK + veri sağlığı + AI öğrenmesi.  │
│                                                                            │
│ ┌── Simülasyon · 3 sekme · Veri Sağlığı L6 sekmesi açık (araştırmacı) ┐│
│ │ [Profil] [Bildirim & Veri] [Veri Sağlığı L6 ✓] ◀ aktif              ││
│ │                                                                          ││
│ │ ┌── DQ ledger · 30 warehouse tablosu · özet ────────────────────────┐││
│ │ │ tablo                          | katman | son taze   | satır  | err7g| güven │││
│ │ │ fact_paper_quality_v3          |  L4   | 2026-05-08 | 12.4M  |  0  | 🟢.97 │││
│ │ │ fact_paper_w_estra             |  L4   | 2026-05-08 | 12.1M  |  0  | 🟢.95 │││
│ │ │ fact_paper_bibcoupling_top50   |  L4   | 2026-05-07 | 643M   |  2  | 🟡.88 │││
│ │ │ fact_paper_pvalue_extraction   |  L5   | 2026-05-06 | 1.8M   |  0  | 🟢.94 │││
│ │ │ fact_paper_gap_v3              |  L5   | 2026-05-08 | 8.4M   |  1  | 🟡.91 │││
│ │ │ fact_paper_citation_role_v2    |  L5   | 2026-05-04 | 38.2M  |  0  | 🟢.93 │││
│ │ └─────────────────────────────────────────────────────────────────────┘│││
│ │ … 24 tablo · ortalama güven 0.92 🟢 · son 7g hata 3                   ││
│ │                                                                          ││
│ │ ┌── Tier · araştırmacı ───────┐ ┌── KVKK + veri export ────────────┐ ││
│ │ │ Akış: Authoring + Defense ✓│ │ • Aydınlatma: ✓ (2026-04-12)     │ ││
│ │ │ ESTRA Pasaport: 6 sinyal    │ │ • Veri export: [JSON+PDF indir]  │ ││
│ │ │ Pinecone semantik arama     │ │ • Hesap silme: [talep et 30g]    │ ││
│ │ │ Profesyonel'e yükselt:      │ │ • Sycophant kilit log: 2 olay    │ ││
│ │ │  + Gemini 2.5 Pro · sınrsz  │ │   (son 30g)                      │ ││
│ │ └─────────────────────────────┘ └──────────────────────────────────┘ ││
│ └──────────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **Üst sekme bar:** 3 sekme (Profil · Bildirim & Veri · Veri Sağlığı L6) — aktif sekme `var(--ink)` bg + beyaz text + radius `4px 4px 0 0`
- **Veri Sağlığı sekmesi (mock'ta default açık):** sticky header tablo, 6 satır görünür + "24 tablo daha" link
- **Tier kartı (sol alt):** `#dcfce7` yeşil bg, mono başlık "Tier · araştırmacı" (kullanıcı tier'ına göre değişir), özet satır + upgrade CTA
- **KVKK kartı (sağ alt):** `#fafaf7` gri bg, 4 satır (aydınlatma/export/hesap silme/sycophant log)
- **Veri export butonu:** outline `var(--ink)` border + small text "JSON+PDF indir"
- **Hesap silme butonu:** outline `#dc2626` red border + red text "talep et (30g)"

### Back (öneri)
1. Sayfa mount → paralel: `GET /settings/profile` + `GET /settings/dq-ledger`
2. Sekme switch lazy load: "Bildirim & Veri" sekmesi → `GET /settings/silent-ledger` + `GET /settings/sycophant-history`
3. "JSON+PDF indir" → `POST /settings/data-export` → polling 24h URL
4. "talep et (30g)" → confirmation modal "hesabımı sil" type-to-confirm → `DELETE /settings/account`

### Tier display (DB 3-tier doğrudan)
```python
TIER_DISPLAY = {
    "ogrenci": "Öğrenci",
    "arastirmaci": "Araştırmacı",
    "profesyonel": "Profesyonel",
}
# Anon = giriş yapmamış kullanıcı (DB satırı yok, vitrin Q'ya yönlendirilir)
# Backend tek doğruluk: user_profiles.tier ENUM
```

### DQ ledger ETL (öneri)
- Cron job (her gün 03:00 EU): 30 warehouse tablosu için `INSERT INTO fact_warehouse_dq_ledger`
- `trust_score` formülü: `(1 - error_7d/100) × coverage_pct × freshness_factor`
  - `freshness_factor = exp(-days_since_refresh / 7)`
- `mart_warehouse_dq_summary` REFRESH MATERIALIZED VIEW

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon:** Ayarlar sayfasına gelmez (login zorunlu)
- **Öğrenci / Araştırmacı / Profesyonel:** tam erişim — Profil + KVKK + DQ ledger şeffaflığı + export + sycophant log
- **KVKK uyum:** EU/TR kullanıcı için aydınlatma metni mecburi; consent_log audit trail (IP + UA hash)

---

## AÇIK SORULAR
1. **Mock revize:** Md'lerde 3-tier'e geçildi; mock `PaperMind_mock_v1.0.html` hâlâ T0-T4 görsel kullanıyor (satır 2118-2128). Mock revize ayrı iş.
2. **`fact_warehouse_dq_ledger` ETL kim doldurur:** ELT pipeline (`pipelines/` altında günlük cron) gerekli. Hangi tablo şu an env'de gerçek veri var, hangi simülasyon? Mock'ta 12.4M / 643M sayıları gerçek mi (B42-030 ile uyumlu mu)?
3. **`mart_warehouse_dq_summary` refresh stratejisi:** REFRESH MATERIALIZED VIEW CONCURRENTLY günlük mü, manuel API call ile mi?
4. **KVKK 30g grace cron:** Account silme cron job hangi servis çalıştıracak (Supabase Edge Function, GitHub Actions, k8s cron)?
5. **Veri export format kararı:** JSON+PDF mi yoksa sadece JSON mu? PDF rendering maliyetli (LaTeX/WeasyPrint). Plan 1'de JSON yetebilir.
6. **`r_estra_snapshot` profile'da ne sıklıkla güncellenir:** Her project ya da kullanıcı ortalaması? Hangi project'in ESTRA'sı gösteriliyor?
7. **ORCID raw → SHA-256 (`orcid_hash`):** Halihazırda `onboarding.py:50` implementasyonu var. Settings sayfasında "ORCID güncelle" butonu olacak mı? UPDATE flow eksik.
8. **Sessiz öğrenme defteri 30g (A3 ile aynı veri):** mock 2087 "tek veri kaynağı" — `mart_user_silent_ledger_30d` (p-10'da önerilmiş) bu sayfanın "Bildirim & Veri" sekmesinde de gösterilecek. Endpoint paylaşımı net.

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar Ayarlar p-15 | `PaperMind_mock_v1.0.html` | 632 |
| 2 | p-15 page block | `PaperMind_mock_v1.0.html` | 2073-2134 |
| 3 | techspec endpoint (profile/data-export/dq-ledger/account) | `PaperMind_mock_v1.0.html` | 2082 |
| 4 | data tables (dim_user_v3, consent_log, silent_ledger_30d, dq_ledger) | `PaperMind_mock_v1.0.html` | 2083 |
| 5 | Wow ayırt edici: DQ ledger görünür | `PaperMind_mock_v1.0.html` | 2086 |
| 6 | Δ revize: tier modeli (mock 5-tier eski; md 3-tier'e revize) | `PaperMind_mock_v1.0.html` | 2087 |
| 7 | 3 sekme bar + Veri Sağlığı aktif | `PaperMind_mock_v1.0.html` | 2093-2097 |
| 8 | DQ ledger tablosu (6 satır görünür + 24 tablo özet) | `PaperMind_mock_v1.0.html` | 2099-2114 |
| 9 | Tier yeşil kart (mock T2; md araştırmacı) | `PaperMind_mock_v1.0.html` | 2118-2121 |
| 10 | KVKK + veri export + hesap silme + sycophant log | `PaperMind_mock_v1.0.html` | 2122-2130 |
| 11 | Onboarding endpoint (kısmen var) | `api/routes/onboarding.py` | 1-60 |
| 12 | 3-tier enum + bridge migration | `db/migrations/0012_user_profile_fields_and_tier_refactor.sql` | 1-30 |
| 13 | Subfield bridge migration | `db/migrations/0014_user_profile_subfields_bridge.sql` | — |
