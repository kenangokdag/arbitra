# V1-S2 — Q1 Frontend Kabuk (Tek Sayfa, Tek Oturum)

**Sprint kodu:** V1-S2 (V1 vitrin sprint alt-sprint)
**Süre:** 1 oturum (bugün)
**Onay:** Omer 2026-05-09 — "V1_S2 başla"
**Üst manifest:** `docs/plans/V1_vitrin_sprint.md` (drift uyarısı §1'de)
**Kanon kaynak:** `Page_Design/Sayfa_Plani_v1/C_vitrin/q1.md` (291 satır) + `docs/SPINE.md` §0.1

---

## §0 — Amaç

`/q1` route'u **frontend kabuk** olarak hayata geç. Q sayfasındaki `<a href="/q1">` link'i artık 404 değil. Sayfa SPINE.md DM-048 + q1.md kanonuna uygun layout'u (sol panel 320px sticky 3 paper card + sağ gövde tier-aware) gösterir; **backend wire bu manifestte değil** (V1-S3'e ertelendi). 3-tier (ogrenci / arastirmaci / profesyonel) frontend mock — backend tier_gate drift'i bu manifeste dokunmaz.

**Bugün biter:** sayfa Chrome'da `localhost:3000/q1?qid=demo&q=test` açılır → sol panel 3 kart, sağ gövde tier'a göre paywall placeholder (anon) veya fixture summary (pro). `npx next build` exit 0 + 0 type error.

---

## §1 — Drift Uyarısı (KRİTİK)

V1 sprint ana planı (`V1_vitrin_sprint.md`) **3 yerde drift**:

| Drift | V1 ana plan | Kanon (SPINE/0012/q1.md) | V1-S2'de davranış |
|---|---|---|---|
| Tier modeli | T0/T1/T1+/T2/T3/T4 (6-tier) | ogrenci/arastirmaci/profesyonel (3-tier) | Frontend 3-tier mock; backend tier_gate'e dokunulmaz |
| Q1 endpoint | `POST /api/q1` Gemini Flash 2-cümle mini-özet | `POST /api/q/literature` K=12 ~400 kelime 2-aşamalı rerank | Frontend `/api/q/literature` çağırır gibi yazılır + 501 fixture fallback (mevcut `lib/chat-fixture.ts` pattern) |
| Q2 | V1-Day1'de `/api/q2` endpoint var | DM-054 ELİMİNE | Q1 sayfasındaki action bar Q2 button **gösterilmez** (sadece Q3 yakında) |

**Drift fix bu manifestte değil.** V1 sprint plan revize ayrı PR (V1-S5 veya sonra). Bu manifest sadece frontend kabuk.

---

## §2 — Sınırlar (kapsam DIŞINDA)

- ❌ Backend `/api/q/literature` endpoint yazımı — V1-S3
- ❌ Mevcut `/api/q1` endpoint'i değiştirme/rename — V1-S5 drift fix
- ❌ Gerçek LLM çağrısı (Gemini Flash) — V1-S3
- ❌ `q:literature:*` Redis cache — V1-S3
- ❌ Pro modunda inline `[1]..[K]` citation hover/click linking gerçek behavior — V1-S2'de SADECE statik DOM yapısı + click handler stub
- ❌ Capture form (`POST /api/waitlist`) backend — V1-S4
- ❌ PaywallModal/CaptureModal yeni implementasyonu — Q sayfasından reuse (varsa); yoksa stub
- ❌ Tier gate mevcut `tier_gate.py` revize — V1-S5
- ❌ TanStack Query kurulumu (q1.md'de `useLiteratureSummary` hook'u TanStack istiyor) — kontrol et, yoksa **fetch + useState** yeter

---

## §3 — Atomic Commit Boundary (6 commit, bottom-up)

> **Revize 2026-05-09:** sıralama foundations→leaf→composite→page bottom-up. Her commit kendi başına `tsc --noEmit` geçmeli; page.tsx en sona alındı, tek-edit'te tüm import'ları finalize eder.
> **Revize 2026-05-09 (post-build):** 2 ek commit — eslint react-hooks/set-state-in-effect refactor + defense-4 stub build unblock (Omer onayı "A").

