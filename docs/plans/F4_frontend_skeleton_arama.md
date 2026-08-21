# F4 — Mini-Plan: Frontend Sprint 1 (App Shell + 8-Ekran Skeleton)

> **Statü**: REVİZE TASLAK — Mockup v3 onayı sonrası (Omer 2026-04-30, "bu daha iyi") + Senaryo B Frontend Lead boş (B-017)
> **Eski sürüm**: Krem-parşömen `#F5EBDD` + Crimson Pro + B42-050 §5 kütüphane fişi (mockup v3 ile **geçersiz**, R5 hiyerarşi gereği)
> **Üst plan**: `docs/plans/F1_master_plan.md`
> **Owner**: Claude (kod %100) · Sercan (post-hoc prod hardening: a11y axe-core, RSC boundary, Sentry frontend, CSP) · Omer (tasarım son söz + her sprint sonu onay)
> **Mockup canonical**: `~/Desktop/papermind-mockup/index.html` v3 (sade dil + beyaza yakın krem + sol sidebar)

---

## §0 Bağlam (3 cümle)

F4-S1 = **app shell + 8-ekran skeleton + design token**: kullanıcının siteye girip sol sidebar'dan tüm ekranları gezebileceği iskelet (içerik fixture sonra). Mockup v3 (Omer onaylı 2026-04-30) tasarım kanonu — eski B42-050 §5 kütüphane fişi (Crimson Pro + ESTRA bar + PMID Geist Mono renklendirme + krem-parşömen `#F5EBDD`) **MVP scope dışına çıkarıldı**, post-MVP polish'e ertelendi; mockup v3 sade paper card + Inter+Lora + beyaza yakın `#FAF8F3` + plain Turkish nav (jargonsuz). F4 artık **tek E4 Arama değil**, 8 ekran shell + routing — Makale Ara/Bana Önerilenler/Sohbet/Okuma Listem/Açık Makale/Profilim/Ana Sayfa/Onboarding stub'ları; her ekranın asıl içeriği F4-S2..S5 sprint'lerinde işlenir (sprint dilimleme §3'te).

---

## §1 Karar günlüğü (mockup v3 alignment)

| Karar | Kaynak | Etki |
|---|---|---|
| **Next.js 16** (App Router + Turbopack default + async PageProps + React 19 RSC) | DM-013 | `web/next.config.ts`, `web/package.json` |
| **Tailwind CSS v4** (CSS variable theming) | önceki F4 §1 (taşındı) | `web/src/styles/globals.css`, `web/tailwind.config.ts` |
| **Mockup v3 design tokens** — `--bg #FAF8F3` (beyaza yakın krem) / `--bg-soft #F4F1EA` (sidebar) / `--bg-card #FFFFFF` (kart) / `--accent #B26B2C` (sıcak amber) / `--ink #1F2937` / Inter UI + Lora başlık | Mockup v3 (Omer onayı 2026-04-30) | `web/src/styles/globals.css` `:root` |
| **Tipografi**: Inter (UI body 400/500/600/700) + Lora (display 400/500/600 + italic 400) — OFL ücretsiz, Google Fonts. **Crimson Pro + Geist Sans + Geist Mono kaldırıldı** (eski B42-050 §2 mockup v3'te kullanılmıyor). | Mockup v3 + Council R13 6-rol post-mockup verdict | `next/font/google` 2 font |
| **shadcn/ui base + override** (mockup v3 stiline geçirilen Button/Input/Card/Tabs/Dialog/Select/Tooltip) | Önceki F4 §1 + chat plan onayı | bileşen tabanı Radix |
| **State stack**: TanStack Query (server) + Zustand (client) + RHF + Zod | Önceki F4 §1 (taşındı) | `web/src/lib/api.ts`, `web/src/lib/zustand-stores/` |
| **Sol sidebar layout** — 240px sidebar + 56px topbar + main grid (mockup v3 SciSpace pattern); 4 nav grup: MVP (6 item: Ana Sayfa/Makale Ara/Bana Önerilenler/Makaleyle Sohbet/Okuma Listem/Açık Makale) + Hesap (Profilim+Ayarlar) + Yakında (3 locked) | Mockup v3 + Omer feedback "üstteki sayfa seçeneklerini solda hayal etmiştim. sci-space gibi" | `web/src/components/Sidebar.tsx` + `Topbar.tsx` |
| **Plain Turkish nav labels** — "Ana Sayfa / Makale Ara / Bana Önerilenler / Makaleyle Sohbet / Okuma Listem / Açık Makale / Profilim / Hoş Geldin"; jargon yasak ("tezgâh / Discovery / Curation / Listener / Anchor" UI'da görünmez) | Mockup v3 + Omer feedback "anlamsız terimler... akademisyen için kullanışlı değil" | sidebar + topbar breadcrumbs |
| **URL routing** — kısa İngilizce slug (tech-friendly): `/` (Ana Sayfa), `/search`, `/top5`, `/chat`, `/reading-list`, `/paper/[id]`, `/profile`, `/onboarding`. **Eski `/kutuphane/arama/[query_id]` iptal** (mockup v3 sade routing). | Mockup v3 + R5 (mockup üstün) | `web/src/app/<route>/page.tsx` |
| **Sade PaperCard** (mockup v3) — Lora başlık 17px + meta Inter 12.5px (yazar/dergi/yıl/atıf) + abstract excerpt 3-line clamp + tags (open access/paywall/Türkçe) + 4 action button (Detay/Listeme ekle/Özetle/Sohbet et). **Eski kütüphane fişi spec (ESTRA bar + PMID Geist Mono 12-segment renklendirme + termo-strip + paper-grain texture) post-MVP polish** | Mockup v3 supersedes B42-050 §5 (R5) | `web/src/components/PaperCard.tsx` (basit varyant) |
| **K1 + K9 runtime invariants korundu** — `year_verified=false` → "Klasik kaynak (yıl yükleniyor)" placeholder, `confidence<0.5` → "?". Backend response shape (`PaperCard.year_verified`, `signals_13`) UI yorumlar, frontend skor uydurmaz. | R8 K1+K9 (sabit) + B-018 backend response | `PaperCard` + `Citation` component |
| **i18n**: `next-intl` baştan kurulu (TR varsayılan + EN/ID slot açık), `[locale]/` route group F5 onboarding sonrası migration; F4-S1 TR-only baseline | Chat plan Q4 + B-005 dil seçimi | `web/src/lib/i18n/{tr,en,id}.ts` flat key |
| **Auth**: dev JWT mock (`localStorage` token, payload `{sub: "dev-user"}`) — Sercan magic-link SMTP (KD-x) gelene kadar; production için `next-auth` + Supabase auth Sercan handoff | Chat plan Q2 + B-018 backend AuthMiddleware | `web/src/lib/auth.ts` |
| **Repo layout**: monorepo `papermind-app/web/` (api/ ile aynı root); `web/` ayrı `package.json` + bağımsız node_modules | Chat plan Q3 + zaten skeleton var | `web/` root, `package.json` |
| **API integration**: fixture-first; backend 501 NotImplemented → "demo verisi gösteriliyor" banner; F2 PASS sonrası gerçek `/api/search` swap; cache `staleTime: 1h` Redis L1 ile hizalı | Önceki F4 §1 + B-018 6 endpoint 501 | `web/src/lib/fixtures/`, `web/src/lib/api.ts` `useFixtureFallback` flag |
| **Loading + Error route segments** (React 19 Suspense + ErrorBoundary) | Council 14 düzeltme (önceki F4 P042a) | `app/loading.tsx`, `app/error.tsx` (root + per-route) |
| **Lucide React** (sidebar icon + action icon) — eski "kalem + cilt-sırtı SVG" F6+'a ertelendi (mockup v3'te yok) | Mockup v3 ascii icon yerine Lucide swap önerilir | `lucide-react` package |
| **Framer Motion**: F4-S1'de **YOK** (sade shell, motion S4'te bottom-bar slide vs.) | Mockup v3 minimalizm | F4-S2+ kararı |
| **Dark mode**: F4'te **YOK** (mockup v3 light-only); B42-050 OPEN-DD4 pilot sonrası | Mockup v3 + OPEN-DD4 | F4 light-only |
| **Mobile responsive**: F4-S1 desktop-first + tablet basic; sm/md breakpoint var, full mobile post-MVP | Önceki F4 §1 (taşındı) | breakpoint sm (640px) flex-col |
| **A11y**: WCAG AA hedefi (kontrast 4.5:1 + focus-visible amber ring + klavye nav + ARIA), Lighthouse a11y ≥90 | Önceki F4 §1 (taşındı) | global CSS focus-visible utility |
| **Test stratejisi**: Vitest + RTL component tests (P037'de setup); Playwright E2E F7'ye ertelendi (Council 14 Fayda-Maliyet) | Önceki F4 §1 + Council 14 | F7 P071 |

---

## §2 Sayfa sözleşmesi (8 ekran shell)

```yaml
layout:
  grid: 240px (sidebar) + 1fr (main); 56px (topbar) + 1fr (main content)
  sidebar: web/src/components/Sidebar.tsx (RSC default; "use client" sadece active state için usePathname)
  topbar: web/src/components/Topbar.tsx ("use client" — global search + breadcrumb dynamic)

routes:
  - path: /
    file: web/src/app/page.tsx
    label_tr: Ana Sayfa
    content_F4-S1: page-title "Hoş geldiniz" + lede + 4 stat placeholder + 3 card placeholder (devam ettiğiniz / öneri / hızlı başlangıç)

  - path: /search
    file: web/src/app/search/page.tsx
    label_tr: Makale Ara
    content_F4-S1: page-title + lede + arama input + filter chip placeholder + 4 PaperCard placeholder
    F4-S2 hedef: gerçek POST /api/search wiring + fixture fallback

  - path: /top5
    file: web/src/app/top5/page.tsx
    label_tr: Bana Önerilenler
    content_F4-S1: page-title + hint banner (sorgu) + 5 PaperCard placeholder ("neden seçildi" stripe)
    F4-S2 hedef: POST /api/top5 wiring (B-018 P050 sonrası)

  - path: /chat
    file: web/src/app/chat/page.tsx
    label_tr: Makaleyle Sohbet
    content_F4-S1: chat-wrap grid (240px context + main) + 1 user msg + 1 assistant msg placeholder
    F4-S3 hedef: POST /api/chat SSE streaming (B-018 P020)

  - path: /reading-list
    file: web/src/app/reading-list/page.tsx
    label_tr: Okuma Listem
    content_F4-S1: page-title + 3 tab (İstiyorum/Okuyorum/Bitirdim) + 4 row placeholder
    F4-S3 hedef: GET /api/reading-list (B-018 P035)

  - path: /paper/[id]
    file: web/src/app/paper/[id]/page.tsx
    label_tr: Açık Makale (breadcrumb dynamic)
    content_F4-S1: page-title + meta + 4 tab (Kısa/Orta/Uzun/Özgün) + summary block placeholder + sidebar künye/yazarlar/ilgili
    F4-S4 hedef: GET /api/papers/{id} (yok — B-010 §3 paper detail Zustand cache pattern; backend endpoint yok, search response'tan cache)

  - path: /profile
    file: web/src/app/profile/page.tsx
    label_tr: Profilim
    content_F4-S1: page-title + profile pic + meta-row 6 satır + 2 card (Tercihler + Aboneliğim)
    F4-S5 hedef: PATCH /api/users/me + tier display

  - path: /onboarding
    file: web/src/app/onboarding/page.tsx
    label_tr: Hoş Geldin
    content_F4-S1: onboard card + ad input + dil select + tier 3-grid + ilgi alanları input
    F4-S4 hedef: POST /api/onboarding (B-018 P046)

state_management:
  server: TanStack Query useQuery (queryKey: ["search", query, k, lang]; staleTime: 1h ↔ Redis L1 TTL)
  client: Zustand (web/src/lib/zustand-stores/) — sidebar collapse state, theme (light-only F4), query store + URL sync
  paperCard_cache: Zustand store (search response paper'ları cache'lenir; /paper/[id] buradan okur — ARCHITECTURE.md §3 pattern KORUNDU)

a11y:
  focus_ring: amber halka — `focus-visible:ring-2 focus-visible:ring-[#B26B2C]`
  contrast: 4.5:1 min (mockup v3 bg=#FAF8F3 / ink=#1F2937 → ratio 13.1:1 ✓)
  keyboard: Tab order doğal, sidebar `<nav>` + `<button>` items, main `<main role="main">`
  aria: sidebar nav-item `aria-current="page"`, topbar `<nav aria-label="Breadcrumb">`

mobile:
  breakpoint: sm (640px) sidebar collapse drawer; md (768px) sidebar inline
  reading max-w: 720px (mockup v3 paper detail)

i18n:
  F4-S1: TR-only baseline (next-intl provider kuruldu, `web/src/lib/i18n/tr.ts` flat key 80-100 string)
  F5: locale switching onboarding seçimine göre
```

---

## §3 İmplementasyon adımları (atomik P-numara — F4-S1 scope)

| P | İş | Dosya | LOC | Test |
|---|---|---|---|---|
| **P037** | Next.js 16 + Tailwind v4 + tooling (tsconfig strict + ESLint + Prettier + path alias `@/`) + dev/build script + .gitignore (web/) | `web/package.json`, `web/next.config.ts`, `web/tsconfig.json`, `web/tailwind.config.ts`, `web/.eslintrc.json`, `web/.prettierrc.json`, `web/.gitignore` | ~150 | smoke: `npm run dev` 200 + `npm run build` 0 type error |
| **P038** | Root layout + 2 font load (Inter + Lora) + design tokens CSS var (`:root` mockup v3 palet) + QueryClientProvider + ThemeProvider scaffold + Toaster slot | `web/src/app/layout.tsx`, `web/src/styles/globals.css`, `web/src/lib/query-client.tsx` | ~180 | smoke: `<html lang="tr">` + bg `#FAF8F3` + Inter+Lora yüklü |
| **P039** | Sidebar component (brand mark + 4 nav grup + active state via usePathname + locked items + mobile drawer placeholder) | `web/src/components/Sidebar.tsx`, `web/src/lib/nav-config.ts` | ~140 | unit: 8 nav item render + active state matchPathname |
| **P040** | Topbar component (dynamic breadcrumb + global search input cmd+k placeholder + 2 icon button + user chip avatar) | `web/src/components/Topbar.tsx` | ~80 | unit: breadcrumb pathname → label mapping; cmd+k focus event |
| **P041** | 8 route stubs — `/` + `/search` + `/top5` + `/chat` + `/reading-list` + `/paper/[id]` + `/profile` + `/onboarding` (her biri page-title + lede + placeholder content matching mockup v3) | `web/src/app/page.tsx` + 7 route folder × `page.tsx` | ~400 | smoke: 8 route 200 dev mode + breadcrumb doğru |
| **P042** | API client (fetch wrapper + Authorization Bearer + 401 redirect + 429 toast + 501 fixture fallback) + dev JWT mock (`localStorage` token) + TanStack Query Provider client | `web/src/lib/api.ts`, `web/src/lib/auth.ts`, `web/src/lib/query-client.tsx` (extend) | ~120 | unit: 401 → /onboarding; 501 → fixture banner; JWT decode payload sub |
| **P043** | TypeScript types backend Pydantic mirror (PaperCard + SearchResponse + Top5Response + ChatMessage + ReadingListItem + Faithfulness + GateWarning + DecisionBand StrEnum) + 5 fixture JSON (search/top5/chat/reading-list/paper) | `web/src/lib/types.ts`, `web/src/lib/fixtures/*.json` | ~250 | unit: type assertion fixture roundtrip; DecisionBand 4 değer |
| **P044** | Loading + Error route segments — root `app/loading.tsx` (3 placeholder card shimmer) + root `app/error.tsx` (Banner + retry); `not-found.tsx` (404 sade) | `web/src/app/loading.tsx`, `error.tsx`, `not-found.tsx` | ~80 | smoke: artificial delay 2s → shimmer; throw → error UI; /unknown → 404 |

**Toplam F4-S1**: 8 atomic commit, ~1400 LOC. Playwright E2E F7'ye ertelendi.

> **Sprint geri kalan dilimleri** (ileride ayrı sprint plan'larında işlenir, şu anki F4 planı dışında):
> - F4-S2 (3 gün): Makale Ara + Bana Önerilenler — gerçek `/api/search` + `/api/top5` wiring + filter UI + tags
> - F4-S3 (3 gün): Sohbet (SSE streaming) + Okuma Listem (CRUD) — `/api/chat` + `/api/reading-list`
> - F4-S4 (2 gün): Açık Makale (özet tabs + Zustand cache okuma) + Onboarding (`/api/onboarding`)
> - F4-S5 (2 gün): Profilim + Ana Sayfa dashboard + a11y/error/empty/mobile pass

---

## §4 Verification (8 manuel smoke senaryosu — F4-S1)

```bash
# S1: Build + type check + lint
cd ~/Desktop/papermind-app/web && npm install && npm run lint && npm run build
# Beklenen: 0 type error + 0 lint error + .next/ klasörü; bundle size <300KB initial

# S2: Dev server + design tokens render
npm run dev   # http://localhost:3000
# Beklenen: <html lang="tr"> body bg #FAF8F3; Inter + Lora yüklendi (DevTools Network); sidebar 240px sol, topbar 56px üst

# S3: 8 route navigation
# Manuel: sidebar'dan her ekrana tıkla
# Beklenen: 8 route 200 + breadcrumb topbar'da güncellenir + active sidebar item highlight

# S4: Plain Turkish nav verify
# Beklenen: sidebar'da "Ana Sayfa / Makale Ara / Bana Önerilenler / Makaleyle Sohbet / Okuma Listem / Açık Makale / Profilim / Hoş Geldin" — jargon yok

# S5: Loading state (artificial)
# loading.tsx delay 2s ekle: `await new Promise(r => setTimeout(r, 2000))`
# Beklenen: 0-2s arası 3 placeholder card shimmer; aria-busy=true

# S6: Error state (mock throw)
# Bir page.tsx'de `throw new Error("test")`
# Beklenen: error.tsx Banner + "Tekrar dene" buton + console error capture

# S7: Lighthouse (Performance + Accessibility + Best Practices)
npx lighthouse http://localhost:3000/ --output html --chrome-flags="--headless"
# Beklenen: Performance ≥90, Accessibility ≥90, Best Practices ≥95
# Önemli: kontrast 4.5:1 + focus ring + ARIA labels PASS

# S8: Mobile responsive smoke (Chrome DevTools 375x667)
# Beklenen: sidebar mobile drawer (collapsed); topbar shrinks; horizontal scroll YOK
```

---

## §5 Critical files

### Frontend touch (Claude kod %100)
- `web/package.json` — Next 16 + React 19 + Tailwind 4 + TanStack Query + Zustand + RHF + Zod + Lucide + next-intl
- `web/next.config.ts` (Turbopack default, async PageProps)
- `web/tsconfig.json` (strict + path alias `@/`)
- `web/tailwind.config.ts` (CSS variable theming, mockup v3 token map)
- `web/.eslintrc.json` + `web/.prettierrc.json` + `web/.gitignore`
- `web/src/styles/globals.css` (mockup v3 `:root` palette + global resets + focus-visible utility)
- `web/src/app/layout.tsx` (root + 2 font load + QueryClientProvider + i18n provider)
- `web/src/app/loading.tsx`, `error.tsx`, `not-found.tsx` (root)
- `web/src/app/page.tsx` (Ana Sayfa)
- `web/src/app/{search,top5,chat,reading-list,paper/[id],profile,onboarding}/page.tsx` (7 route stubs)
- `web/src/components/Sidebar.tsx`, `Topbar.tsx`
- `web/src/lib/nav-config.ts` (sidebar grup + label config)
- `web/src/lib/api.ts` (fetch wrapper + 501 fallback + JWT)
- `web/src/lib/auth.ts` (dev JWT mock)
- `web/src/lib/query-client.tsx` (Provider client)
- `web/src/lib/types.ts` (backend Pydantic mirror)
- `web/src/lib/fixtures/*.json` (5 fixture)
- `web/src/lib/i18n/tr.ts` (TR baseline strings 80-100 key)

### Tests touch (Vitest + RTL)
- `web/__tests__/sidebar.test.tsx` (8 nav + active state)
- `web/__tests__/topbar.test.tsx` (breadcrumb mapping)
- `web/__tests__/api.test.ts` (401/429/501 fallback)
- ~~Playwright E2E~~ → **F7 P071'e ertelendi**

### Read-only (DOKUNMA — pre-flight Read zorunlu)
- `~/Desktop/papermind-mockup/index.html` (mockup v3 — design canon)
- `~/Desktop/papermind-app/docs/plans/F1_master_plan.md`
- `~/Desktop/papermind-app/docs/plans/F3a_search.md` (endpoint kontrat tüketimi P042+S2)
- `~/Desktop/papermind-app/docs/HEDEF.md` (E1-E5 ekran tanımları + C1-C11)
- `~/Desktop/papermind-app/docs/ARCHITECTURE.md` (§3 paper detail Zustand cache pattern)
- `~/Desktop/papermind-app/docs/DM_RULES.md` (R1-R13 + R13.9 alan sahipliği + HK gates)
- `~/Desktop/papermind-app/api/models/*.py` (Pydantic kaynak — types.ts mirror referansı)

### YOK / silindi (eski F4 plan'dan kaldırıldı)
- ~~`web/src/components/EstraBar.tsx`~~ → post-MVP (mockup v3'te yok)
- ~~`web/src/components/PmidSegments.tsx`~~ → post-MVP (PMID Geist Mono renklendirme yok)
- ~~`web/src/components/Banner.tsx` el-yazısı~~ → sade banner (mockup v3 hint pattern)
- ~~`web/src/components/KararBant.tsx`~~ → F4-S2'de basit tag (canon/strong/frontier/risk)
- ~~`web/src/components/GateUyari.tsx`~~ → F4-S2 hint banner

---

## §6 TODO(sercan) — production hardening %20 (post-hoc)

> Frontend Lead boş (B-017). Sercan Backend Lead ana alan; frontend hardening post-hoc PR review batch (Council R13.9).

### 6.1 Frontend infrastructure
- [ ] Vercel project init + env var (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`)
- [ ] Sentry frontend init (`@sentry/nextjs` + KVKK PII scrub patterns paylaşılır)
- [ ] axe-core a11y audit (Lighthouse'a ek runtime DevTools)

### 6.2 RSC vs Client Component boundary review
- [ ] Server Components default: `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`
- [ ] Client Components: `Sidebar.tsx` (usePathname), `Topbar.tsx` (cmd+k state), `PaperCard.tsx` (interaktif), `query-client.tsx` (TanStack hydration)

### 6.3 Hardening
- [ ] CSP header (`web/middleware.ts`) — `script-src 'self'` + nonce
- [ ] Bundle analyzer (`@next/bundle-analyzer`) — initial chunk <300KB
- [ ] Web Vitals — LCP <2.5s, CLS <0.1, INP <200ms

### 6.4 Quality gate (F4-S1 PR merge öncesi)
- [ ] S1-S8 PASS (manuel smoke)
- [ ] Lighthouse Performance ≥90 + Accessibility ≥90
- [ ] 0 console error / warning dev mode
- [ ] Bundle size first-load <300KB

---

## §7 Commit disiplini

- **Branch**: `feat/F4-frontend-shell` (eski `feat/F4-frontend-skeleton` ile çakışmasın)
- **Atomic commit**: P037..P044 ayrı commit (hibrit workflow B-014 — lokal-first, push timing Omer kontrolünde)
- **Pre-flight Read**: §5 Read-only listesi — özellikle mockup v3 + ARCHITECTURE §3
- **Test gate**: §4 verification S1-S8 PASS olmadan PR merge **YASAK**
- **Co-Authored-By**: `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` her commit footer
- **Commit message format**: `[P0XX] web: <kısa öz>` (örn. `[P039] web: Sidebar 8 nav + 4 grup + active state`)
- **Hook bypass yasak**: pre-commit FAIL → root cause fix; `--no-verify` kullanma
- **Plan değişikliği**: bu mini-plan revize edilmeden code edit yasak (CLAUDE.md §0 / R1)

---

## §8 Önkoşullar — GÜNCEL DURUM (2026-04-30 gece)

### ✅ Kapanmış
| Önkoşul | Kapanış |
|---|---|
| DM-013 Next.js 16 stack onayı | ✅ DECISIONS.md |
| Mockup v3 design canon | ✅ Omer onayı 2026-04-30 ("bu daha iyi") |
| B-005 dil seçimi onboarding (TR/EN/ID) | ✅ DECISIONS.md |
| B-017 Senaryo B Frontend Lead boş | ✅ DECISIONS.md (post-hoc Sercan) |
| Chat plan stack onayı (5 karar lock) | ✅ Omer "onaylıyorum" 2026-04-30 |

### ⏳ F2/F3 backend bağımlılıkları (F4-S1'i ENGELLEMEZ — fixture-first)
| Önkoşul | Statü | Etki |
|---|---|---|
| F2 PASS (P006 HybridPoolRouter + P008 LVR concrete) | ⏳ Pinecone B-012 sonrası | F4-S2 gerçek `/api/search` swap |
| F3 PASS (chat SSE + summarize + reading-list concrete) | ⏳ Sercan handoff'lar | F4-S3+ gerçek wiring |

### ⏳ Aktif notlar
| Konu | Statü |
|---|---|
| METHOD §1 Akademik Mekanlar | ✅ tezgâh metaforu Omer onaylı (eski engelleyici düştü, mockup v3 yansıdı) |
| OPEN-DD4 Dark mode | ⏳ pilot sonrası karar (F4 light-only) |

**Sonuç**: F4-S1 tüm önkoşullar açık. Plan onayı sonrası P037 başlar.

---

## §Council R13 — F4-S1 revize plan (2026-04-30, post-mockup v3)

**Alan:** Frontend
**Alan sahibi (BAĞLAYICI):** _BOŞ_ (B-017 Senaryo B); Omer hakem + Sercan post-hoc onay açık iş listesinde

| # | Üye | Oy | Gerekçe (1 cümle) | İstediği (RED/YELLOW ise) |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟢 GREEN | Mockup v3 dosyası (`~/Desktop/papermind-mockup/index.html`) tam okunabilir, design tokens (`#FAF8F3`, Inter+Lora, sidebar grid) verifiable; Next 16 + React 19 + Tailwind 4 doğrulu (DM-013 + 2026-04 stable). | — |
| 2 | Akademik İsabet | 🟢 GREEN | K1 (year_verified) + K9 (confidence "?") runtime invariants korundu; signals_13 backend response shape değişmedi; PaperCard mockup v3 sade ama 13 sinyal görünürlüğü F4-S2'de tag/badge ile sağlanır. | — |
| 3 | Fayda-Maliyet | 🟢 GREEN | F4-S1 ~1400 LOC / 4 gün shell + skeleton — kütüphane fişi+ESTRA+PMID renklendirme post-MVP'ye ertelenince ~990 LOC iddiasından ~600 LOC tasarruf; sade mockup hızlı ship + iterate. | — |
| 4 | Daha İyisi Var Mı? | 🟢 GREEN | shadcn/ui base + override 2026 endüstri default; sol sidebar SciSpace pattern doğrulu (rakip benchmark); next-intl + App Router 2026'da Next 16 i18n best practice. | — |
| 5 | Global Çözüm | 🟡 YELLOW | i18n kuruldu (TR/EN/ID slot); a11y WCAG AA hedefi; **mobile drawer F4-S1'de placeholder** — mobile responsive tam pass S5'e ertelendi → Omer hakem mi? | F4-S1'de en azından sidebar collapse drawer çalışır (CSS-only), tam mobile pass S5; Omer "kabul" dese GREEN |
| 6 | Son Kullanıcı Avukatı | 🟢 GREEN | Mockup v3 sade dil + plain Turkish nav + beyaza yakın krem akademisyen + öğrenci için kullanışlı (Omer feedback "anlamsız terimler ile dolu" → çözüldü); 8 ekran shell tıklamayla gezilebilir → "ne yapacağımı anladım" testi geçer. | — |
| **A** | **Frontend Lead (BOŞ)** | — | Sandalye boş; karar 6 rol + Omer; post-hoc Sercan PR review açık iş listesi (KD-21 yeni). | — |

**Sonuç**: 5 GREEN + 1 YELLOW (Global Çözüm mobile drawer S1 vs S5 sorusu). **Omer hakem zorunlu** (1 YELLOW + alan sahibi yok kuralı, R13.9). Karar gerekli: F4-S1 mobile drawer **placeholder** mı (CSS-only collapse) yoksa **tam çalışır** mı?

**Empirik test gerekli mi?** EVET → S2 dev render mockup v3 ile yan-yana karşılaştır + S7 Lighthouse a11y ≥90 verify.

**KD-21 (yeni Bilinen Borç)**: Frontend post-hoc Sercan review batch — F4-S1..S5 sprint sonu PR'ları biriktirilip Sercan'a tek seferde verilir; Sercan return notları F4-followup commit'lere düşer.

---

**Final commitment**: Bu mini-plan onaylanırsa P037 commit'i `feat/F4-frontend-shell` branch'inde 24 saat içinde açılır; verification S1+S2+S3 PASS ile P037 PR mergeable. Tam F4-S1 (P037..P044) 4 günde browser'dan 8 ekran sidebar gezilebilir mockup v3 parite.
