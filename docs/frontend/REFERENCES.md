# REFERENCES.md — Tasarım Referans Paneli

> **Amaç:** PaperMind UI'nın "warm-academic + minimal-professional + scholarly-modern" pozisyonu için **canlı kıyas seti**. Her referans 2-3 anahtar pattern + bizim adaptasyon notu.
>
> **Kullanım:** yeni component yazarken / Council R13'te "Daha İyisi Var Mı?" üyesi referans çağrılır / mockup v3 polish'i tartışılırken empirik dayanak.

---

## 1. Anthropic Claude.ai (en yakın referans — warm-academic-scholarly)

**URL:** https://claude.ai
**Pozisyon:** warm + minimal + scholarly. PaperMind hedefiyle birebir kesişen tek major ürün.

**Anahtar pattern'ler:**
- **Palet:** warm-bias bg (#FAFAF7 / kremimsi off-white), saf siyah text yerine `#1A1A1A` ink, accent `#CC7755` (turuncu-amber, manuscript hissi). Bizim mockup v3 #FAF8F3 + #1F2937 + #B26B2C ile birebir uyum.
- **Tipografi:** sans (Tiempos / Source Sans / system) gövde + serif start screen başlıkları. Bizim Inter+Lora benzer mantık.
- **Whitespace:** rakipten %30-50 fazla; her panel kendi başına nefes alır. Sidebar + main grid mockup v3'te aynı (240+main).
- **Mikro-imza:** logo manuscript-letter "C" (italic serif) — bizim brand mark amber-square + "P" benzer ekol.
- **Transition:** ease-out + 150-200ms; "fade-in conversation list" mockup v3'e referans.

**PaperMind adaptasyonu:** %85 zaten uygulu. Eksik: Claude.ai'nin "soft serif italic header" (start screen'de "How can I help?") — bizim Ana Sayfa'da Lora italic h1 buna eşdeğer.

---

## 2. Stripe Dashboard (professional + warm-tech)

**URL:** https://dashboard.stripe.com
**Pozisyon:** professional + warm-tech. Akademik değil ama "ciddi enterprise" güveni doping.

**Anahtar pattern'ler:**
- **Shadow stack:** 2-3 katman composition (Stripe Press blog 2022 yazılı). `box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 4px 12px rgba(0,0,0,.06)` standart. Bizim `--shadow-sm/md/lg` ile birebir.
- **Type scale:** 12/13/14/16/20/24/32/40 (Stripe-press); biz 12/13/14.5/17/22/28 (mockup v3 daha kompakt).
- **Spacing:** baseline grid 4px; nav-item padding 8×12 (bizim 7×10 mockup v3 daha kompakt).
- **Tactile transition:** `transform: translateY(-1px)` hover'da; biz `active:translate-y-px` (shadcn default).
- **Form layout:** label-üstü, input-altı, error-altında — mockup v3 form pattern'i Stripe ekol.

