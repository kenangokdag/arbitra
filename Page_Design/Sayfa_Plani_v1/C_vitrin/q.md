# Q — Hızlı İnceleme

> **Vitrin funnel giriş sayfası.** Pilot scope kalbi.
> **Kanon kararlar:** DM-046 (tier), DM-047 (havuz), DM-052 (chip + CTA), DM-054 (Q2 elimine), DM-055 (Q1+Q3 bağımsız endpoint).
> **Halüsinasyon yasağı:** tüm REPO claim'leri canlı doğrulandı (2026-05-08).

---

## KONUM

- **Route:** `/q`
- **Dosya:** `web/src/app/(app)/q/page.tsx` — 281 satır `[REPO]`
- **İlişkili DM:** DM-046, DM-047, DM-052, DM-054, DM-055

---

## MEVCUT

3 hard-coded `MOCK_PAPERS` (Liu/Yıldız/Park); range type `20|50|100` (state var, sonuca etkisiz); tier badge `"T0 · anonim · 3 sorgu / gün"` (sayaç yok, statik); action bar Q1 active `<a href="/q1">`, Q2/Q3 disabled `"yakında"`; "Projeme Dönüştür" button onClick'siz; hero metni OpenAlex'e referans veriyor; URL `?q=` sync (`useSearchParams + router.replace`). **DM-054 ile Q2 ELİMİNE; bu sayfa revizyonunda Q2 button silinir, Q3 aktif edilir.**

---

## ROL

Vitrin funnel **giriş sayfası**. Kullanıcı sorgu yazar → 3/20/50 kart önizleme → "Literatür Özeti" `/q1` veya "Metod Önerisi" `/q3` (iki bağımsız CTA, DM-055) → kayıt funnel'i. Pilot scope kalbi.

---

## PİLOT?

**EVET** — DM-046..052 kanon.

---

## BAĞIMLILIK

- **Giriş:**
  - URL `?q=` query param (landing/derin link/organik trafik)
  - `langdetect` (TR/EN/ID sınıflandırma sorgu üzerinde — havuz + özet dili için)
- **Çıkış:**
  - `/q1?qid={query_id}` — Anon: paywall placeholder, Pro: literatür özeti (sorgu dilinde — TR/EN/ID); endpoint `POST /api/q/literature`
  - `/q3?qid={query_id}` — Anon: paywall placeholder, Pro: metod önerisi (havuz metod dağılımı + 2-3 metod öneri + sample/dataset hint, sorgu dilinde); ayrı bağımsız endpoint `POST /api/q/method` (DM-055)
  - **Q2 ELİMİNE** (DM-054) — `/q2` route YOK, açılmayacak
  - `POST /api/waitlist` — "Projeme Dönüştür" capture form
  - Redis cache: `q:search:{sha256(query)}` 1h, `q:ratelimit:{ip_hash}` günlük

---

## SAYFA YAPISI (ASCII layout)

