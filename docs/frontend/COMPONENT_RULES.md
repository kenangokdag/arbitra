# COMPONENT_RULES.md — shadcn Override Politikası

> **Kapsam:** her `npx shadcn@latest add @<registry>/<component>` sonrası uygulanacak override checklist. Default shadcn vendor look = "amatör tabela"; PaperMind = warm-academic + minimal-professional + scholarly-modern.
>
> **Bağlayıcı kaynak:** F4-S1.5 §Council 31 (Defne Yıldız BAĞLAYICI GREEN); mockup v3 (`~/Desktop/papermind-mockup/index.html`).

---

## 0. Sıralama (her import için)

```
1. npx shadcn@latest add @shadcn/<comp>
2. dosyayı oku (src/components/ui/<comp>.tsx)
3. 7-checklist (§1) — uymayanı override
4. dev server localhost:3000 → 1 sayfada render
5. ekran inspect (DevTools computed style) → 4 token doğrula
6. unit test ekle (variant snapshot + a11y)
7. commit (atomic — tek component tek commit)
```

---

## 1. 7-checklist (override öncesi sor)

| # | Kontrol | Pas / fail |
|---|---|---|
| 1 | **Token uyumu** — `bg-primary` / `text-foreground` / `border-border` semantic isimler kullanılıyor mu? Raw renk (`bg-blue-500`, `#3b82f6`) yasak. | bakılır |
| 2 | **Radius** — mockup v3 hattı: chip/button=6 (sm), card=10 (md), modal/sheet=14 (lg). `rounded-xl` ve üstü mockup v3'te yok → token tanımı eklenmeli ya da `rounded-lg`'e çevrilmeli. | bakılır |
| 3 | **Shadow stack** — `shadow-md` 2-katman (Stripe ekol). Tek-katman shadow yasak. `shadow-2xl` aşırı, MVP'de kullanılmaz. | bakılır |
| 4 | **Transition** — `transition-all` jenerik, yasak. Yerine `transition-[<list>]` + `duration-150/200/300` + `ease-[cubic-bezier(0.16,1,0.3,1)]`. | bakılır |
| 5 | **A11y** — `focus-visible:ring-3 focus-visible:ring-ring/50` + `aria-invalid:` state + keyboard nav radix/base-ui'den geliyor. Eklenmesi gereken: `aria-label` icon-only button'larda. | bakılır |
| 6 | **Icon library** — `lucide-react` (components.json `iconLibrary: lucide`). Community registry farklı icon kütüphane import etmişse swap zorunlu. | bakılır |
| 7 | **Import path** — community registries hardcoded `@/components/ui/...` import edebilir. Bizim alias `@` doğru ama bazı registry default `~/` kullanır → rewrite zorunlu. | bakılır |

---

## 2. Anti-pattern listesi (yasak)

- ❌ **`space-y-*` / `space-x-*`** — yerine `flex flex-col gap-*` ya da `grid gap-*`
- ❌ **`w-* h-*` eşit boyutlarda** — yerine `size-*`
- ❌ **`overflow-hidden text-ellipsis whitespace-nowrap`** uzun zincir — yerine `truncate`
- ❌ **`dark:*` manual override** — token mapping üzerinden gitmeli (post-MVP `.dark` block'ta)
- ❌ **Inline `style={{ color: "#..." }}`** — token-only
- ❌ **Custom `animate-pulse` div** — `Skeleton` component
- ❌ **`<hr>` veya `<div className="border-t">`** — `Separator` component
- ❌ **`shadow-sm` tek-katman** override edilmemiş halde — globals.css `--shadow-sm` 2-katman ile uyumsuz olur (default Tailwind shadow-sm farklı)
- ❌ **`rounded-md` shadcn default** — mockup v3'te md=10px, ama Tailwind default md=6px değil; explicit `rounded-[var(--radius-md)]` ya da config'den emin ol

---

## 3. Component-bazlı override notları (büyür her import sonrası)

### 3.1 — Button (✅ override edildi, F4-S1.5 P047)

- `rounded-sm` (6px), `tracking-[-0.005em]`, `transition-[<5-prop>] duration-150 ease-[cubic-bezier(0.16,1,0.3,1)]`
- secondary variant: manuscript underline (`border-b-2 border-b-primary`)
- default size: `h-9 px-3.5` (mockup v3 6×14)
- `dark:*` class'ları kaldırıldı (KD-22 post-MVP)
- Test: `button.test.tsx` 11/11 PASS

### 3.2 — Card (sıradaki — F4-S2 öncesi)

Önerilen override:
- `rounded-md` (10px) — mockup v3 card radius
- `shadow-sm` 2-katman default; hover'da `shadow-md` (Defne tactile feel)
- border `1px var-rule` (kremin grisi, jenerik gri değil)
- header: `pt-6 px-6 pb-4`; content: `px-6 py-4`; footer: `pt-4 px-6 pb-5` (Stripe spacing)
- title: `font-serif text-lg tracking-[-0.01em]` (Lora 17px italic option)

### 3.3 — Sidebar (sıradaki — F4-S2 öncesi)

Önerilen: `@shadcn/sidebar-01` block (sade nav grouped by section) çalıştır → mockup v3 hattına çek:
- bg `--sidebar` (= `--color-bg-soft #F4F1EA`)
- nav-item radius-sm + padding 7×10 + gap-2.5
- active state aria-current="page" + bg-sidebar-accent + text-foreground
- locked badge: `Badge variant="outline" size="sm"` ("Yakında")

### 3.4 — Dialog / Sheet (sıradaki)

Önerilen:
- `rounded-lg` (14px) modal
- `shadow-lg` 2-katman
- backdrop `bg-foreground/40 backdrop-blur-sm`
- title: serif font + tracking
- close button: ghost variant + `size-icon-sm`

---

## 4. Verify komutu (her override sonrası)

```bash
# Build + type + lint + test
npm run build && npm run lint && npx vitest run

# Dev server visual
npm run dev
# → localhost:3000 ekranlarda DevTools inspect:
#   button.bg = oklch/rgb(amber B26B2C → 178, 107, 44)
#   card.bg = #FFFFFF
#   sidebar.bg = #F4F1EA
#   body.bg = #FAF8F3
#   transition-timing-function = cubic-bezier(0.16, 1, 0.3, 1)
```

Kanıt fail → P-NNN-fix commit ile düzelt; PASS → atomic commit.

---

## 5. Bilinen Borçlar (KD-22 + KD-23 yeni)

- **KD-22**: Dark mode `.dark` block + chart-* token mockup v3 dark variant mapping (post-MVP, B-019 ile uyumlu)
- **KD-23**: Tier-1 community registries (`@aceternity` / `@magicui` / `@kibo-ui`) için 2. konsey turu (F4-S2 başında)