**PaperMind adaptasyonu:** Shadow stack ✅ (Aşama 1'de eklendi). Type scale ✅. Tactile ✅ Button.tsx'te. Eksik: Stripe-grade icon-text alignment (icon `data-icon` pattern) — Tier-1 Card import sonrası ele alınır.

---

## 3. Linear (sharp + dark-themed)

**URL:** https://linear.app
**Pozisyon:** sharp + dark + tech. Bizim warm-academic'e DOĞRUDAN kopya YASAK ama "command palette + keyboard-first nav" pattern'i alınır.

**Anahtar pattern'ler:**
- **Command palette:** Cmd+K → fuzzy search + actions. Bizim topbar global search Cmd+K mockup v3'te zaten var.
- **Keyboard nav:** her listede `j/k` + Tab + Enter; mockup v3 nav focus-visible amber halka + keyboard ok.
- **Skeleton loading:** subtle pulse (1.2s ease-in-out, opacity 0.4→0.7) — bizim `Skeleton` component aynı mantık.
- **Type hierarchy:** 4-katman ink (text-primary/secondary/tertiary/quaternary). Bizim `--color-ink/ink-soft/ink-mute/ink-faint` aynı 4-katman.

**PaperMind adaptasyonu:** Renk teması KOPYA EDİLMEZ (Linear dark, biz light-warm). Pattern: Cmd+K ✅, ink hierarchy ✅, keyboard nav F4-S2'de wiring sırasında.

---

## 4. ResearchRabbit (akademik referans — biz neye DEĞİLİZ?)

**URL:** https://researchrabbitapp.com
**Pozisyon:** akademik form + jenerik MUI palet + dark gradients. Anti-pattern referansı ("biz buna benzemeyeceğiz").

**Anti-pattern'ler (yapmayacaklarımız):**
- ❌ **MUI default palet** (mavi #1976D2 primary) — generic-tech, akademik sıcaklık yok
- ❌ **Tek-radius 4px** — depth hierarchy yok
- ❌ **"Discover papers" mavi gradient banner** — sterile, tıbbi cihaz hissi
- ❌ **Sidebar metallic gri** — krem/parchment ekol değil
- ❌ **Heading'de san-serif (Roboto)** — akademik dergi konvansiyonu serif

**PaperMind farkı:**
- Warm krem bg vs ResearchRabbit'in cold-white
- Lora italic display vs Roboto regular
- 3-katman radius scale vs tek 4px
- Manuscript underline (secondary button border-b amber) vs jenerik solid button

---

## 5. Diğer (kısa referans — gerek olunca derinleşir)

| Ürün | Tek anahtar pattern |
|---|---|
| **SciSpace** | MUI generic; biz ondan AYRILMAK İÇİN warm-academic seçtik |
| **Consensus** | minimal-cold-white + sade Tailwind; bizden type scale daha az detaylı |
| **Elicit** | white-blue-pure; sterile akademik laboratuar hissi (anti-pattern) |
| **Notion** | warm + tech (akademik DEĞİL); micro-typography iyi ama scholarly imza eksik |
| **Vercel Dashboard** | sharp-tech-dark; renk kopya değil, layout grid pattern referans |
| **Stripe Press (kitap micro-site)** | type-driven layout; akademik whitepaper kıyas için |

### 5.1 Animation curve ilham bankası (post-MVP polish için)

| Pattern | Curve | Kullanım niyeti |
|---|---|---|
| **Ease-out-expo** (mevcut canon) | `cubic-bezier(0.16, 1, 0.3, 1)` 150/200/300ms layered | UI etkileşim default — Stripe/Linear/Anthropic ekol |
| **Elastic settle** (ilham) | `cubic-bezier(0.175, 0.885, 0.32, 1.1)` 500ms | macOS Dock cascade, "neighbor scale" hover (1.5×/1.3×/1.15×) — KD-25 post-MVP color picker / annotation highlight / profil accent override için 5 semantic swatch ile (rainbow değil) |
| **3D rotate library shelf** | `linear infinite` 12s + `rotateX(-15deg)` tilt | "Sizin için arıyoruz" loading state — KD-24 SearchPending F4-S2 wiring; uiverse ilkhoeri ilham, decision_band 4-band semantic strips ile |
| **Slide-out label state** | `transform translateY(0→100%) + opacity 1→0` 200ms ease | KD-26 dropdown menu item state geçişleri (favorite toggle: "Add favorite" → "Remove from favorite", inline rename input slide-in, hold-to-confirm yerine AlertDialog) — uiverse Vercel context menu ilham |

### 5.2 Dark overlay surface pattern (KD-26 — F5/F6)

PaperMind ana sayfa cool-academic light kalır, **floating overlay'ler (dropdown/popover)** koyu varyant alabilir — Stripe Dashboard + Anthropic Claude.ai dosya menüsü + Linear context menu kanıtı: ana sayfa light, dropdown'lar slate-900 üstüne slate-50 ink. "Asil + depth + scholarly elevation" iletisi.

**Yeni token grubu (F5/F6 sprint'inde `globals.css`'e eklenecek):**
- `--surface-overlay-dark-bg`: slate-900 (`#0f172a`)
- `--surface-overlay-dark-fg`: slate-50 (`#f8fafc`)
- `--surface-overlay-dark-border`: slate-700 (`#334155`)
- `--surface-overlay-dark-hover`: slate-800 (`#1e293b`)
- `--surface-overlay-dark-danger`: red-300 (`#fca5a5`) — destructive aksiyonlar için ink

**Kullanım yerleri:** profil avatar dropdown (F5) + reading list `…` more menu (F6). Cmd+K command palette ve paper detay inline popover'ları **light kalmaya devam eder** (mevcut `--popover` tokens).

**Empirik test:** Anthropic Claude.ai dosya menüsü + Linear context menu yan-yana screenshot, F5 Council 37'de Defne BAĞLAYICI A satırında kanıt olarak.

---

## 6. Council R13 "Daha İyisi Var Mı?" üyesi için kanıt formatı

```
[Alternatif] Anthropic Claude.ai'nin login sayfası 2026'da serif-italic
"How can we help?" h1 kullanmaya başladı (kanıt: claude.ai/login screenshot
2026-04-20). Mockup v3'te Ana Sayfa h1'i yine Lora italic — birebir uyum.
Adaptasyon yapılır mı? GREEN — token zaten hazır.
```

Kanıt formatı: ürün adı + sayfa + tarih + screenshot/URL + bizim adaptasyonumuz.

---

## 7. PaperMind kıyas pozisyonu (özet matris)

| Eksen | SciSpace | Consensus | Elicit | Anthropic | Stripe | **PaperMind** |
|---|---|---|---|---|---|---|
| Sıcaklık | cold | cold | sterile | warm | warm | **warm** |
| Karakter | tech-form | minimal | clinical | scholarly | enterprise | **scholarly-modern** |
| Tipografi | san-serif | san-serif | san-serif | sans+serif | sans-only | **sans (Inter) + serif (Lora) çift** |
| Palet | mavi-MUI | beyaz-flat | mavi-beyaz | krem-amber | gri-mavi | **krem-amber (mockup v3)** |
| Radius scale | 1-katman | 2-katman | 1-katman | 2-katman | 3-katman | **3-katman (6/10/14)** |
| Shadow stack | 1-katman | yok | yok | 2-katman | 2-3-katman | **2-katman + lg 2-katman** |
| Mikro-imza | yok | yok | yok | logo italic | tactile lift | **manuscript underline (secondary border-b)** |

→ PaperMind açık konum: **warm-academic-scholarly + Stripe-grade depth**.
