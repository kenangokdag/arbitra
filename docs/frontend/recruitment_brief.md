# Frontend Lead — İşe Alım Brief'i

> **Statü:** **post-MVP'ye ertelendi** (B-017, 2026-04-30) — Senaryo B kararı: MVP boyunca Claude kod üretir + Omer iterasyon yapar + freelance illustrator 7 asset sağlar + Sercan post-hoc prod hardening. Frontend Lead aranması pilot sonrası kalite eşiği değerlendirmesinde tekrar açılır.
> **Council sandalyesi:** Frontend Lead boş kalır → kararları 6 değerlendirici rol + Omer alır; Sercan post-hoc onay açık iş listesine düşer (R13.9 alan sahibi yoksa kuralı).
> **İş bölümü (B-017 ile dondurulu):** Şimdi → MVP: Claude kod + Omer iterasyon + freelance illustrator + Sercan post-hoc. Pilot sonrası → kalite eşiği yetersizse Senaryo A (Frontend Lead arama) yeniden açılır.

---

> ⚠️ **Bu brief arşiv niteliğinde** — pilot sonrası tetiklenecek. Aktif aday süreci YOK. Aktif freelance illustrator brief: `docs/frontend/illustrator_brief.md`.

---

## 1. Proje özeti (aday için)

**PaperMind v4** — akademisyenler için literatür keşfi, hakemlik, savunma simülasyonu platformu (TR + EN + Bahasa Indonesia). Veri tabanı: 24.87M paper × 1024-d BGE-M3 embedding + 31.85M ghost + 504K gap matrix + ESTRA puanları + Council eleştirisi.

**Frontend kapsamı (B42-047 + B42-050 dondurulmuş):**
- 5 Tezgâh (Discovery / Curation / Gap Atlas / Authoring / Defense) × 25 alt-sayfa
- Notion-benzeri Defter (Tiptap block-based, per-project, drag-drop, /-slash menu)
- Danışman varlığı her sayfada (banner + chatbox + ✒ amber sembol)
- Lineer-zorunlu → serbest navigasyon (denizci pusulası rotası)
- 5.5 Simülasyon Odası — perde-reveal sinematik girişi (Google Flow video) + persona avatar + chatbox (Framer Motion)
- "Akademik Defter & Akşam Kütüphanesi" metaforu — kütüphane fişi PaperCard, cilt-sırtı sidebar

**Stack:**
- Next.js 16 (Turbopack default, App Router, async PageProps, React 19 RSC)
- Tailwind v4 (CSS-first config, 4-zone × 2-mode = 8 set CSS variable)
- shadcn/ui — **default görünüm sıfır**, full custom-styled
- Tipografi: Crimson Pro (display + banner italic) + **Lora serif body** (rakip ayrışım — rakipler hep sans-only)
- Tiptap block-based editor
- Framer Motion + Google Flow video asset (perde) + custom SVG pack
- TanStack Query + Zustand + RHF + Zod + Recharts + Visx
- next-intl (TR-only MVP + altyapı), WCAG AA, prefers-reduced-motion

---

## 2. Aranan profil — 4 öncelik

| Öncelik | Profil | Akademik fit | Teknik fit |
|---|---|---|---|
| **1** | Design Engineer + akademik araştırma tooling deneyimi (Tiptap/Notion-clone katkıcısı, Crimson Pro/Lora typography hassasiyeti) | Yüksek | Çok yüksek |
| **2** | Senior Next.js + Türk akademik UI deneyimi (üniversite IR sistemi, TÜBA/TÜBİTAK proje frontend, akademik dergi UI) | Yüksek | Yüksek |
| **3** | Junior+ "meraklı, öğrenmeye açık" (Sercan eşi — yüksek lisans/asistan, AI-asistanlı geliştirme) | Yüksek | Orta |
| **4** | Açık-kaynak Tiptap/BlockNote/Lexical contributor | Düşük | Çok yüksek |

**Bütçe ve zaman dengesi:**
- #1 ideal ama nadir + pahalı (Türkiye'de design engineer profili az);
- #2 sağlam ama akademik UI tecrübesi olan az;
- #3 Sercan ile uyumlu dinamik (öğren-üret), bütçe dostu, "iç ses" akademik kullanıcı için doğal;
- #4 saf teknik, akademik fit zayıf — design engineer'la pair gerekir.

**Önerilen sıralama: #3 → #2 → #1.** (Önce iç çevre, başaramazsak dış arama.)

---

## 3. Üç canlı değerlendirme görevi (top adaylar için)

### Görev A — Custom shadcn theme (90 dk)

**Brief:** Tailwind v4 + shadcn/ui kurulu boş Next.js 16 projesinde, B42-050 design direction'a uygun **Discovery zone** custom theme kur.

**Gereksinimler:**
- Crimson Pro (display) + Lora (serif body, weight 400/600) + Geist Sans (UI) + Geist Mono (PMID 12-segment) — 4 font, OFL ücretsiz
- 4-zone × 2-mode = 8 CSS variable set (light/dark Discovery + Curation + Gap Atlas + Authoring + Defense — sadece Discovery zonunu uygula, diğerleri placeholder)
- Discovery light zone: `--bg: #F5EBDD` (krem-parşömen) + `--ink: #1A1F3A` + `--accent: #E8A157` (abajur amber)
- shadcn `Button` 4-sınıf (primary amber + secondary ink-border + ghost + adviser-ask pill)
- TypeScript strict, ruff eşi prettier+ESLint
- Tek atomic commit + `npm run typecheck && npm run lint && npm run build` PASS

**Değerlendirme:**
- ✅ B42-050 §5 paletten sapma yok
- ✅ shadcn default görünüm sıfır (tema gerçekten kustomize)
- ✅ Lora body kullanımı (rakip ayrışım ana sinyal)
- ✅ CSS variable yaklaşımı (zone+theme attribute pattern)

