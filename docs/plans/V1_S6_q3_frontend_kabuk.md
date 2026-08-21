# V1-S6 — Q3 Frontend Kabuk (Tek Sayfa, Tek Oturum)

**Sprint kodu:** V1-S6 (V1 vitrin sprint alt-sprint, V1-S2 paralel pattern)
**Süre:** 1 oturum
**Onay:** bekleniyor — "V1-S6 başla"
**Üst manifest:** `docs/plans/V1_vitrin_sprint.md` (drift uyarısı V1-S2 ile aynı)
**Kanon kaynak:** `Page_Design/Sayfa_Plani_v1/C_vitrin/q3.md` (353 satır) + `docs/SPINE.md`
**Şablon:** `docs/plans/V1_S2_q1_frontend_kabuk.md`

---

## §0 — Amaç

`/q3` route'u **frontend kabuk** olarak hayata geç. Q sayfasındaki `<a href="/q3">` link'i artık `disabled "yakında"` değil; tıklayınca Q3 sayfası açılır. Sayfa q3.md kanonuna uygun layout'u (sol panel 320px sticky 3 paper card + sağ gövde tier-aware: anon paywall · pro distribution chart + suggestions + sample hint) gösterir; **backend wire bu manifestte değil** (V1-S7'ye ertelenir). 3-tier mock V1-S2 ile aynı (`useTierMock`).

**Bugün biter:** sayfa Chrome'da `localhost:3000/q3?qid=demo&q=test` açılır → sol panel 3 kart, sağ gövde tier'a göre paywall placeholder (anon) veya fixture distribution + 2 suggestion + sample hint (pro). Q sayfasından Q3 butonuna tıklayınca 200 OK. `npx next build` exit 0 + 0 type error.

---

## §1 — Drift Uyarısı

V1-S2 ile aynı drift hattı (3-tier vs 6-tier, vb.). Bu manifest sadece frontend kabuk; drift fix V1-S5'e ertelendi.

**V1-S6'ya özel drift:**
| Drift | q3.md kanon | V1-S6'da davranış |
|---|---|---|
| `useTier` hook | q3.md `useTier` der | `useTierMock` reuse (V1-S2 ile aynı) |
| LeftPanelPapers shared | q3.md "Q1'den shared'a taşındı" | **Bu manifestte yapılır** (Q1 import path güncellenir, refactor scope içinde) |
| PaywallPlaceholder shared | q3.md "Q1'den shared'a, copy parametrik" | **Bu manifestte yapılır** (parametrik copy) |
| MethodDistributionChart | q3.md "CSS-only horizontal bar" | Frontend kabuk: fixture'dan render, hover sync TODO(V1-S7) |
| Q sayfası Q3 button | q3.md "disabled → aktif (paywall-aware)" | **Bu manifestte aktive edilir** (`q/page.tsx` `disabled` kaldırılır) |

---

## §2 — Sınırlar (kapsam DIŞINDA)

- ❌ Backend `POST /api/q/method` endpoint — V1-S7 (yeni manifest)
- ❌ Gerçek LLM çağrısı (Method classification + Suggestion + SampleHint LLM Pass) — V1-S7
- ❌ Redis cache `q:method:*` + `q:method_classify:*` — V1-S7
- ❌ Pro modunda hover sync (sol kart ↔ sağda örnek paper highlight) — V1-S6'da SADECE statik DOM + click handler stub
- ❌ Q sayfası Q2 button — DM-054 ELİMİNE (disabled "yakında" kalır, gizlenmez)
- ❌ Tier gate / supabase auth — V1-S5
- ❌ V1-S2 lint cleanup (26 pre-existing eslint hatası) — ayrı PR

---

## §3 — Atomic Commit Boundary (6 commit, bottom-up)

Her commit kendi başına `tsc --noEmit` geçmeli; page.tsx en sonda.

