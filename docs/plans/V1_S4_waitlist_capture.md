# V1-S4 — Waitlist Capture Form Backend (Scope A — Minimal)

**Sprint kodu:** V1-S4
**Süre:** 1 oturum
**Onay:** bekleniyor — "V1-S4 başla"
**Üst manifest:** `docs/plans/V1_vitrin_sprint.md` §0 (waitlist tek satır mention; bu sprint detaylandırır)
**Kanon kaynak:** Yeni kabul (no prior spec). Scope A onaylandı 2026-05-09.
**Şablon:** `docs/plans/V1_S5_backend_tier_canon.md`

---

## §0 — Amaç

Landing sayfasındaki 2 stub button'a (`landing/page.tsx:499` "Erken erişim" + `:1073` "Erken erişim için kaydolun") gerçek waitlist backend bağlamak: email + isim capture → Supabase `waitlist` table → success modal. **Onay e-postası YOK** (V1_vitrin_sprint.md §11 scope dışı kuralı). Spam koruması: honeypot field + IP rate limit (Redis sliding window). **KVKK consent yok** (Scope A; eğer marketing email atılacaksa Scope B'ye geç — KD-V1-S4-05).

**Bugün biter:**
- `db/migrations/0017_waitlist_table.sql` — `waitlist` table (email UNIQUE)
- `api/models/waitlist.py` — Pydantic forbid + EmailStr + honeypot
- `api/routes/waitlist.py` — POST `/api/waitlist` (IP rate limit + honeypot + Supabase insert)
- `api/middleware/auth.py` — `/api/waitlist` PUBLIC_PATHS'e ekle
- `web/src/components/marketing/WaitlistModal.tsx` — email + name + honeypot + submit
- `web/src/lib/api/waitlist.ts` — POST client
- `web/src/app/(marketing)/landing/page.tsx` — 2 button onClick → modal
- `tests/integration/test_waitlist_routes.py` — 5 senaryo (happy + duplicate + invalid + honeypot + rate limit)
- `pytest tests/integration/test_waitlist_routes.py`: PASS · `mypy api/routes/waitlist.py api/models/waitlist.py` clean
- Manuel smoke: landing → modal → submit → Supabase'da row görünür

---

## §1 — Kontrat (API + DB)

### POST `/api/waitlist`

**Request:**
```json
{
  "email": "user@example.com",
  "name": "Ad Soyad",
  "source": "landing_hero" | "landing_pricing",
  "_hp": ""
}
```

**Validasyon:**
- `email`: Pydantic `EmailStr`, max 254 char (RFC 5321)
- `name`: 2-100 char, sadece string
- `source`: enum (`landing_hero` | `landing_pricing`)
- `_hp` (honeypot): boş string ZORUNLU; doluysa 200 OK döndür ama DB'ye yazma (bot'u bilgilendirme)

**Response 200:**
```json
{ "ok": true, "queued_at": "2026-05-09T12:34:56Z" }
```

**Response 409 (duplicate email):**
```json
{ "error": "already_queued" }
```

**Response 422 (validation):** Pydantic default (forbid extra)
**Response 429 (rate limit):** `{ "error": "rate_limited", "retry_after_seconds": 60 }`

### DB Schema (`waitlist` table)

```sql
CREATE TABLE waitlist (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       VARCHAR(254) NOT NULL UNIQUE,
  name        VARCHAR(100) NOT NULL,
  source      VARCHAR(32)  NOT NULL,
  ip          INET,
  user_agent  TEXT,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX waitlist_created_at_idx ON waitlist (created_at DESC);

-- RLS: kapalı (sadece service-role yazabilir/okuyabilir; anon kullanıcı backend üzerinden geçer)
ALTER TABLE waitlist ENABLE ROW LEVEL SECURITY;
```

---

## §2 — Sınırlar (kapsam DIŞINDA)

