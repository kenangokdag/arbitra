# V1-S10 — Vitrin Tek Sayfa (Q + Embedded Literatür Özeti)

**Sub-sprint kodu:** V1-S10
**Önkoşullar:** V1-S8 ✅ KAPANDI (PR #24, 2026-05-09) — useQ pattern hazır
**Plan tarihi:** 2026-05-09
**Tek doğruluk kaynağı:** Bu manifest
**Revize:** Omer 2026-05-09 — "vitrin temiz olsun. sadece sorgu literatür incelemesi yeterli"

---

## §0 — Amaç

Vitrin'i 6 sayfadan **tek sayfa**'ya indir: `/q`. Akış: kullanıcı sorgu yazar → 25 makale listelenir → seçer (free=3, pro=tümü) → "Literatür Özeti Üret" → aşağıda **akademik makale formatlı** özet açılır.

Q1, Q2, Q3, Q4, Q5 sayfaları + ilgili tüm backend endpoint kodları **silinir** (ölü kod kalmaz).

---

## §1 — Mevcut durum (envanter — SİLİNECEK)

### Frontend (silinir)

- `web/src/app/(app)/q1/` — Q1 Literatür Özeti sayfası
- `web/src/app/(app)/q3/` — Q3 Metod Önerisi sayfası
- ~~`web/src/app/(app)/q2/`~~ — yok zaten (placeholder backend tarafında)
- ~~`web/src/app/(app)/q4/`, `q5/`~~ — branch'te silindi (abandon)
- `web/src/lib/q1-api.ts` + `q3-api.ts` (+ test'leri)
- `web/src/lib/q1-fixture.ts` (+ test'i)
- `web/src/hooks/useLiteratureSummary.ts` + `useMethodSuggestion.ts` (+ test'leri)
- `web/src/components/q1/*` + `web/src/components/q3/*` (ActionBar, MethodSuggestionList, SampleHintBlock)

### Backend (silinir)

- `api/routes/q.py:251-361` — Q3 (`/api/q3`), Q4 (`/api/q4`), Q5 (`/api/q5`) endpoint'leri
- `api/models/q.py` — Q3Request/Response, Q4Request/Response, Q5Request/Response, CitationFormat, SampleAlternative, SampleHint, Q3Suggestion, Q3SuggestionLLM, MethodTag StrEnum
- `api/services/role_modules/vitrin_method.py` + `vitrin_paraphrase.py`
- `api/services/citation_formatter.py` (+ test'leri)
- `api/middleware/tier_gate.py` — `QUOTA` dict'inden `/api/q3`, `/api/q4`, `/api/q5` satırları
- `tests/integration/test_q_routes.py` — Q3/Q4/Q5 ilgili testler

### Backend (refactor)

- `/api/q1` endpoint adı **değişir** → `/api/q/literature-review`
- Kontrat değişir: `query` → `paper_ids: list[str]` (kullanıcının seçtikleri)
- `vitrin_literature` brief revize: tek paragraf ~400 kelime → **akademik makale formatı** (4 bölüm + kaynaklar)
- `LiteratureSummaryLLM` Pydantic model **revize** (yeni structured schema)

### Sidebar

- `web/src/lib/nav-config.ts:51-56` — Vitrin pages 4 satır → **1 satır** ("Hızlı İnceleme" tek)

---

## §2 — Yeni Q sayfa UX (KD-V1-S10-04)

```
┌─────────────────────────────────────────────────────────┐
│ Vitrin · Q  ›  Hızlı İnceleme            [Tier badge]   │
├─────────────────────────────────────────────────────────┤
│ Konunu yaz, makaleleri seç, literatür özetini al.       │
│                                                          │
│ [🔍 Anahtar kelime / soru / DOI...           ] [Ara →]  │
├─────────────────────────────────────────────────────────┤
│ 25 makale · alaka sırasıyla                              │
│ Free: en fazla 3 makale seçebilirsin (giriş yap → tümü) │
│                                                          │
│ ☐ [01] Attention Is All You Need                         │
│       Vaswani A. et al. · NeurIPS, 2017 · 50000 atıf    │
│       Abstract...                                        │
│                                                          │
│ ☑ [02] BERT: Pre-training of Deep Bidirectional...      │
│       Devlin J. et al. · NAACL, 2019 · 75000 atıf       │
│       Abstract...                                        │
│ ...                                                      │
│                                                          │
│ Seçili: 1/3       [Literatür Özeti Üret →]              │
├─────────────────────────────────────────────────────────┤
│ ▾ Literatür Özeti (panel açılır, 4 bölüm makale formatı)│
│                                                          │
│   1. Giriş                                               │
│   ...                                                    │
│   2. Mevcut Çalışmalar                                   │
│   ...                                                    │
│   3. Tartışma                                            │
│   ...                                                    │
│   4. Sonuç                                               │
│   ...                                                    │
│   Kaynaklar                                              │
│   [01] Vaswani A. et al. (2017)...                       │
│   ...                                                    │
└─────────────────────────────────────────────────────────┘
```

---

## §3 — Yol kararları

### KD-V1-S10-01 — 25 makale liste (sabit)

OpenAlex polite-pool 25 makale çek. Eski tier-bazlı limit (anon=3, authed=5) kalkar. Sebep: kullanıcı seçim yapacak; 3-5 az, 25 yeterli envanter.

### KD-V1-S10-02 — Seçim limiti tier-bazlı

- **Anon (free):** max 3 makale (UI disable 4. seçimde)
- **Authed (pro):** tümü (25). Backend `paper_ids` body'de validate.

V1-S5 canon'da 3 authed tier (ogrenci/arastirmaci/profesyonel) aynı kota; "pro" = giriş yapan = authed_tiers (3 tier toplam).

### KD-V1-S10-03 — "Literatür Özeti Üret" butonu (otomatik DEĞİL)

Her seçimde otomatik LLM call YASAK (kota patlar). Buton:
- ≥1 seçim olmadan disabled
- Tıklayınca → mutation tetiklenir → loading → panel açılır

### KD-V1-S10-04 — Akademik **literatür inceleme bölümü** (revize 2026-05-09)

**Revize sebebi:** İlk versiyonda title + 4 alt-bölüm (introduction / current_studies /
discussion / conclusion) + numaralı references = komple akademik makale çıktısı
yazılmıştı. Omer browser smoke'ta düzeltti: "bir makale düşün, literatür inceleme
bölümü 1-1.5 sayfa olur, çok abartılmaz". Çıktı tek blok prose; per-paper scale.

Çıktı kontratı (LLM structured output):

```python
class LiteratureReviewLLM(BaseModel):
    content: str  # 50-5000 char, tek blok prose
    references: list[Reference]  # numaralı, APA-style

class Reference(BaseModel):
    index: int  # [01], [02]
    citation: str  # "Vaswani, A. et al. (2017). Attention Is All You Need. NeurIPS."
```

**Uzunluk sözleşmesi:** Per-paper ~30-40 kelime (~2 satır) yoğun sentez.
- N=1 → ~30 kelime (tek kaynak odaklı)
- N=12 → ~400 kelime (~1 sayfa)
- N=25 → ~750 kelime (~1.5 sayfa)

Hard cap yok; uzunluk N ile lineer ölçeklenir. Akademik üçüncü tekil; başlık /
alt-bölüm / "ben/biz" yasak; cümle içi cite [NN] format zorunlu.

**Frontend render:** Tek `<article>` — header "Literatür İncelemesi" etiketi +
`<p>` content (crimson, leading-relaxed, max 70ch) + numaralı `<ol>` references.
Eski 4-Section component silindi.

### KD-V1-S10-05 — Eski endpoint'leri komple sil (ölü kod yasak)

`api/routes/q.py`'den Q3/Q4/Q5 fonksiyonları + ilgili modeller + role_modules + service'ler **silinir**. `LOCKED_SOON_PATHS` veya backwards-compat shim YOK. Git history zaten saklar; geri lazım olursa cherry-pick.

### KD-V1-S10-06 — `/api/q1` adı değişir → `/api/q/literature-review`

`/api/q1` Q1 sayfası kalkıyor; ad anlamsız. Yeni canon: `/api/q/literature-review`. Body kontratı:

```python
class LiteratureReviewRequest(BaseModel):
    paper_ids: list[str] = Field(min_length=1, max_length=25)  # OpenAlex IDs
    lang: Lang = "tr"
```

`/api/q1` yolu **silinir**, redirect/alias yok (vitrin sadece bizim, breaking change güvenli).

### KD-V1-S10-07 — Liste üstü filtreler + Tümünü Seç + sıralama (eklendi 2026-05-09)

**Ek sebep:** Omer talebi — "üstte tümünü seç işareti ve filtreler koy. makaleye uygun
ulaşılabilecek verilere dayalı filtre koy. başla, sıralama da koyalım."

**Veri kaynağı kuralı:** Filtre sadece `PaperPreviewApi`'de hâlihazırda var olan
field'lardan kurulur (`year`, `citedByCount`, `abstract`). Yeni backend field
yok; round-trip yok — istisna: yıl backend filter (OpenAlex'in `from_publication_date` /
`to_publication_date` parametresi).

**4 filtre + Tümünü Seç + sıralama:**

| # | Kontrol | Tip | Etki |
|---|---|---|---|
| F1 | Yıldan / Yıla (iki number input arama formu içinde) | Backend | `/api/q` POST body'sine `year_from`/`year_to` ekler; submit'te re-query, queryKey değişir |
| F2 | Min atıf (number input) | Frontend (pure) | `applyLocalFilters.minCitations` — eşik altı liste dışı |
| F3 | Sadece abstract'ı olanlar (checkbox) | Frontend (pure) | `applyLocalFilters.hasAbstractOnly` — `abstract == null` atılır |
| F4 | Sıralama (radio: alaka / atıf↓ / yıl↓) | Frontend (pure) | `relevance` = backend sırası korunur, `citations_desc` / `year_desc` re-sort |
| SA | Tümünü Seç (üst satır checkbox + indeterminate) | UI | `selectAllClamped(visible, maxSelect)` — anon=3, authed=25 clamp; tekrar tıklayınca temizler |

**Pure helper kontratı** (`web/src/lib/q-filters.ts` — testlenebilir):

```typescript
type SortMode = "relevance" | "citations_desc" | "year_desc";
type LocalFilters = { minCitations: number; hasAbstractOnly: boolean; sort: SortMode };

applyLocalFilters(papers: PaperPreviewApi[], filters: LocalFilters): PaperPreviewApi[]
selectAllClamped(visible: PaperPreviewApi[], maxSelect: number): Set<string>
isAllVisibleSelected(visible: PaperPreviewApi[], selected: Set<string>, maxSelect: number): boolean
```

`useQ` arg'ları `yearFrom?: number; yearTo?: number` ile genişler; queryKey'e dahil
(yıl değişince yeni network request).

**UX sırası:**
- Yıl input'ları arama formu içinde (Ara butonuna basınca backend'e gider)
- Diğer filtreler + sıralama + Tümünü Seç bar'ı sonuç listesinin **üstünde**
- Tümünü Seç işaretlenince sonuç listesindeki ilk N (anon=3, authed=25) seçilir;
  tekrar tıklayınca temizlenir; karma durumda HTML `indeterminate` flag

---

## §4 — Atomic commit boundary

| # | Commit | Dosya | LOC | Test |
|---|---|---|---|---|
| V1-S10-01 | `chore: vitrin ölü kod silme (Q1/Q2/Q3/Q4/Q5 frontend + Q3/Q4/Q5 backend)` | Yukarıda §1 SİLİNECEK listesinin tamamı + sidebar nav-config tek satır | -2500 (silme) | mevcut testler PASS (kalan suite) |
| V1-S10-02 | `feat(api): /api/q/literature-review endpoint (paper_ids + makale formatı)` | `api/routes/q.py` (yeni endpoint) + `api/models/q.py` (yeni `LiteratureReviewRequest/Response`, `LiteratureReviewLLM`, `Reference`) + `api/services/role_modules/vitrin_literature.py` (brief revize 4 bölüm) + `api/middleware/tier_gate.py` (yeni endpoint quota) + `tests/integration/test_q_routes.py` (yeni test) | ~350 | integration + canlı LLM smoke |
| V1-S10-03 | `feat(web): /q tek sayfa rewrite (25 makale + checkbox seçim + literatür özeti panel)` | `web/src/app/(app)/q/page.tsx` (rewrite) + `web/src/lib/q-api.ts` (limit=25) + `web/src/lib/lit-review-api.ts` (yeni) + `web/src/hooks/useLitReview.ts` (yeni, useMutation) + testler (4+ vitest) | ~600 | vitest hook + adapter + manuel smoke |
| V1-S10-04 | `docs: V1 vitrin sprint kapanış (V1-S9 revert + V1-S10 KAPANDI)` | `docs/plans/V1_vitrin_sprint.md` (§A revize) | ~30 | — |
| V1-S10-05 | `fix(api,web): literatür özeti makale değil bölüm — single content (~30-40 kelime/kaynak)` | `api/models/q.py` + `api/routes/q.py` + `api/services/role_modules/vitrin_literature.py` + `web/src/lib/lit-review-api.ts` + `web/src/app/(app)/q/page.tsx` ReviewPanel | ~120 | mevcut suite + browser smoke |
| V1-S10-06 | `feat(web): /q liste üstü filtreler + Tümünü Seç + sıralama (KD-V1-S10-07)` | `web/src/lib/q-filters.ts` (yeni pure helper) + `web/src/lib/q-filters.test.ts` + `web/src/hooks/useQ.ts` (yearFrom/yearTo) + `web/src/hooks/useQ.test.tsx` (+1 test) + `web/src/app/(app)/q/page.tsx` (filter bar + select-all) | ~350 | vitest pure helper + hook + tsc + browser |

**Toplam:** -2500 silme, ~1500 yeni LOC. Net -1000.

---

## §5 — Backend kontrat

### `/api/q` (mevcut, sadece limit değişir)

```python
@router.post("/q", response_model=QResponse)
async def q(req: QRequest, ...) -> QResponse:
    papers = await search_papers(req.query, limit=25, ...)  # 3/5 → 25 sabit
```

### `/api/q/literature-review` (yeni — KD-V1-S10-04 revize 2026-05-09)

```python
class LiteratureReviewRequest(BaseModel):
    paper_ids: list[str] = Field(min_length=1, max_length=25)
    lang: Lang = "tr"

class Reference(BaseModel):
    index: int
    citation: str

class LiteratureReviewLLM(BaseModel):
    content: str = Field(min_length=50, max_length=5000)  # tek blok prose
    references: list[Reference]                            # numaralı, APA-style

class LiteratureReviewResponse(BaseModel):
    review: LiteratureReviewLLM
    quota_remaining: int
    quota_reset: str
```

Anon kotası: max 3 paper_ids (backend validate); authed: max 25.

---

## §6 — Frontend kontrat

```typescript
// q-api.ts (mevcut, limit=25)
export type QResponseApi = { papers: PaperPreviewApi[]; quotaRemaining: number; quotaReset: string };

// lit-review-api.ts (yeni — KD-V1-S10-04 revize 2026-05-09)
export type ReferenceApi = { index: number; citation: string };
export type LiteratureReviewApi = {
  content: string;
  references: ReferenceApi[];
};
export type LitReviewRequest = { paperIds: string[]; lang?: "tr" | "en" | "id" };
export type LitReviewResponseApi = {
  review: LiteratureReviewApi;
  quotaRemaining: number;
  quotaReset: string;
};

export async function generateLitReview(req: LitReviewRequest, signal?): Promise<LitReviewResponseApi>;
```

`useLitReview` → `useMutation<LitReviewResponseApi, Error, LitReviewRequest>`.

---

## §7 — Test piramidi

| Katman | Dosya | Senaryo |
|---|---|---|
| Backend integration | `tests/integration/test_q_routes.py` | (a) `/api/q/literature-review` happy path, (b) anon paper_ids>3 → 403, (c) authed paper_ids=25 → 200, (d) paper_ids boş → 422 |
| LLM unit | `tests/unit/test_role_modules.py` | `vitrin_literature` brief 4 bölüm + references çıktısı schema valid |
| Q1 backend test SİL | `tests/integration/test_q1_*` | mevcut Q1 testleri silme |
| Q3/Q4/Q5 backend test SİL | `tests/integration/test_q_routes.py` Q3/Q4/Q5 senaryoları | silme |
| Frontend hook | `useLitReview.test.tsx` | idle, mutate→success, error 403, paperIds boş gönderilmez |
| Frontend adapter | `lit-review-api.test.ts` | snake_case body `paper_ids`, snake→camel response, references array passthrough |
| Frontend pure (V1-S10-06) | `q-filters.test.ts` | applyLocalFilters min cite + has-abstract + sort modları + kombinasyon; selectAllClamped clamp; isAllVisibleSelected true/false/empty |
| Frontend hook (V1-S10-06) | `useQ.test.tsx` | yearFrom/yearTo verilince fetchQ'ya iletilir |
| Manuel browser | `/q` | (a) sorgu → 25 makale, (b) free 3 limit + 4. tıkta disabled, (c) "Literatür Özeti Üret" → tek blok özet + numaralı kaynak panel açılır, (d) sidebar Vitrin tek satır, (e) yıl filter submit'te yeni network request, (f) min cite + has-abstract anlık liste daraltır, (g) Tümünü Seç clamp'e uyar (anon=3) |

---

## §8 — Sınırlar (kapsam DIŞINDA)

- ❌ Q1, Q2, Q3, Q4, Q5 backwards-compat (404 olsun)
- ❌ Multi-language özet (tr/en/id altyapısı kalır ama V1'de sadece tr test)
- ❌ Save/export literatür özeti (V2)
- ❌ Pro tier'lar arasında ayrı kota (V1-S5 canon: 3 authed tier aynı, V2'de ayrıştırma)
- ❌ Paper detail page (Q sayfasında abstract preview yeter)
- ❌ Citation export (BibTeX/RIS) — Q5 zaten silindi

---

## §9 — Riskler

| # | Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|---|
| 1 | Pro 25 paper LLM context patlar | Düşük | Orta | Gemini Flash 1M context, 25*500≈12.5K token OK; UI'de "uzun bekleme" loader |
| 2 | LLM 4 bölüm structured output uyumsuz | Orta | Orta | `structured_output_schema=LiteratureReviewLLM` + retry 2x (Q1 paterni); fail → 502 |
| 3 | Q1/Q3 silme regression — başka kod ref ediyor mu? | Orta | Yüksek | Silme öncesi `Grep` zorunlu; ref bulunursa update (chat sayfası, project routes vs.) |
| 4 | Anon paper_ids>3 backend validation atlanır → kota bypass | Düşük | Orta | Backend tier-aware validate, frontend ek kontrol |
| 5 | Sidebar tek satır = sayfa hissi boş | Düşük | Düşük | Sidebar'da "Vitrin · Hızlı İnceleme" yeterli; diğer workbench'ler zaten görünür |

---

## §10 — DoD

- [ ] V1-S10-01: ölü kod silindi (frontend + backend), tüm kalan testler PASS
- [ ] V1-S10-02: `/api/q/literature-review` endpoint çalışıyor (canlı LLM smoke)
- [ ] V1-S10-03: `/q` sayfası 25 makale + checkbox + buton + 4 bölüm panel
- [ ] V1-S10-04: sprint manifest §A güncel (V1-S9 revert + V1-S10 KAPANDI)
- [ ] tsc clean, `npx next build` exit 0, vitest tüm suite PASS
- [ ] Manuel browser: sorgu yap → 25 makale → 3 seç → buton → akademik makale formatlı özet
- [ ] Sidebar Vitrin grubunda **tek** "Hızlı İnceleme" satırı
- [ ] PR #25 açık + Omer browser onayı + squash merge
- [ ] V1 vitrin sprint **YENİDEN KAPANDI** — 1 sayfa (Q embedded literatür özeti)

---

## §11 — Onay sinyali

Plan onaylandı sayılır:
- Omer "V1-S10 başla" der **veya**
- Omer "tek sayfa onaylı" der

Tek "evet"/"tamam" plan onayı sayılmaz (CLAUDE.md §0).

---

## §12 — Sıradaki adım (onay sonrası)

V1-S10-01: yeni branch `v1-s10-vitrin-tek-sayfa` (main'den), önce `Grep` ile silinecek dosyaların başka yerden ref edilmediğini doğrula, sonra silme commit'i.
