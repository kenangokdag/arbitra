# V1-S8 — Q sayfası backend wire (OpenAlex preview)

**Sub-sprint kodu:** V1-S8
**Önkoşullar:** V1-S7 ✅ KAPANDI (PR #23, 2026-05-09) — Q1+Q3 wire pattern hazır
**Plan tarihi:** 2026-05-09
**Tek doğruluk kaynağı:** Bu manifest.

---

## §0 — Amaç

`/q` sayfasını `MOCK_PAPERS` hardcoded fixture'tan kurtar; gerçek `/api/q` (OpenAlex polite-pool) endpoint'ine bağla. Q1+Q3 ile aynı `useQuery` pattern.

**Sebep:** V1 sprint plan §2 Q satırı "anon 3 mk preview / authed 5 mk preview" diyor. V1-S2 frontend kabuk Q'yu mock bıraktı; V1-S3 sadece Q1'i, V1-S7 sadece Q3'ü bağladı. Q wire açık kaldı.

---

## §1 — Mevcut durum (envanter)

**Backend (`api/routes/q.py:49-75`):** `POST /api/q` ✅ hazır
- `QRequest`: `query` (2-500), `year_from`, `year_to`, `lang` (Pydantic forbid)
- `QResponse`: `papers: list[PaperPreview] (max 5)` + `quota_remaining` + `quota_reset`
- OpenAlex `search_papers(...)` → `PaperPreview[]` (id, doi, title, abstract, year, venue, authors:list[str], cited_by_count)
- Tier gate: anon=3/gün, authed=5/gün (`api/middleware/tier_gate.py`)

**Frontend (`web/src/app/(app)/q/page.tsx`):**
- `MOCK_PAPERS: Paper[]` hardcoded (line 29-58) — 3 fixture: Fuzzy AHP, Multi-criteria, TOPSIS
- `Paper` type (line 19-27): `id, title, authors:string, venue, year, citations, tr`
- `runSearch(q)` sadece `setSubmitted(q)` + URL replace; backend'e gitmiyor
- Q3 ActionButton zaten aktif (`/q3?q=...`) — V1-S7'den kalan, dokunulmuyor

**Adapter farkı:**
| Backend `PaperPreview` | Frontend `Paper` (eski mock) |
|---|---|
| `authors: list[str]` | `authors: string` (formatted) |
| `cited_by_count: int` | `citations: int` |
| `abstract: string \| null` | `tr: string` (Türkçe özet, mock'ta yazılmış) |

`tr` alanı backend'de yok → kaldırılır veya `abstract` ile değiştirilir.

---

## §2 — Yol kararları

### KD-V1-S8-01 — `tr` alanı kaldırılır

Backend Türkçe çeviri yapmıyor; Q sayfası anon hızlı önizleme (LLM YOK, plan §2). Mock'taki `tr` alanı kart altında "akademik özet" hissi veriyordu ama uydurma. Yerine `abstract`'tan ilk ~200 karakter veya boş.

### KD-V1-S8-02 — Authors formatlama frontend'de

Backend `list[str]` döndürür. Frontend adapter `[a, b, c]` → `"a; b; c"` (3'ten fazlaysa `"a et al."`). Q1 sayfasında aynı pattern var (`useLiteratureSummary` adapter'ında); reuse edilebilir veya kopyalanır.

### KD-V1-S8-03 — Empty-state + error/loading paterni Q1/Q3 ile simetri

Q1/Q3 sayfasında `Loading/Error/Empty` component üçlüsü var. Q için aynı pattern: kullanıcı sorgu girene kadar empty hint, fetch sırasında loading skeleton, hata `MethodError` benzeri kart.

### KD-V1-S8-04 — Q3 ActionButton aktivasyonu için `submitted` state korunur

Mevcut `submitted` state Q3 link'i için kullanılıyor (`/q3?q=${submitted}`). API response geldikten sonra da bu state ayakta kalır. Yani: arama başarılı olunca hem paper kartları hem ActionButton render edilir.

---

## §3 — Atomic commit boundary

| # | Commit | Dosya | LOC | Test |
|---|---|---|---|---|
| V1-S8-01 | `feat(web): /q page wire — useQ hook + OpenAlex preview` | `web/src/lib/q-api.ts` (yeni client + adapter) + `web/src/hooks/useQ.ts` (yeni TanStack hook) + `web/src/app/(app)/q/page.tsx` (MOCK_PAPERS sil → useQ hook + Loading/Error/Empty) + `web/src/hooks/useQ.test.tsx` (yeni) | ~150 | Vitest hook + manuel browser smoke |
| V1-S8-02 | `docs(v1): mark Q wire complete in sprint manifest` | `docs/plans/V1_vitrin_sprint.md` (§A V1-S8 kapanış satırı) | ~3 | — |

**Atomik kuralı:** V1-S8-01 olmadan V1-S8-02 yazılmaz. Test piramidi V1-S8-01 içinde.

---

## §4 — Frontend kontrat

### `web/src/lib/q-api.ts` (yeni)

```typescript
export type QLang = "tr" | "en" | "id";

export type QRequest = {
  query: string;
  yearFrom?: number;
  yearTo?: number;
  lang?: QLang;
};

type BackendPaperPreview = {
  id: string;
  doi: string | null;
  title: string;
  abstract: string | null;
  year: number | null;
  venue: string | null;
  authors: string[];
  cited_by_count: number;
  mini_summary: string | null;  // Q'da hep null
};

type BackendQResponse = {
  papers: BackendPaperPreview[];
  quota_remaining: number;
  quota_reset: string;
};

export type PaperPreviewApi = {
  id: string;
  doi: string | null;
  title: string;
  abstract: string | null;
  year: number | null;
  venue: string | null;
  authors: string[];      // raw list
  authorsLabel: string;   // "Liu, Y.; Zhang, W." veya "Liu, Y. et al."
  citedByCount: number;
};

export type QResponseApi = {
  papers: PaperPreviewApi[];
  quotaRemaining: number;
  quotaReset: string;
};

export async function fetchQ(req: QRequest, signal?: AbortSignal): Promise<QResponseApi>;
```

Adapter: snake_case → camelCase + `authorsLabel` türetimi (3'ten fazla → "first et al.").

### `web/src/hooks/useQ.ts` (yeni)

```typescript
export function useQ(args: { query: string; lang?: QLang; enabled: boolean }) {
  return useQuery<QResponseApi, Error>({
    queryKey: ["q", args.query, args.lang ?? "tr"],
    queryFn: ({ signal }) => fetchQ({ query: args.query, lang: args.lang }, signal),
    enabled: args.enabled && args.query.length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}
```

### `web/src/app/(app)/q/page.tsx` revize

- `MOCK_PAPERS` + local `Paper` type → **silinir**
- `useQ` hook eklenir; `enabled = submitted.length >= 2`
- Sonuç bandı `papers.map`: `PaperPreviewApi`'dan render (`title`, `authorsLabel · venue, year · citedByCount atıf`, `abstract` ilk 200 char)
- Loading: spinner + "Aranıyor..." (Q3 sayfasındaki `MethodLoading` paterni)
- Error: kart kırmızı + retry button (Q3 sayfasındaki `MethodError` paterni)
- Empty (henüz arama yapılmadı): mevcut "Yukarıya bir sorgu yaz veya örneklerden birini dene." dashed kart **kalır**
- Empty (sonuç 0): yeni dashed kart "Bu sorgu için makale bulunamadı"
- Q3 ActionButton href `/q3?q=${submitted}` **dokunulmuyor** (V1-S7'den kalan)

---

## §5 — Test piramidi

| Katman | Dosya | Senaryo |
|---|---|---|
| **Frontend hook** | `web/src/hooks/useQ.test.tsx` (yeni, ~80 LOC) | (a) enabled=false → no-call, (b) success → data render, (c) query<2 → no-call, (d) fetch error → isError |
| **Frontend adapter** | `web/src/lib/q-api.test.ts` (yeni, ~50 LOC) | (a) authors 4+ → "X et al.", (b) authors ≤3 → "; "-join, (c) authors boş → "—", (d) abstract>220 → truncate "…", (e) snake_case body |
| **Manuel browser** | `/q` → 3 farklı sorgu | (a) loading spinner, (b) 3-5 makale gerçek başlık (Fuzzy AHP YOK), (c) Q3 ActionButton hâlâ çalışıyor, (d) anon 4. sorgu → 429 hata kartı |

**Backend tarafında değişiklik yok** → mevcut `tests/integration/test_q_routes.py` Q senaryoları zaten geçiyor.

---

## §6 — Sınırlar (kapsam DIŞINDA)

- ❌ Q1 wire değişiklik (V1-S3'te ship edildi)
- ❌ Q3 wire değişiklik (V1-S7'de ship edildi)
- ❌ Year filter UI (`year_from`/`year_to` backend desteği var ama Q sayfasında range slider yok — V2)
- ❌ Authed `mini_summary` Q sayfasında (Q1 zaten authed mini-özet veriyor; Q anon-first preview)
- ❌ Backend yeni endpoint / yeni model
- ❌ Tier gate revize
- ❌ OpenAlex re-rank veya year boost (V2)

---

## §7 — Riskler

| # | Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|---|
| 1 | OpenAlex 503/timeout | Orta | Düşük | Backend zaten 503 + UI error kartı + retry button |
| 2 | Anon kota dev'de Redis yok → bypass | Düşük | Düşük | tier_gate Redis miss → log warn + allow (V1-S5 pattern) |
| 3 | TanStack cache aynı sorgu için stale → kullanıcı yenileme bekler | Düşük | Düşük | staleTime 5dk Q1/Q3 ile simetri; refetch button gerekirse V1-S9 |
| 4 | `abstract` çok uzun → kart bozulur | Orta | Düşük | İlk 200 char + "…" truncation frontend'de |

---

## §8 — DoD

- [ ] V1-S8-01 commit + Vitest PASS (useQ + page render)
- [ ] `tsc` clean
- [ ] `npx next build` exit 0
- [ ] Manuel browser smoke: `/q?q=transformer attention` → gerçek paper title (örn. "Attention Is All You Need" veya benzeri OpenAlex hit)
- [ ] Q3 ActionButton hâlâ çalışıyor (regresyon kontrolü)
- [ ] V1-S8-02 docs commit
- [ ] PR #24 açık + Omer browser onayı + squash merge

---

## §9 — Onay sinyali

Plan onaylandı sayılır:
- Omer "V1-S8 başla" der **veya**
- Omer "Q-wire onaylı" der

Tek "evet"/"tamam" plan onayı sayılmaz (CLAUDE.md §0).

---

## §10 — Sıradaki adım (onay sonrası)

V1-S8-01: yeni branch `v1-s8-q-wire` (main'den), `web/src/lib/q-api.ts` + `web/src/hooks/useQ.ts` ilk commit.
