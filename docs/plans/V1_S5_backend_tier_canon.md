# V1-S5 — Backend Tier Canon Refactor (3-tier + anon)

**Sprint kodu:** V1-S5
**Süre:** 1 oturum
**Onay:** bekleniyor — "V1-S5 başla"
**Üst manifest:** `docs/plans/V1_vitrin_sprint.md` (drift kaynağı; bu sprint revize eder)
**Kanon kaynak:** `db/migrations/0012_user_profile_fields_and_tier_refactor.sql` (3-tier ENUM) + CLAUDE.md §6
**Şablon:** `docs/plans/V1_S6_q3_frontend_kabuk.md`

---

## §0 — Amaç

Backend tier modelini DB canon'una hizala: `T0/T1/T1+/T2/T3/T4` (6-tier) → `anon` + `ogrenci/arastirmaci/profesyonel` (4-mode). Frontend `useTierMock` zaten canon (V1-S2'de yapıldı); sırada backend `tier_gate.py` + bağlı route/test/doc. V1-S3 (Q1 LLM endpoint wire) bu refactor'sız tier uyumsuzluğu üretir — bu sprint V1-S3'ün önkoşuludur.

**Bugün biter:**
- `api/middleware/tier_gate.py` Tier enum 4-mode + QUOTA tablosu canon
- `api/routes/q.py` + `api/models/q.py` + `api/middleware/auth.py` + `api/config.py` tier string + comment uyum
- `tests/integration/test_q_routes.py` assertions `anon`/`ogrenci` ile günceli
- `docs/plans/V1_vitrin_sprint.md` 3-tier canon + DM-054 (Q2 elimine) + Q3 aktif olarak revize
- `CLAUDE.md` §6 "5-tier T0-T4 eski" satır canon
- `pytest tests/integration/test_q_routes.py`: PASS · `mypy` clean

---

## §1 — Drift hattı (mevcut → canon)

| Mevcut sembol | Canon karşılığı | Açıklama |
|---|---|---|
| `Tier.T0` | `Tier.ANON = "anon"` | DB'de yok, sadece in-memory |
| `Tier.T1` | `Tier.OGRENCI = "ogrenci"` | DB default tier (0012 migration) |
| `Tier.T1P` | (silinir) | Ücretli one-shot — V1'de "yakında", canon'da karşılığı yok |
| `Tier.T2` | (silinir) | V1 scope dışı |
| `Tier.T3` | (silinir) | V1 scope dışı |
| `Tier.T4` | (silinir) | V1 scope dışı |
| (yok) | `Tier.ARASTIRMACI = "arastirmaci"` | DB tier 2 — V1'de ogrenci ile aynı kota |
| (yok) | `Tier.PROFESYONEL = "profesyonel"` | DB tier 3 — V1'de ogrenci ile aynı kota |

**Quota stratejisi V1'de:** anon vs authed iki seviye; 3 authed tier şu an aynı kota (ogrenci default). İleride (V2/V3) authed tier'lar arası kota farklılaşırsa QUOTA tablosu tier-başına ayarlanır — V1-S5 scope'u rename + structure, kota ayrıştırma değil.

---

## §2 — Sınırlar (kapsam DIŞINDA)

- ❌ `LOCKED_SOON_PATHS`'tan `/api/q3` çıkarmak — V1-S7 (Q3 endpoint kanlı canlı yapılınca)
- ❌ Quota değer ayrıştırma (ogrenci=5, arastirmaci=20, profesyonel=100 vb.) — V2'de iş kararı
- ❌ Frontend tier UI değişikliği — `useTierMock` zaten canon, dokunulmaz
- ❌ DB ENUM değişikliği — 0012 migration zaten 3-tier
- ❌ Q4/Q5 endpoint test'leri — şu an `LOCKED_SOON_PATHS` dışında ama V1-S2 scope'unda değil; mevcut kotaları korunur, refactor'a tabi tutulur

---

## §3 — Atomic Commit Boundary (4 commit, bottom-up)