- ❌ Confirmation email — Scope B/C (yeni `email_service.py` + Resend/SMTP)
- ❌ KVKK consent checkbox — Scope B (Türk pazarı marketing email atıldığında zorunlu)
- ❌ Magic-link auth flow — V1_vitrin_sprint.md §11 zaten scope dışı bildirmiş
- ❌ Admin dashboard / waitlist görüntüleme UI — V2 backlog
- ❌ Captcha (reCAPTCHA / hCaptcha) — honeypot + rate limit MVP yeter
- ❌ Email validation servisi (e.g., Hunter.io MX check) — sadece RFC format kontrolü
- ❌ A/B testing source farklılaştırma — `source` enum kayıt için, analytics V2

---

## §3 — Atomic Commit Boundary (3 commit, bottom-up)

| # | Commit | Dosya | LOC | Test |
|---|---|---|---|---|
| V1-S4-01 | `feat(api): waitlist endpoint + 0017 migration + tests` | `db/migrations/0017_waitlist_table.sql` (yeni, ~20) + `api/models/waitlist.py` (yeni, ~40) + `api/routes/waitlist.py` (yeni, ~90) + `api/middleware/auth.py` (PUBLIC_PATHS satır) + `api/main.py` (router include) + `tests/integration/test_waitlist_routes.py` (yeni, ~140) | ~290 | `pytest tests/integration/test_waitlist_routes.py` PASS · `mypy api/routes/waitlist.py api/models/waitlist.py` clean |
| V1-S4-02 | `feat(web): WaitlistModal + landing 2 button wire` | `web/src/components/marketing/WaitlistModal.tsx` (yeni, ~120) + `web/src/lib/api/waitlist.ts` (yeni, ~30) + `web/src/app/(marketing)/landing/page.tsx` (2 button onClick + modal mount, ~15) | ~165 | Manuel smoke: `cd web && pnpm dev` → modal aç/submit/success/duplicate state |
| V1-S4-03 | `docs(plans): V1_vitrin_sprint.md §A revize V1-S4 KAPANDI` | `docs/plans/V1_vitrin_sprint.md` (§A revize notu) | ~10 | doc-only |

**Toplam:** ~465 LOC.
**Branch:** `feat/V1-S4-waitlist-capture` (yeni branch off main; V1-S5 mergediği için clean baseline).

---

## §4 — Dosya Manifesti

**Yeni (8 dosya):**

```
db/migrations/0017_waitlist_table.sql                  [V1-S4-01]
api/models/waitlist.py                                 [V1-S4-01]
api/routes/waitlist.py                                 [V1-S4-01]
tests/integration/test_waitlist_routes.py              [V1-S4-01]
web/src/components/marketing/WaitlistModal.tsx         [V1-S4-02]
web/src/lib/api/waitlist.ts                            [V1-S4-02]
docs/plans/V1_S4_waitlist_capture.md                   [bu dosya — V1-S4-01 bundle]
```

**Değişen (3 dosya):**

```
api/middleware/auth.py                                 [V1-S4-01 — PUBLIC_PATHS satır]
api/main.py                                            [V1-S4-01 — router.include]
web/src/app/(marketing)/landing/page.tsx               [V1-S4-02 — 2 button onClick + modal mount]
docs/plans/V1_vitrin_sprint.md                         [V1-S4-03 — §A revize]
```

---

## §5 — Kritik kararlar (KD)

