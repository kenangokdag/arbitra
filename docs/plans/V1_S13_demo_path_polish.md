# V1-S13 — Demo Path Cilası (BibliometricSummaryPage Pilot)

**Sub-sprint kodu:** V1-S13
**Önkoşullar:** F10 Phase 1 ✅ (BibliometricSummaryPage iskelet `e001a41`); V1-S12 ✅ (mevcut branch base)
**Plan tarihi:** 2026-05-10
**Tek doğruluk kaynağı:** Bu manifest
**Onay:** Omer 2026-05-10 — "evet. onaylıyorum. bütün iyileştirmeleri yapalım."
**Branch:** `feat/V1-S13-demo-path-polish` (off `v1-s12-sesli-arama-ve-dinlet` HEAD)

---

## §0 — Amaç

Demo path discovery-3 (`BibliometricSummaryPage`) tek dosya pilotunda 2 katman cila uygula:
- **Yol B (perceived quality):** açılış staggered reveal + bar/list hover state + skeleton loading
- **Yol C (epistemic showcase):** veri kaynağı pili + metrik "neden bu sayı?" popover + DemoHint genişletme

Pilot başarılıysa pattern (`<DataProvenance>`, motion variants, skeleton) diğer 29 sayfaya **ayrı plan**la yayılır. **Yol A (chart library swap)** bu plan dışı, sonraki sprint'e ertelendi.

---

## §1 — Mevcut durum (envanter — okundu)