```
┌────────────────────────────────────────────────────────────────────┐
│ [Vitrin · Q] › Hızlı İnceleme        [Anon · 3 sorgu / gün] (badge)│
├────────────────────────────────────────────────────────────────────┤
│  Konunu yaz, 3 makale gör.                                         │
│  [italic alt: "Akademik dizinlerden alaka sırasıyla… hesap         │
│   gerekmez."]                                                      │
├────────────────────────────────────────────────────────────────────┤
│  [🔎 ____________________________________________________ ][Ara →] │
│                                                                    │
│  Görünüm:  ●3   ○20 🔒   ○50 🔒    (Anon: 20/50 → paywall modal)  │
│                                     (Pro: hepsi aktif)             │
├────────────────────────────────────────────────────────────────────┤
│ N makale · alaka sırasıyla · 50'lik havuzdan      "{query…}"       │
│                                                                    │
│ ┌──────────────────────────────────────────────────────────┐       │
│ │[01]  Title                                    [TR/EN rozet]│      │
│ │      Authors · Venue, Year · NN atıf                       │     │
│ │      "TR kısa özet — italic Crimson."                      │     │
│ └──────────────────────────────────────────────────────────┘       │
│ [02] ... [03] ...                                                  │
│ (Pro 20/50: react-window virtualized list)                         │
├────────────────────────────────────────────────────────────────────┤
│ Bu N makaleden ne üretelim?                                        │
│ [Q1 Literatür Özeti]   [Q3 Metod Önerisi]   |  [✨ Projeme Dön.]   │
│ (Anon Q1/Q3 → paywall modal "Pilot Pro Deneme Sürecini Başlat")    │
│ (Q2 ELİMİNE — DM-054, button yok)                                  │
└────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Frontend

**Mevcut dosya revizyonu** (`web/src/app/(app)/q/page.tsx`):

- `MOCK_PAPERS` sabit array → SİL
- `Range = 20 | 50 | 100` → `Range = 3 | 20 | 50` (DM-052)
- Hero alt-metin: "OpenAlex" → "akademik dizinler"
- Veri akışı: `useSearchPapers(query, range)` hook'u ile `POST /api/q/search` çağrısı
- Range chip render: `tier === "anon" && [20, 50].includes(r)` → `<Lock>` ikonu + onClick `setShowPaywall(true)`
- Action button Q1: `tier === "anon"` → onClick paywall modal; `tier === "pro"` → `router.push(\`/q1?qid=${query_id}\`)`
- Action button Q3: `tier === "anon"` → onClick paywall modal; `tier === "pro"` → `router.push(\`/q3?qid=${query_id}\`)`
- "Projeme Dönüştür" onClick → `setShowCapture(true)`
- Tier badge sayaç: `useRateLimit()` hook'u ile `GET /api/q/ratelimit`

**Yeni dosyalar:**

- `web/src/hooks/useSearchPapers.ts` — TanStack Query useQuery, key=`["q-search", query, range]`, `enabled: !!submitted`
- `web/src/hooks/useRateLimit.ts` — TanStack Query useQuery, polling 60s, key=`["q-ratelimit"]`
- `web/src/hooks/useTier.ts` — cookie `pm_tier` okur (`"anon"` | `"pro"`), pilot için `"anon"` default
- `web/src/components/PaywallModal.tsx` — copy: "Literatür Özeti İçin Deneme Sürecini Başlat" + "Pro'ya Geç" butonu (Faz 2'de Stripe checkout, pilot için trial token akışı)
- `web/src/components/CaptureModal.tsx` — form: e-posta + research_area dropdown + submit → `POST /api/waitlist`

**State:**

- TanStack Query server state (mevcut `web/package.json`'da `@tanstack/react-query` var — doğrulanacak Faz 1'de)
- URL `?q=` query param (mevcut pattern)
- Local `useState`: `query`, `range`, `submitted`, `showPaywall`, `showCapture`
- Tier kaynağı: client cookie `pm_tier=anon|pro` (Faz 2'de Supabase session ile değiştirilecek)

**Interactions:**

- `<form onSubmit>` → `runSearch(query)` → `router.replace + setSubmitted` → `useSearchPapers` tetiklenir
- Chip tıklama (Anon, 20/50): `setShowPaywall(true)`
- Q1 tıklama (Anon): `setShowPaywall(true)` | (Pro): `router.push("/q1?qid=" + query_id)`
- Q3 tıklama (Anon): `setShowPaywall(true)` | (Pro): `router.push("/q3?qid=" + query_id)`
- "Projeme Dönüştür" tıklama: `setShowCapture(true)`

### Backend

**Yeni endpoint: `POST /api/q/search`**

Request:

```python
class QSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=500)
    range: Literal[3, 20, 50] = 50
```

Response:

```python
class QSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_id: str                           # uuid4 hex
    pool_size: int = 50
    papers: list[PaperCard]                 # range'e göre 3/20/50
    sources: list[Literal["s2", "trdizin"]]
    paywall: bool                           # tier=anon AND range in [20,50]
    rate_limit: RateLimitInfo

class PaperCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paper_id: str                           # "s2:abc123" veya "trdizin:456789"
    rank: int                               # 1..50 (50-paper havuz üzerinden sabit)
    title: str
    authors: str                            # "Liu, Y. & Zhang, W."
    venue: str
    year: int
    citations: int | None                   # TRDizin'de null
    card_summary: str                       # 1-2 cümle, sorgu dilinde (TR/EN/ID)
    card_lang: Literal["tr", "en", "id"]    # sorgu diline eşit
    source: Literal["s2", "trdizin"]

class RateLimitInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    remaining: int                          # Anon: 0..3
    reset_at: datetime                      # gece yarısı UTC
```

**Service:** `api/services/q_search_service.py` (yeni)

1. `langdetect.detect(query)` → `"tr"` | `"en"` | `"id"` (Bahasa Indonesia). Diğer diller → `"en"` fallback.
2. Redis cache: `q:search:{sha256(query)}:{lang}` hit → return
3. Paralel `httpx.AsyncClient` ile fetch:
   - **S2:** `GET https://api.semanticscholar.org/graph/v1/paper/search/relevance?query={q}&limit={30 if lang=='tr' else 50}&fields=paperId,title,authors,venue,year,citationCount,abstract` — header `x-api-key: {S2_API_KEY}` (env, opsiyonel; yoksa polite 1 req/sec)
   - **TRDizin (sadece lang=='tr'):** `GET https://search.trdizin.gov.tr/api/defaultSearch/publication/?q={q}&order=relevance-DESC&page=1&limit=20` (auth gereksiz, JSON). EN/ID query'lerde TRDizin atlanır → S2 50.
4. Normalize → `PaperCard` array. Card summary üretimi:
   - S2 (abstract genelde EN): Gemini Flash 2.0 ile **sorgu dilinde** 1-2 cümle özet (cache: `q:card_summary:{paper_id}:{lang}` 30g TTL)
   - TRDizin native (lang==tr): `abstract.tr` direkt kullanılır (LLM çağrısı yok)
5. Native skor sıralaması ile birleştir → top-50 → range'e göre kes
6. Cache yaz, `query_id` (uuid4) üret, response dön

**Diğer endpoint'ler:**

- `POST /api/waitlist` — body `{email: EmailStr, research_area: str, query_id: str | None}` → Supabase `waitlist` insert
- `GET /api/q/ratelimit` — IP'den `RateLimitInfo` döner (badge için)

**Middleware:** `api/middleware/rate_limit.py` — IP SHA-256 hash → Redis sliding window `q:ratelimit:{ip_hash}` günlük 3 (Anon), aşılırsa HTTP 429 + `RateLimitInfo` body

### Veri

**Yeni Supabase migration:** `0017_waitlist.sql`

```sql
create table waitlist (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  research_area text,
  query_id text,
  source_query text,
  created_at timestamptz not null default now()
);
create index idx_waitlist_email on waitlist (email);
-- RLS: insert anon-OK, select service-role only
```

**Redis cache key'leri:**

- `q:search:{sha256(query)}:{lang}` → JSON `QSearchResponse`, TTL 1h
- `q:card_summary:{paper_id}:{lang}` → str, TTL 30g
- `q:ratelimit:{ip_hash}` → int counter, TTL gece yarısı UTC reset

**External API'ler (gerçek, dökümante):**

- **S2 Graph API v1:** `https://api.semanticscholar.org/graph/v1/paper/search/relevance` — public, opsiyonel API key
- **TRDizin Public API:** `https://search.trdizin.gov.tr/api/defaultSearch/publication/` — auth yok, JSON. Geliştirici dökümanı: https://development.trdizin.gov.tr/

**Card summary üretimi (sorgu dilinde):**

- S2 papers: Gemini Flash 2.0 prompt → "Bu abstract'ı 1-2 cümlede `{lang}` akademik özet" (lang ∈ tr/en/id); cache `q:card_summary:{paper_id}:{lang}` 30g
- TRDizin papers (lang==tr): native `abstract.tr` field doğrudan kullanılır (LLM çağrısı yok)
- EN/ID query: TRDizin atlanır, S2 50; S2 abstract sorgu dilinde özetlenir

---

## TIER DAVRANIŞI

### Anon (T0)

- Range chip: `3` aktif (default), `20/50` → 🔒 + paywall modal
- Sorgu limiti: günlük 3 (IP-rate, badge'de canlı sayaç)
- Action bar Q1/Q2/Q3 → paywall modal
- "Projeme Dönüştür" → capture modal (waitlist insert)

### Pro

- Range chip: 3/20/50 hepsi aktif
- Sorgu limiti: F2'de netleşir (placeholder: 1000/gün)
- Action bar Q1/Q2/Q3 → `router.push("/q1?qid=...")` direkt
- "Projeme Dönüştür" → kayıtlı user için proje yarat akışı (F2'de detaylı)

---

## AÇIK SORULAR

**Yok — %100 plan.** F2'de netleşecek 3 parametre (placeholder ile çözüldü, blokör değil):

- S2 API key (env: `S2_API_KEY`) — varsa rate limit yüksek, yoksa polite 1 req/sec
- Pro tier sorgu limiti (placeholder: 1000/gün)
- Trial token mekanizması (cookie vs Stripe vs pilot key)

---

## TEST KAPSAMI (gelecek implementasyon için)

- **Unit:** `q_search_service.test.py` — langdetect TR/EN/ID routing, S2 normalize, TRDizin normalize (sadece TR), cache hit/miss, native skor merge, `card_summary` dil tutarlılığı
- **Integration:** `test_q_search_endpoint.py` — `POST /api/q/search` happy path (TR → S2 30 + TRDizin 20; EN → S2 50; ID → S2 50), Anon range=50 → `paywall=true`, rate limit 4. sorguda 429
- **Smoke:** Live S2 + TRDizin tek-shot fixture (`tests/fixtures/q_search_v1.json`) — gerçek API yanıtı sabitlenir, regresyon koruması
- **Frontend:** Vitest — `useSearchPapers` mock response, paywall modal Anon davranışı, chip lock state, capture modal submit