| # | Commit | Dosya | LOC tahmin | Test |
|---|---|---|---|---|
| V1-S2-01 | `feat(v1-s2): q1 fixture data + tier mock hook` | `web/src/lib/q1-fixture.ts` (yeni) + `web/src/hooks/useTierMock.ts` (yeni) | ~60 | unit (fixture şape, tier mock) |
| V1-S2-02 | `feat(v1-s2): q1 left panel paper cards (sticky)` | `web/src/components/q1/LeftPanelPapers.tsx` (yeni) | ~80 | unit (rendering 3 cards) |
| V1-S2-03 | `feat(v1-s2): q1 right body — paywall + summary fixture` | `web/src/components/q1/PaywallPlaceholder.tsx` + `LiteratureSummary.tsx` + `Q1ActionBar.tsx` (3 yeni) | ~150 | unit (paywall ve summary render) |
| V1-S2-04 | `feat(v1-s2): q1 route shell + tier-aware layout` | `web/src/app/(app)/q1/page.tsx` (yeni) + `web/src/app/(app)/q1/loading.tsx` (yeni) | ~120 | manuel render |
| V1-S2-05 | `fix(v1-s2): useTierMock useSyncExternalStore refactor + eslint cleanup` | `web/src/hooks/useTierMock.ts` + `useTierMock.test.tsx` + `web/src/app/(app)/q1/page.tsx` revize | ~30 | retest 32/32 |
| V1-S2-06 | `chore(defense-4): ReferenceIntegrityPage stub (V1-S2 build unblock)` | `web/src/components/project/ReferenceIntegrityPage.tsx` (yeni stub) | ~15 | next build PASS |

**Toplam:** ~410 LOC (q1.md tahmini ~200, ek %50 fixture/test).
**Branch:** `feat/V1-S2-q1-frontend` (off main).
**Push timing:** Omer kontrolünde, smoke + visual review sonrası.

---

## §4 — Dosya Manifesti

**Yeni (8 dosya):**

```
web/src/app/(app)/q1/
  page.tsx                    [V1-S2-01]
  loading.tsx                 [V1-S2-01]
web/src/components/q1/
  LeftPanelPapers.tsx         [V1-S2-02]
  PaywallPlaceholder.tsx      [V1-S2-03]
  LiteratureSummary.tsx       [V1-S2-03]
  Q1ActionBar.tsx             [V1-S2-03]
web/src/lib/
  q1-fixture.ts               [V1-S2-04]
web/src/hooks/
  useTierMock.ts              [V1-S2-04]
```

**Test:**
```
web/src/components/q1/__tests__/
  LeftPanelPapers.test.tsx
  PaywallPlaceholder.test.tsx
  LiteratureSummary.test.tsx
  Q1ActionBar.test.tsx
```

