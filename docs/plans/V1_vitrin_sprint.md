# V1 — Vitrin Sprint (anon + 3-tier Prototip)

**Sprint kodu:** V1 (Vitrin)
**Süre:** Day 1-3 ilk kabuk + V1-S2..V1-S7 sub-sprint genişletme
**Onay:** Omer 2026-05-07 — "V1 başla"
**Revize:** Omer 2026-05-09 — V1-S5 backend tier canon (3-tier + DM-054)
**Revize:** Omer 2026-05-09 — V1-S10 vitrin tek sayfa (Q1/Q3/Q4/Q5 silindi, `/q` embedded literatür özeti)
**Tek doğruluk kaynağı:** Bu manifest + `docs/plans/V1_S5_backend_tier_canon.md` + `docs/plans/V1_S10_vitrin_tek_sayfa.md`

---

## §A — Revize notu (2026-05-09 / V1-S5)

İlk Day 1-3 plan'ı (V1-01..V1-12 commit'ler) eski 6-tier'da yazıldı ve atomik commit zinciri olarak shipped. V1-S5 revize ile:
- **Tier modeli 6→4:** `T0/T1/T1+/T2/T3/T4` → `anon + ogrenci/arastirmaci/profesyonel` (DB 0012 ENUM canon)
- **DM-054:** Q2 (Giriş Bölümü) sonsuza dek "yakında" — backend `LOCKED_SOON_PATHS` korunur
- **V1-S2..V1-S7 sub-sprint:** Q1 (V1-S2 ✅ KAPANDI 2026-05-09) + Q3 (V1-S6 ✅ + V1-S7 ✅ KAPANDI 2026-05-09) + V1-S3 (Q1 literature wire ✅ KAPANDI 2026-05-09) + V1-S4 (waitlist ✅ KAPANDI 2026-05-09) + V1-S5 (backend tier canon ✅ KAPANDI 2026-05-09) — Day 2-3 frontend slot'unun yerini alır
- **V1-S3 KAPANDI 2026-05-09:** `/api/q1` per-paper döngüden tek Gemini Flash structured output call'a geçti (K=12 + ~400 kelime literatür özeti + cümle başına alıntı + grounding validator). Frontend Q1 sayfası `useLiteratureSummary` hook ile wired; anon path backend'e fetch atmaz (V1-S5 canon korunur). Kapsam DIŞINDA (V2 işi): Redis Q havuzu cache, 2-stage rerank, `/api/q/literature` ayrı endpoint adı, `query_id` miras mekanizması.
- **V1-S7 KAPANDI 2026-05-09:** `/api/q3` saf LLM single-call (Yol C, KD-V1-S7-01) — 3 metod önerisi + 7-tag taksonomi + alternatifli sample hint. `LOCKED_SOON_PATHS`'ten çıkarıldı, `QUOTA`'ya `{anon: 3, authed: 10}` eklendi (KD-V1-S7-03). Frontend `useMethodSuggestion` TanStack hook + Q3 sayfası tek sütun (sol paper paneli kalktı, KD-V1-S7-02), Q sayfası Q3 ActionButton aktif `/q3?q=...`. UI'da "LLM önerisi · uygulamadan önce literatür kontrolü öneririz" disclaimer (paper grounding YOK). Kapsam DIŞINDA (V2 işi): DM-055 havuz paylaşımı, per-paper classification, distribution chart, suggestion grounding.
- **V1-S8 KAPANDI 2026-05-09:** `/q` sayfası `MOCK_PAPERS` fixture'tan kurtuldu, gerçek `/api/q` (OpenAlex polite-pool) endpoint'ine bağlandı. Frontend `useQ` TanStack hook + `q-api` adapter (snake_case body, authorsLabel "X et al." 4+, abstract truncate 220 char). Loading/Error/NoResults/EmptyHint state paterni Q1/Q3 ile simetrik. Backend dokunulmadı (zaten hazırdı, V1-09 commit'inde wire açıkta kalmıştı). DM-009 kararı (OpenAlex birincil + Semantic Scholar fallback) MVP scope'unda yarım — SS fallback V2'ye ertelendi (SS anonim API 429 rate-limited, key başvurusu MVP timeline'ını aşar). Kapsam DIŞINDA (V2 işi): year filter UI, authed mini_summary Q sayfasında, Semantic Scholar fallback.
- **V1-S10 KAPANDI 2026-05-09:** Vitrin 6 sayfadan **tek sayfa**'ya indirildi (`/q`). Akış: kullanıcı sorgu → 25 makale liste (KD-V1-S10-01) → checkbox seçim (anon=3, authed=25; KD-V1-S10-02) → "Literatür Özeti Üret" butonu (KD-V1-S10-03, otomatik fetch YOK) → akademik makale formatlı panel (4 bölüm: Giriş/Mevcut Çalışmalar/Tartışma/Sonuç + numaralı kaynaklar; KD-V1-S10-04). Q1, Q3, Q4, Q5 frontend sayfaları + ilgili backend endpoint/model/role_module/service kodları **silindi** (KD-V1-S10-05; ölü kod yasak, backwards-compat shim YOK). `/api/q1` → `/api/q/literature-review` adı değişti (KD-V1-S10-06; body `paper_ids: list[str] + lang`). Sidebar Vitrin grubu 4 satırdan 1 satıra ("Hızlı İnceleme"). Kalan endpoint'ler: `/api/q` (anon=3, authed=5 günlük), `/api/q/literature-review` (anon=3, authed=10), `/api/q2` (LOCKED_SOON_PATHS, DM-054). Net diff: -2500 silme + ~1000 yeni LOC = -1500. Kapsam DIŞINDA (V2 işi): save/export literatür özeti, multi-language production, paper detail page, citation export, pro tier'lar arası kota ayrıştırma.
- **V1-01..V1-12 hash'leri sabittir;** geçmiş commit mesajlarındaki T0/T1 referansları historical (kod ileri yönlü canon)