| # | Commit | Dosya | LOC | Test |
|---|---|---|---|---|
| V1-S5-01 | `refactor(api): tier_gate.py + q routes 6-tier T0..T4 → 4-tier anon+3-canon` | `api/middleware/tier_gate.py` (Tier enum + QUOTA + _tier_for_request + comments) + `api/routes/q.py` (`quota["tier"] == Tier.ANON.value` import + line 51) + `tests/integration/test_q_routes.py` (assertions T0/T1 → anon/ogrenci) | ~95 | `pytest tests/integration/test_q_routes.py` PASS · `mypy api/middleware` clean |
| V1-S5-02 | `refactor(api): q models + auth + config comment canon` | `api/models/q.py` (comments T0/T1 → anon/ogrenci) + `api/middleware/auth.py` (comments) + `api/config.py` (comment) | ~15 | `pytest` PASS (regression yok) |
| V1-S5-03 | `docs(plans): V1_vitrin_sprint.md 3-tier canon + DM-054 + Q3 aktif revize` | `docs/plans/V1_vitrin_sprint.md` (§0..§12 revize) | ~100 (revize) | doc-only |
| V1-S5-04 | `docs: CLAUDE.md §6 mock canon güncelle (4-mode anon+3-tier)` | `CLAUDE.md` (§6 tek satır) | ~3 | doc-only |

**Toplam:** ~210 LOC.
**Branch:** `feat/V1-S5-backend-tier-canon` (yeni — V1-S2+S6 PR henüz açık, V1-S5 bağımsız PR olur).

---

## §4 — Dosya Manifesti

**Değişen (7 dosya):**

```
api/middleware/tier_gate.py        [V1-S5-01 — Tier enum + QUOTA refactor]
api/middleware/auth.py             [V1-S5-02 — comment T0→anon]
api/routes/q.py                    [V1-S5-02 — string compare + comment]
api/models/q.py                    [V1-S5-02 — comment]
api/config.py                      [V1-S5-02 — comment]
tests/integration/test_q_routes.py [V1-S5-01 — assertion update]
docs/plans/V1_vitrin_sprint.md     [V1-S5-03 — full revize]
CLAUDE.md                          [V1-S5-04 — §6 satır]
```

**Yeni:** Yok (refactor only).

---

## §5 — Kritik kararlar (KD)

- **KD-V1-S5-01:** `Tier.OGRENCI` default authed tier (`_tier_for_request` user_id varsa OGRENCI). İleride DB'den profil fetch ile gerçek tier (`SELECT tier FROM auth.users WHERE id = ...`). V1-S5 scope'u: in-memory rename + canonical default.
- **KD-V1-S5-02:** `Tier.T1P` (ücretli one-shot) silinir; V1 mock'unda zaten "yakında" 403 dönüyordu — anon/3-tier canon'da yer almaz. İleride paid tier eklenirse ayrı ENUM (`paid_*`) önerilir.
- **KD-V1-S5-03:** QUOTA tablosu authed-tier'ların 3'ü için aynı limit (V1 scope). Ayrıştırma V2 iş kararı; bu sprint scope dışı.
- **KD-V1-S5-04:** `LOCKED_SOON_PATHS` aynı kalır (`/api/q2` + `/api/q3`); Q3 frontend kabuk açıldı ama backend endpoint V1-S7'de yapılacak. Frontend Q3 sayfası fixture-only render eder, `/api/q3` çağırmaz — mevcut 403 koruması zarar vermez.
- **KD-V1-S5-05:** Doc revize (V1-S5-03) `V1_vitrin_sprint.md` §0-§12'yi 3-tier'a çevirir; eski "T0-T4" referansları arşiv yerine **inline strikethrough yok** — temiz canon yazılır. Eski versiyon `git log` ile bulunur.

---

## §6 — Halüsinasyon Kod-Seviyesi

- **HK-1 Pydantic forbid:** Refactor'da yeni model yok; mevcut `Q*Request/Q*Response` ConfigDict aynı kalır.
- **HK-2 Kaynak yorum:** `tier_gate.py` `# kaynak: db/migrations/0012_user_profile_fields_and_tier_refactor.sql §3 ENUM` ile referansla.
- **HK-3 Canlı smoke:** N/A — refactor (yeni LLM/dış API çağrısı yok).
- **HK-4 Runtime assert:** Yok — Pydantic enum validation yeterli (`tier: Tier` field tip).
- **HK-5 Funnel parallelism:** N/A.
- **HK-6 mypy strict:** Refactor sonrası `mypy api/middleware api/routes api/models` clean.
- **HK-7 Reproducibility:** N/A.