### Frontend stack (web/package.json)
- Next 16.0 + React 19 + Tailwind 4 + Turbopack
- `@base-ui/react@^1.4.1` ✅ (Tooltip + Popover Yol C için kullanılacak)
- `@tanstack/react-query@^5.59` ✅ (loading state için P004'te kullanılacak)
- `lucide-react@^0.460` ✅ (Info ikonu)
- `tw-animate-css@^1.4` (mevcut, tutulur)
- **`motion` YOK** → P001'de eklenir

### Pilot dosya
- `web/src/components/project/BibliometricSummaryPage.tsx` (458 satır):
  - 5 blok: Top metrik (4 kart) · Yıl bar · Dil donut · Lotka bar · Top-10 yazar+dergi
  - Saf CSS bar/donut (Recharts dependency YOK — canon)
  - CSS değişkenleri: `var(--color-accent)`, `var(--color-bg-card)`, `var(--color-rule)` vb.
  - Native `title=` HTML tooltip mevcut (lines 173, 249) → P005'te Base UI Popover ile değiştirilir/genişletilir
  - Helper'lar: `MetricCard`, `ChartCard`, `TopBarList`, `DemoHint`

### Test pattern
- `DefenseFormatPage.test.tsx`, `ProjectClosurePage.test.tsx` aynı dizinde — Vitest + RTL pattern.

### Mevcut bileşenler (yayılım için referans)
- `EstraBars.tsx` — D/W/S/T bar pattern (kanıt seviyesi UI'ı için ilham)
- `AdvisorBanner.tsx` — zone-aware bilgi paneli (mevcut, dokunulmaz)

---

## §2 — Hedef çıktı

### Yol B
1. **Mount stagger:** sayfa açılınca 5 ana blok 80ms aralıkla `opacity 0→1 + translateY 4→0` (240ms ease-out). `useReducedMotion()` true ise: instant render.
2. **Bar hover:** yıl bar + Lotka bar `opacity 0.75→1 + outline 1.5px var(--color-accent)`; top-10 liste row `bg-soft` hover.
3. **Skeleton:** `<BibliometricSummaryPageSkeleton />` — header gray + 4 metric placeholder + 4 chart placeholder. Backend Phase 2'de bağlanınca `useQuery({isLoading})` ile tetiklenir; şimdi export edilir, bağlanmaz.

### Yol C
4. **DataProvenance pill:** her ChartCard sağ-üstünde `Kaynak · N=240 · 2026-05-09 · A` etiketi. Hover'da Base UI Popover (openOnHover):
   - Kaynak (örn. warehouse aggregate)
   - Örneklem (N + eksik veri sayısı)
   - Hesaplama (1-2 cümle metod özeti)
   - Güncellik (tarih)
   - Kanıt seviyesi (A/B/C)
5. **MetricCard "neden":** 4 üst kartta sağ-üst `Info` ikonu (lucide). Hover/click Popover:
   - Hesaplama özeti (örn. "Medyan yıl: 240 makalenin yayın yılı medyanı, P25=2017, P75=2023")
6. **DemoHint genişletme:** "neden mock?" link → Popover'da Phase 2 plan referansı (`docs/plans/F10_back_front_integration_demo_path.md` §3).

---

## §3 — Yol kararları

### KD-V1-S13-01 — `motion` (motion/react), framer-motion DEĞİL
Modern fork (motion-dev), React 19 native. Bundle ~50-60KB gzipped, tree-shakable. Tüm sayfalara yayılım için tek değer.

### KD-V1-S13-02 — Tooltip vs Popover karar matrisi
- **Native HTML `title=`:** bar üstü hover (mevcut, korunur — hızlı, her cihazda çalışır)
- **Base UI Popover (openOnHover):** info ikonu, pill — Base UI doc'unun explicit önerisi (touch + screen reader accessibility)
- **Base UI Tooltip:** kullanılmaz (bu pilotta).

### KD-V1-S13-03 — Veri "kanıt seviyesi" değer aralığı
- **A** = warehouse aggregate (canlı SQL hesap)
- **B** = cached (Pinecone metadata, ghost-card vb.)
- **C** = estimate / synthetic (mock fixture, sentetik üretim)
- Pilotta tüm 5 blok = **A** (canon: "mock = ürün", fixture'ı A grade simüle et).

### KD-V1-S13-04 — Skeleton bağlama post-MVP
P004'te skeleton bileşeni yazılır + export edilir; **şimdi BibliometricSummaryPage'de tetiklenmez** (fixture sync). Phase 2 backend wiring'de `useQuery` bağlandığında `isLoading ? <Skeleton/> : <Page/>` deseniyle aktive edilir. Şimdi ölü kod değil — pattern hazırlığı + test edilebilir.

### KD-V1-S13-05 — `<DataProvenance>` ayrık dosya
`web/src/components/project/DataProvenance.tsx` — sonraki 29 sayfaya yayılım için reusable. Props: `source`, `n`, `missing?`, `method`, `updatedAt`, `confidence: "A" | "B" | "C"`.

### KD-V1-S13-06 — Push timing
Lokal-only (Hibrit workflow B-014). Omer "push" diyene kadar bekle.

---

## §4 — Atomik commit boundary (R13.13 build PASS empirik kanıt zorunlu)

| # | Commit | Kapsam | Yeni LOC (~) |
|---|---|---|---|
| P001 | `chore(web): add motion library` | `npm install motion` + smoke import test | 30 |
| P002 | `feat(web): mount stagger reveal on BibliometricSummaryPage` | motion variants + 5 blok stagger + useReducedMotion | 60 |
| P003 | `feat(web): bar/list hover polish (B2)` | year bar + lotka + top-10 hover state | 40 |
| P004 | `feat(web): BibliometricSummaryPageSkeleton + motion shimmer` | skeleton bileşeni export | 90 |
| P005 | `feat(web): DataProvenance pill + Base UI Popover (C1)` | DataProvenance.tsx + 5 ChartCard entegrasyon | 110 |
| P006 | `feat(web): MetricCard "neden bu sayi?" Popover (C2)` | Info ikon + hesaplama popover'ları | 70 |
| P007 | `feat(web): DemoHint Phase 2 reference Popover (C3)` | DemoHint genişletme | 30 |

**Toplam:** ~430 LOC, 7 atomik commit, ~7-9h.

**Her commit öncesi zorunlu (R13.13):**
```
cd web && npm run build && npm run typecheck
```
PASS log commit body'de inline (`✓ Compiled successfully` + son 3 satır).

---

## §5 — Test / kanıt

### Yeni test: `web/src/components/project/BibliometricSummaryPage.test.tsx`
- T1: Render no crash (5 blok DOM'da)
- T2: motion variants present (data-state="visible" reach edilir)
- T3: Reduced motion: instant render (variants delayChildren=0)
- T4: Popover open on Info hover (DataProvenance pill)
- T5: MetricCard Info ikonu mevcut + popover içerik render

Ayrı test: `web/src/components/project/DataProvenance.test.tsx`
- T1: Render with required props
- T2: Confidence A/B/C renkleri
- T3: openOnHover behavior

### Browser smoke (Omer manuel, sprint sonu)
1. `cd web && npm run dev` → http://localhost:3000
2. `/q` → sorgu → Literatür Özeti → "Projeye Dönüştür" → `/project/p1/discovery-3` aç
3. ✅ 5 blok yumuşak staggered açılıyor
4. ✅ Bar hover'da accent outline beliriyor
5. ✅ Sağ-üst pill hover → popover (kaynak/N/güncellik/kanıt) açılıyor
6. ✅ MetricCard Info hover → "neden bu sayı?" popover açılıyor
7. ✅ DemoHint "neden mock?" link → Phase 2 popover
8. ✅ macOS Reduce Motion ON → animasyonsuz, anında render

---

## §6 — Risk

1. **Bundle size:** motion ~50-60KB gzipped. Kabul (tree-shake düzgün; tüm sayfalara yayılım için stratejik). İzleme: P001 sonrası `next build` output Total First Load JS delta.
2. **Tooltip/Popover karışıklığı:** Karar net (KD-02). Pattern doc P005 commit body'sinde özet.
3. **CSS variable canon kayması:** Popover bg/ink mevcut tokenlerle (`--color-bg-card`, `--color-ink`, `--color-rule`). Yeni renk YOK.
4. **Demo path bozma:** F10 Phase 1 demo akışı (`/q → Literatür Özeti → Projeye Dönüştür → discovery-3`) korunmalı. Browser smoke'ta verify (§5).
5. **Mevcut `title=` HTML tooltip silme:** P003'te bar hover'da motion outline ekleyince `title=` kalır mı? **Karar:** Native title kalır (mobil hover yok, accessibility yedek); motion outline fareyle hover'da tetiklenir. Çift katman OK.

---

## §7 — Negatif kapsam (yapılmayacak)

- ❌ Recharts/Visx/Observable Plot grafik kütüphanesi — Yol A, ayrı sprint
- ❌ Mobile responsive iyileştirme — F4-S5 scope
- ❌ Dark mode — KD-22 post-MVP
- ❌ Diğer 29 project sayfası — pilot başarılıysa yayılım ayrı plan
- ❌ TanStack Query backend wiring — Phase 2 (F10 Phase 2)
- ❌ Accessibility full audit — Base UI'ın getirdiği ARIA yeterli pilotta
- ❌ Animasyon abartısı (parallax, page transition, route morph) — akademik canon ihlali
- ❌ Yeni font/palette — mevcut canon (slate/amber-700/Lora/Inter) korunur

---

## §8 — Açık sorular (cevaplandı)

| # | Soru | Cevap |
|---|---|---|
| 1 | Plan onayı? | ✅ "evet. onaylıyorum. bütün iyileştirmeleri yapalım." (2026-05-10) |
| 2 | Branch base? | feat/V1-S13-demo-path-polish off v1-s12-sesli-arama-ve-dinlet (sensible default) |
| 3 | Push timing? | Lokal-only, Hibrit workflow (KD-V1-S13-06) |

---

## §9 — Closure kriteri

- 7/7 atomik commit landed lokal
- Vitest 5+3 yeni test PASS
- `npm run build` + `tsc --noEmit` PASS
- Browser smoke 8/8 ✅ (Omer manuel)
- STATE.md update: V1-S13 KAPANDI ✅ + `<DataProvenance>` + motion pattern artık reusable
- NEXT_ACTION update: yayılım planı önerisi (29 sayfa için pattern application sprint)