## §0 — Amaç

Vitrin tabakasını prototip-çalışır hale getir: **anon** (anonim) + **ogrenci/arastirmaci/profesyonel** (3-tier authed) için **tek sayfa** (`/q`) — sorgu + 25 makale + seçim + embedded literatür özeti. V1-S10 öncesi 6 sayfa (Q · Q1 · Q2 · Q3 · Q4 · Q5) plandı; V1-S10 (2026-05-09) ile Q1/Q3/Q4/Q5 silindi, Q2 LOCKED_SOON_PATHS olarak kaldı (DM-054). V1'de 3 authed tier aynı kotada (KD-V1-S5-03; ayrıştırma V2 iş kararı).

## §1 — Sınırlar (kapsam DIŞINDA)

- ❌ Ödeme entegrasyonu (Stripe/iyzico/PayTR) → "Yakında" placeholder modu
- ✅ Vitrin LLM = **Gemini Flash** (mevcut F8 LLMService) — ayrı provider eklemek YOK
- ❌ Authed tier'lar arası kota ayrıştırma (ogrenci=5, arastirmaci=20, profesyonel=100) → V2 iş kararı
- ❌ Atölye/proje workspace akışı
- ❌ DM_RULES'a yeni kural eklemek (R14/R15 ertelendi)

## §2 — Kapsam (V1-S10 sonrası: tek sayfa)

| # | Endpoint | Sayfa | anon | authed (ogrenci/arastirmaci/profesyonel) |
|---|---|---|---|---|
| `/api/q` | `/q` (üst kısım) | Hızlı inceleme — 25 mk liste | 3 sorgu/gün, 25 mk gösterim, max 3 mk seçim | 5 sorgu/gün, 25 mk gösterim, max 25 mk seçim |
| `/api/q/literature-review` | `/q` (alt panel, embedded) | Literatür özeti — 4 bölüm akademik makale formatı + numaralı kaynaklar | 3/gün üretim · max 3 paper_ids (KD-V1-S10-02) | 10/gün üretim · max 25 paper_ids |
| `/api/q2` | `/q2` (route yok, backend defansif) | — | 403 tier_locked_soon (DM-054 sonsuza dek) | 403 tier_locked_soon |

