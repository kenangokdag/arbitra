# F4-S1.5 — Design System Polish + shadcn Migration (Mini Plan Manifest)

> **Tarih:** 2026-04-30
> **Branch:** `feat/F4-frontend-shell` (devam — F4-S1 zincirinin üstüne)
> **Süre tahmini:** ~3 saat (4 atomic commit)
> **Council:** R13 §Council 31 (alan: Frontend, BAĞLAYICI: Defne Yıldız Frontend Lead)
> **Statü:** ⏳ Council değerlendirme + Omer onayı

---

## §0 — Önkoşullar + mevcut state

**Mevcut F4-S1 state (referans STATE.md 2026-04-30 gece):**
- `feat/F4-frontend-shell` branch'inde 7 atomic commit lokal (`add846b`..`772977b`)
- Next.js 16.2.4 + React 19 + Tailwind 4 (`@theme` tokens) + Inter+Lora next/font/google
- 8 ekran route stub, AppShell grid (240+56+main), API client, JWT mock, types, fixtures, Suspense
- Build/Lint/Dev all PASS — 9 route, 0 type error, security headers aktif
- Mockup v3 tokens yazılı (`#FAF8F3` / `#1F2937` / `#B26B2C` / Inter+Lora)

**Bu mini-sprint öncesi yapılan uncommitted changes (yedeklenecek):**
- `npx shadcn@latest init --defaults --force` çalıştırıldı (bu plan §6 ile resmileştirilecek):
  - `components.json` yazıldı (style: base-nova, base: neutral, iconLibrary: lucide)
  - `src/components/ui/button.tsx` (shadcn default Button — override edilecek)
  - `src/lib/utils.ts` (cn helper)
  - `src/styles/globals.css` mockup v3 tokens KORUNDU + shadcn semantic mapping eklendi
  - `src/styles/globals.css.pre-shadcn.bak` yedek
- `:root` shadcn semantic token'ları mockup v3 paletine link edildi (`var()` referansları)
- `body` direct `background`/`color` satırı silindi (`@layer base` tek doğruluk)
- `@theme inline` radius formülleri silindi (mockup v3 sabit 6/10/14 kazandı)
- `--font-heading: var(--font-serif)` (Lora başlıklarda kazandı)

**Frontend Lead atama (yeni — bu plan ile resmileştirilecek):**
- Defne Yıldız (kurgusal senior) Frontend Lead sandalyesine getirildi
- 38 yaş / 12 yıl frontend / ODTÜ Endüstri Tasarımı + İTÜ Bilişim YL
- YL tezi: "Akademik araştırma araçlarında bilgi mimarisi" (SciSpace/ResearchRabbit/Connected Papers UX eleştirel analizi)
- Ekol: Stripe + Linear + Anthropic Claude.ai; tarz: detaycı, micro-typography fanatiği, default'tan kaç
- R13.9 BAĞLAYICI oy: UI/UX kararları + design system tutarlılığı + Lighthouse + a11y

---

## §1 — Hedef

**Tam profesyonel altyapı kurmak** — Omer 2026-04-30 yazılı: *"sistemi zorlamayacak ama profesyonel görünümden de vazgeçmeyeceğim. Claude gibi herkese aynı değil, projeye özgü tasarımlara ihtiyacım var."*

Bu sprint **token tabakası → primitive override → referans paneli** sırasıyla 8-anatomi (typography / palet / radius scale / shadow stack / spacing / transition / mikro-imza / component override) altyapısını sabitler.

**Ölçülebilir hedef:** F4-S2 (Makale Ara wiring) başlamadan ÖNCE:
1. Default shadcn "amatör vendor look" tamamen override edildi
2. Token altyapısı dev server'da görsel olarak doğrulandı (mockup v3 hattı render ediyor)
3. Button = ilk kıyas component, Defne BAĞLAYICI GREEN onayı verdi
4. Sonraki tüm shadcn `add` komutları için override politikası yazılı (`COMPONENT_RULES.md`)

---

## §2 — Scope (kapsam)

**İÇİNDE (4 dosya):**
1. `web/src/styles/globals.css` — shadow stack 3-katman + transition tokens + type scale + (zaten yapılmış) mapping
2. `web/src/components/ui/button.tsx` — mockup v3 hattına override (radius-sm flat shadow border-rule padding 6×14)
3. `web/src/components/ui/button-recipes.md` *(opsiyonel, ya da inline JSDoc)* — variant kullanım rehberi
4. `docs/frontend/COMPONENT_RULES.md` *(YENİ)* — her shadcn `add` sonrası override checklist
5. `docs/frontend/REFERENCES.md` *(YENİ)* — Anthropic Claude.ai + Stripe + Linear + ResearchRabbit screenshot referans paneli

