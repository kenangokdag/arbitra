# F4-S4 — Danışman ChatboxPanel global surface (D16 canonical)

> **Durum:** ✅ KAPANDI 2026-05-01 — 7 atomic commit + 1 docs commit (8 total, B-023)
> **Son güncelleme:** 2026-05-01 (closure)
> **Önkoşul:** F4-S2 (Chat-First Hybrid Arama) + F4-S3 (Hızlı Tarama) sıraya alındı; **F4-S4 main branch üstünden Omer onayıyla erken yapıldı** (B-019 tek-branch kararı F4-S2/S3 plan onayları geldiğinde uygulanır).
> **Branch:** `feat/F4-frontend-shell` üstüne devam (F4 boyunca tek branch — B-019 kararı)
> **Sprint LOC tahmini:** ~480–560
> **Sprint süre tahmini:** 1.5–2 gün
> **Mockup canon:** `~/Downloads/D16-Chatbox.html` (635 satır, 3 state demo + dark variant)

---

## §0 — Önkoşullar + mevcut state

**Kapanmış (kanıt):**
- F4-S1 (B-019) 7 commit + F4-S1.5 (B-020) 4 wrap + 1 fix commit lokal `feat/F4-frontend-shell`
- F4-S2 P058+P058.1 KAPANDI (`e0b25ae` + `5081a08`) — SearchPending 3D carousel
- D16-Chatbox.html canonical mockup hazır (Omer 2026-05-01 talimatı: "amber olmasın, açık renk şık profesyonel" → D16 bu vizyonun direkt uygulaması)