**V1-S10 öncesi planlanan ama silinen:** Q1, Q3, Q4, Q5 sayfaları + `/api/q1`, `/api/q3`, `/api/q4`, `/api/q5` endpoint'leri (KD-V1-S10-05). Geri lazım olursa git history'den cherry-pick (V1-S3, V1-S7 commit'leri).

## §3 — Atomic Commit Boundary

### Day 1 — Backend (5 commit)

| # | Commit | Dosya | LOC | Test |
|---|---|---|---|---|
| V1-01 | `feat(v1): openalex polite-pool service` | `api/services/openalex_polite.py` + model | ~120 | unit + canlı smoke |
| V1-02 | `feat(v1): vitrin LLM modes (LLMService extension)` | `api/services/role_modules/vitrin_summary.py` + `vitrin_paraphrase.py` | ~80 | unit + canlı Gemini Flash smoke |
| V1-03 | `feat(v1): citation formatter (Crossref)` | `api/services/citation_formatter.py` + model | ~100 | unit + canlı Crossref smoke |
| V1-04 | `feat(v1): tier gate middleware + quota` | `api/middleware/tier_gate.py` + Redis counter | ~80 | unit |
| V1-05 | `feat(v1): /api/q + /api/q1 + /api/q4 + /api/q5 routes` | `api/routes/q.py` + `api/models/q.py` | ~200 | integration |

### Day 2 — Frontend (4 commit)

| # | Commit | Dosya | LOC |
|---|---|---|---|
| V1-06 | `feat(v1): SidebarD9 + tier-locked groups` | `web/src/components/sidebar/SidebarD9.tsx` | ~150 |
| V1-07 | `feat(v1): TierMatrix + PaywallSoonModal` | `web/src/components/tier/*` | ~120 |
| V1-08 | `feat(v1): /q + /q1 wired pages` | `web/src/app/q/page.tsx`, `/q1` | ~180 |
| V1-09 | `feat(v1): /q2 + /q3 placeholder + /q4 paraphrase + /q5 citation` | `web/src/app/q[2-5]/page.tsx` | ~200 |

### Day 3 — Auth + deploy + smoke (3 commit)

| # | Commit | Dosya | LOC |
|---|---|---|---|
| V1-10 | `feat(v1): supabase magic-link auth flow` | `web/src/lib/auth.ts` + middleware | ~80 |
| V1-11 | `feat(v1): rate limit (Redis daily counter)` | `api/middleware/tier_gate.py` quota | ~40 |
| V1-12 | `chore(v1): vercel preview + smoke matrix doc` | `docs/runbook/v1_smoke.md` | — |

## §4 — Backend mimari

```
HTTP → Auth (mevcut) → RateLimit (mevcut) → tier_gate (V1 yeni)
                                              ↓
                                         /api/q, /api/q1, /api/q4, /api/q5
                                              ↓
        ┌─────────────────────────┬───────────┴────────────┬─────────────────┐
        ↓                         ↓                        ↓                 ↓
openalex_polite (Q/Q1)   LLMService.call(flash)     citation_formatter      tier_gate
                         mode=vitrin_summary (Q1)         (Q5)              quota check
                         mode=vitrin_paraphrase (Q4)                        Redis counter
```

**Yeni provider yok**: Gemini Flash zaten F8'de aktif; sadece yeni `mode` (role_modules) eklenir.

## §5 — Frontend mimari

```
SidebarD9 (Vitrin açık · 1-14 kilitli "yakında")
  ↓
/q, /q1: wired (api call + sonuç render)
/q2: placeholder + PaywallSoonModal (DM-054 sonsuza dek)
/q3: useMethodSuggestion hook → /api/q3 saf LLM (anon kotalı, V1-S7) · sol paper paneli yok
/q4: textarea → /api/q4 → sonuç + kopyala
/q5: DOI input + format radio (APA/MLA/Chicago/Harvard) → /api/q5 → kopyala
TierMatrix: 3-tier authed (ogrenci/arastirmaci/profesyonel) — V1'de aynı kota, V2'de ayrıştırma
PaywallSoonModal: tetikleyici Q1 anon, Q2 sonsuza dek, Q4/Q5 kota dolu
```

## §6 — Tier gate kontrat (V1-S5 canon)

```python
# api/middleware/tier_gate.py — kaynak: db/migrations/0012 ENUM
class Tier(StrEnum):
    ANON = "anon"
    OGRENCI = "ogrenci"
    ARASTIRMACI = "arastirmaci"
    PROFESYONEL = "profesyonel"

AUTHED_TIERS = (Tier.OGRENCI, Tier.ARASTIRMACI, Tier.PROFESYONEL)


def _authed_quota(limit: int | None) -> dict[Tier, int | None]:
    """V1 scope: 3 authed tier aynı kota. Ayrıştırma V2 iş kararı."""
    return {t: limit for t in AUTHED_TIERS}


QUOTA = {
    "/api/q":                   {Tier.ANON: 3, **_authed_quota(5)},   # 25 mk preview günlük kota
    "/api/q/literature-review": {Tier.ANON: 3, **_authed_quota(10)},  # V1-S10: tek özet endpoint'i
}

# Q2 → LOCKED_SOON_PATHS — her tier 403 "tier_locked_soon" (DM-054 sonsuza dek)
# V1-S10 (2026-05-09): /api/q1, /api/q3, /api/q4, /api/q5 silindi (KD-V1-S10-05).
```

**Kota dolu**: 429 + `{"error": "quota_exceeded", "next_reset": "<ISO>", "soon": true}`
**Anon Q1**: 401 + `{"error": "auth_required_for_tier", "min_tier": "ogrenci"}`
**Tier yetersiz / locked**: 403 + `{"error": "tier_locked_soon", "soon": true}`

## §7 — Council (R13)

**Alan:** Backend + Frontend
**Alan sahibi:** Sercan (Backend) — post-hoc onay; Frontend Lead boş → 6 rol + Omer

| # | Üye | Oy | Gerekçe | İstediği |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟢 | Memory'de Q4/Q5 kotaları net; Gemini Flash `gemini-flash-tr` alias mevcut F8'de doğrulanmış | — |
| 2 | Akademik İsabet | 🟢 | Crossref APA/MLA/Chicago/Harvard standart; OpenAlex polite-pool e-mail var | — |
| 3 | Fayda-Maliyet | 🟢 | 12 commit / 3 gün gerçekçi; mevcut middleware reuse, yeni LLM provider yok | — |
| 4 | Daha İyisi Var Mı? | 🟡 | Citation için citation.js kütüphanesi var ama Crossref direkt template daha basit | KD: Q5 production'da citation.js değerlendir |
| 5 | Global Çözüm | 🟢 | Tier enum tüm corpus için, kota Redis günlük TTL | — |
| 6 | Son Kullanıcı Avukatı | 🟢 | "Yakında" mesajı dürüst; ödeme aldatması yok | — |
| **A** | **Sercan (post-hoc)** | ⏳ | API contract Pydantic forbid + integration test sonrası onay | — |

**Sonuç:** GREEN ilerle. KD-V1-01: Q5 citation.js değerlendirme post-MVP.
**Empirik test gerekli:** EVET — Gemini Flash warm test (HK-3) + Crossref `/works/{doi}` snapshot.

## §8 — Halüsinasyon Kod-Seviyesi (HK-1..HK-7)

- **HK-1 Pydantic forbid**: Tüm `Q*Request/Q*Response` modelleri `model_config = ConfigDict(extra="forbid")`
- **HK-2 Kaynak yorum**: Kotalar kod yorumunda `# kaynak: project_papermind_vitrin_sprint.md §Day 3 rate limit`
- **HK-3 Canlı smoke**: Gemini Flash (LLMService.call canlı) + Crossref + OpenAlex her biri için en az 1 canlı smoke test fixture
- **HK-4 Runtime assert**: `assert citation_format in {"APA","MLA","Chicago","Harvard"}, "Q5 invalid format"`
- **HK-5 Manifest verify**: N/A (yeni veri import yok)
- **HK-6 mypy strict**: Yeni dosyalar mypy strict + `Any` yok
- **HK-7 Reproducibility**: Test fixture deterministic (`random.seed(42)` gerekirse)

## §9 — DoD (R13.13 build kanıt zorunlu)

- [ ] `pytest` PASS — Q + Q1 + Q4 + Q5 unit + integration
- [ ] `mypy --strict` clean (yeni dosyalar)
- [ ] `ruff` clean
- [ ] `npx next build` exit 0 + son 3 satır log (R13.13)
- [ ] Vercel preview link açık
- [ ] 9-smoke matrix manuel verify (Day 3)
- [ ] Pydantic forbid extra her response model
- [ ] `git log --oneline` → V1-01..V1-12 hash'leri (R13.12)

## §10 — Riskler

| Risk | Etki | Mitigasyon |
|---|---|---|
| Gemini Flash cold-start 10-30s | Q1/Q4 ilk istek yavaş | retry pattern (502/503/504/524) + UI "Düşünüyor..." |
| Crossref rate limit (50 req/sec polite) | Q5 batch'te 429 | mailto polite header + Redis cache 24h DOI lookup |
| Magic-link e-mail teslim | anon→ogrenci geçiş kırık | Supabase Auth default SMTP (custom yok = scope dışı) |
| 6 sayfa frontend Day 2'ye sığmaz | Day 3'e kayar | Q2/Q3 ultra-basit (sadece modal trigger) — minimum viable |
| Sidebar kilitli sayfa içerik | Kullanıcı 404 görür | Tüm 1-14 route'lara `<LockedPage />` placeholder (DM-054 Q2 örneği) |

## §11 — Bağımlılıklar (mevcut)

- ✅ `GEMINI_API_KEY` `.env`'de aktif; `config/litellm_models.yaml` `gemini-flash-tr` alias mevcut
- (HF Qwen endpoint `.env`'de durur ama V1'de kullanılmaz)
- ✅ `OPENALEX_EMAIL` polite-pool (`dr.ofrencber@gaziantep.edu.tr`)
- ✅ Supabase magic-link altyapı (mevcut JWKS ES256)
- ✅ Redis (mevcut, kota counter için)
- ✅ `api/utils/resilience.py` (timeout/retry pattern reuse)

## §12 — Sıradaki adım

V1-01: `api/services/openalex_polite.py` + `api/models/q.py` Pydantic models — atomic commit.

---

**Memory referansları:**
- `~/.claude/projects/-Users-omer/memory/project_papermind_vitrin_sprint.md` — sprint detayı
- `~/.claude/projects/-Users-omer/memory/project_papermind_tiers.md` — tier matrisi
- `~/.claude/projects/-Users-omer/memory/MEMORY.md` — index