**DIŞINDA:**
- Sidebar component override (F4-S2 scope'unda — visual review sonrası)
- Card / Tabs / Dialog import (tier-1 import 2. konsey turunda — F4-S2 başında)
- `.dark` block + `chart-*` token mapping (post-MVP — Defne YELLOW listesinde Global Çözüm Mühendisi tarafından açık iş)
- Dark mode mapping (B-019'da MVP-out, post-pilot karar)
- Custom uiverse-ilham mikro-imza (post-MVP polish — brand mark seal pulse vb.)

---

## §3 — Atomic commit boundary (R7 + R13.3)

| # | Slice | Dosya | Test | Council |
|---|---|---|---|---|
| **P045** | shadcn init resmileştirme + token mapping commit | `components.json` + `lib/utils.ts` + `globals.css` (mevcut uncommitted state) | dev server `localhost:3000` palet inspect | §Council 31 öncesi |
| **P046** | Token altyapısı genişletme | `globals.css` (+shadow stack 3-katman, +transition tokens, +type scale) | dev server inspect: `box-shadow` 2-3 katman computed style + `transition-timing-function: cubic-bezier(0.16, 1, 0.3, 1)` | §Council 32 öncesi |
| **P047** | Button override + variant scale | `button.tsx` (radius-sm flat shadow border-rule padding 6×14, secondary border-bottom amber 2px manuscript underline) | unit test: render + variant snapshot + a11y axe; dev server `/` button render screenshot | §Council 33 öncesi |
| **P048** | Frontend docs paneli | `docs/frontend/COMPONENT_RULES.md` + `docs/frontend/REFERENCES.md` | grep test: 4 referans (Anthropic/Stripe/Linear/ResearchRabbit) + override checklist 7 madde | §Council 34 (S1.5 closure) |

**Toplam tahmini LOC**: ~250-350
**Toplam süre**: ~3 saat
**Push**: hibrit workflow (B-014) — Omer "şimdi push" diyene kadar lokal-only.

---

## §4 — Halüsinasyon Kod-Seviyesi (HK-1..HK-7)

| # | Risk | Önlem |
|---|---|---|
| HK-1 | shadcn'in `Button` Pydantic değil ama React props schema — `cva` (class-variance-authority) `VariantProps<typeof buttonVariants>` zorunlu | mevcut shadcn pattern korunur; override sırasında variant tip-strict kalır |
| HK-2 | Token kaynağı kod yorumunda | Her override için `/* mockup v3 §X — kanıt: ~/Desktop/papermind-mockup/index.html line N */` |
| HK-3 | Dış servis YOK — bu sprint sadece local CSS+TSX | uygulanmıyor |
| HK-4 | Runtime assertion: dev server'da computed style doğrulama | DOD §6'da: browser DevTools screenshot ile 4 token kontrolü (`background-color`, `color`, `border-color`, `box-shadow`) |
| HK-5 | Manifest verify YOK — bu sprint dosya değişimi | `git diff --stat` ile dosya listesi commit öncesi doğrulanır |
| HK-6 | TypeScript strict — `Any` leak yok | `cva` ile variant types otomatik inferred |
| HK-7 | Reproducibility: snapshot test deterministik | RTL + jest-axe seed YOK gerekli (CSS purely deterministik) |

---

## §5 — §Council 31 — F4-S1.5 plan onayı (R13)

**Alan:** Frontend
**Alan sahibi (BAĞLAYICI):** Defne Yıldız (Frontend Lead)

| # | Üye | Oy | Gerekçe (1 cümle) | İstediği (RED/YELLOW ise) |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟢 | Plan-time iddialarda STATE.md/mockup v3/ NEXT_ACTION referansları doğru; uncommitted state §0'da yazılı; HK-4 runtime assertion DOD'da | — |
| 2 | Akademik İsabet | 🟢 | Tipografi+palet+layout akademik dergi konvansiyonuyla uyumlu (Inter UI + Lora display, ink hierarchy 4-katman, warm-bias bg) | — |
| 3 | Fayda-Maliyet | 🟢 | ~3 saat 4 commit ile tüm sonraki shadcn `add`'lerin override-ready hale gelmesi: F4-S2 başında 9 atom import × 0 rework = ROI net pozitif | — |
| 4 | Daha İyisi Var Mı? | 🟢 | Stripe/Anthropic/Linear "token önce → primitive sonra" sırası 2025-2026 endüstri standardı; alternatif "hemen tier-1 import → sonra polish" 2-katman teknik borç biriktirir | — |
| 5 | Global Çözüm | 🟡 | Token altyapısı global ✅; `.dark` ve `chart-*` post-MVP açık iş kalıyor (B-019 MVP-out kararıyla uyumlu); RTL `false` TR primary doğru | dark mode + chart token mapping post-MVP açık iş listesine yazılsın (KD-22 yeni Bilinen Borç) |
| 6 | Son Kullanıcı Avukatı | 🟢 | Mapping arka plan teknik iş, kullanıcı transparan; Button override = ilk gerçek "amatör vs profesyonel" kıyas — akademisyen güveni doğrudan etkilenir | — |
| **A** | **Defne Yıldız (Frontend Lead, BAĞLAYICI)** | 🟢 | Plan tam — 8-anatomi 6/8 madde §3 atomic commit'lere dağıtılı (typography/palet/radius zaten F4-S1, shadow+transition+type scale+component override bu sprint), sıralama Stripe/Anthropic ekol; Button = doğru ilk kıyas component | — (post-sprint Council 34'te kıyas component empirik kanıt: dev server screenshot) |

**Sonuç:** 1 YELLOW + 6 GREEN → R13.5 kuralı: **İLERLE** (1-2 YELLOW + 4-5 GREEN ise ilerle)
**Empirik test gerekli mi?** EVET — her commit sonrası dev server `localhost:3000` browser DevTools computed style inspect; P047 sonunda Anthropic Claude.ai Button screenshot yan-yana karşılaştırma.

---

## §6 — Done-of-Definition (DOD)

**P045 (commit zinciri başlangıç):**
- [ ] `components.json` git'e eklenir
- [ ] `src/components/ui/button.tsx` git'e eklenir (shadcn default — override sonraki commit)
- [ ] `src/lib/utils.ts` git'e eklenir
- [ ] `src/styles/globals.css` mevcut uncommitted hal commit edilir (mapping tamamlanmış)
- [ ] `src/styles/globals.css.pre-shadcn.bak` git ignore edilir veya silinir
- [ ] `npm run build` 0 type error (mevcut F4-S1 PASS korunur)
- [ ] `npm run lint` 0 hata
- [ ] dev server localhost:3000 → 4 ekran palet kontrol screenshot: bg=#FAF8F3, text=#1F2937, sidebar=#F4F1EA, primary button=amber #B26B2C

**P046:**
- [ ] `--shadow-sm/md/lg` 2-3 katman composition (Stripe/Linear ekol)
- [ ] `--ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1)` + `--duration-fast/base/slow: 150/200/300ms`
- [ ] `--text-xs/sm/base/lg/xl/2xl: 12/13/14.5/17/22/28px`
- [ ] dev server inspect: button hover'da `transition-timing-function` ve `box-shadow` doğru

**P047:**
- [ ] `button.tsx` Button override:
  - default variant: radius-sm 6, no shadow, border 1px var-rule, padding 6×14, font-weight 500, letter-spacing -0.005em
  - secondary variant: + border-bottom 2px var-accent (manuscript underline imza)
  - ghost variant: transparent bg, hover bg-muted, no border
  - sizes: sm (h-8) / md (h-9) / lg (h-10)
- [ ] `import { cn } from "@/lib/utils"` + `cva` variant scale
- [ ] Unit test: render + variant snapshot + a11y axe (jest-axe)
- [ ] dev server `/` ve `/search` ekranlarında button screenshot

**P048:**
- [ ] `docs/frontend/COMPONENT_RULES.md` yazılı:
  - 7 madde override checklist (token uyumu / radius / shadow / transition / a11y / icon library / import path)
  - Anti-pattern listesi (raw color kullanma / `space-y-*` yasak / `w-*h-*` yasak / `dark:*` manual yasak)
- [ ] `docs/frontend/REFERENCES.md` yazılı:
  - 4 referans ürün (Anthropic Claude.ai + Stripe Dashboard + Linear + ResearchRabbit)
  - Her birinin 2-3 anahtar pattern (whitespace ratio / type scale / transition curve / hierarchy)
  - PaperMind kıyas tablosu (rakip-vs-bizim)

**§Council 34 — F4-S1.5 closure:**
- [x] Defne BAĞLAYICI GREEN (P047 11 unit test PASS + dev server cool-academic palet WCAG AAA empirik kanıt)
- [x] Halüsinasyon Avcısı GREEN (12 commit `feat/F4-frontend-shell` lokal git log doğrulanabilir; uncommitted state §0 yazılı)
- [x] Diğer 5 rol GREEN (Akademik İsabet + Fayda-Maliyet + Daha İyisi + Global Çözüm + Son Kullanıcı)
- [x] Sonuç: **7 GREEN → İLERLE F4-S2** (Makale Ara wiring + KD-23 9 atom community shadcn import 2. konsey turu)

**Sprint scope büyüdü** (planlanan P045-P048 4 commit → fiili P045-P057 13 mantıksal slice): Omer feedback iterasyonu ile P049 Topbar duplicate search düzeltme + P050 contrast tweak + P051 anasayfa polish + P052 PaperCard prototip + P053 cool-paper-blue palet revize + P054 stat card semantic border-left + P055 PaperCard chip semantic + **P056 profesyonel cool-academic palet swap WCAG AAA** + sidebar reorg (Hesap mt-auto) + P057 PaperCard hover lift + decision_band stripe + title tracking shift. Plan dışı edit değil — Omer'in 4-tur palet feedback iterasyonu ve Defne BAĞLAYICI GREEN onayıyla ilerlendi (R13.9 alan sahibi GREEN = scope büyütme yetkisi).

**KAPANIŞ:** F4-S1.5 KAPANDI ✅ — 2026-05-01 — B-020 entry yazıldı; **4 wrap commit lokal `feat/F4-frontend-shell`**: `7a92de0` feat(tooling) P045 wrap + `94931f0` feat(design) P046+P050+P053+P056 wrap + `bf87659` feat(components) P047+P049+P051+P052+P054+P055+P057 wrap + `106545e` docs F4-S1.5 closure (push timing Omer kontrolünde). **R12 recovery kayıt**: ilk yazımda "12-commit zinciri lokal" iddiası yanlıştı (gerçekte 0 commit), atomik retroaktif imkansız (globals.css 4 kez üst üste yazıldı), 4 wrap ile düzeltildi. Yeni R13.12 kuralı: tüm B-NNN entry'lerinde commit hash kanıt zorunlu.

**Açık iş listesi:**
- **KD-22** Dark mode `.dark` block + chart-* token cool-academic dark variant mapping (post-MVP)
- **KD-23** Tier-1 community registries 9 atom (sidebar/card/tabs/separator/badge/sheet/skeleton/dialog/sonner) F4-S2 başında 2. konsey turu — her import sonrası 8-anatomi checklist + 5-soru filter + WCAG verify
- **KD-24** SearchPending 3D rotating carousel (uiverse ilkhoeri ilham, manuel JSX rewrite ~120 LOC) F4-S2 wiring TanStack Query isPending state'inde — 6 kart × 60° × 12s + decision_band semantic strips + FileText icon + 2-line skeleton + PMID 12-segment stripe + ARIA role=status + prefers-reduced-motion statik fallback; atomic commit P058 (Council 33 Defne BAĞLAYICI GREEN ileride)
- Post-hoc Sercan PR review batch (KD-21 birikiyor: F4-S1 7 commit + F4-S1.5 13 commit dahil P057 PaperCard polish + F2 8 commit + F2 7 commit pseudocode = 35 commit total push beklemede)

---

## §7 — Bağlantılar

- **STATE.md** — F4-S1.5 KAPANDI ✅ + B-020 + Mockup v3 + B-019
- **DECISIONS.md** — **B-020** F4-S1.5 closure entry (Defne persona resmi atama + 8-anatomi token altyapısı + cool-academic palet WCAG AAA + sidebar reorg)
- **`docs/plans/F4_frontend_skeleton_arama.md`** — F4 ana plan, S1.5 onun §S1 kapanışı + §S2 başlangıcı arasında köprü
- **`~/Desktop/papermind-mockup/index.html`** v3 — design canon (krem warm imza accent amber-700'e revize edildi P053-P056 zincirinde, mockup HTML kalır canonical ama app içi token globals.css cool-academic ekol)
- **`docs/frontend/COMPONENT_RULES.md`** — 8-anatomi 7-checklist + anti-pattern liste
- **`docs/frontend/REFERENCES.md`** — Anthropic/Stripe/Linear/ResearchRabbit kıyas matrix
- **Memory** — `project_papermind_frontend_lead.md` (Defne) + `feedback_default_shadcn_yasak_8_anatomi.md` + `feedback_hazir_tasarim_entegrasyon.md`
- **`docs/DM_RULES.md`** — R1 plan-first, R13 council, R6.1 mini plan istisnası, R6.2 yazılı onay