| # | Commit | Dosya | LOC tahmin | Test |
|---|---|---|---|---|
| V1-S6-01 | `feat(v1-s6): q3 fixture data` | `web/src/lib/q3-fixture.ts` (yeni) | ~80 | unit (fixture şape, distribution sum 100, suggestion ⊆ used_paper_ids) |
| V1-S6-02 | `refactor(shared): LeftPanelPapers q1→shared + Q1 import güncelle` | `web/src/components/shared/LeftPanelPapers.tsx` (yeni, q1'den taşıma) + `q1/LeftPanelPapers.tsx` (sil) + `app/(app)/q1/page.tsx` (import güncelle) + `LeftPanelPapers.test.tsx` (import path güncelle) | ~10 (taşıma) | retest 5/5 PASS |
| V1-S6-03 | `refactor(shared): PaywallPlaceholder q1→shared + parametrik copy` | `web/src/components/shared/PaywallPlaceholder.tsx` (yeni, props: title, copy, ctaPrimary, ctaSecondary) + `q1/PaywallPlaceholder.tsx` (sil) + `app/(app)/q1/page.tsx` (import güncelle, Q1 copy props) + `PaywallPlaceholder.test.tsx` (parametrik test) | ~30 (props ekleme + copy eksternal) | retest 4/4 PASS |
| V1-S6-04 | `feat(v1-s6): q3 sağ gövde — distribution + suggestions + sample hint` | `web/src/components/q3/MethodDistributionChart.tsx` + `MethodSuggestionList.tsx` + `SampleHintBlock.tsx` + `Q3ActionBar.tsx` (4 yeni) | ~180 | unit (4 component render) |
| V1-S6-05 | `feat(v1-s6): q3 route shell + tier-aware layout` | `web/src/app/(app)/q3/page.tsx` + `loading.tsx` (2 yeni) | ~110 | manuel render |
| V1-S6-06 | `feat(vitrin): q sayfası Q3 button aktive (DM-054)` | `web/src/app/(app)/q/page.tsx` (Q3 ActionButton `disabled` kaldır) | ~3 | next build PASS + Q→Q3 link kanıt |

**Toplam:** ~410 LOC.
**Branch:** mevcut `feat/V1-S2-q1-frontend` üzerinde devam (push edilmedi, V1-S2+S6 birlikte PR olabilir; alternatif: yeni branch — Omer kararı §12'de).

---

## §4 — Dosya Manifesti

**Yeni (8 dosya):**

```
web/src/app/(app)/q3/
  page.tsx                    [V1-S6-05]
  loading.tsx                 [V1-S6-05]
web/src/components/shared/
  LeftPanelPapers.tsx         [V1-S6-02 — q1'den taşıma]
  PaywallPlaceholder.tsx      [V1-S6-03 — q1'den taşıma + parametrik]
web/src/components/q3/
  MethodDistributionChart.tsx [V1-S6-04]
  MethodSuggestionList.tsx    [V1-S6-04]
  SampleHintBlock.tsx         [V1-S6-04]
  Q3ActionBar.tsx             [V1-S6-04]
web/src/lib/
  q3-fixture.ts               [V1-S6-01]
```

**Test (yeni 5):**
```
web/src/components/shared/LeftPanelPapers.test.tsx     (q1'den taşıma)
web/src/components/shared/PaywallPlaceholder.test.tsx  (q1'den taşıma + parametrik test)
web/src/components/q3/MethodDistributionChart.test.tsx
web/src/components/q3/MethodSuggestionList.test.tsx
web/src/components/q3/SampleHintBlock.test.tsx
web/src/components/q3/Q3ActionBar.test.tsx
web/src/lib/q3-fixture.test.ts
```

**Silinen (2):** `web/src/components/q1/LeftPanelPapers.tsx` + `q1/PaywallPlaceholder.tsx` (shared'a taşındığı için).

**Değişen (3):** `q1/page.tsx` (import path) + `q1/LeftPanelPapers.test.tsx` (path) + `q1/PaywallPlaceholder.test.tsx` (parametrik) + `q/page.tsx` (Q3 disabled kaldır).

**Dokunulmayan:** `useTierMock`, `q1-fixture`, `LiteratureSummary`, `Q1ActionBar`, backend, `q1.md`/`q3.md` kanon.

---

## §5 — Frontend Mimari

### URL & Query State

```
/q3?qid={query_id}&q={query_text}
```
- `qid` zorunlu — yoksa "Q'dan başlayın" placeholder + `<a href="/q">` (V1-S2 ile aynı pattern)

### Tier Davranışı (V1-S2 ile aynı 4 mod)

| Tier | Sağ gövde | CTA |
|---|---|---|
| `anon` | shared/PaywallPlaceholder (Q3 copy) | "Deneme Sürecini Başlat" + "Projeme Dönüştür" |
| `ogrenci` | DistributionChart + SuggestionList + SampleHintBlock (fixture) | (CTA yok) |
| `arastirmaci` | aynı | (CTA yok) |
| `profesyonel` | aynı | (CTA yok) |

### Layout (q3.md ASCII'sine sadık)

```
ContainerWidth: 1200px max
Grid: [320px sol] [1fr sağ]  (gap 24px)
Sticky: sol panel md:sticky md:top-4
Mobile (<768px): sol panel kart blok üstte
```

### Bileşen Sözleşmeleri (TypeScript types)

```ts
// web/src/lib/q3-fixture.ts
import type { PaperCard } from "@/lib/q1-fixture"; // Q1+Q3 ortak schema

export type MethodTag =
  | "experimental_rct"
  | "observational"
  | "qualitative"
  | "mixed_methods"
  | "systematic_review"
  | "simulation"
  | "theoretical";

export type MethodDistribution = {
  method: MethodTag;
  methodLabel: string;     // sorgu dilinde label, fixture TR
  percentage: number;      // 0..100, sum ≈ 100
  paperCount: number;
};

export type MethodSuggestion = {
  method: MethodTag;
  methodLabel: string;
  rationaleText: string;   // 40-500 char, fixture TR
  examplePaperId: string;  // ⊆ usedPaperIds
  exampleRank: number;     // 1..50
};

export type SampleHint = {
  typicalSampleSize: string;
  datasetsOrTools: string[];
};

export type Q3MethodData = {
  distribution: MethodDistribution[];
  suggestions: MethodSuggestion[];
  sampleHint: SampleHint;
  usedPaperIds: string[];  // K=25 placeholder, fixture'da 3 paper id (p1/p2/p3)
  lang: "tr" | "en" | "id";
};
```

### Veri Akışı (V1-S6'da)

```
useTierMock() → tier
  ↓
useSearchParams() → qid, q
  ↓
qid yoksa → "Q'dan başlayın" placeholder
qid varsa:
  - tier === "anon" → fixture papers + shared/PaywallPlaceholder (Q3 copy)
  - tier !== "anon" → fixture papers + DistributionChart + SuggestionList + SampleHintBlock
```

**V1-S7'ye marker:** `// TODO(V1-S7): swap fixture for fetch('/api/q/method', { qid })`.

---

## §6 — Halüsinasyon Kod-Seviyesi (HK-1..7)

- **HK-2 Kaynak yorum:** Her dosyanın başında `// kaynak: Page_Design/Sayfa_Plani_v1/C_vitrin/q3.md §<bölüm>`
- **HK-4 Runtime assert:** `assert(papers.length === 3, "Q3 fixture must have exactly 3 cards")` ve `assert(distribution.reduce((s, d) => s + d.percentage, 0) === 100, "distribution sum must be 100")` mount'ta
- **HK-5 Funnel manifest:** `q3-fixture.ts` paper id'leri Q1 fixture (`q1-fixture.ts`) ile **paralel** (p1/p2/p3 — Q→Q1+Q3 funnel'de aynı paper'lar görünür). `examplePaperId ⊆ {p1,p2,p3}`.
- **HK-6 tsc strict:** `tsc --noEmit` exit 0
- **HK-7 Reproducibility:** Fixture deterministic (random yok)

---

## §7 — 7-Kontrol Council

| # | Kontrol | Durum | Not |
|---|---|---|---|
| 1 | Literatür | 🟢 | SciSpace + Consensus Method Distribution pattern, CSS-only chart endüstri kabul |
| 2 | Halüsinasyon | 🟢 | q3.md kanon, fixture deterministic, frontend-only |
| 3 | Fayda-maliyet | 🟢 | ~410 LOC / 1 oturum; V1-S2 pattern reuse, refactor 2 dosya |
| 4 | Daha kolayı | 🟡 | shared/ refactor opsiyonel — q3'e duplicate kopya da yapılabilir; **shared seçildi** çünkü 2. faz drift riskini şimdi kapatıyor |
| 5 | Son kullanıcı avantajı | 🟢 | Q→Q3 link 404'tan/disabled'dan çıkar; pilot funnel Q⇄Q1+Q3 simetrik |
| 6 | Rakip karşılaştırma | 🟢 | SciSpace `methods overview` ile uyum, Consensus'ta benzer panel yok — niş avantaj |
| 7 | Lokal vs global | 🟢 | shared/ taşıma global; useTierMock global; lokal hack yok |

**Sonuç:** GREEN ilerle.

---

## §8 — DoD (Build Empirik Kanıt — R13.13)

- [ ] `cd web && npx tsc --noEmit` → exit 0
- [ ] `cd web && npm run build` → exit 0 + son 3 satır log commit body'de
- [ ] `cd web && npm run dev` → http://localhost:3000/q3?qid=demo&q=test 200 OK
- [ ] Q sayfasından Q3 butonuna tıkla → /q3 200 OK (disabled kaldı kanıtı)
- [ ] Chrome manuel: 4 tier scenario (anon/ogrenci/arastirmaci/profesyonel) tek tek refresh + sağ gövde değişimi gözle
- [ ] `npx vitest run` → tüm testler PASS (mevcut 71 + yeni ~25 = ~96)
- [ ] Mobile 375px (Chrome DevTools) — sol panel kart blok üstte, sağ gövde alt

**Empirik kanıt commit body'sinde:** son `next build` 3 satır + vitest test count.

---

## §9 — Risk + Sonraki Faz Hooks

### Risk

| Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|
| shared/ refactor Q1 testlerini kırar | Orta | 9 q1 test FAIL | V1-S6-02/03 her commit sonrası `vitest run` retest zorunlu |
| q3-fixture distribution sum != 100 | Düşük | HK-4 assert fire | unit test fixture-shape doğrulama |
| MethodDistributionChart CSS-only render Tailwind v4 OKLCH ile renk drift | Düşük | Görsel | Mevcut palette token kullan (`amber-700`, `emerald-600`) |
| Q sayfası Q3 button aktive edildikten sonra Q1+Q3 button visual hierarchy bozulur | Düşük | UX | Mevcut ActionButton component reuse, sadece `disabled` kaldır |

### Sonraki Faz Hooks

- **V1-S7:** `POST /api/q/method` endpoint + `useMethodSuggestion` hook + Gemini Flash 2-pass (classify + suggest) + Pydantic structured output (yeni manifest)
- **V1-S4:** `0017_waitlist` migration + capture form (Q1+Q3 ortak)
- **V1-S5:** V1 ana sprint plan revize (3-tier ratify + Q2 elimine + tier_gate refactor)
- **V1-S8:** lint cleanup (V1-S2 + landing rewrite kalıntı 26 hata)

**TODO marker tablosu:**
- `// TODO(V1-S7)` — endpoint wiring
- `// TODO(V1-S4)` — capture form submit
- `// TODO(V1-S5)` — supabase auth

---

## §10 — Brief Uyum Sinyali

Bu manifesti okuyup koda başlamadan önce:

1. ✅ Bu manifestin başlığı **V1-S6** (V1 ana plan değil)
2. ✅ Backend dokunulmaz — sadece `web/src/`
3. ✅ 3-tier mock (`useTierMock` reuse, V1-S2'den)
4. ✅ q3.md (353 satır) kanon — layout, copy text, ASCII'ye sadık
5. ✅ Q1+Q3 paper id'ler (p1/p2/p3) **aynı** — HK-5 funnel
6. ✅ Mevcut backend `/api/q/method` ÇAĞRILMIYOR — fixture only
7. ✅ shared/ refactor V1-S2 q1 component'lerini taşır (kopya değil) — Q1 testleri kırılmadan retest PASS zorunlu
8. ✅ Q sayfası Q2 button GİZLENMEZ (DM-054 ELİMİNE ama UI'dan kaldırılma değil — disabled "yakında" kalır)
9. ✅ TODO(V1-S7/S4/S5) marker'ları kod içinde

**Drift sinyali:** yukarıdan biri okuyup sapıyorsa **STOP**, plan revize.

---

## §11 — Bilinen Borçlar (KD)

- KD-V1-S6-01: `MethodDistributionChart` CSS-only horizontal bar (kütüphane yok); F2'de chart kütüphanesi (recharts) değerlendirme
- KD-V1-S6-02: hover sync (sol kart ↔ sağ örnek paper highlight) statik — V1-S7 gerçek wiring
- KD-V1-S6-03: Multi-lang (TR/EN/ID) fixture'da sadece TR; V1-S7 LLM wiring sonrası
- KD-V1-S6-04: V1-S2 lint 26 hata + landing page rewrite kalıntı — V1-S8 cleanup

---

## §12 — Onay & Başlatma

**Branch kararı:** `feat/V1-S2-q1-frontend` (mevcut, V1-S2 6 commit + uncommitted'lar 4 commit toplam 10 commit) **üzerinde** devam → V1-S6 6 commit ekle = 16 commit. Tek PR `V1-S2 + V1-S6 vitrin frontend kabuk` olur.

**Alternatif:** Yeni `feat/V1-S6-q3-frontend` branch off main. Daha temiz history ama V1-S2 PR'ı önce push edilmeli.

**Default seçim:** mevcut branch üstünde devam (Omer aksini söylemezse).

Omer explicit onay: **"V1-S6 başla"** yazınca:

1. V1-S6-01 → -02 → -03 → -04 → -05 → -06 sırayla atomic commit
2. Her commit sonrası `tsc --noEmit` + `vitest run` PASS
3. -02/-03 sonrası Q1 test 9/9 PASS retest
4. DoD §8 checklist tamamlanmadan PR açılmaz

**Tahmini süre:** 1 oturum (~2-3 saat aktif).
