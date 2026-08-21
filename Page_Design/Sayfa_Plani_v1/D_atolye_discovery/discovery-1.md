# Discovery-1 — Araştırma Alanı (Kütüphaneci sohbeti + Çapa kilidi)

> **Atölye Discovery'nin giriş kapısı.** F9 1.1 sürümü P097 frontend bloku.
> **Backend kanon:** F9 P094 (librarian Stage A) + P095 (anchor-candidates Stage B) main'de canlı; P096 (anchor/lock + ESTRA) IN-QUEUE.
> **Halüsinasyon yasağı:** tüm REPO claim'leri canlı doğrulandı (2026-05-08).

---

## KONUM

- **Route:** `/project/{id}/discovery-1`
- **Frontend dosyası:** ROUTE FALLBACK — `web/src/app/(app)/project/[id]/[[...slug]]/page.tsx` switch'inde **case yok**, `default → PlaceholderPage` `[REPO]`
- **Backend dosyaları (canlı):**
  - `api/routes/research_area.py` — 2 endpoint: `POST .../messages` (Stage A), `POST .../anchor-candidates` (Stage B) `[REPO]`
  - `api/services/role_modules/librarian.py` — Stage A 2-tur orchestrator (P094, PR #14 `7ebaa31`) `[REPO]`
  - `api/services/anchor_finder.py` — Stage B HyDE → fan-out → RRF → rerank (P095, PR #17 `9af5be0`) `[REPO]`
  - `api/models/research_area.py` — Pydantic forbid: MessageRequest / MessageResponse / ParsedUnderstanding / HydePacket / AnchorCandidate / AnchorCandidatesResponse `[REPO]`
  - `prompts/librarian_v1.md` — lru_cache prompt `[REPO]`
- **İlgili plan:** `docs/plans/F9_kesif_workbench.md §7-§8` `[REPO]`
- **İlişkili sprint:** F9 P097 frontend (~520 LOC, NEXT_ACTION'da "discovery-1 araştırma alanı bağlama")
- **İlişkili DM:** K-031 (RLS+manuel zırh), K-029 (asyncpg/session pooler), R13.13 (build PASS empirik kanıt)

---

## MEVCUT

**Frontend:** Hiçbir şey. `discovery-1` sidebar'da görünür (`nav-config.ts:64 { id: "discovery-1", label: "Arastirma Alani" }`) ama route fallback'i `PlaceholderPage` rendır eder — `findWorkbenchInfo("discovery-1")` workbench label'ı verir, gövde sadece "yakında" placeholder'ıdır.

**Backend:** İki endpoint canlı + Pydantic + LLMService + Pinecone+tsvector hibrit havuz. 17 unit + 2 integration test PASS (`test_librarian.py` + `test_research_area.py`); 6 unit + 3 integration (`test_anchor_finder.py` + `test_anchor_candidates.py`) PASS.

**Sözleşme (canlı endpoint):**

```
POST /api/project/{project_id}/research-area/messages
  Request:  MessageRequest{ content: 1-2000 char, attempt_no: 1-10 }
  Response: MessageResponse{
    turn_no: 1|2,
    parsed_understanding: ParsedUnderstanding{
      focuses: [3 string], field, subfield?, interdisc, confidence: high|med|low,
      adviser_text, finished
    },
    adviser_text, finished
  }
  Hata: 401 missing_user_id, 404 project_not_found (RLS güvenli),
        422 validation, 503 supabase_unavailable | llm_unavailable
```

```
POST /api/project/{project_id}/research-area/anchor-candidates
  Request:  body yok (server tarafı parsed_understanding'i Stage A'dan okur)
  Response: AnchorCandidatesResponse{
    candidates: [1-3 × AnchorCandidate{ paper_id, title, abstract_preview,
                  field?, language?, year?, decision_band: high|med|low, q_weak: 0-1 }],
    packet_p, packet_s
  }
  Hata: 401, 404, 409 stage_a_incomplete, 503 llm_unavailable, 504 pools_empty
```

**Henüz yok:** P096 anchor/lock background job + ESTRA scorer + cluster_expander (~280 LOC, brief panoda). Lock olmadan "çapayı kilitle" CTA backend'i yok.

---

## ROL

Atölye Discovery'nin **giriş sayfası**. Kullanıcı projeye girince ilk burada Kütüphaneci ile **2-tur sohbet** eder; sistem alanı/odakları/disiplinerlik confidence'ını parse eder; sonra **3 çapa makale adayı** sunar; kullanıcı birini seçer → çapa kilitlenir → discovery-2..5 ve tüm sonraki modüller bu çapaya bağlanır. Funnel'in **proje DNA'sını belirleyen sayfa** — geri dönüş anti-pattern (yeniden çapa = yeni proje).

---

## PİLOT?

**HAYIR — pilot scope dışı.** Pilot kanon: `Q ⇄ Q1 funnel + capture form` (DM-052/053). Discovery-1 F9 1.1 sürümünün son frontend bloku (P097); pilot launch sonrası kullanıma açılır. **Plan canon** — backend zaten main'de, frontend P097'de bağlanır.

---

## BAĞIMLILIK

- **Giriş:**
  - Project create akışı (onboarding `research_focus_en` miras → Tur 1 prefill için kullanılabilir, [KARAR])
  - Project overview sayfasından "Araştırma Alanı" sidebar tıklaması
  - URL: `/project/{id}/discovery-1` (slug; project layout AppShell sarar)
- **Çıkış:**
  - **Çapa kilitlendi:** `router.push("/project/{id}/discovery-2")` (Konu Belirleme — havuz expand)
  - **409 stage_a_incomplete:** Sayfa içi "Önce sohbeti tamamla" inline error, anchor-candidates fetch reddedilir
  - **504 pools_empty:** "Havuz yetersiz, sorgu daraltılmalı" hint + "Tur 1'e dön" CTA (yeni sohbet)
- **Backend bağımlılığı:** F9 P096 (anchor lock) — frontend "Çapayı Kilitle" CTA için backend lock endpoint'i şart. P097 başlamadan önce P096 tamamlanmalı.

---

## SAYFA YAPISI (ASCII layout)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [Atölye · Keşif] › Araştırma Alanı                  [Pro · proje çapası] │
├──────────────────────────────────────────────────────────────────────────┤
│ Kütüphaneci ile 2 tur sohbet — alanı netleştirelim, sonra çapa.          │
│ [italic alt: "Yanıtlarınızı odak/alan/disiplinerlik açısından özetleyip  │
│  3 çapa makale adayı çıkaracağız. Her tur Gemini Flash ile."]            │
├──────────────────────────────────────────────────────────────────────────┤
│  ╔════════════ SOHBET (üst) ═════════════════════════════════════════╗   │
│  ║ [Adviser Lora italic]  "Hangi konuyu araştırıyorsun? Birkaç       ║   │
│  ║                         cümleyle anlatır mısın?"                  ║   │
│  ║ [User Inter]            "MCDM ile yükseköğretim akreditasyon..."  ║   │
│  ║ [Adviser]               "Anladım. Şu noktayı netleştirelim..."    ║   │
│  ║ [User]                  "..."                                     ║   │
│  ║ [Adviser turn-2]        "Yanıtladığın için teşekkürler."          ║   │
│  ╚═══════════════════════════════════════════════════════════════════╝   │
│  ┌──── PARSED UNDERSTANDING (Tur 2 sonu pin kart) ──────────────────┐    │
│  │ Odaklar:   [#focus-1] [#focus-2] [#focus-3]                       │   │
│  │ Alan:      MCDM · Yükseköğretim akreditasyon                      │   │
│  │ Alt-alan:  Türkiye vakası                                         │   │
│  │ Disiplinerlik:  ☑ Disiplinler-arası                                │   │
│  │ Güven:     ●●●○  med                                              │   │
│  └──────────────────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────────────┤
│  ╔════════════ ÇAPA ADAYLARI (alt, 3 kart yatay) ═════════════════════╗  │
│  ║ ┌─[01]─────────┐  ┌─[02]─────────┐  ┌─[03]─────────┐                ║ │
│  ║ │ Title         │  │ Title         │  │ Title         │              ║ │
│  ║ │ year · lang   │  │ year · lang   │  │ year · lang   │              ║ │
│  ║ │ field         │  │ field         │  │ field         │              ║ │
│  ║ │ "abstract     │  │ "abstract     │  │ "abstract     │              ║ │
│  ║ │  preview…"    │  │  preview…"    │  │  preview…"    │              ║ │
│  ║ │ [decision_   │  │ [decision_   │  │ [decision_   │                 ║ │
│  ║ │  band: high]  │  │  band: med]   │  │  band: low]   │              ║ │
│  ║ │ q_weak 0.42   │  │ q_weak 0.61   │  │ q_weak 0.78   │              ║ │
│  ║ │ ( ) Bu çapa   │  │ ( ) Bu çapa   │  │ ( ) Bu çapa   │              ║ │
│  ║ └───────────────┘  └───────────────┘  └───────────────┘              ║ │
│  ╚═══════════════════════════════════════════════════════════════════╝  │
├──────────────────────────────────────────────────────────────────────────┤
│ [⬅ Tur 1'e dön]                              [Çapayı Kilitle ▶ Konu →]   │
│  (sohbet sıfırlanır + parsed silinir)         (P096 lock + discovery-2)  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## BOŞLUK

- Tüm frontend (P097 ~520 LOC) — sayfa, hook'lar, parsed pin kart, anchor 3-kart grid
- Switch case `discovery-1` ekleme (`web/src/app/(app)/project/[id]/[[...slug]]/page.tsx`)
- P096 backend lock endpoint (frontend "Çapayı Kilitle" CTA bekler)
- ESTRA scorer (decision_band kararı için P096'da netleşir)
- onboarding research_focus_en prefill akışı (opsiyonel, [KARAR])

---

## KARAR

**[KARAR]** Frontend 4 katmanlı yapı:

1. **`<ChatThread>` reuse** — mevcut `web/src/components/chat/ChatThread.tsx` (B-023 P076) yeniden kullanılır:
   - Adviser: Lora italic warm-neutral; User: Inter ink
   - Variant: `"page"` (full-page modu, ChatboxPanel modu yok)
   - typing 3-dot Tur 2 LLM beklerken
2. **`<ParsedUnderstandingCard>` (yeni)** — Tur 2 sonu render edilen pin kart:
   - 3 focus chip (semantic amber outline), field+subfield Lora italic, interdisc checkbox readonly, confidence ●●●○ 3-step badge
   - Sticky `bottom-24` + slide-up 280ms cubic-bezier(.16,1,.3,1) — Tur 2 cevabı geldiğinde belirir
3. **`<AnchorCandidateCard>` ×3** (yeni) — `<PaperCardLite>` reuse + 2 ek alan:
   - decision_band semantic chip: high=emerald-700, med=amber-700, low=stone-500
   - q_weak gösterimi: `0.00-1.00` mono + tooltip ("Zayıf eşleşme skoru — düşük = güçlü eşleşme")
   - Radio behavior: tıklama → `selectedAnchor = paper_id`, kart border-left-4 amber-700
4. **`<DiscoveryActionBar>`** (yeni veya inline):
   - Sol: "Tur 1'e dön" outline (sohbet reset onay modal)
   - Sağ: "Çapayı Kilitle" ink amber-700, disabled `!selectedAnchor || !P096`

**State machine:**

```
IDLE → SENDING_TURN_1 → AWAITING_USER_TURN_2 → SENDING_TURN_2
     → PARSED_PINNED → FETCHING_ANCHORS → ANCHORS_READY
     → SELECTING_ANCHOR → LOCKING (P096) → → → DONE → /discovery-2
```

**Hata akışları:**

- 422 validation → ChatThread input border-red + toast
- 503 llm_unavailable → "Kütüphaneci geçici olarak yanıt veremiyor" inline error + retry button
- 409 stage_a_incomplete (anchor-candidates için) → "Sohbet tamamlanmadı, Tur 2'yi bitir" (UX hatası — Tur 2 finish=true olmadan anchor fetch edilmez, frontend gate)
- 504 pools_empty → "Havuz yetersiz, sorgu daraltılmalı" + "Tur 1'e dön" CTA
- Network → TanStack Query retry (3 kez, exponential backoff)

---

## NASIL

### Frontend dosyalar

**Yeni:**

- `web/src/components/project/ResearchAreaPage.tsx` (~280 LOC) — orchestrator
- `web/src/components/project/ParsedUnderstandingCard.tsx` (~80 LOC)
- `web/src/components/project/AnchorCandidateCard.tsx` (~100 LOC) — `<PaperCardLite>` wrap
- `web/src/hooks/useResearchAreaConversation.ts` (~80 LOC) — TanStack Query mutation, 2-tur state machine
- `web/src/hooks/useAnchorCandidates.ts` (~40 LOC) — `useQuery`, `enabled: !!parsed.finished`
- `web/src/hooks/useAnchorLock.ts` (~30 LOC) — P096 mutation, başarı → `router.push("/project/{id}/discovery-2")`

**Mevcut dosya revizyonu:**

- `web/src/app/(app)/project/[id]/[[...slug]]/page.tsx` — switch'e satır:
  ```tsx
  case "discovery-1": return <PageShell><ResearchAreaPage projectId={id} /></PageShell>;
  ```
- `web/src/lib/api.ts` — `apiFetch` zaten var; yeni helper `researchAreaSend(projectId, content, attemptNo)` + `researchAreaAnchors(projectId)` + `researchAreaLock(projectId, paperId)`

**TanStack Query keys:**

- `["research-area", projectId, "messages"]` — sohbet geçmişi (server'dan turn_no ile dönen MessageResponse'lar; client local message log da tutulur)
- `["research-area", projectId, "anchor-candidates"]` — staleTime 30dk (idempotent)
- `["research-area", projectId, "lock"]` — mutation, invalidates `["project", projectId]`

**State (ResearchAreaPage):**

- `messages: ChatThreadMessage[]` (local — server message store yok pilot scope dışı)
- `parsed: ParsedUnderstanding | null`
- `phase: "turn1" | "awaiting_user" | "turn2_sending" | "parsed" | "anchors"`
- `selectedAnchor: paper_id | null`
- TanStack Query: messages mutation + anchors useQuery + lock mutation

### Backend (canlı, frontend bağlanacak)

`POST /api/project/{id}/research-area/messages` ✅
`POST /api/project/{id}/research-area/anchor-candidates` ✅
`POST /api/project/{id}/research-area/anchor/lock` ⏳ **P096 gerekli** — `{paper_id}` body, response `{locked: true, anchor_paper_id, project_id}`; ESTRA bar miras + cluster_expander tetikleme.

### Veri

- Supabase `projects` tablosuna `anchor_paper_id` kolonu (P096 migration)
- Supabase `research_area_turns` tablosu — Stage A 2-tur log (P094'de eklendi, frontend okumaz, server orchestration)
- Redis cache: `anchor_candidates:{project_id}` 30dk TTL (idempotent rerun aynı top-3'ü dönsün)

---

## TIER DAVRANIŞI

**Anon:** Sayfa erişilemez. Project create için auth gerekir → onboarding → Pro tier kontrolü → discovery-1.

**Pro:** Tüm sayfa aktif. Sohbet limiti F9 backend'de yok (1 proje = 1 araştırma alanı; çapa kilitlendi → reset = yeni proje).

**Free tier:** YOK (DM-046).

---

## AÇIK SORULAR

| # | Soru | Engellediği | Önerilen yön |
|---|---|---|---|
| **AS-1** | Onboarding `research_focus_en` Tur 1'e prefill mi olsun? | UX akışı | **Hayır** — F9 P094 brief sıfırdan parse eder; prefill confidence düşürür. Sohbet boş başlar. `[KARAR]` |
| **AS-2** | Çapa kilitlendikten sonra sayfa görünüm? | Geri ziyaret | Read-only mode — ChatThread expanded readonly + parsed pin + seçili anchor highlighted "✓ Çapan" rozet + "Çapayı Sıfırla" link (yeni proje uyarısı). `[KARAR]` |
| **AS-3** | Tur 1'e dön → sohbet reset onayı modal mı yoksa inline mı? | UX | Modal — `<ConfirmDialog>` "Sohbet ve parsed silinecek, devam?" çünkü iş kaybı vardır. `[KARAR]` |
| **AS-4** | P096 anchor lock idempotent mi (aynı paper_id 2x kilitlenebilir)? | Backend sözleşme | Idempotent — 2. çağrı no-op + 200 dön; farklı paper_id 409 (zaten kilitli). P096 brief'inde netleşecek. `[KARAR]` |
| **AS-5** | 3 anchor adayından hiçbiri uygunsa? | UX | "Sorgu daralt" CTA + "Tur 1'e dön" — Stage B yeniden çalışmaz; Tur 2 yeniden = yeni anchor. `[KARAR]` |

---

## TEST KAPSAMI

**Backend (mevcut):**
- `tests/integration/test_research_area.py` — 2-tur happy path + 422 validation + 401 auth + 404 RLS güvenli
- `tests/integration/test_anchor_candidates.py` — 200 + 409 stage_a + 504 empty + Pinecone vec=80 enrich check
- `tests/unit/test_librarian.py` — 7 unit (Tur 1/2, parsed, fence strip, K-031 zırh)
- `tests/unit/test_anchor_finder.py` — 6 unit (HyDE, RRF, rerank, suspicious filter)

**Frontend (yeni — Vitest):**
- `ResearchAreaPage.test.tsx` — render, sohbet flow (Tur 1 → Tur 2 → parsed pin → anchors load), selectedAnchor state, "Çapayı Kilitle" disabled when null
- `ParsedUnderstandingCard.test.tsx` — render with 3 focus / interdisc / confidence levels
- `AnchorCandidateCard.test.tsx` — decision_band semantic colors (high/med/low), radio behavior, q_weak format
- `useResearchAreaConversation.test.ts` — mock api 200/422/503 paths
- Smoke: live `MOCK_API=true` env, dev mode JWT mock user, sohbet 2-tur tam akış (Vitest DOM + jsdom)

---

## BU SAYFA İÇİN KARARA BAĞLANACAK DM

- **DM-XXX** ParsedUnderstanding pin kart UX (Tur 2 sonu sticky bottom-24, slide-up 280ms)
- **DM-XXX** Anchor card decision_band semantic palette (high=emerald-700 / med=amber-700 / low=stone-500)
- **DM-XXX** Onboarding research_focus_en prefill kararı (AS-1: hayır, sıfırdan)
- **DM-XXX** Çapa kilitlendi sonrası sayfa read-only mode (AS-2)
- **DM-XXX** P096 anchor lock idempotent davranışı (AS-4)

---

## SONRAKI

P097 frontend brief yazımı — bu plan onaylandıktan + P096 KAPANDIKTAN sonra:
1. Switch case ekleme (1 satır)
2. ResearchAreaPage + 3 alt component (~520 LOC toplam)
3. 3 hook + 5 Vitest dosyası
4. Tek atomic commit veya 3-commit zinciri (R13 council kararı)
5. Empirik kanıt: tsc --noEmit + next build EXIT 0 + Vitest PASS + smoke browser dev