**Mevcut çalışma alanı:**
- `app/(app)/chat/page.tsx` (128 LOC) — full-page chat, TanStack Query + apiFetch + 501 fallback + 3-dot pending; mevcut ama **panel'e refactor edilecek** (shared `<ChatThread>` çıkarılacak)
- F4-S2 plan'ında **`ChatBubble.tsx` + `ChatInput.tsx`** ayrı sprint bileşenleri (search refinement için) — F4-S4 bu prim itifleri **reuse eder**, paralel ikinci yazım yok
- Zustand 5 paket dependency'de mevcut (`web/package.json:36`), 0 kullanım — F4-S2 P059 `useSearchStore` ilk store; F4-S4 ikinci store (`useUiStore`) aynı pattern ile
- `globals.css`'te `.advisor-banner` + `.advisor-pulse` keyframes mevcut (B42-051 zone sistemi); ChatboxPanel **bu pulse'u kullanmaz** (D16 mockup'ta amber pulse YOK, status dot emerald-400)
- `lib/zone.ts` `ADVISOR_AMBER` export edilmiş (`#E8A157`); ChatboxPanel **bunu da kullanmaz** (Q1 cevap: amber yok)
- `PaperCard.tsx:252` "Danismana sor" linki `/chat?paper={id}&advisor=true` → F4-S4'te **panel açılışı** ile değiştirilecek (paper context ile panel açılır)

**Engelleyici dependency'ler:**
- `/api/chat` backend 501 NotImplementedError döndürür (B-018 P020 SSE Cosmos KD-18 ertelendi); F4-S4 fixture-driven gelişir, F3 P020 SSE concrete olunca swap noktası tek dosya (`lib/chat-fixture.ts`)
- F4-S2 P060 (`ChatBubble.tsx` + `ChatInput.tsx`) henüz yazılmadı; **F4-S4 ancak F4-S2 P060 tamamlandıktan sonra başlar** (sıralı bağımlılık)

---

## §1 — Hedef

F4-S4 = **Danışman global yan-panel surface** — her sayfanın üstünde slide-in floating chatbox; D16 mockup canon.

1. **Chat token grubu** (`globals.css` ek) — D16 `--chat-bg`/`--chat-surface`/`--chat-border`/`--chat-adviser`/`--chat-user-bg`/`--chat-header` token sözlüğü; light + dark variant; raw hex YASAK
2. **`useUiStore` Zustand store** — namespace `ui.chatbox.{open, context, thread}`; ileride global UI state için (drawer/dialog/toast) genişletilebilir altyapı
3. **`<ChatThread>` shared sub-component** — mesaj listesi + typing + suggestions + input; mevcut `/chat` page **ve** ChatboxPanel ortak kullanır (DRY, Council 34 #3)
4. **`<ChatboxPanel>` floating shell** — 370×620 fixed bottom-right + slideIn 280ms + ESC/click-outside kapanma + portal mount + `prefers-reduced-motion` fade fallback + mobile <414px full-width override
5. **Pen icon** (`lib/icons/pen.tsx`) — D16 inline `<symbol id="pen">` JSX karşılığı
6. **3 state**: empty (greeting + 3 starter) / conversation (ctx-card + msgs + suggestions) / dark (data-theme yerine `chatbox.dark` class — MVP TR-only, dark mode KD-22 post-MVP ama panel kendi içinde **token-gated dark** destekler)
7. **Trigger wiring** — Topbar'da "Danışmana sor" ikon-button (Pen icon) panel açar; PaperCard "Danismana sor" linki `paper_context` ile panel açar (sayfa değişmez)
8. **`/chat` full-page refactor** — `ChatPage` → `<ChatThread>` reuse + PageHeader korur; mobile fallback olarak çalışmaya devam eder

**Out-of-scope (Faz 2 / KD):**
- Zone-spesifik 5×3 starter sorular (mockup 3 generic yeterli; pilot feedback sonrası genişler — KD-29 yeni)
- Multi-thread / thread history / persisted conversation (P020 SSE backend hazır olunca F5'te) — KD-30 yeni
- Voice input + dictation — Faz 2
- Markdown render bubble içeriğinde (kod/listele/tablo) — F5'te `react-markdown` + Shiki entegrasyonu
- Backend SSE streaming — F3 P020 concrete olduğunda swap

---

## §2 — Scope

### 2.1 Chat token grubu (`web/src/styles/globals.css` ek)

D16 satır 9-31 birebir miras. `@theme` bloğunun **dışına**, `:root` bloğunun **altına** ayrı `:root` ek bloğu olarak; `.dark` veya `.chatbox-dark` selector'a karşılık dark variant.

```css
/* Chat surface — D16 canonical (warm-neutral editorial; amber YOK).
   Danışman global tek kimlik (zone bağımsız). Kaynak: D16-Chatbox.html. */
:root {
  --chat-bg:       #F7F7F5;   /* warm off-white panel bg */
  --chat-surface:  #FFFFFF;   /* input + suggestion + starter card bg */
  --chat-border:   #E4E4E0;   /* panel border + bubble border */
  --chat-adviser:  #EFEFED;   /* Danışman bubble bg (stone-100 toned) */
  --chat-user-bg:  var(--color-ink);    /* kullanıcı bubble = ink (zaten #0f172a) */
  --chat-header:   var(--color-ink);    /* header bg = ink siyah */
  --chat-status:   #4ade80;   /* aktif dot emerald-400 */
}

/* Dark variant — D16 satır 350-417 */
.chatbox-dark {
  --chat-bg:       #1C1C1E;
  --chat-surface:  rgba(255,255,255,0.06);
  --chat-border:   rgba(255,255,255,0.08);
  --chat-adviser:  rgba(255,255,255,0.06);
  --chat-user-bg:  rgba(255,255,255,0.10);
  --chat-header:   #1C1C1E;
  --chat-status:   #4ade80;
}

@keyframes chatbox-slide-in {
  from { transform: translateX(20px); opacity: 0; }
  to   { transform: translateX(0);    opacity: 1; }
}

@keyframes chatbox-typing-dot {
  0%, 80%, 100% { opacity: 0.25; transform: scale(0.8); }
  40%           { opacity: 0.85; transform: scale(1); }
}

@media (prefers-reduced-motion: reduce) {
  /* slide-in → sadece fade; typing dots → statik 50% opacity */
}
```

**Kanıt:** her token D16'daki line referansı `// kaynak: D16-Chatbox.html L<n>` kod yorumunda (HK-2).

### 2.2 `useUiStore` (`web/src/stores/ui.ts`)

```typescript
type ChatboxContext = { kind: "page"; pageId: string; label: string }
                    | { kind: "paper"; paperId: string; title: string }
                    | null;

type UiState = {
  chatbox: {
    open: boolean;
    context: ChatboxContext;   // hangi sayfa/paper açtı
    thread: ChatMessage[];     // mesaj geçmişi (in-memory MVP)
  };
};

type UiActions = {
  openChatbox: (ctx?: ChatboxContext) => void;
  closeChatbox: () => void;
  appendMessage: (msg: ChatMessage) => void;
  resetThread: () => void;
};
```

- Persistence YOK (MVP) — refresh'te thread sıfırlanır; KD-30 (Faz 2 persisted conversation)
- F4-S2 `useSearchStore` pattern'i ile uyumlu (eşit naming + selector hook)
- `web/src/stores/ui.ts` dosyası — search store ile aynı klasör

### 2.3 Pen icon (`web/src/components/icons/pen.tsx`)

D16 satır 423-430 inline SVG'nin React karşılığı:

```tsx
export function PenIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M14 2L7 13l4 4 11-7-8-8z"/>
      <path d="M7 13l-4 8 8-4"/>
      <line x1="11" y1="17" x2="7" y2="13"/>
    </svg>
  );
}
```

- `web/src/components/icons/pen.tsx` (yeni `icons/` klasör)
- Lucide `PenLine` yerine D16 birebir geometri (mockup canon)

### 2.4 `<ChatThread>` shared sub-component

- `web/src/components/chat/ChatThread.tsx`
- Props: `{ messages, onSend, isPending, suggestions?, contextCard?, emptyState? }`
- Slot composition: header **dışında** her şey burada (header'ı parent verir — ChatboxPanel mini header, /chat page PageHeader)
- D16 satır 152-252 (msgs + typing + suggestions) tam karşılığı
- Bubble adviser: `font-serif italic` Lora 14px + `--chat-adviser` bg + `border-bottom-left-radius: 3px`
- Bubble user: `font-sans` Inter 13.5px + `--chat-user-bg` bg + `border-bottom-right-radius: 3px`
- Date separator (`Bugün`, `Dün`, ISO date)
- Scroll-to-bottom on new message + typing
- Message avatar: adviser PenIcon + 24px circle bg-soft border-rule-soft; user Lora italic initial (kullanıcı adı yoksa "S" placeholder, F5'te auth bağlanınca name initial)

### 2.5 `<ChatboxPanel>` floating shell

- `web/src/components/ChatboxPanel.tsx`
- `"use client"` direktifi
- Portal: `createPortal(<panel/>, document.body)` — z-index hiyerarşi temiz
- Position: `fixed bottom-6 right-6` (mockup floating, sağ alt yaygın); mobile <640px → `fixed inset-x-0 bottom-0 top-16` full-width override
- Boyut: `w-[370px] h-[620px]` light + `max-h-[calc(100vh-3rem)]` overflow guard; mobile full-width
- `border-radius: 16px` + 3-katman shadow (D16 line 64-67 birebir, slate-900 RGB)
- Animasyon: `chatbox-slide-in 280ms cubic-bezier(.16,1,.3,1) both`
- Kapanma: ESC keydown + scrim YOK (D16: scrim yok, dış tıklamayla kapanma yok — kullanıcı close butonuyla kapatır; **MVP karar**)
- Focus trap: panel açılınca textarea `autoFocus`; `react-aria` veya `@base-ui/react` minimal — manual focus-trap ileride (F5/KD-31)
- 3 state render:
  - `thread.length === 0` → empty (D16 line 433-478)
  - `thread.length > 0` → conversation (D16 line 481-565)
  - `dark` toggle prop (default false; F5 system theme bağlanınca `prefers-color-scheme` veya `useTheme()`)
- Header: ink bg + PenIcon avatar (white-translucent ring) + "Danışman" Lora italic 14.5px + status dot + context badge (JetBrains Mono 9.5px white-translucent pill, `useUiStore.context.label` from)
- Context card (D16 line 137-150): conversation state'te header altında, ink-pale bg + ink-mute icon + "Şu an **{context.label}** sayfasındasın." mesajı
- Input footer: textarea auto-resize (38px → 96px max) + send button ink bg `opacity:0.85 hover` (D16 birebir, amber yok)

### 2.6 Trigger button (Topbar refactor)

- Mevcut `Topbar.tsx` (63 LOC) — Cmd+K ikon + nav-config; **Pen ikon eklenir** (sağda, Cmd+K solda)
- Click → `openChatbox({ kind: "page", pageId, label: pageLabel })` (sayfa context'i otomatik)
- `usePathname()` + `nav-config.ts` mapping → context label çıkar
- `aria-label="Danışmana sor"` + `data-state="open|closed"`
- Keyboard shortcut: `Cmd+J` / `Ctrl+J` (Cmd+K çakışmaz)

### 2.7 PaperCard "Danismana sor" rewiring

- `PaperCard.tsx:252` mevcut `<Link href="/chat?paper={id}&advisor=true">` → `<button onClick={() => openChatbox({ kind: "paper", paperId, title })}>` (sayfa değişmez, panel açılır)
- Eski `/chat?paper=` query param desteği `/chat` full-page'de **kalır** (deep link mobile fallback için), ama `PaperCard` artık sayfa değiştirmez

### 2.8 `/chat` full-page refactor

- `app/(app)/chat/page.tsx` (128 LOC) → `<ChatThread>` reuse + PageHeader + container layout
- Aynı mutation hook + state; sadece UI body `<ChatThread>` componentine devredilir
- Mobile fallback: panel <640px'te full-width açılırken, `/chat` URL'si direct erişim için kalır
- LOC: 128 → ~75 (sub-component'e yardımcılarla)

### 2.9 Backend wiring (501 fixture)

- `web/src/lib/chat-fixture.ts` — D16'daki örnek diyalog (3 mesaj çifti) JSON'a çevrilmiş; `apiFetchOrFixture('/api/chat', ...)` 501 → fixture chunk return + 600ms artificial delay (typing UX)
- TODO marker: `// TODO(P020): swap to SSE streaming when F3 chat endpoint concrete`
- HK-3 dış servis empirik: gerçek `/api/chat` 501 yanıt smoke test fixture'ı `tests/fixtures/chat_501.json` (zaten F4-S1 paterninde benzer mevcut)

---

## §3 — Atomic commit boundary (R7 + R13.3 + R13.12)

**Plan: 7 atomic commit + 1 doc commit (8 total) — R13.12 commit hash kanıt zorunlu**

| # | P-no | Slice | LOC | Dosya | Hash |
|---|---|---|---|---|---|
| 1 | P073 | Chat token grubu globals.css ek + keyframes + reduced-motion | ~50 | `styles/globals.css` | `78dd164` (idempotent — branduyum commit'inde zaten mevcut) |
| 2 | P074 | Pen icon component + unit test | ~25 | `components/icons/pen.tsx` + test | `74bab55` |
| 3 | P075 | `useUiStore` Zustand store + types + selector hooks | ~70 | `stores/ui.ts` + test | `2b59ad4` |
| 4 | P076 | `<ChatThread>` shared sub-component (mesaj/typing/suggestions/avatar) | ~140 | `components/chat/ChatThread.tsx` + test | `6a4f7ab` |
| 5 | P077 | `<ChatboxPanel>` floating shell (header/ctx-card/3-state/portal/animations) | ~180 | `components/ChatboxPanel.tsx` + test | `81699d2` |
| 6 | P078 | Topbar "Danışmana sor" trigger + Cmd+J shortcut + AppShell mount (lib/keybindings.ts dropped — tek shortcut için ayrı dosya overkill, Topbar inlined) | ~40 | `Topbar.tsx` + `AppShell.tsx` | `9da69fe` |
| 7 | P079 | PaperCard rewiring + `/chat` page refactor (`<ChatThread>` reuse) + chat-fixture | ~70 | `PaperCard.tsx` + `app/(app)/chat/page.tsx` + `lib/chat-fixture.ts` + `ChatboxPanel.tsx` (fixture wiring) | `4935950` |
| 8 | docs | F4-S4 closure + B-023 entry + Council 35 + KD-29/30/31 + STATE/NEXT_ACTION | — | `docs/*` | (bu commit) |

**Toplam: ~575 LOC + docs**

---

## §4 — Halüsinasyon Kod-Seviyesi (HK-1..HK-7)

- **HK-1** Pydantic schema gate: `ChatRequest`/`ChatChunk` zaten F4-S1 `lib/types.ts`'de mevcut (Pydantic mirror); F4-S4 sadece UI, schema değişmez
- **HK-2** Sayı/eşik kaynağı kod yorumunda: tüm chat token'ları `// kaynak: D16-Chatbox.html L<n>` referansı; bubble border-radius 3px, panel 370×620, slide 280ms — hepsi D16 line referanslı
- **HK-3** Dış servis empirik kanıt: `/api/chat` 501 fixture smoke test mevcut F4-S1 paterninde; F3 P020 SSE concrete olunca yeni snapshot fixture
- **HK-4** Runtime assertion: `useUiStore` invariant `assert(thread.every(m => m.role === "user" || m.role === "assistant"))` her appendMessage'da
- **HK-5** Manifest verify: D16-Chatbox.html disk üzerinde sabitlenir (mockup `~/Desktop/papermind-mockup-D16-frozen/` altına kopyala — Omer kararı, F4-S4 başında)
- **HK-6** Type-strict no-Any-leak: `ChatboxContext` discriminated union zod schema; `useUiStore` `Any` yok
- **HK-7** Reproducibility seed: chat-fixture artificial delay 600ms sabit (test'lerde mock); typing dot animation deterministic delay (.18s/.36s D16 satır 247-248)

---

## §5 — §Council 35 — F4-S4 plan onayı (R13)

**Alan:** Frontend (a11y + state + portal + zone bağımsızlık)
**Alan sahibi (BAĞLAYICI):** Defne Yıldız (Frontend Lead)
**D16 mockup ışığında revize sonrası oylar — Council 34 ön-değerlendirmesinin uzantısı:**

| # | Üye | Oy | Gerekçe (1 cümle) | İstediği (RED/YELLOW ise) |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟢 | Tüm chat-* token'lar D16 line referanslı; raw hex sadece D16 mockup'tan miras (`#F7F7F5`/`#FFFFFF`/`#E4E4E0`/`#EFEFED`/`#4ade80`/`#1C1C1E`) — mockup canonical kanıt; user-bg + header `var(--color-ink)` reuse | — |
| 2 | Akademik İsabet | 🟢 | Danışman global yan-panel rakip ayrışım (Elicit/SciSpace/Consensus modal-only, sürekli yan-panel yok); akademisyen multi-task UX (sayfada kalır, sohbet eder) | — |
| 3 | Fayda-Maliyet | 🟢 | ~575 LOC 1.5-2 gün; F4-S2 P060 `ChatBubble`/`ChatInput` reuse net negatif çift-yazım; `/chat` full-page refactor LOC azaltır (128 → 75) | — |
| 4 | Daha İyisi Var Mı? | 🟢 | Floating panel + portal + manual ESC = ~180 LOC; @base-ui Dialog "side: right" full-screen drawer pattern, D16 floating tasarımına **uymaz** (drawer != floating window); manual yaklaşım doğru | — |
| 5 | Global Çözüm | 🟡 | Mobile <414px full-width override + ESC kapanma + reduced-motion fade fallback plan §2.5'te yazılı; **hâlâ eksik**: focus-trap (textarea açılışta autoFocus minimal, gerçek focus-trap KD-31 post-MVP); i18n: tüm string'ler hard-coded TR (next-intl placeholder F5'e ertelenir, KD-22 paralel) | KD-31 focus-trap + i18n placeholder kabul edildiğine dair §6 DOD'a açıkça yazılsın |
| 6 | Son Kullanıcı Avukatı | 🟢 | D16 3 generic starter ("Bu konuyu nasıl daraltırım?" / "Hangi yöntemi kullanmalıyım?" / "Bu makaleyi neden dahil etmeliyim?") akademisyen için somut; Pen icon + Lora italic Danışman kimliği marka kararı | — |
| **A** | **Defne Yıldız (Frontend Lead, BAĞLAYINI)** | 🟢 | D16 warm-neutral editorial palet "scholarly-modern + minimal-professional" Defne ekol uyumlu; floating panel + ink siyah header Stripe/Linear/Anthropic 2025 pattern; `<ChatThread>` shared sub-component DRY canon; portal + slideIn 280ms cubic-bezier ease-out-expo token-uyumlu | empirik kanıt: P077 sonrası dev server `/` → Topbar Pen icon click → panel sağ alt floating render → 3 state empirik (empty + conversation + reduced-motion fade); `/chat` page mobile fallback render |

**Sonuç:** 6 GREEN + 1 YELLOW + Defne BAĞLAYICI GREEN → R13.5 kuralı: **İLERLE**
**Bypass kayıt (Global Çözüm YELLOW):** focus-trap + i18n KD-31'e ertelendi, MVP scope dışı; DOD §6'da explicit kabul.
**Sercan (Backend Lead, alan dışı yorum):** `/api/chat` 501 fixture kalıcı değil; F3 P020 SSE Cosmos KD-18 kapanınca `lib/chat-fixture.ts` swap edilir (TODO marker gözle takip edilebilir); zod `ChatRequest` schema F4-S1'den miras, drift yok.

---

## §6 — Done-of-Definition (DOD)

**P073 — Chat token grubu:**
- [ ] `globals.css` `:root` ek bloğu 7 token + `.chatbox-dark` 7 token + 2 keyframe
- [ ] `prefers-reduced-motion` slide-in → opacity-only fade
- [ ] D16 line referansı her token yorumunda
- [ ] Build PASS (Tailwind v4 token consume eder)

**P074 — Pen icon:**
- [ ] D16 satır 423-430 birebir SVG geometri
- [ ] `width`/`height`/`color` props inherit
- [ ] Snapshot test render

**P075 — `useUiStore`:**
- [ ] `chatbox.{open, context, thread}` 3 alan
- [ ] 4 action: openChatbox / closeChatbox / appendMessage / resetThread
- [ ] `ChatboxContext` discriminated union (page | paper | null)
- [ ] Selector hook 4 adet
- [ ] Unit test: open/close + context set + thread append + invariant

**P076 — `<ChatThread>`:**
- [ ] Mesaj rendering: adviser (Lora italic + chat-adviser bg + tail-bottom-left) + user (Inter + chat-user-bg + tail-bottom-right)
- [ ] Typing indicator 3-dot animasyon (D16 keyframe)
- [ ] Suggestion chips (D16 line 254-269 birebir)
- [ ] Date separator
- [ ] Scroll-to-bottom on new message
- [ ] Avatar slot (PenIcon adviser + initial user)
- [ ] Unit test: 3 mesaj render + typing render + chip click → callback

**P077 — `<ChatboxPanel>`:**
- [ ] Portal mount + `fixed bottom-6 right-6`
- [ ] 370×620 light + mobile <640px full-width override
- [ ] 16px radius + 3-katman shadow
- [ ] Slide-in 280ms cubic-bezier (reduced-motion fade fallback)
- [ ] Header: ink bg + Pen avatar + Lora italic name + status dot + context badge + close button
- [ ] Empty state: PenIcon ring + greeting + 3 starter (D16 line 448-468)
- [ ] Conversation state: ctx-card + ChatThread + suggestions
- [ ] ESC keydown → closeChatbox
- [ ] textarea autoFocus on open
- [ ] axe-core PASS (role="dialog", aria-labelledby, aria-modal=false — non-modal floating)
- [ ] **Defne BAĞLAYICI empirik:** dev server'da Topbar Pen click → panel render + 3 state cycle + reduced-motion media query toggle ekran kaydı

**P078 — Topbar trigger:**
- [ ] Pen ikon-button (32px, ink hover, Cmd+J shortcut)
- [ ] `usePathname()` → context label auto-detect
- [ ] `aria-label="Danışmana sor (Cmd+J)"`
- [ ] Cmd+K (P049) çakışma yok empirik kontrol

**P079 — Rewiring + chat-fixture:**
- [ ] PaperCard "Danismana sor" → `openChatbox({ kind: "paper", ... })`
- [ ] `/chat` page → `<ChatThread>` reuse + PageHeader korur
- [ ] `lib/chat-fixture.ts` D16 örnek diyalog
- [ ] `/chat?paper={id}&advisor=true` deep link mobile fallback çalışır
- [ ] Build + lint + typecheck + test all PASS

**§Council 35 closure (sprint sonu):**
- [ ] Defne BAĞLAYICI GREEN (3 state empirik + Topbar trigger + /chat refactor + Pen icon)
- [ ] Halüsinasyon Avcısı GREEN (8 commit `git log --oneline` doğrulandı, B-023 entry'sinde tam hash listesi R13.12)
- [ ] Diğer 5 rol GREEN
- [ ] Sercan alan-dışı GREEN (zod schema drift sıfır + chat-fixture swap noktası tek dosya marker)
- [ ] Sonuç: 7 GREEN → İLERLE F4-S5 (Profil + Home polish + a11y/mobile pass) veya F5 sprint başlangıcı

**Açık iş listesi (KD korumalı):**
- KD-29 Zone-spesifik 5×3 starter sorular (pilot feedback sonrası genişletme; mockup 3 generic MVP yeterli)
- KD-30 Multi-thread + persisted conversation (F3 P020 SSE concrete + Postgres `chat_threads` tablo migration F5'te)
- KD-31 Focus-trap (gerçek `react-aria` veya `@base-ui` focus-trap entegrasyonu — MVP textarea autoFocus yeterli)
- KD-32 Markdown render bubble (kod block + listele + tablo, F5 `react-markdown` + Shiki)

---

## §7 — Bağlantılar

- **Mockup canon:** `~/Downloads/D16-Chatbox.html` (635 satır) — F4-S4 başında `~/Desktop/papermind-mockup-D16-frozen/D16-Chatbox.html` altına dondurulacak (HK-5)
- **STATE.md** — F4-S4 başlangıçta mini-update + KD-29..32 ekleme
- **DECISIONS.md** — bu plan kapanışında **B-023** entry (F4-S4 KAPANDI + 8 atomic commit hash + Council 35 closure + chat token grubu canon + KD-29..32)
- **F4-S2 plan** (`F4_S2_arama_top5.md`) — P060 `ChatBubble` + `ChatInput` primitif yazımı (F4-S4 onları **reuse**, ikinci yazım yok)
- **F4-S3 plan** (`F4_S3_hizli_tarama.md`) — F4-S4'ten önce kapanır (sprint kuyruğu sırası)
- **DM_RULES R13.9** — Defne BAĞLAYICI sandalye + Sercan alan-dışı yorum
- **DM_RULES R13.12** — commit hash kanıt zorunluluğu uygulanır
- **`docs/frontend/COMPONENT_RULES.md`** — 8-anatomi 7-checklist (Chatbox için: typography Inter+Lora ✓, palet chat-* token-only ✓, radius 16px panel + 11px bubble custom override ✓, shadow 3-katman D16 birebir ✓, spacing D16 12/14/9/13 px scale ✓, transition 280ms cubic-bezier ✓, mikro-imza Pen icon + Lora italic Danışman ✓, component override @base-ui Dialog reddedildi manual portal ✓)
- **`docs/frontend/REFERENCES.md`** — §5.2 dark overlay surface KD-26 yan-panel paternine uygun (Council 35 doğruladı)
