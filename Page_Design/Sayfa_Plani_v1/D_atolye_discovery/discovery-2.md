# Discovery-2 — Konu Belirleme (Top-5 paper kuratörlüğü + tek paper kilidi)

> **Çapa lock'tan sonraki ilk modül.** Kullanıcı 5 öneriden tekini seçer → "konu" projeye kilitlenir.
> **Mock = ürün:** `web/src/components/project/TopicSuggestionPage.tsx` 164 satır, `/api/top5` wired.
> **Halüsinasyon yasağı:** repo state canlı doğrulandı (2026-05-08).

---

## KONUM

- **Route:** `/project/{id}/discovery-2`
- **Frontend:** `web/src/components/project/TopicSuggestionPage.tsx` (164 satır) `[REPO]`
  - Switch case mevcut: `case "discovery-2": return <PageShell><TopicSuggestionPage /></PageShell>;` (page.tsx:90) `[REPO]`
- **Backend:** `api/routes/top5.py` — `POST /api/top5` real 5-layer pipeline (B-018 + Council 37f) `[REPO]`
  - Service DI: `Listener / Anchor / PoolRouter / Reranker / Curator` (search.py'den miras)
  - Cache: `cache_get(CacheNamespace.QUERY, key)` Redis 1h TTL
  - Margin gate: raw reranker score üzerinde
- **Pydantic:** `api/models/top5.py` — `Top5Request{query, session_id, margin=0.7, k=5}` + `Top5Response{papers: list[PaperCard], needs_clarify, margin_used}` `[REPO]`
- **İlgili kararlar:** OPEN-005 (margin eşiği default 0.7 onay bekliyor) `[REPO]`

---

## MEVCUT

**Frontend (mock = ürün):**

- `useQuery(["top5-topics", activeQuery])` → `apiFetch<Top5Response>("/api/top5", {body:{query, k:5, margin:0.3, session_id: crypto.randomUUID()}})`
- DEFAULT_QUERY = `"MCDM cok kriterli karar verme"` (hard-coded)
- 5-kart grid (md:2 col), her kart:
  - Title (Lora 15px semibold)
  - 3-line clamp `abstract_excerpt`
  - `authors · year · paper_id (mono)`
  - **"Konu bana kilitli" Lock chip** (statik — backend lock yok, sadece görsel)
  - 2 buton: `Bu paper'i seç` (gradient amber, setSelectedId) + `Detay gör` (outline, **onClick yok**)
- Selected kart: border-left-4 amber + box-shadow + "Seçildi" rozet
- Üstte AdvisorBanner: *"Sana en ilgili 5 paper'i getirdim. Hangileri ilgini cekiyor, beraber inceleyelim — bu sonuclar sana ozel."*
- Üstte sorgu input + "Ara" gradient amber button (hand-typed query mode)
- staleTime 15dk
- `data?.needs_clarify` → amber warning panel "Sorgu daha spesifik olursa daha iyi sonuclar alabiliriz."
- isError → red error panel
- Loading: 5 placeholder pulse kart

**Backend (canlı):**

```
POST /api/top5
  Request:  Top5Request{ query: 3-512 char, session_id, margin: 0-1 (def 0.7), k: 1-10 (def 5) }
  Response: Top5Response{
    papers: list[PaperCard] (max 10),
    needs_clarify: bool,
    margin_used: float
  }
  Hata: 503 (resilience timeout / dep failure)
```

Pipeline: `listener.understand(query) → anchor.match → pool_router.fan_out → reranker.score → curator.select`. Margin gate raw reranker skoru üzerinde aktif; needs_clarify flag chat clarify branch tetikler.

---

## ROL

Çapa kilitlendikten (discovery-1) sonra **Konu Kilidi** sayfası. Çapa makaleyle ilgili top-5 paper havuzdan curated edilir; kullanıcı **bir** tanesini "konu" olarak kilitler. Bu kilit sonraki tüm modüllerin (discovery-3..5, curation, gapatlas) merkez referansıdır. Funnel: "Çapa = alan kaplaması" → "Konu = spesifik araştırma sorusu odağı".

---

## PİLOT?

**HAYIR — pilot scope dışı.** Discovery-1 ile aynı F9+ frontend grubu. Backend canlı, frontend mock seviyesi (mock = ürün ama eksikleri var — aşağıda).

---

## BAĞIMLILIK

- **Giriş:**
  - discovery-1'den lock sonrası (`anchor_paper_id` projede kilitli)
  - Sidebar "Konu Belirleme" tıklaması (project layout)
- **Çıkış:**
  - **Konu kilitlendi:** project state'e `topic_paper_id` yazılır → discovery-3..5 erişilebilir; sidebar disabled state kalkar
  - "Detay gör" → **[KARAR]** paper detail modal veya `/paper/{id}` route (mevcutta tıklama yok)
- **Backend bağımlılığı:** Konu lock endpoint **yok** — yeni endpoint gerekli (`POST /api/project/{id}/topic/lock`)

---

## SAYFA YAPISI (ASCII)

```
┌──────────────────────────────────────────────────────────────────────┐
│ [Atölye · Keşif] › Konu Belirleme              [Pro · konu kilidi]  │
├──────────────────────────────────────────────────────────────────────┤
│ [AdvisorBanner Lora italic]                                          │
│ "Sana en ilgili 5 paper'i getirdim. Hangileri ilgini cekiyor,       │
│  beraber inceleyelim — bu sonuclar sana ozel."                       │
├──────────────────────────────────────────────────────────────────────┤
│  [🔎 _____________________________________________________] [Ara →] │
│  (sorgu yeniden alıntı + needs_clarify ise inline öneri)             │
├──────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────┐  ┌────────────────────────────┐      │
│  │ Title (Lora 15)             │ │ Title                      │      │
│  │ "abstract_excerpt 3-line…" │  │ "abstract_excerpt…"        │      │
│  │ Author · 2024 · paper_id    │ │ Author · 2023 · paper_id   │      │
│  │ [🔒 Konu bana kilitli]      │ │ [🔒 Konu bana kilitli]      │      │
│  │ [Bu paper'i seç ▶][Detay]   │ │ [Bu paper'i seç ▶][Detay]  │      │
│  └────────────────────────────┘  └────────────────────────────┘      │
│  ┌────────────────────────────┐  ┌────────────────────────────┐      │
│  │ ...                        │ │  ...                        │      │
│  └────────────────────────────┘  └────────────────────────────┘      │
│  ┌────────────────────────────┐                                      │
│  │ ... 5. paper                │                                     │
│  │  ✓ Seçildi (border-left-4) │                                     │
│  └────────────────────────────┘                                      │
├──────────────────────────────────────────────────────────────────────┤
│ [⬅ Çapayı yeniden seç]                  [Konuyu Kilitle ▶ Bibliyo →]│
│  (discovery-1 unlock onay)              (POST topic/lock + disc-3)   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## BOŞLUK

- **Detay gör onClick yok** — paper detail modal veya route navigation eksik
- **Selected ID kalıcılaşmıyor** — sayfa yenilenince kayboluyor (URL state veya server state yok)
- **margin: 0.3 hard-coded** — backend default 0.7, frontend 0.3 ile override → margin gate gevşek; kullanıcı ayarlayamıyor (genelde de ayarlamamalı, ama default 0.7 olmalı)
- **DEFAULT_QUERY = "MCDM cok kriterli karar verme"** — hard-coded sample; çapa kilitlendiğinde anchor paper'ın query'si yüklenmeli (otomatik)
- **"Konu bana kilitli" Lock chip statik** — backend lock yok, sadece görsel
- **Konu lock endpoint yok** — "Konuyu Kilitle" CTA backend'i yok
- **needs_clarify warning sadece text** — chat clarify branch UX akışı yok (sorgu daraltma için kullanıcıya rehberlik)
- **session_id her render'da `crypto.randomUUID()`** — anlamsız, server cache key parçası ama her UUID farklı → cache asla hit etmez (UX hatası, KD)

---

## KARAR

**[KARAR]** Reverse-engineer + 7 düzeltme (mock büyük ölçüde kanon, eksikleri kapatılır):

1. **Anchor query auto-load** — `discovery-1`'den `anchor_paper_id` projede kilitli ise `useQuery(["project", id]).anchor.title` veya parsed_understanding'in pseudo_paragraph'ı initial query olarak yüklenir; kullanıcı isterse override eder.
2. **margin = 0.7** — backend default'a uy; frontend hard-coded 0.3 silinir, OPEN-005 user kararı (eski karar).
3. **session_id stable** — `useMemo(() => crypto.randomUUID(), [projectId])` — proje başına 1 session; cache hit edebilsin.
4. **Selected ID kalıcılaşır** — `useState` yerine TanStack Query mutation `["project", id, "topic-pick"]`; URL `?topic={paper_id}` query param.
5. **"Konuyu Kilitle" CTA** — Sayfa altına aksiyon barı eklenir, `selectedId` set olunca aktifleşir; tıklama → `POST /api/project/{id}/topic/lock` (yeni endpoint) → success → `router.push("/project/{id}/discovery-3")`.
6. **Detay gör → paper detail** — tıklama `<Dialog>` modal aç (mevcut `Dialog` shadcn), abstract full + signals_13 + "Tam metni aç" external link. Modal content yeni `<PaperDetailDialog>` component.
7. **needs_clarify chat branch** — true ise inline `<ClarifyHint>`: "Sorguda 2-3 spesifik terim daha ekle" + 3 öneri chip (Gemini Flash mini-call ile, F9 brief'inde geliştirilir).

**Lock chip "Konu bana kilitli" semantiği:** Statik amber chip yanıltıcı (kullanıcı sandığı an konu kilitli oluyor zannediyor). Değişiklik: chip metni → `"Bu paper konuya aday"` outline gri; konu kilitlendiğinde seçili kart üzerinde solid emerald-700 chip `"✓ Konun"`.

---

## NASIL

### Frontend dosyalar

**Revize:**

- `web/src/components/project/TopicSuggestionPage.tsx` — 7 düzeltme yukarıdaki KARAR'a göre
- `web/src/app/(app)/project/[id]/[[...slug]]/page.tsx` — projectId'yi component'e geçir: `<TopicSuggestionPage projectId={id} />`

**Yeni:**

- `web/src/hooks/useTopic.ts` (~50 LOC) — TanStack Query mutation `topicLock(projectId, paperId)`, useQuery `topicGet(projectId)` (lock state)
- `web/src/components/project/PaperDetailDialog.tsx` (~80 LOC) — shadcn Dialog wrap, paper full abstract + meta + external link
- `web/src/components/project/TopicLockBar.tsx` (~50 LOC) — sticky bottom action bar (`<DiscoveryActionBar>` ortak component'in 2. kullanımı)

### Backend (yeni endpoint)

**Yeni:** `POST /api/project/{project_id}/topic/lock`

```python
class TopicLockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paper_id: str = Field(min_length=1, max_length=64)

class TopicLockResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    topic_paper_id: str
    locked_at: datetime
```

Service: `api/services/topic_service.py` — Supabase `projects` tablo update `topic_paper_id` kolon (yeni migration `0019_projects_topic_paper_id.sql`). K-031 RLS+manuel zırh. Idempotent (aynı paper_id 2x → no-op 200; farklı paper_id → 409).

### Veri

- Migration `0019_projects_topic_paper_id.sql` — `alter table projects add column topic_paper_id text;`
- Redis cache: konu lock değişiminde `cache_invalidate("project", project_id)` (project state staleness koruma)

---

## TIER DAVRANIŞI

**Anon:** Erişilemez (proje gerekir).
**Pro:** Tüm özellikler aktif. Konu sayısı 1/proje (kilitli; reset = yeni proje).
**Free:** YOK.

---

## AÇIK SORULAR

| # | Soru | Engellediği | Önerilen yön |
|---|---|---|---|
| **AS-1** | Konu kilidi reset'lenebilir mi (kullanıcı yanlış seçtim derse)? | UX | **Evet, ama uyarılı** — `<ConfirmDialog>` "discovery-3..5 verileri silinecek, devam?" + `POST .../topic/unlock`. Çapa reset analojisi. `[KARAR]` |
| **AS-2** | needs_clarify=true durumunda Gemini Flash öneri chip'i otomatik mi yoksa user clarify yazsın diye mi bırakılsın? | UX | **Otomatik 3 öneri chip** — Gemini Flash mini-call (P094 librarian pattern reuse, lru_cache). Click → query'ye ekle + auto-submit. `[KARAR]` |
| **AS-3** | k (paper sayısı) kullanıcı override edebilsin mi? | UX | **Hayır** — k=5 sabit; UI'da ayar yok. Pro+ feature post-MVP (DM-046 Pro+ ELİMİNE → kalıcı sabit). `[KARAR]` |
| **AS-4** | margin 0.7 kullanıcı görür mü? | UX şeffaflık | Görünmesin; backend internal. needs_clarify zaten margin signal'ını UX'e taşıyor. `[KARAR]` |
| **AS-5** | "Detay gör" modal vs `/paper/{id}` route? | Navigation | **Modal** — sayfa içi flow korunur (`<Dialog>`); konu seçimi state kaybolmaz. Route variant geri/ileri butonu kırar. `[KARAR]` |

---

## TEST KAPSAMI

**Backend (mevcut):**
- `tests/integration/test_top5_endpoint.py` — happy path, margin gate, needs_clarify, cache hit
- Topic lock endpoint için **yeni**: `test_topic_lock_endpoint.py` (idempotent, 409 farklı paper, 401 auth)

**Frontend (yeni — Vitest):**
- `TopicSuggestionPage.test.tsx` — 5-kart render, selectedId state, anchor query auto-load, margin=0.7
- `PaperDetailDialog.test.tsx` — açılış/kapanış, abstract render, external link
- `TopicLockBar.test.tsx` — disabled when null, lock mutation, success route push
- `useTopic.test.ts` — mock 200/409/503

---

## BU SAYFA İÇİN KARARA BAĞLANACAK DM

- **DM-XXX** Topic lock endpoint sözleşmesi (idempotent + 409 conflict semantik)
- **DM-XXX** Anchor query auto-load (parsed pseudo_paragraph mı anchor title mı)
- **DM-XXX** needs_clarify chip otomasyonu (AS-2)
- **DM-XXX** Lock chip semantiği (statik aday → kilitli ✓ konun)
- **DM-XXX** session_id strategy (proje başına stable UUID)