### Görev B — PaperCard prototipi (60 dk)

**Brief:** Statik mock paper verisinden (JSON dosyası verilir) **PaperCard kütüphane fişi** komponenti yap.

**Gereksinimler:**
- Bg `#FAF7F2` + 1px gri-bej border + 6px radius + paper-grain texture (CSS radial-gradient)
- PMID 12-segment (örn. `2.07.103.T11466.0.0.C.M.M.tr.R.v1`) — Geist Mono 11px, segment renklendirme (D=indigo, F=sage, S=slate, T=plum, Y=amber, Q=bronze, I=burgundy)
- Lora başlık 16px, max 2 satır truncate
- ESTRA termo-strip (8 segment, soldan sağa renk skalası)
- ⌘ citation count sağ-üst (Geist Mono küçük)
- Hover: 6px → 8px shadow + 1px scale
- **GhostCard varyantı** (opacity 0.85 + dashed border + "Klasik kaynak" rozeti + **yıl gizli — K1 halüsinasyon yasağı**, sadece year_verified gösterilir; verilmediğinde `—` placeholder)
- Storybook veya `app/(test)/paper-card/page.tsx` ile 4 varyant (corpus + ghost + dark mode corpus + dark mode ghost)

**Değerlendirme:**
- ✅ K1 halüsinasyon yasağı uygulanmış (ghost yıl gizli)
- ✅ PMID segment renklendirme akademisyene anlamlı (rastgele renk değil, B42-040 12 chip kategorisiyle uyumlu)
- ✅ Kütüphane fişi metaforu görselde belirgin (texture + serif tipografi + paper-grain)
- ✅ Dark mode "Gece Kütüphanesi" mood'u (light invers değil, kendi atmosferi)

### Görev C — Council eleştirisi simülasyonu (45 dk yazılı)

**Brief:** Connected Papers, Litmaps, Elicit, SciSpace screenshot'ları verilir (önceden hazırlanmış). 7-kontrol formatında "PaperMind frontend bu rakiplerden nasıl ayrışıyor / ayrışmalı" 3-4 paragraf yazılır.

**Gereksinimler:**
- 7-kontrol başlıkları: Literatür, Halüsinasyon, Fayda-Maliyet, Daha kolayı, Son kullanıcı, Rakip, Lokal/global
- Her başlık altında somut UI/UX karar (renk, tipografi, animasyon, navigasyon, komponent seçimi, micro-interaction) — soyut "daha güzel olmalı" yasak
- En az 1 yerde **B42-050 metaforuna referans** (kütüphane / akşam / defter / pusula / danışman amber sembolü)
- En az 1 yerde **akademik kullanıcı kazancı** (öğrenci/araştırmacı/profesör için somut iş çıkış)
- En az 1 yerde **rakip eleştirisi** (Connected Papers soğuk-grafik / Litmaps dramatik-cluttered / Elicit ruhsuz-form / SciSpace jenerik-SaaS)

**Değerlendirme:**
- ✅ Sycophancy yok ("PaperMind harika" yerine "PaperMind X riskini yönetiyor ama Y'de zayıf")
- ✅ Akademik isabet (alan/konu/yayın/atıf doğru terminoloji)
- ✅ Kütüphane metaforuyla rakip kategorisinden ayrışım net
- ✅ Yazım kalitesi (Türkçe akademik dil, jargon olmadan)

---

## 4. Tatbikat: Canlı bir Council §-toplantısı

Görev A + B + C tamamlandıysa, gerçek bir Council toplantısına aday gözlemci olarak alınır. Konu: o günkü Frontend mini-plan kararı (örn. F4 Council 26: SSE chat scroll davranışı). Aday önce dinler (15 dk), sonra **Frontend Lead sandalyesinden** GREEN/YELLOW/RED + 1 cümle gerekçe verir. Bu reaction Sercan + Omer ile karşılaştırılır — yapısal uyum ölçülür (sycophancy davranışı, alan-spesifik teknik gerekçe verme yeteneği).

---

## 5. İlan / duyuru taslağı (LinkedIn / Twitter / Discord)

```
PaperMind v4 — akademik literatür keşif platformu — Frontend Lead arayışı.

Stack: Next.js 16 + Tailwind v4 + shadcn/ui (FULL custom) + Tiptap + Framer Motion +
       Recharts + TanStack Query + Zustand. TypeScript strict. WCAG AA.

Görev: 5 tezgâh × 25 alt-sayfa, Notion-benzeri Defter, perde-reveal simülasyon odası,
       "Akademik Defter & Akşam Kütüphanesi" tasarım yönü.

Aranan: design engineer hassasiyeti + akademik UX duyarlılığı (Tiptap/block editor
        deneyimi tercih). Türkçe akademik kullanıcı düşünebilen.

Süreç: 3 küçük canlı görev (~3.5 saat toplam) → Council gözlemci tatbikatı → karar.

Konum: Hibrit (TR), uzaktan da olabilir. Bütçe pozisyona göre.

Detay + başvuru: <e-posta veya form bağlantısı>
```

---

## 6. Açık iş listesi

- [ ] Omer aday öncelik sıralamasını onaylar (#3 → #2 → #1 önerisi mi, başka mı?)
- [ ] Aday adresleri toplanır (Sercan ağı + Omer GAÜ ağı + Twitter/Discord duyurusu)
- [ ] Görev A + B + C için boş Next.js 16 starter repo hazırlanır (Sercan veya Omer)
- [ ] Mock paper verisi JSON Görev B için hazırlanır (PaperCard 4 varyant)
- [ ] Connected Papers / Litmaps / Elicit / SciSpace screenshot paketi Görev C için hazırlanır
