# F4-S2 — Chat-First Hybrid Arama + Karar Hafızası + Akıllı Butonlar + Top-5 modal + 10 atom shadcn

> **Durum:** TASLAK — Council 36 onayı bekliyor
> **Son güncelleme:** 2026-05-01 (B-021 Chat-First Pivot + B-022 ESTRA Validator onayı sonrası revize)
> **Önkoşul:** F4-S1 KAPANDI (B-019, 7 commit) + F4-S1.5 KAPANDI (B-020, 4 wrap commit lokal)
> **Branch:** `feat/F4-frontend-shell` üstüne devam (yeni branch açılmaz; F4 boyunca tek branch B-019 kararı)
> **Sprint LOC tahmini:** ~1200-1400
> **Sprint süre tahmini:** 4-5 gün (DM-002r: 5-6 hafta MVP bütçesine uyumlu)

---

## §0 — Önkoşullar + mevcut state

**Kapanmış (kanıt commit hash'leri):**
- F4-S1 (B-019): `add846b` plan revize → `a073b8f` P037 tooling → `22b86f4` P038 layout+tokens → `71b2877` P039+P040 sidebar+topbar+appshell → `a86c61b` P041 8 ekran route stub → `40b16c1` P042+P043 api+types+fixtures → `772977b` P044 Suspense → `8a45af3` handoff
- F4-S1.5 (B-020): `7a92de0` feat(tooling) wrap-1 + `94931f0` feat(design) wrap-2 + `bf87659` feat(components) wrap-3 + `106545e` docs wrap-4 + `ea7b2a0` hash injection fix

**Mevcut çalışma alanı:**
- 9 ekran route stub mevcut (statik); `/search` şu an sadece search input + 5 select filter + 2 fixture PaperCard render
- `apiFetchOrFixture` 501 fallback wiring hazır; `web/src/lib/api.ts` + `auth.ts` + `types.ts`
- `web/src/components/PaperCard.tsx` 6-action prototip + P057 hover lift + decision_band stripe
- shadcn init resmileşti + 8-anatomi token altyapısı + cool-academic palet WCAG AAA
- Sadece `@shadcn/button` import edilmiş (mockup v3 8-anatomi override + 11 unit test PASS)

**Engelleyici dependency'ler:**
- **Pinecone B-012 metadata patch** hâlâ koşum sürüyor (Omer Colab) — F4-S2 search wiring fixture+501 fallback ile başlar; gerçek API entegrasyon Pinecone close olunca F2 Day 3-4 ince işçilik ile birlikte
- **Backend B-018 8 commit + 7 pseudocode commit** hâlâ unpushed — F4-S2 fixture-driven gelişir, backend 501 döner
- **F2 P004 mini-benchmark** Qwen2.5/Cosmos/Phi-4 4 aday × 230 örneklem henüz koşulmadı — UI wiring etkilenmez

---

## §1 — Hedef

F4-S2 = **Chat-First Hybrid Arama** (DM-017 pivot) + **Karar Hafızası UI** (DM-019) + **Akıllı Yönlendirme Butonları** (B-022 §8) + **Top-5 modal (E3) shell** + **10 atom community shadcn import** (KD-23):

1. **Chat-First Hybrid Arama** — doğal dil chat input (default) + "Gelişmiş Arama" toggle (keyword modu) + mesaj baloncukları (kullanıcı + sistem) + refinement loop UI (0-2 tur) + URL state sync + 5 broad filter + apiFetchOrFixture + 501→"demo verisi" banner + PaperCard primitif refactor + KD-24 SearchPending 3D carousel
2. **Karar Hafızası UI** — PaperCard üzerinde 4 karar butonu (accept/reject/bookmark/note) + project_decisions fixture + r-ESTRA feedback sinyal (backend wiring F2)
3. **Akıllı Yönlendirme Butonları** — DOI link + Google Scholar arama + Atıf Kopyala (APA/Chicago/Harvard) PaperCard "Daha Fazla" menüsü altında (metadata'dan otomatik üretim)
4. **Top-5 modal shell** — Dialog primitif + Tabs "neden seçildi" stripe + 5-paper PaperCard list + margin filter (OPEN-005 default 0.7); `/api/top5` 501 fallback fixture
5. **10 atom shadcn community import** — sidebar/card/tabs/separator/badge/sheet/skeleton/dialog/sonner + dropdown-menu; her import sonrası 8-anatomi checklist + WCAG verify

**Out-of-scope (Faz 2 post-MVP):**
- KD-27: kütüphaneci chat refinement (multi-turn arama içi chat panel)
- KD-28: gelişmiş arama (konu 12-chip / yöntem 15-chip / q_weak / karar bandı)
- AI ile Tartış prompt + Unpaywall OA + Benzer Makaleler butonları (Post-MVP)
- Proje yapısı UI (sidebar proje listesi + proje CRUD) → F4-S3'e ayrılır
- Karar tipi method_select/topic_narrow/topic_expand/direction_set → Faz 2

---

## §2 — Scope (kapsam)

### 2.1 Chat-First Hybrid Arama (DM-017)

**Chat Input (default mod):**
```
┌─────────────────────────────────────────────────────┐
│  💬 Araştırma amacınızı yazın...                    │
│                                                     │
│  [Gelişmiş Arama ▸]                                 │
└─────────────────────────────────────────────────────┘
```
- Tek satır textarea (auto-expand, max 3 satır)
- Enter → gönder, Shift+Enter → yeni satır
- Placeholder: "MCDM yöntemlerinin eğitimde kullanımını araştırıyorum..."
- "Gelişmiş Arama" toggle → keyword form (mevcut 5 filter + atıf eşiği açılır)

**Mesaj Baloncukları (refinement loop):**
```
Kullanıcı: "MCDM yöntemlerinin eğitimde kullanımını araştırıyorum"
    ↓
Sistem:    "Hangi eğitim kademesini hedefliyorsunuz?"
           [K-12] [Yükseköğretim] [Mesleki] [Hepsini ara]
    ↓
Kullanıcı: "Yükseköğretim"
    ↓
→ Arama başlar (SearchPending → PaperCard listesi)
```
- `web/src/components/ChatBubble.tsx` — kullanıcı (sağ, accent bg) + sistem (sol, muted bg)
- Refinement chip butonları (sistem baloncuğu altında, Badge primitif)
- "Hepsini ara" → refinement skip, direkt arama
- Max 2 tur refinement (3. turda otomatik arama)
- Fixture: `web/src/fixtures/refinement_demo.json` (1 tur soru-cevap örneği)

**Gelişmiş Arama (toggle ile açılır — keyword modu):**
- Mevcut 5 broad filter korunur:
  1. **Yıl** — `Tüm yıllar` / `Son 5 yıl` / `Son 10 yıl` / `Custom range`
  2. **Alan** — `Tüm alanlar` + 5-8 OpenAlex top-level domain; multi-select Badge chips
  3. **Dil** — `Tüm diller` / `TR` / `EN` / `ID`; multi-select
  4. **Açık erişim** — `Hepsi` / `Sadece açık erişim`
  5. **Sıralama** — `İlgililiğe göre` / `Yıla göre` / `Atıf sayısına göre`
- Opsiyonel atıf eşiği: `Tümü` / `50+` / `100+` / `500+`
- Chat modunda filtreler daraltılmış (collapsible) — kullanıcı isterse açar

**URL state sync:**
- `useSearchParams` + Zustand store (`useSearchStore`) — query/mode(chat|advanced)/year/domain/lang/oa/sort/citation_min URL'den hydrate
- Browser back/forward navigation çalışır
- Bookmark + paylaş edilebilir aramalar
- `mode=chat` (default) vs `mode=advanced` URL param

**Backend wiring:**
- `apiFetchOrFixture('/api/search', ...)` POST request
- 501 NotImplemented → Hint banner "demo verisi"
- Pending state → KD-24 SearchPending 3D carousel
- Chat modu: backend'e `{query: "doğal dil", mode: "chat"}` gönderilir → P004 QwenListener intent_classify (F2 Day 3-4 concrete)

**PaperCard primitif refactor:**
- Mevcut PaperCard → shadcn `<Card>` primitif (KD-23 atom #2)
- Chip → shadcn `<Badge>` primitif (KD-23 atom #5) + variant
- Hover lift + decision_band stripe + tracking shift **korunur**

### 2.1b Karar Hafızası UI (DM-019)

PaperCard üzerinde 4 karar butonu (MVP scope — B-022 §7):

```
┌─ PaperCard ──────────────────────────────────────┐
│  [Başlık]                                        │
│  [Abstract 3-line] [Chip] [Chip]                 │
│                                                  │
│  [Detay] [Listeme Ekle] [Özetle] [Sohbet Et]    │
│  ─────────────────────────────────────────────── │
│  Karar: [✓ Kabul] [✗ Reddet] [★ Yer İmi] [📝 Not]│
│         (reason dropdown: "konu dışı"/"eski"/    │
│          "zayıf metodoloji"/"diğer")              │
│  ─────────────────────────────────────────────── │
│  [Daha Fazla ▼]                                  │
│    ├── 🔗 DOI Link                               │
│    ├── 🔗 Google Akademik                        │
│    └── 📋 Atıf Kopyala (APA/Chicago/Harvard)     │
└──────────────────────────────────────────────────┘
```

- Reject tıklanınca reason dropdown (4 seçenek + serbest metin)
- Accept/Bookmark sessiz (reason opsiyonel)
- Note → küçük textarea modal (Dialog primitif)
- Fixture: `web/src/fixtures/decisions_demo.json` (localStorage persist, backend wiring F2)
- Toast (Sonner): "Karar kaydedildi" / "Not eklendi"

### 2.1c Akıllı Yönlendirme Butonları (B-022 §8)

PaperCard "Daha Fazla" dropdown-menu altında (KD-26 atom):

| Buton | Kaynak | Link Üretimi |
|-------|--------|-------------|
| DOI Link | `paper.doi` | `https://doi.org/{doi}` — yeni sekmede açılır |
| Google Akademik | `paper.title + paper.authors[0]` | `https://scholar.google.com/scholar?q="{title}"+{author}` |
| Atıf Kopyala | `paper.*` metadata | APA/Chicago/Harvard formatında clipboard'a — toast onay |

- Tüm linkler PaperCard metadata'sından otomatik üretilir
- DOI yoksa buton disabled + tooltip "DOI bilgisi mevcut değil"
- Atıf Kopyala: 3 format arası toggle (default APA), clipboard API + toast "APA formatında kopyalandı"
- `web/src/lib/citation-format.ts` — APA/Chicago/Harvard formatter (~60 LOC)

### 2.2 Top-5 modal shell

- `<Dialog>` (KD-23 atom #8) + `<Tabs>` (KD-23 atom #3) + `<Separator>` (KD-23 atom #4)
- Tab 1: "5 öneri" — 5-paper PaperCard list + her kart altında "neden seçildi?" 1-line explainer (signals_13 placeholder)
- Tab 2: "Margin (kalibrasyon)" — F3a Curator margin filter slider (OPEN-005 default 0.7); kullanıcı margin değiştirir → 5 yeni öneri (F3a P008 LVR + decision_band threshold yeniden çalışır)
- `/api/top5` 501 fallback fixture (`tests/fixtures/top5_demo.json` üretilecek)

### 2.3 10 atom community shadcn import

**Sıra (her atom için Council 33-mini § + 8-anatomi checklist + token uyum + WCAG verify):**
```
1.  @shadcn/sidebar       — block; mockup v3 sol panel + locked badge composite ile
2.  @shadcn/card          — Card.tsx primitif swap (mevcut 2-katman shadow + Lora italic title korunur)
3.  @shadcn/tabs          — Top-5 modal "neden seçildi" tab + paper detay tabs için reuse
4.  @shadcn/separator     — sidebar grup ayraçları + Top-5 modal tab separator
5.  @shadcn/badge         — chip semantic renkler PaperCard refactor + filter chips
6.  @shadcn/sheet         — mobile drawer placeholder (S5 tam mobile pass'a kadar CSS-only collapse)
7.  @shadcn/skeleton      — loading.tsx 3 placeholder swap + paper detay skeleton (F6'ya hazırlık)
8.  @shadcn/dialog        — Top-5 modal + onboarding adım adım (F5'e hazırlık)
9.  @shadcn/sonner        — toast: 501 banner + Nota ekle / Listeme onay feedback
10. @shadcn/dropdown-menu — KD-26: B reading list more (F6) + C profil avatar (F5); F4-S2'de sadece import + scaffold, dark overlay variant F5'te
```

**8-anatomi override checklist** (her atom için, KD-23 mevcut COMPONENT_RULES.md §1):
- Typography (Inter UI 14.5px + Lora display) ✓
- Palet (token-only, raw renk yasak) ✓
- Radius scale (sm 6 / md 10 / lg 14) ✓
- Shadow stack (2-katman) ✓
- Spacing (4-8-12-16-24-32-48 scale) ✓
- Transition (cubic-bezier(0.16,1,0.3,1) layered 150/200/300ms) ✓
- Mikro-imza (component-spesifik, örn. Card 2-katman shadow + Lora italic title) ✓
- Component override (default vendor look reddi) ✓

### 2.4 KD-24 SearchPending atomic commit (P058)

- `web/src/components/SearchPending.tsx` ~120 LOC
- 6 kart × 60° rotation + 12s linear infinite + decision_band semantic strips (canon emerald/strong blue/frontier amber/risk orange) + FileText Lucide icon + 2-line skeleton + PMID 12-segment stripe brand seal paralel
- ARIA: `role="status"` + `aria-live="polite"` + `aria-label="Sizin için akademik makaleler aranıyor"`
- `prefers-reduced-motion` → statik 3-skeleton fallback (mevcut `loading.tsx` pattern reuse)
- Empirik test: dev server `/search?q=test` → query gönder → pending 1.5-3s SearchPending render → PaperCard list

---

## §3 — Atomic commit boundary (R7 + R13.3 + R13.12)

**Plan: 15 atomic commit + 1 doc commit (16 total) — R13.12 commit hash kanıt zorunlu uygulanır**

**KAPANAN COMMIT'LER (lokal `feat/F4-frontend-shell`):**
- P058 → `e0b25ae` feat(search): SearchPending 3D rotating carousel pending state (2026-05-01)
- P058.1 → `5081a08` fix(search): Tailwind v4 utility generation bug — düz CSS class swap (2026-05-01, R12 recovery)

| # | P-no | Slice | LOC | Dosya | Hash |
|---|---|---|---|---|---|
| 1 | P058 | SearchPending 3D carousel (+P058.1 polish fix) | ~130 | `SearchPending.tsx` + `globals.css` + `search/page.tsx` + test | `e0b25ae` + `5081a08` ✅ |
| 2 | P059 | Zustand search store + URL state sync (mode=chat\|advanced eklendi) | ~90 | `stores/search.ts` + `lib/url-state.ts` | |
| 3 | P060 | ChatInput + ChatBubble component + refinement fixture | ~120 | `components/ChatInput.tsx` + `components/ChatBubble.tsx` + `fixtures/refinement_demo.json` | |
| 4 | P061 | Search filter UI (5 broad filter + atıf eşiği + chat/advanced toggle) | ~150 | `components/SearchFilters.tsx` | |
| 5 | P062 | Search page wiring (chat-first + apiFetchOrFixture + 501 banner + pending) | ~100 | `app/search/page.tsx` (refactor) | |
| 6 | P063 | shadcn @sidebar + @card + @separator import + 8-anatomi override | ~120 | `components/ui/{sidebar,card,separator}.tsx` | |
| 7 | P064 | shadcn @badge + PaperCard primitif refactor (Card+Badge swap) | ~90 | `components/ui/badge.tsx` + `components/PaperCard.tsx` (refactor) | |
| 8 | P065 | shadcn @tabs + @dialog + @sheet import + 8-anatomi override | ~140 | `components/ui/{tabs,dialog,sheet}.tsx` | |
| 9 | P066 | shadcn @skeleton + @sonner import + loading.tsx swap + Toaster mount | ~70 | `components/ui/{skeleton,sonner}.tsx` + `app/{loading,layout}.tsx` | |
| 10 | P067 | shadcn @dropdown-menu + akıllı butonlar scaffold | ~60 | `components/ui/dropdown-menu.tsx` + `components/PaperCardActions.tsx` | |
| 11 | P068 | Karar hafızası UI (4 buton + reason dropdown + localStorage persist) | ~100 | `components/DecisionBar.tsx` + `stores/decisions.ts` + `fixtures/decisions_demo.json` | |
| 12 | P069 | Atıf kopyala (APA/Chicago/Harvard formatter + clipboard + toast) | ~70 | `lib/citation-format.ts` + `components/CitationCopy.tsx` | |
| 13 | P070 | Top-5 modal shell + Dialog+Tabs+Separator wiring + fixture | ~150 | `components/Top5Modal.tsx` + `app/top5/page.tsx` (refactor) + fixture | |
| 14 | P071 | Sonner toast wiring (501 banner + karar onay + atıf kopyala feedback) | ~40 | `lib/toast.ts` + ilgili page integrations | |
| 15 | P072 | Chat-first integration test (chat→refinement→search→result→decision flow) | ~60 | `__tests__/search-flow.test.tsx` | |
| 16 | docs | F4-S2 closure + B-023 entry + Council 36 + KD güncellemeleri | ~ | docs/* | |

**Toplam: ~1360 LOC + docs**

---

## §4 — Halüsinasyon Kod-Seviyesi (HK-1..HK-7)

- **HK-1** Pydantic schema gate: SearchRequest/SearchResponse extra=forbid (mevcut F2 P010, F4-S2 sadece UI)
- **HK-2** Sayı/eşik kaynağı kod yorumunda: 5 filter default değerleri + atıf eşiği threshold'ları (50/100/500) `// TODO(F4-S2-fixture): backend filter param maple — Pinecone B-012 close sonrası gerçek lookup`
- **HK-3** Dış servis empirik kanıt: F4-S2 fixture-driven, backend 501 döner; KD-24 SearchPending pending duration test'i (1.5s artificial delay fixture)
- **HK-4** Runtime assertion: search store URL state sync invariant (`url.params === store.state` her update'te)
- **HK-5** Manifest verify pre-import: shadcn `add` öncesi `npx shadcn@latest docs <comp>` URL fetch + Read; default vendor look detect → 8-anatomi override
- **HK-6** Type-strict no-Any-leak: SearchFilters props zod schema'dan inferred (no `any`)
- **HK-7** Reproducibility seed: SearchPending 6-card position/delay deterministic (seed=42)

---

## §5 — §Council 36 — F4-S2 revize plan onayı (R13)

**Alan:** Frontend
**Alan sahibi (BAĞLAYICI):** Defne Yıldız (Frontend Lead)
**Revize sebebi:** B-021 Chat-First Pivot + B-022 ESTRA Validator + DM-019 Karar Hafızası onaylandı → F4-S2 scope genişledi

| # | Üye | Oy | Gerekçe (1 cümle) | İstediği (RED/YELLOW ise) |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟢 | Chat-first UI fixture-driven (backend QwenListener intent_classify henüz yok, 501 fallback); karar hafızası localStorage persist doğru — backend wiring F2'de; HK-1..HK-7 korunur | — |
| 2 | Akademik İsabet | 🟢 | Chat-first 4/4 rakip pattern'i ile uyumlu; "Gelişmiş Arama" toggle akademisyen keyword alışkanlığını koruyor; karar butonu reject+reason r-ESTRA öğrenme için kritik sinyal | — |
| 3 | Fayda-Maliyet | 🟡 | ~1360 LOC 4-5 gün hedef; scope %30 genişledi (chat UI + karar + akıllı butonlar); **risk**: 5 güne sığmazsa chat integration test (P072) ertelenebilir | P072 integration test sprint sonunda yapılır, gerekirse F4-S3'e kayar |
| 4 | Daha İyisi Var Mı? | 🟢 | ChatBubble + refinement chip UX pattern Elicit/Undermind'da kanıtlanmış; citation-format.ts APA/Chicago/Harvard üç format yeterli (IEEE/Vancouver Post-MVP) | — |
| 5 | Global Çözüm | 🟢 | DecisionBar + citation-format reuse edilebilir (Top-5 + reading-list + paper detay aynı bileşeni kullanır); chat/advanced URL mode param tüm sprint'lerde tutarlı | — |
| 6 | Son Kullanıcı Avukatı | 🟢 | Chat default = düşük giriş bariyeri; reject reason seçenekleri kullanıcı dostu (dropdown, serbest metin zorlamaz); DOI+Scholar+Atıf Kopyala gerçek zaman tasarrufu | — |
| **A** | **Defne Yıldız (Frontend Lead, BAĞLAYICI)** | 🟢 | Chat-first + karar hafızası PaperMind'ı rakiplerden ayıran 2 özellik; UI scope genişlemesi 8-anatomi altyapısı sayesinde manageable; ChatBubble scholarly-modern accent bg + muted bg + Badge refinement chip Defne ekol uyumlu | empirik kanıt: P062 sonrası dev server `/search?mode=chat&q=MCDM+eğitim` → chat bubble render → refinement chip → search → PaperCard + DecisionBar |

**Sonuç:** 1 YELLOW + 6 GREEN → R13.5 kuralı: **İLERLE**
**Bypass kayıt (Fayda-Maliyet YELLOW):** P072 integration test sprint sonuna ertelenebilir, scope daraltma gerektirmez.
**Sercan (Backend Lead, alan dışı yorum):** Chat mode backend'e `{mode: "chat", query: "..."}` gönderir; F2 P004 QwenListener'a intent_classify eklenmeden frontend fixture-driven kalır; project_decisions tablosu migration F4-S3 veya F2 Day 5'te yazılır (şimdi localStorage).

---

## §6 — Done-of-Definition (DOD)

**P058 — SearchPending:**
- [ ] Component dev server `/search?demo=loading` route'unda 12s linear infinite render
- [ ] 6 kart × 60° rotation + decision_band 4 semantic strip görünür
- [ ] ARIA role=status + aria-live=polite axe-core PASS
- [ ] prefers-reduced-motion `chrome://flags` → statik fallback render
- [ ] Unit test: render + ARIA attributes + reduced-motion media query

**P059 — Zustand store + URL state:**
- [ ] `useSearchStore` 8 field (query/mode/year/domain/lang/oa/sort/citation_min)
- [ ] `mode: "chat" | "advanced"` (default "chat")
- [ ] `useUrlSync` hook URL → store hydrate + store → URL replace
- [ ] Browser back/forward navigation HMR-stable
- [ ] Unit test: hydrate + replace + mode toggle

**P060 — ChatInput + ChatBubble:**
- [ ] ChatInput: single-line textarea, Enter gönder, Shift+Enter yeni satır
- [ ] ChatBubble: kullanıcı (sağ, accent bg) + sistem (sol, muted bg)
- [ ] Refinement chip butonları (Badge primitif, max 4 seçenek)
- [ ] Fixture: 1 tur soru-cevap demo
- [ ] Unit test: render + chip click → callback

**P061 — Search filter UI:**
- [ ] 5 broad filter + atıf eşiği + chat/advanced toggle
- [ ] Chat modunda filtreler collapsible (varsayılan kapalı)
- [ ] Unit test: toggle mode + filter interaction

**P062 — Search page wiring:**
- [ ] Chat mode: bubble → refinement → search → PaperCard list
- [ ] Advanced mode: keyword form → filter → search → PaperCard list
- [ ] apiFetchOrFixture + 501 Hint banner + SearchPending
- [ ] Sonuç sayısı live count

**P063-P067 — 10 atom shadcn import:**
- [ ] Her atom için 8-anatomi override commit
- [ ] WCAG kontrast verify
- [ ] Bundle size delta gözlem

**P068 — Karar hafızası UI (DecisionBar):**
- [ ] 4 buton: accept/reject/bookmark/note
- [ ] Reject → reason dropdown (4 seçenek + serbest)
- [ ] Note → mini textarea Dialog
- [ ] localStorage persist (decisions store)
- [ ] Toast onay

**P069 — Atıf kopyala:**
- [ ] APA/Chicago/Harvard formatter
- [ ] Clipboard API + toast "kopyalandı"
- [ ] DOI yoksa buton disabled

**P070 — Top-5 modal:**
- [ ] Dialog + Tabs + Separator primitif wiring
- [ ] 5-paper PaperCard list + DecisionBar reuse
- [ ] Margin slider OPEN-005 default 0.7

**P071 — Sonner toast wiring:**
- [ ] Toaster mount layout.tsx
- [ ] 501 banner + karar onay + atıf kopyala feedback
- [ ] axe-core PASS

**P072 — Integration test:**
- [ ] Chat→refinement→search→result→decision tam akış
- [ ] Advanced mode→filter→search→result tam akış

**§Council 36 closure (sprint sonu):**
- [ ] Defne BAĞLAYICI GREEN (chat-first + karar + akıllı butonlar ekran kaydı + 10 atom 8-anatomi override empirik)
- [ ] Halüsinasyon Avcısı GREEN (16 commit `git log --oneline` doğrulandı, B-023 entry'sinde tam hash listesi R13.12)
- [ ] Diğer 5 rol GREEN
- [ ] Sercan alan-dışı GREEN (zod type drift sıfır + localStorage→backend migration path açık)
- [ ] Sonuç: 7 GREEN → İLERLE F4-S3 (Proje yapısı + Sohbet+Liste) veya F2 Day 3-4 ince işçilik

**Açık iş listesi (KD korumalı):**
- KD-22 Dark mode + chart-* (post-MVP)
- KD-26 Dark overlay dropdown variant — F5 §6.5'te token grubu ekleme
- KD-27 Kütüphaneci chat refinement (Faz 2 pilot validation)
- KD-28 Gelişmiş arama 12-chip/15-chip/q_weak/karar bandı (Faz 2 pilot feedback)

---

## §7 — Bağlantılar

- **STATE.md** — F4-S1.5 KAPANDI ✅ + B-020 + KD-22..28
- **DECISIONS.md** — bu plan kapanışında **B-023** entry (F4-S2 KAPANDI + 16 atomic commit hash + Council 36 closure + KD-27/28 final)
- **`docs/plans/F4_frontend_skeleton_arama.md`** — F4 ana plan, S1 + S1.5 kapanışından sonra S2
- **`~/Desktop/papermind-mockup/index.html`** v3 — design canon `/search` ekranı line 717-892 (5 select filter + sonuç listesi)
- **`docs/plans/F4_S1_5_design_system_polish.md`** — 8-anatomi token altyapısı kaynak
- **`docs/frontend/COMPONENT_RULES.md`** — 8-anatomi 7-checklist + anti-pattern
- **`docs/frontend/REFERENCES.md`** — §5.1 animation curve bankası + §5.2 dark overlay surface (KD-26 için)
- **Master plan §1** — E4 Makale Ara + E3 Top-5 single-turn scope (KD-27 chat refinement Faz 2)
