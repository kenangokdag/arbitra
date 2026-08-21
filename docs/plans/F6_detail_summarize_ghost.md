# F6 — Mini-Plan: E5 Detay + Summarize + Ghost Enrichment

> **Statü**: TASLAK — F1' master plan onayı sonrası (B-001 §16) + Council 16. tur (2026-04-30)
> **Üst plan**: `docs/plans/F1_master_plan.md` + `docs/plans/F4_*` + `F5_*` (E5 Zustand paper-cache F4 P043'te kuruldu)
> **Şablon**: ARCHITECT_PROMPT_TEMPLATE §0..§7 + R13 §Council
> **Owner**: Claude (prototype %80) · Sercan (poll endpoint reliability + KVKK enrichment audit %20) · Omer (OPEN-006 ghost cache TTL onayı)

---

## §0 Bağlam (3 cümle)

E5 "Çalışma Masası — paper detay" + on-demand özet (Celery async) + ghost paper enrichment (OpenAlex polite pool) — kullanıcının arama sonucundan paper'a tıkladığında **tam ürün akışı kapanır**: 13 sinyal + 12 chip rozetleri + NedenPanel engineer-mode + LVR atıf popover + reading list CRUD + ghost "Detay özet" enrichment. Niş ayrım: jenerik paper preview değil — **B42-045 PaperCard M31 13 sinyal** (CD₅ disruption / Sleeping Beauty / d-ESTRA R+E / sentence-role / Q_weak / MQ_Tier1) görünür, "Neden?" tıklarsa engineer-mode açılır, ghost için K1 yıl scrub runtime enforce. Mimari pattern (ARCHITECTURE.md §3 dondurulmuş): `/api/papers/{id}` ayrı endpoint **YOK** — Zustand `paper-cache-store` (F4 P043) search response'tan PaperCard'ı okur, ek özet için `/api/summarize`, ghost detayı için `/api/enrichment` çağrılır.

---

## §1 Karar günlüğü

| Karar | Kaynak | Etki |
|---|---|---|
| **`/api/papers/{id}` endpoint YOK** — Zustand paper-cache (F4 P043) ile client-side cache pattern; search response'taki PaperCard buradan okunur | ARCHITECTURE.md §3 + master §3 5-endpoint scope | E5 sayfa Zustand store reader |
| Cache miss durumu (kullanıcı doğrudan paper URL'ine girerse veya eski sekme): "Önce arama yapın" CTA + redirect /kutuphane (E4) | Edge case — kabul | P053 guard logic |
| E5 13 sinyal görüntü (B42-045 §3 M31): paper.signals_13 obje; her sinyal için micro-card (Lora 14px değer + Geist Sans 12px label) | B42-045 §3 + ARCHITECTURE.md §1 | `web/src/components/SignalGrid.tsx` |
| 12 chip rozet (B42-040 entry: DI/SB/d/Ravg/RS/MQk/Ck/EDk/BC/SR/TSP/RX) — z>1.0 tetiklenenler renkli, diğerleri soluk | B42-040 + master §10 chip_library_spec | `web/src/components/ChipBadgeGrid.tsx` |
| **NedenPanel engineer-mode** — "Neden?" tıklarsa açılır panel: 13 sinyal detay + chip skor + KararBant gerekçesi | ESTRA P1 + master §10 | `web/src/components/NedenPanel.tsx` (Sheet shadcn) |
| **"Detay özet ver" CTA** → POST `/api/summarize` `{paper_id, mode: "detailed"}` (sync 202 + poll); abstract zaten görünür (DM-012 corpus için mevcut abstract direkt) | DM-012 + F3c §2 | `web/src/components/SummarizePanel.tsx` |
| Summarize sync mode (`mode: "abstract"`) **kullanılmaz E5'te** — abstract zaten paper.abstract_excerpt'tan görünür; sadece detailed mode istenir | DM-012 master §3 | only detailed branch |
| Polling pattern: 202 + task_id → `setInterval` 3s → GET `/api/summarize/{task_id}` (status: queued/running/done/failed) → done ise SummaryDoc render | F3c §2 + master §4.3 | `web/src/lib/hooks/useSummarizePolling.ts` |
| **LVR atıf popover** — SummaryDoc.citations_lvr her cümle hover → tooltip (Radix Tooltip) "Bu cümle paper {ref_id} satır {span} ile %{lvr*100} eşleşiyor" | B42-045 K5 + F3c §2 | `web/src/components/CitationHover.tsx` |
| **K1 yıl scrub frontend tarafta** — backend zaten year_verified=false ise year drop yapar; defansif olarak frontend `paper.year_verified === false` ise UI'da yıl render YASAK; "Klasik kaynak (yıl yükleniyor)" placeholder | B42-045 K1 + master §6.1 | PaperCard + GhostCard render guard |
| **Reading list CRUD** — F3e endpoint tüketimi: POST add + DELETE remove + LIST (sol-nav badge); optimistic update (TanStack mutation) | F3e §2 + B42-047 A1 | `web/src/components/ReadingListBadge.tsx` + `Button.tsx` "Listeye ekle" |
| **Ghost paper detayı**: GhostCard'a tıkla → mini-detay paneli (PMID + Q_proxy + indegree); "Detay özet" CTA → POST `/api/enrichment` `{ghost_id}` → polling 30-60s → abstract + DOI + OpenAlex link | DM-005 + F3d §2 | `web/src/components/GhostDetailPanel.tsx` |
| Ghost enrichment cache TTL: **OPEN-006** (master 7d vs DM-006 90d); F6'da default 7d UI varsayar (Sercan backend'te ayar yapar, frontend transparent) | OPEN-006 (Omer F6 öncesi netleşir) | F6 sırasında öğrenmek gerekmez |
| **Okuma önerisi listesi** (HEDEF.md §2 E5): paper detay sağ kolonda "İlgili paperlar" — corpus 50 komşu (PaperCard list) + ghost ek (GhostCard list); kaynak: search response'unun `papers[]` neighborhood + ghost `is_ghost=true` filtre | HEDEF.md §2 + DM-005 | `web/src/components/RelatedPapersList.tsx` |
| K9 enforce: `confidence < 0.5` PMID segment "?" placeholder render | B42-045 K9 + master §6.1 | `PmidSegments.tsx` (F4 P040) extension |
| Gate uyarısı (G1-G7) renderiding: paper.gate_warnings → GateUyari component (F4 P041) | F3a §2 + ESTRA Politikası v1.1 | reuse F4 P041 component |
| **Playwright E2E F6'dan ertelendi → F7 Quality** (Council 16 Fayda-Maliyet) | Council 16 + master §15 F7 | F6'da manuel smoke + RTL component test |

---

## §2 Sayfa sözleşmesi (E5 Detay)

```yaml
route: /[locale]/calisma-masasi/paper/[pmid]
auth: Supabase JWT + RLS
data_source:
  primary: Zustand paper-cache-store (F4 P043) — search response'tan
  fallback_404: "Önce arama yapın" CTA + redirect /[locale]/kutuphane
  on_demand_summarize: POST /api/summarize {paper_id, mode: "detailed"} → poll
  on_demand_enrichment: POST /api/enrichment {ghost_id} → poll (sadece is_ghost=true)
  reading_list: POST/DELETE /api/reading-list

ui_layout:
  header:
    PaperCard detail mode (B42-050 §5 detail-mode 280px+ varyantı)
    PMID 12-segment renkli mono
    title (Lora 22px display)
    authors + venue + year (year_verified=true ise; K1 enforce)
    Birincil "Listeye ekle" buton (B42-050 §4) + "Detay özet ver" buton
  body_2col:
    left_col_8: SignalGrid (13 sinyal) + ChipBadgeGrid (12 chip) + KararBant + GateUyari + NedenPanel "Neden?" link
    right_col_4: RelatedPapersList (corpus 50 + ghost ek) + ReadingListBadge
  bottom_section:
    SummarizePanel: status (queued/running/done/failed) + SummaryDoc render with LVR popover
    GhostDetailPanel (sadece is_ghost=true): enrichment status + abstract

state:
  paper: PaperCard from Zustand (cache hit) | null (cache miss → CTA)
  summary: SummaryDoc | null
  summarizeStatus: "idle"|"queued"|"running"|"done"|"failed"
  enrichment: EnrichmentDoc | null
  readingListMember: boolean

a11y:
  SignalGrid: <ul role="list"> + her micro-card aria-label "ESTRA: CD₅=0.42 (high disruption)"
  NedenPanel: Sheet — focus trap + ESC kapatır
  CitationHover: aria-describedby + 200ms delay show
```

---

## §3 İmplementasyon adımları (atomik P-numara)

| P | İş | Dosya | LOC | Test |
|---|---|---|---|---|
| **P053** | E5 Detay sayfa shell + Zustand paper-cache reader + cache miss CTA | `web/src/app/[locale]/calisma-masasi/paper/[pmid]/page.tsx`, `loading.tsx`, `error.tsx` | ~140 | smoke: cache hit → render; cache miss → CTA + redirect |
| **P054** | SignalGrid (13 sinyal micro-card) + ChipBadgeGrid (12 chip rozet, z>1 vurgu) | `web/src/components/SignalGrid.tsx`, `ChipBadgeGrid.tsx` | ~180 | unit: 13 sinyal render; chip z<1 → muted; z≥1 → renkli |
| **P055** | NedenPanel engineer-mode (Sheet shadcn) — "Neden?" tıklayınca açılır 13 sinyal + chip detay + KararBant gerekçesi | `web/src/components/NedenPanel.tsx` | ~120 | unit: open/close state; ESC kapatır; focus trap |
| **P056** | "Detay özet ver" + useSummarizePolling hook + SummarizePanel + SummaryDoc render | `web/src/components/SummarizePanel.tsx`, `web/src/lib/hooks/useSummarizePolling.ts` | ~180 | unit: polling state machine; mock task done → render |
| **P057** | LVR atıf popover (Radix Tooltip) — SummaryDoc.citations_lvr cümle hover | `web/src/components/CitationHover.tsx` | ~80 | unit: hover → tooltip "lvr=0.85 paper W123 span [40,82]" |
| **P058** | Reading list CRUD — TanStack mutation + optimistic + ReadingListBadge sol-nav | `web/src/components/ReadingListBadge.tsx`, `web/src/lib/hooks/useReadingList.ts` | ~140 | integration: add → optimistic + revalidate; remove → undo toast |
| **P059** | RelatedPapersList — corpus 50 komşu + ghost ek (PaperCard list-mode reuse F4 P040) | `web/src/components/RelatedPapersList.tsx` | ~100 | unit: corpus + ghost filter render; ghost is_ghost=true variant |
| **P060** | GhostDetailPanel + useEnrichmentPolling + abstract render + DOI link | `web/src/components/GhostDetailPanel.tsx`, `web/src/lib/hooks/useEnrichmentPolling.ts` | ~140 | unit: polling 30-60s; abstract render; DOI external link |
| **P061** | E5 i18n string'leri (en + tr + id) — 3 dil | `web/src/i18n/{en,tr,id}.json` (extension) | ~120 (3×40) | smoke: TR detay sayfa "Neden?" "Listeye ekle" "Detay özet ver" |

**Toplam**: 9 atomic commit, ~1200 LOC. Playwright E2E F7'ye ertelendi.

---

## §4 Verification (komut + beklenen output, 8 manuel smoke senaryosu)

```bash
# S1: Build + type
cd ~/Desktop/papermind-app/web && npm run build
# Beklenen: 0 type error; bundle size <350KB initial (E5 ek bundle ~50KB)

# S2: E5 cache hit happy path
# manuel: /en/kutuphane/arama/test → arama yap → PaperCard tıkla → /en/calisma-masasi/paper/W123
# Beklenen: 13 sinyal SignalGrid render; 12 chip ChipBadgeGrid render (3 chip z>1 renkli); KararBant + GateUyari görünür

# S3: NedenPanel engineer-mode
# manuel: "Neden?" tıkla
# Beklenen: Sheet sağdan açılır; 13 sinyal detay + chip skor + KararBant gerekçesi; ESC kapatır; focus trap

# S4: Detay özet ver + polling + LVR popover
# manuel: "Detay özet ver" tıkla
# Beklenen: status "queued" → 3s → "running" (progress 0.4) → 25s → "done" + SummaryDoc render
# Cümle hover → tooltip "lvr=0.85 paper W123 span [40,82]"

# S5: K1 enforce GhostCard
# manuel: arama include_ghost=true → ghost paper detay → /en/calisma-masasi/paper/W_GHOST_xyz
# Beklenen: GhostDetailPanel; PMID render ama YEAR YOK; "Klasik kaynak (yıl yükleniyor)" placeholder; "Detay özet" buton görünür

# S6: Ghost enrichment polling
# manuel: ghost paper "Detay özet" tıkla → POST /api/enrichment
# Beklenen: 202 + task_id → polling 30-60s → done + abstract + DOI + OpenAlex link button

# S7: Reading list CRUD optimistic
# manuel: paper detayda "Listeye ekle" tıkla → instant toast "Eklendi" → ReadingListBadge sol-nav +1
# undo: "Listeyi gör" → DELETE → toast "Çıkarıldı" + badge -1
# Beklenen: optimistic update <50ms; revalidate sonrası kalıcı

# S8: Cache miss redirect
# manuel: tarayıcıyı yeni sekmede /en/calisma-masasi/paper/W999 (cache'de yok)
# Beklenen: "Önce arama yapın" CTA + 3s sonra redirect /en/kutuphane (auto)
```

---

## §5 Critical files

### Frontend touch
- `web/src/app/[locale]/calisma-masasi/paper/[pmid]/page.tsx`, `loading.tsx`, `error.tsx`
- `web/src/components/SignalGrid.tsx` (13 sinyal micro-card)
- `web/src/components/ChipBadgeGrid.tsx` (12 chip rozet)
- `web/src/components/NedenPanel.tsx` (Sheet engineer-mode)
- `web/src/components/SummarizePanel.tsx` + `web/src/lib/hooks/useSummarizePolling.ts`
- `web/src/components/CitationHover.tsx` (Tooltip LVR)
- `web/src/components/ReadingListBadge.tsx` + `web/src/lib/hooks/useReadingList.ts`
- `web/src/components/RelatedPapersList.tsx`
- `web/src/components/GhostDetailPanel.tsx` + `web/src/lib/hooks/useEnrichmentPolling.ts`

### Tests touch
- `tests/web/unit/signal-grid.test.tsx` + `chip-badge-grid.test.tsx`
- `tests/web/unit/use-summarize-polling.test.ts` (state machine 4-state)
- `tests/web/unit/use-enrichment-polling.test.ts`
- `tests/web/integration/detail-page.test.tsx` (RTL: cache hit → 13 sinyal render)
- `tests/web/integration/summarize-flow.test.tsx` (mock 202 + poll → done + LVR hover)
- ~~`tests/web/e2e/detail-summarize-e2e.spec.ts`~~ → **F7'ye ertelendi**

### Read-only (DOKUNMA)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-045-MIMARI-V1.md` (M31 PaperCard 13 sinyal + K1/K5/K9)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-040*` (12 chip + 4 freeze faz)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-050-DESIGN-DIRECTION.md` (§5 PaperCard detail mode)
- `~/Desktop/papermind-app/docs/plans/F1_master_plan.md`
- `~/Desktop/papermind-app/docs/plans/F3c_summarize.md` (POST + GET poll sözleşmesi)
- `~/Desktop/papermind-app/docs/plans/F3d_enrichment.md` (ghost enrichment sözleşmesi)
- `~/Desktop/papermind-app/docs/plans/F3e_reading_list.md` (CRUD sözleşmesi)
- `~/Desktop/papermind-app/docs/plans/F4_frontend_skeleton_arama.md` (PaperCard + Zustand cache)
- `~/Desktop/papermind-app/docs/ARCHITECTURE.md` (§3 paper detail Zustand cache pattern)

---

## §6 TODO(sercan) — production hardening %20

### 6.1 Polling reliability
- [ ] Exponential backoff (3s → 5s → 8s → cap 10s) — backend overload sırasında
- [ ] Polling timeout: detailed summarize >60s → "Beklenen süre aşıldı" CTA + Sentry capture
- [ ] AbortController cleanup component unmount (özet polling, ghost enrichment polling)

### 6.2 KVKK enrichment audit
- [ ] OpenAlex .edu.tr polite pool header doğrulama (Sercan F3d backend)
- [ ] Ghost abstract cache TTL OPEN-006 onayı (frontend transparent ama backend ayar)
- [ ] Sentry breadcrumb: enrichment_id + fetch_duration + cache_hit_pct

### 6.3 Performance
- [ ] SignalGrid + ChipBadgeGrid React.memo + useMemo (13×12 = 25 micro-card)
- [ ] CitationHover lazy-load (Tooltip Radix Portal)
- [ ] RelatedPapersList virtualization (50 corpus + ghost): `react-window` veya Next 16 native streaming

### 6.4 a11y hardening
- [ ] axe-core runtime audit (her merge öncesi)
- [ ] NedenPanel focus trap (Radix native ✓ ama smoke test)
- [ ] Klavye navigation: Tab → "Listeye ekle" → "Detay özet ver" → "Neden?" → SignalGrid

### 6.5 Reading list `…` more menu — KD-26 (Council 38 ileride)
- [ ] `@shadcn/dropdown-menu` primitif (KD-23 10. atom F4-S2'de import edilmiş; F5 §6.5'te dark overlay variant token grubu zaten globals.css'te)
- [ ] Reading list item her satırda `…` (more) ikon button → dropdown açılır
- [ ] Menü maddeleri: "Detay" / "Etiket ekle" / "Notlarımı gör" / "Listeden çıkar"
- [ ] uiverse Vercel-style ilham: inline rename pattern (etiket adı düzenle) + slide-out label state animation + grouped separator (Hızlı / Yönetim / Tehlikeli)
- [ ] "Listeden çıkar" → AlertDialog confirm ("Bu makaleyi listeden çıkar? Notlar saklanır.") — Hold-to-Confirm pattern REDDEDİLDİ (keyboard fail)
- [ ] Etiket inline rename: shadcn `<Input>` + edit toggle state + Enter/Esc keyboard handling + optimistic update
- [ ] Empirik kanıt: F5 §6.5'te eklenmiş profil dropdown ile aynı dark overlay variant + uiverse layout pattern → tutarlı UI sözleşmesi
- [ ] §Council 38 — Defne BAĞLAYICI A satırı + Sercan alan-dışı yorum (reading list CRUD context)

---

## §7 Commit disiplini

- **Branch**: `feat/F6-detail-summarize-ghost`
- **Atomic commit**: P053..P061 ayrı commit + ayrı PR
- **Pre-flight Read**: §5 Read-only listesi
- **Test gate**: §4 S1-S8 PASS olmadan merge **YASAK**
- **Co-Authored-By**: Claude Opus 4.7
- **Commit message**: `[P0XX] web: <kısa öz>` (örn. `[P056] web: SummarizePanel + useSummarizePolling hook`)

---

## §8 Önkoşullar — GÜNCEL DURUM (2026-04-30)

### ✅ Kapanmış
| Önkoşul | Kapanış |
|---|---|
| ARCHITECTURE.md §3 paper detail Zustand cache pattern | ✅ A Grubu güncellemesi |
| B42-040 12 chip listesi | ✅ Papermind_V2/DECISIONS.md |
| B-008 PaperCard upload (24.86M) | ✅ |

### ⏳ F4 + F5 + F3c + F3d + F3e bağımlı
| Önkoşul | Statü |
|---|---|
| **F4 PASS** (P037-P043 + Zustand paper-cache F4 P043) | ⏳ F4 sprint |
| **F5 PASS** (E1+E2+E3 + i18n F5 P044) | ⏳ F5 sprint |
| **F3c PASS** (`/api/summarize` POST + GET poll) | ⏳ F3c sprint |
| **F3d PASS** (`/api/enrichment` POST + poll) | ⏳ F3d sprint |
| **F3e PASS** (`/api/reading-list` CRUD) | ⏳ F3e sprint |

### ⏳ Aktif engelleyiciler
| Önkoşul | Statü | Kim |
|---|---|---|
| **OPEN-006 Ghost cache TTL** (7d master vs 90d DM-006 L1) | ⏳ Omer F6 öncesi | F3d backend ayar, F6 frontend transparent |
| **chip_library_spec.md** (12 chip backend formül + cohort) | ⏳ Sercan F2 P002 | ChipBadgeGrid render z>1 cohort yorumu için |

---

## §Council — R13 16. tur (B Grubu F6 taslağı, 2026-04-30)

| # | Üye | Verdict | Gerekçe (1 cümle) | RED/YELLOW ne istedi (1 cümle) |
|---|---|---|---|---|
| 1 | **Halüsinasyon Avcısı** | ✅ GREEN | ARCHITECTURE.md §3 dondurulmuş `/api/papers/{id}` YOK pattern'ine sadık; B42-045 13 sinyal + B42-040 12 chip referansları doğrulanmış | — |
| 2 | **Akademik İsabet** | ✅ GREEN | K1/K5/K9 runtime enforce; LVR atıf cümle-düzey popover; NedenPanel engineer-mode P1 transparency; akademisyen sezgisel kullanım | — |
| 3 | **Fayda-Maliyet Hakemi** | ⚠️ YELLOW | 9 commit ~1200 LOC E5 detay + summarize + ghost + reading list 4 fonksiyonel akış için makul ama **virtualization (react-window)** RelatedPapersList'te 50+ kart için TODO(sercan) §6.3'e bırakılmış — F6 başlangıçta sadece map render ile 50 kart performance sorunu olabilir; M2 RAM 8GB yavaş cihazlarda smooth scroll riski | İstiyor: P059 (RelatedPapersList) baseline'a "ilk 10 kart eager + 40 kart `IntersectionObserver` lazy-mount" eklensin (basit virtualization, react-window'suz; ~30 LOC) — TODO yerine planın içinde |
| 4 | **Daha İyisi Var Mı?** | ⚠️ YELLOW | Polling 3s default — **SSE poll endpoint** veya **WebSocket** modern alternatif; ama Celery + Redis pattern için polling yeterli (basit + güvenilir) ✓ | İstiyor: §1 Karar günlüğüne "polling tercihi: SSE/WebSocket yerine 3s polling — Celery task pattern + Redis broker basit + Render ALWAYS-restart proxy timeout dostu (DM-014); ileri vizyon Faz 2'de WebSocket düşünülür" cümle eklensin (gerekçe transparency) |
| 5 | **Global Çözüm Mühendisi** | ✅ GREEN | i18n F5'te kuruldu, F6 sadece string ekleme; mobile breakpoint F4 P040 PaperCard'ta belgelenmiş; SignalGrid `grid-cols-2 md:grid-cols-3 lg:grid-cols-4` responsive | — |
| 6 | **Son Kullanıcı Avukatı** | ✅ GREEN | "Neden?" engineer-mode opt-in (kullanıcıyı boğmaz); LVR popover hover (görsel rahatsızlık yok); reading list optimistic instant feedback; ghost detay K1 dürüst pozisyonlama | — |

**Karar (R13.5)**: 4 GREEN + 2 YELLOW (3+ değil); bypass entry gerekmez. Düzeltme ile 6 GREEN'e:
1-2. ✅ GREEN
3. **Düzeltme P059**: "ilk 10 eager + 40 IntersectionObserver lazy-mount" baseline (Fayda-Maliyet YELLOW → GREEN) — §3 P059 satırına eklendi
4. **Düzeltme §1**: polling tercihi gerekçe cümlesi eklendi (Daha İyisi YELLOW → GREEN) — §1 Karar günlüğü "Polling pattern" satırına eklendi
5-6. ✅ GREEN

**Council 16 düzeltme uygulandı**:
- §3 P059 satırı: "RelatedPapersList — corpus 50 + ghost ek (PaperCard list-mode reuse F4 P040); **ilk 10 eager + 40 IntersectionObserver lazy-mount** (basit virtualization, ~30 LOC ek)"
- §1 Karar günlüğü "Polling pattern" satırına ek: "(SSE/WebSocket yerine polling: Celery + Redis pattern basit + Render ALWAYS-restart proxy timeout dostu DM-014; ileri vizyon Faz 2 WebSocket)"

---

**Final commitment**: Bu mini-plan onaylanırsa P053 commit'i F4+F5+F3c+F3d+F3e PASS sonrası `feat/F6-detail-summarize-ghost` branch'inde 24 saat içinde açılır; verification S1+S2+S4 PASS ile P053 PR mergeable. Tam E5+Summarize+Ghost (P053..P061) 4-5 günde browser'dan görünür çalışır (master §9 F6 süresi).