---

## §7 — Test stratejisi

**V1-S5-01 sonrası (zorunlu):**
```bash
pytest tests/integration/test_q_routes.py -v
```
Beklenen: tüm test'ler PASS (assertion'lar `anon`/`ogrenci` ile güncellenmiş).

**V1-S5-02 sonrası (regresyon):**
```bash
pytest tests/integration/test_q_routes.py tests/unit/ -v
```
Beklenen: regression yok (comment-only değişiklik, ama yine de tüm suite çalıştır).

**V1-S5-03/04 sonrası:** doc-only, test yok.

**Test-environment önkoşulu:** `pytest` venv'de çalışıyor mu? Önce `pytest --collect-only tests/integration/test_q_routes.py` ile doğrula. Çalışmıyorsa V1-S5-01'i durdur, environment fix önce.

---

## §8 — Riskler

| Risk | Etki | Mitigasyon |
|---|---|---|
| pytest venv çalışmıyor (Python env kırık) | V1-S5-01 doğrulama yapılamaz | İlk adım: `pytest --collect-only` smoke; venv eksikse plan'ı durdur, env fix önce |
| `_tier_for_request` test mock'ta user_id farklı tier ile yollar (T2 vb.) | Test uyumsuz | Test fixture'larında tier override pattern var mı kontrol; gerekirse fixture canon'a güncelle |
| Q1 401 mesajı `min_tier: "T1"` → `min_tier: "ogrenci"` UI'da görünür | Frontend hata mesajı | Bu sprint frontend dokunulmaz; mesaj canon'a yazılır, V1-S3'te frontend bu key'i okuyacak |
| `Tier.T1P` silinmesi `__all__` veya bir import'ta kullanılıyorsa | Import error | `grep -rn 'T1P\|Tier.T2\|Tier.T3\|Tier.T4' api/ tests/` ile kullanım yerleri tara, hepsini sil |
| Plan revize (§3) `V1_vitrin_sprint.md` revize ederken Day 1-3 commit hash'leri eskiyle çelişir | Tarihsel kayıt karmaşası | Manifest §10 "Geçmiş commit'ler eski tier ile yazıldı, hash sabittir; canon ileri yönlü uygulanır" notu |

---

## §9 — Bağımlılıklar (mevcut)

- ✅ `db/migrations/0012_user_profile_fields_and_tier_refactor.sql` — 3-tier ENUM canon kaynağı
- ✅ `web/src/hooks/useTierMock.ts` — frontend zaten 4-mode (V1-S2)
- ✅ Redis (mevcut, kota counter için — refactor'da Redis key formatı değişmez)
- ✅ pytest fixture'leri (kontrol edilecek — §8 risk)

---

## §10 — Kabul kriterleri

- [ ] `Tier` enum 4-mode (`ANON`, `OGRENCI`, `ARASTIRMACI`, `PROFESYONEL`)
- [ ] `QUOTA` tablosu 4 tier için tanımlı (anon vs authed split, 3 authed aynı limit)
- [ ] `tests/integration/test_q_routes.py`: tüm assertion'lar `anon`/`ogrenci` ile güncellendi, PASS
- [ ] `grep -rn "T0\|T1\|T1P\|T2\|T3\|T4" api/ tests/` → sadece test dosyalarındaki yorum/string-literal'lar yok (kod yok)
- [ ] `mypy api/middleware api/routes api/models` clean
- [ ] `V1_vitrin_sprint.md` §0-§12 3-tier canon
- [ ] `CLAUDE.md` §6 satır güncel
- [ ] 4 commit zinciri (V1-S5-01..V1-S5-04) `git log` ile görünür

---

## §11 — Sıradaki adım (onay sonrası)

V1-S5-01: `pytest --collect-only tests/integration/test_q_routes.py` smoke → PASS ise tier_gate.py refactor + test güncelle → atomic commit.

---

**Plan referansları:**
- `docs/plans/V1_vitrin_sprint.md` — üst manifest (bu sprint revize eder)
- `docs/plans/V1_S2_q1_frontend_kabuk.md` — frontend tier 4-mode pattern
- `db/migrations/0012_user_profile_fields_and_tier_refactor.sql` — DB canon kaynağı
- `CLAUDE.md` §6 — proje bağlamı (revize edilecek)