- **KD-V1-S4-01:** `/api/waitlist` PUBLIC_PATHS'e eklenir (Bearer gerektirmez, anon-only). Authed kullanıcı submit ederse de aynı path; sadece kayıt amaçlı, tier kontrolü yok.
- **KD-V1-S4-02:** IP rate limit: **3 request / IP / 60 saniye** (Redis sliding window — mevcut `rate_limit.py` pattern'i route-level uygula). 4. istek 429. Honeypot doluysa rate limit sayacı tüketmeden 200 OK fake (bot'a sinyal verme).
- **KD-V1-S4-03:** Duplicate email: 409 `{"error": "already_queued"}` — silently 200 dönmek user'ı yanıltır; gerçek hata mesajı UI'da "zaten listemizdesiniz" olarak gösterilir.
- **KD-V1-S4-04:** `name` required (Scope A — basit form). Scope B'de role/use_case eklenirse `name` zorunlu kalır, ek alanlar opsiyonel.
- **KD-V1-S4-05:** **KVKK consent YOK** (Scope A) — bu liste yalnızca "ben sonradan ulaşayım" demand signal. Eğer Türk kullanıcılara marketing email atılacaksa Scope B'ye geçilmeli (consent checkbox + privacy policy link). Schema migration'a `consent_marketing BOOLEAN` eklemek V2'de geriye uyumlu.
- **KD-V1-S4-06:** `ip` ve `user_agent` opsiyonel kayıtlı — anti-fraud forensic için (KVKK md.5 meşru menfaat). 90 gün sonra anonimleştirme V2 işi.
- **KD-V1-S4-07:** Rate limit Redis bağlantısı yoksa **fallback yok** — eğer Redis düşerse waitlist endpoint 503 döner. Lokal yarabandı (in-memory dict) yapmıyoruz çünkü multi-worker FastAPI'de bypass olur (global çözüm prensibi).

---

## §6 — Halüsinasyon Kod-Seviyesi

- **HK-1 Pydantic forbid:** `WaitlistRequest` ve `WaitlistResponse` `ConfigDict(extra="forbid", frozen=True)`. EmailStr için `pydantic[email]` ekstra; `pyproject.toml`'da varsa kullan, yoksa V1-S4-01 öncesi `uv add pydantic[email]`.
- **HK-2 Kaynak yorum:** `routes/waitlist.py` başında `# kaynak: docs/plans/V1_S4_waitlist_capture.md §1 (kontrat)`.
- **HK-3 Canlı smoke:** N/A (dış API yok). Supabase insert smoke V1-S4-01 sonunda manuel.
- **HK-4 Runtime assert:** `source` field StrEnum (`WaitlistSource.LANDING_HERO`, `LANDING_PRICING`); Pydantic enum validation yeterli.
- **HK-5 Funnel parallelism:** N/A.
- **HK-6 mypy strict:** `mypy api/routes/waitlist.py api/models/waitlist.py` clean. `auth.py` ve `main.py` mevcut state'i koru.
- **HK-7 Reproducibility:** Migration idempotent değil (CREATE TABLE) — geri almak için `0017_waitlist_table_down.sql` sprint'te scope dışı (V1 prototip).

---

## §7 — Test stratejisi

### `tests/integration/test_waitlist_routes.py` (5 senaryo)

```python
# 1. Happy path: valid email + name → 200 + DB row
def test_waitlist_happy_path()

# 2. Duplicate email → 409 already_queued
def test_waitlist_duplicate_email_returns_409()

# 3. Invalid email format → 422 (Pydantic EmailStr)
def test_waitlist_invalid_email_returns_422()

# 4. Honeypot doluysa → 200 OK (fake) ama DB'ye yazılmaz
def test_waitlist_honeypot_filled_silent_drop()

# 5. Rate limit: 4. istek 429
def test_waitlist_rate_limit_4th_request_429()
```

**V1-S4-01 sonrası (zorunlu):**
```bash
pytest tests/integration/test_waitlist_routes.py -v
pytest tests/integration/test_q_routes.py -v  # regresyon
```
Beklenen: 5/5 yeni PASS · q_routes 17/17 PASS (regression yok).

**V1-S4-02 sonrası (manuel UI smoke — CLAUDE.md §3.6 zorunlu):**
- `cd web && pnpm dev`
- `/landing` aç → "Erken erişim" tıkla → modal aç
- Email + isim doldur → submit → success state
- Tekrar submit (aynı email) → "zaten listemizdesiniz" görün
- Geçersiz email → inline error
- DevTools Network tab: POST /api/waitlist 200 → 409
- Supabase dashboard `waitlist` tablo → row var mı

**V1-S4-03 sonrası:** doc-only.

---