**Dokunulmayan (pasif bağımlılık):**
- `web/src/app/(app)/q/page.tsx` — Q sayfası (sadece `<a href="/q1">` link'i bağlı, mevcut)
- `api/routes/q.py` + `api/middleware/tier_gate.py` — backend, V1-S3/S5'e ertelendi
- `Page_Design/Sayfa_Plani_v1/C_vitrin/q1.md` — kanon, dokunulmaz

---

## §5 — Frontend Mimari

### URL & Query State

```
/q1?qid={query_id}&q={query_text}
```
- `qid` zorunlu (Q sayfasından gelmeli) — yoksa "Q'dan başlayın" placeholder + `<a href="/q">` redirect button
- `q` opsiyonel (display-only başlık için)

### Tier Mock

`useTierMock.ts` — localStorage'dan `papermind_tier_mock` okur (default: `"ogrenci"`); döndürür: `{ tier: "ogrenci" | "arastirmaci" | "profesyonel" | "anon", isAuthenticated: boolean }`.

**Tier → Q1 davranışı:**
| Tier | Sağ gövde | CTA |
|---|---|---|
| `anon` | PaywallPlaceholder | "Deneme Sürecini Başlat" + "Projeme Dönüştür" |
| `ogrenci` | LiteratureSummary fixture (~400 kelime, K=3 statik) | "Pro Özelliklerini Gör" (V1-S5) |
| `arastirmaci` | LiteratureSummary fixture | (CTA yok) |
| `profesyonel` | LiteratureSummary fixture | (CTA yok) |

**Why 3-tier ama anon dahil:** 0012 migration 3-tier kullanıcı tipi (ogrenci/arastirmaci/profesyonel); auth yapmadan giren = `anon` view. Yani Q1'de davranışsal 4 mod (anon + 3 user tier).

### Layout (q1.md ASCII'sine sadık)

```
ContainerWidth: 1200px max
Grid: [320px sol] [1fr sağ]  (gap 24px)
Sticky: sol panel top-0 (scroll'la birlikte)
Mobile (<768px): sol panel collapsible accordion top
```

### Bileşen Sözleşmeleri (TypeScript types)

```tsx
// web/src/lib/q1-fixture.ts
export type PaperCard = {
  rank: number;        // 01..03 (V1-S2'de 3 sabit)
  id: string;
  title: string;
  authors: string;
  venue: string;
  year: number;
  citations: number;
  lang: "tr" | "en" | "id";
  shortAbstract: string;  // italic 2-3 cümle
};

export type CitationRef = { sentenceIdx: number; paperIds: string[] };

export type LiteratureSummaryData = {
  text: string;          // ~400 kelime markdown
  citations: CitationRef[];
  lang: "tr" | "en" | "id";
};
```

### Veri Akışı (V1-S2'de)

```
useTierMock() → tier
  ↓
useSearchParams() → qid, q
  ↓
qid yoksa → "Q'dan başlayın" placeholder
qid varsa:
  - tier === "anon" → fixture papers (3 kart) + PaywallPlaceholder
  - tier !== "anon" → fixture papers + fixture summary (LiteratureSummary)
```

**V1-S3'e marker:** `// TODO(V1-S3): swap fixture for fetch('/api/q/literature', { qid })`.

---

## §6 — Halüsinasyon Kod-Seviyesi (HK-1..7)

- **HK-1 Pydantic forbid:** N/A (backend yok). TypeScript karşılığı: `as const` literal types + `satisfies` operator.
- **HK-2 Kaynak yorum:** Her dosyanın başında `// kaynak: Page_Design/Sayfa_Plani_v1/C_vitrin/q1.md §<bölüm>`
- **HK-3 Canlı smoke:** N/A (no external call). Replace: `npm run dev` + Chrome 4 tier scenario manuel verify.
- **HK-4 Runtime assert:** `assert(papers.length === 3, "Q1 fixture must have exactly 3 cards")` mount'ta.
- **HK-5 Manifest verify:** `q1-fixture.ts` paper id'leri ile q.md'deki `MOCK_PAPERS` (Q sayfası) **paralel** (Liu/Yıldız/Park) — Q→Q1 funnel'de aynı paper'lar görünür.
- **HK-6 mypy/tsc strict:** `tsc --noEmit` exit 0 + `eslint` clean.
- **HK-7 Reproducibility:** Fixture deterministic (random yok); test snapshot stable.

---

## §7 — 7-Kontrol Council (DM_RULES R2)

| # | Kontrol | Durum | Not |
|---|---|---|---|
| 1 | Literatür | 🟢 | SciSpace + Consensus pattern: sol panel sticky + sağ özet — endüstri standart |
| 2 | Halüsinasyon | 🟢 | q1.md kanon, V1 plan drift'i §1'de açık, fixture deterministic, frontend-only |
| 3 | Fayda-maliyet | 🟢 | ~410 LOC / 1 oturum; backend dokunulmadığı için risk minimum, geri alma kolay |
| 4 | Daha kolayı | 🟡 | TanStack Query yerine fetch + useState seçildi (kurulu mu kontrol et). Daha basit. |
| 5 | Son kullanıcı avantajı | 🟢 | Q→Q1 link 404'tan çıkar; 4 tier mode'u görsel test edilebilir |
| 6 | Rakip karşılaştırma | 🟢 | SciSpace `/explore/topic/{slug}` ile birebir uyum (sticky panel + summary), Consensus'tan farkımız: TR dil + 3-tier |
| 7 | Lokal vs global | 🟢 | Lokal hack yok. Tier mock localStorage = geçici (V1-S5 supabase auth ile değişir). `// TODO(V1-S5)` marker'ı zorunlu |

**Sonuç:** GREEN ilerle.
**KD-V1-S2-01:** TanStack Query ekleme kararı V1-S3'te (gerçek API çağrısı gelince).

---

## §8 — DoD (Build Empirik Kanıt — R13.13)

- [ ] `cd web && npx tsc --noEmit` → exit 0
- [ ] `cd web && npx next build` → exit 0 + son 3 satır log commit body'de
- [ ] `cd web && npx next dev` → http://localhost:3000/q1?qid=demo&q=test 200 OK
- [ ] Chrome manuel: 4 tier scenario (localStorage `papermind_tier_mock` → `"anon"`/`"ogrenci"`/`"arastirmaci"`/`"profesyonel"`) tek tek refresh + sağ gövde değişimi gözle doğrulanır
- [ ] `npx vitest run web/src/components/q1/__tests__/` → tüm testler PASS
- [ ] `npx eslint web/src/{app/(app)/q1,components/q1,lib/q1-fixture.ts,hooks/useTierMock.ts}` → 0 error
- [ ] Q sayfasından `<a href="/q1">` linkine tıkla → 200 OK (404 düzeldi kanıtı)
- [ ] Mobile 375px (Chrome DevTools) — sol panel collapse accordion görünür

**Empirik kanıt commit body'sinde:** son `next build` 3 satır + vitest test count.

---

## §9 — Risk + Sonraki Faz Hooks

### Risk

| Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|
| TanStack Query kurulu değil → import error | Orta | Build kırılır | İlk adımda `package.json` + `cd web && npm ls @tanstack/react-query` doğrula. Yoksa fetch+useState. |
| Q sayfası `MOCK_PAPERS` ile Q1 fixture id mismatch | Düşük | Funnel test inconsistency | HK-5: aynı id'leri kullan (p1/p2/p3). |
| Sticky sol panel mobile'da scroll bozulur | Düşük | UX | Mobile <768px accordion (Tailwind `md:sticky`). |
| 3-tier frontend mock + backend 6-tier drift kullanıcıya görünür | Düşük | Sadece localStorage'a dokunan dev görür; prod akışı backend'i hiç çağırmıyor V1-S2'de | V1-S3 wiring'de drift fix zorunlu (DoD'a giriyor) |

### Sonraki Faz Hooks

- **V1-S3:** `/api/q/literature` endpoint + `useLiteratureSummary` hook + Gemini Flash + Pydantic structured output (yeni manifest)
- **V1-S4:** `0017_waitlist` migration + `POST /api/waitlist` + capture form actual submit
- **V1-S5:** V1 ana sprint plan revize (3-tier ratify + Q2 elimine + tier_gate refactor + `/api/q1` rename veya `/api/q/literature` co-existence)
- **V1-S6:** Q3 frontend kabuk (Q3 sayfası, q3.md kanon, V1-S2 pattern reuse)

**TODO marker tablosu (kod içinde aranacak):**
- `// TODO(V1-S3)` — endpoint wiring (≥3 yer beklenir)
- `// TODO(V1-S4)` — capture form submit
- `// TODO(V1-S5)` — supabase auth (useTierMock yerine)

---

## §10 — Brief Uyum Sinyali (executor için)

Bu manifesti okuyup koda başlamadan önce:

1. ✅ Bu manifestin başlığı **V1-S2** (V1 ana plan değil)
2. ✅ Backend dokunulmaz — sadece `web/src/`
3. ✅ 3-tier mock (ogrenci/arastirmaci/profesyonel + anon) frontend-only
4. ✅ q1.md (291 satır) kanon — layout, copy text, ASCII'ye sadık
5. ✅ Q sayfası `MOCK_PAPERS` (p1/p2/p3) ile Q1 fixture aynı id'ler
6. ✅ Mevcut `/api/q1` endpoint'i ÇAĞRILMIYOR — fixture only
7. ✅ TODO(V1-S3/S4/S5) marker'ları kod içinde

**Drift sinyali:** yukarıdaki 7 maddeden biri okuyup sapıyorsa **STOP**, plan revize.

---

## §11 — Bilinen Borçlar (KD)

- KD-V1-S2-01: TanStack Query ekleme V1-S3'e ertelendi
- KD-V1-S2-02: Mobile (<768px) accordion'un keyboard navigation (a11y) full pass V1-S5'te
- KD-V1-S2-03: PaywallModal/CaptureModal henüz Q sayfasında yok — Q1'de stub button (onClick → console.log) bırakılır; gerçek modal V1-S4'te
- KD-V1-S2-04: i18n (Q1 sağ gövde TR/EN/ID dil tespiti) — fixture'da sadece TR; multi-lang V1-S3 LLM wiring sonrası

---

## §12 — Onay & Başlatma

Omer explicit onay: **"plan onaylandı"** veya **"V1-S2 başla"** yazınca:

1. Önce: `cd web && npm ls @tanstack/react-query` kontrol (KD-V1-S2-01 kararı netleşir)
2. Sonra: branch `feat/V1-S2-q1-frontend` aç
3. V1-S2-01 → -02 → -03 → -04 sırayla atomic commit
4. DoD §8 checklist tamamlanmadan PR açılmaz

**Tahmini süre:** 1 oturum (~3-4 saat aktif).