## §8 — Riskler

| Risk | Etki | Mitigasyon |
|---|---|---|
| `pydantic[email]` extras yüklü değil → `EmailStr` ImportError | V1-S4-01 ilk import patlar | İlk adım: `python -c "from pydantic import EmailStr"` smoke; yoksa `uv add 'pydantic[email]'` |
| Supabase `waitlist` table create migration runner ile uygulanmaz | endpoint `relation does not exist` patlar | Migration dosyasını ayrıca `psql` veya Supabase SQL editor'de manuel çalıştır; runner V1 prototipte yarı-otomatik |
| Redis bağlantı yok → rate limit middleware patlar | `/api/waitlist` 503 | KD-V1-S4-07: kabul edildi (fallback yok). Test'te Redis mock ile geçer; production'da Redis zorunlu |
| Bot honeypot'u yenip duplicate email spam atar | DB UNIQUE 409, log noise | Rate limit 3/60s + email UNIQUE yeter; Captcha V2 |
| Landing page 1202 satır — modal mount yeri tartışmalı | Yanlış z-index/portal | `<WaitlistModal />` `<body>` portal değil; root component'in en altında render edilir, `useState` ile kontrol |
| `EmailStr` IDN/punycode normalizasyonu yok → `Ömer@example.com` ≠ `ömer@example.com` | Edge case duplicate | Email lower() + ASCII normalize V1-S4-01'de uygula (Pydantic field_validator) |
| Frontend `WaitlistModal` Tailwind v4 + landing inline-style farkı | Görsel uyumsuzluk | Modal landing'in mevcut palette'ini takip eder (indigo/violet gradient, stone neutral); manuel smoke'ta görsel onay |

---

## §9 — Bağımlılıklar (mevcut)

- ✅ Supabase client (`api/db/supabase_client.py`)
- ✅ Redis (rate_limit middleware aktif)
- ✅ AuthMiddleware (PUBLIC_PATHS satır eklenecek)
- ✅ `pyproject.toml` Pydantic v2 (sadece `[email]` extra kontrol)
- ✅ Landing page mevcut (`web/src/app/(marketing)/landing/page.tsx`)
- ❓ pytest fixture'leri Supabase için var mı? Yoksa V1-S4-01 öncesi `tests/conftest.py` review

---

## §10 — Kabul kriterleri

- [ ] `db/migrations/0017_waitlist_table.sql` Supabase'da uygulanmış (manuel veya runner)
- [ ] `POST /api/waitlist` 5 senaryo test PASS
- [ ] `/api/waitlist` PUBLIC_PATHS'te (Bearer gerektirmez)
- [ ] Honeypot field UI'da `display:none` + `aria-hidden`
- [ ] IP rate limit 3/60s aktif (Redis)
- [ ] Email lower-case normalize (duplicate önleme)
- [ ] Landing 2 button onClick → modal aç (manuel smoke PASS)
- [ ] Modal: success state · duplicate state · invalid email error · loading state
- [ ] Supabase `waitlist` tablosunda en az 1 test row görünür (manuel smoke sonrası)
- [ ] `mypy api/routes/waitlist.py api/models/waitlist.py` clean
- [ ] `pytest tests/integration/test_q_routes.py` regresyon PASS (17/17)
- [ ] `docs/plans/V1_vitrin_sprint.md` §A revize: V1-S4 KAPANDI ✅

---

## §11 — Sıradaki adım (onay sonrası)

V1-S4-01 ön-adımı: `python -c "from pydantic import EmailStr"` + `pytest --collect-only` smoke. PASS ise migration yaz → model → route → test → atomic commit.

---

**Plan referansları:**
- `docs/plans/V1_vitrin_sprint.md` §0 (waitlist tek satır mention)
- `docs/plans/V1_S5_backend_tier_canon.md` (şablon, atomic commit pattern)
- `api/middleware/rate_limit.py` (Redis sliding window pattern)
- `api/middleware/auth.py` (PUBLIC_PATHS — yeni satır)
