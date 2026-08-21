# V1-S3 — Q1 Literatür Özeti wire (frontend ↔ backend)

**Sub-sprint kodu:** V1-S3
**Önkoşullar:** V1-S2 ✅ (Q1 frontend kabuk, PR #18 merged), V1-S5 ✅ (4-tier canon, PR #19), V1-S4 ✅ (waitlist, PR #20)
**Plan tarihi:** 2026-05-09
**Tek doğruluk kaynağı:** Bu manifest + `Page_Design/Sayfa_Plani_v1/C_vitrin/q1.md` (canon sözleşme)

---

## §0 — Amaç

Q1 sayfasının fixture'ını gerçek backend'e bağla: Q'dan miras kalan sorgu için K paper + literatür özeti üret, Q1 frontend'i fetch'e geçir. Pilot funnel ana değer ekranını yaşat.

---

## §1 — Mevcut durum (envanter)

**Frontend (`web/src/app/(app)/q1/page.tsx`)** — V1-S2 PR #18 ile geldi:
- `useTierMock()` hook (anon/ogrenci/arastirmaci/profesyonel)
- Fixture: `Q1_FIXTURE_PAPERS` (3 kart) + `Q1_FIXTURE_SUMMARY` (literature summary obj)
- TODO satırı (`page.tsx:94`): `// TODO(V1-S3): swap fixture for fetch('/api/q/literature', { qid })`
- Anon → `<PaywallPlaceholder>` (3 kart + 2 CTA), Pro → `<LiteratureSummary>` (3 kart + ~400 word + citation sync)

**Backend (`api/routes/q.py:77-120`)** — V1-S5 ile geldi:
- `POST /api/q1` — `Q1Request{query, year_from, year_to, lang}` → 5 paper + her paper için 2-cümle `mini_summary`
- LLM: `llm_service.call(prompt, tier="flash", mode="vitrin_summary")`
- Per-paper LLM call (5 LLM çağrısı/request)
- Tier gate var, Redis cache YOK

**Sözleşme uyumsuzluğu (kritik):**
- Frontend canon (`q1.md`): `POST /api/q/literature {query_id}` → Redis havuzdan K=12 paper + tek `summary_text` (~400 kelime) + `citations[]` map
- Backend mevcut: `POST /api/q1 {query, ...}` → 5 paper + per-paper mini_summary
- Q endpoint Redis'e havuz yazmıyor — `query_id` miras mekanizması mevcut değil

---

## §2 — Scope kararı

İki seçenek; tek doğru cevap yok, trade-off var.

### Scope A — Minimal pilot wire (önerilen)

Q1 frontend'i mevcut `/api/q1`'e bağla, en küçük değişiklikle çalıştır.

- Backend: `/api/q1` response shape'i Q1 frontend'in beklediği şekle yakınlaştır (papers + tek aggregate summary alanı eklenir)
- LLM: tek Gemini Flash çağrısı — `K paper abstract → 1 literatür özeti + citation map` (per-paper döngü değil, tek prompt)
- K = 3 (anon paywall) / 12 (authed) — sadece authed için LLM çalışır
- Cache YOK (V1 prototip), Redis miras YOK
- Pydantic structured output ile citation grounding (rank dışı paper_id reject)
- Frontend: `useLiteratureSummary` hook (TanStack Query) yazılır, fixture replace
- Tier mapping: `anon` → paywall response (papers + summary=null), `ogrenci/arastirmaci/profesyonel` → full
- Dil: prompt language Q'dan miras (`req.lang`); prompt 3 dil için switch

**LOC tahmini:** backend ~140 (route revize + Pydantic genişletme + structured output validator), frontend ~80 (hook + page swap)
**Süre:** 1 gün
**Risk:** Düşük — mevcut Gemini Flash hattı çalışıyor (V1-S5 smoke PASS)

### Scope B — Canon q1.md uygulanması

Tam canon — `/api/q/literature` yeni endpoint + Q havuzu Redis cache + 2-stage rerank.

- Backend: yeni `/api/q/literature` endpoint + `q_literature_service.py` + Q endpoint Redis pool yazımı (~250 LOC)
- 2-stage rerank: native skor (50→25) + Gemini Flash structured output (25→12) + literature summary üretimi (3 LLM call/request)
- Frontend: aynı (~80 LOC)

**LOC tahmini:** backend ~350, frontend ~80
**Süre:** 2-3 gün
**Risk:** Orta — Redis dev ortamında graceful degrade pattern doğrulama + 2-stage rerank prompt iterasyonu

### KD-V1-S3-01: Scope A önerilir

**Neden:**
- V1 ethos: prototip + 5 user pilot; 1-stage rerank yeterli sinyal verir
- LLM maliyet: Scope B 3× call/request, Scope A 1× call/request
- Frontend canon API path (`/api/q/literature`) cosmetic — Scope A'da `/api/q1` korunur, frontend hook URL'si değişir
- Q havuzu Redis miras: V2 işidir, V1'de query yeniden çağırılır (cache miss tolere edilir, latency 2-3s kabul)

**Scope B'ye terfi:** pilot 5 user feedback'inde "rerank kalitesi yetersiz" sinyal gelirse V2'de yapılır.

---

## §3 — Atomic commit boundary (Scope A varsayımı)

| # | Commit | Dosya | LOC | Test |
|---|---|---|---|---|
| V1-S3-01 | `feat(api): /api/q1 literature summary single-call + citation grounding` | `api/routes/q.py` (revize) + `api/models/q.py` (Q1Response genişletme: `papers max_length=5 → 12` + `CitationMap` yeni + `summary_text/citations/used_paper_ids` field'ları) + `api/services/role_modules/vitrin_literature.py` (yeni — prompt builder + parser + rank validator) + `tests/integration/test_q1_routes.py` (yeni) | ~140 | unit Pydantic validator + integration mock LLM + canlı Gemini smoke |
| V1-S3-02 | `feat(web): useLiteratureSummary hook + Q1 page wire + Q→Q1 query forward` | `web/src/hooks/useLiteratureSummary.ts` (yeni) + `web/src/app/(app)/q1/page.tsx` (fixture → hook, qid→q param) + `web/src/lib/q1-api.ts` (yeni client + backend↔frontend adapter) + `web/src/app/(app)/q/page.tsx` (ActionButton href: `/q1?q={submitted}` — Risk #5 mitigasyonu) + `web/src/hooks/useLiteratureSummary.test.tsx` | ~120 | Vitest hook + manuel browser smoke |
| V1-S3-03 | `docs(v1): mark V1-S3 KAPANDI in sprint manifest` | `docs/plans/V1_vitrin_sprint.md` §A | ~2 | — |

**Atomik kuralı:** her commit'te tsc + ruff + mypy + ilgili test PASS. V1-S3-01 olmadan V1-S3-02 ship edilmez.

---

## §4 — Backend sözleşme (Scope A)

```python
# api/models/q.py (genişleme)

class CitationMap(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sentence_idx: int = Field(ge=0)
    paper_ids: list[str] = Field(min_length=1)  # rank string "01".."12"

class Q1Response(BaseModel):  # mevcut response, alanlar eklenir
    model_config = ConfigDict(extra="forbid")
    papers: list[PaperPreview] = Field(max_length=12)  # REVİZE — eski max_length=5 (K=12 için artırılır)
    summary_text: str | None                # YENİ — Pro: ~400 kelime, anon: None
    citations: list[CitationMap] | None     # YENİ — Pro: cümle→paper map, anon: None
    used_paper_ids: list[str] | None        # YENİ — Pro: ["01".."12"], anon: None
    quota_remaining: int                    # MEVCUT
    quota_reset: str                        # MEVCUT
```

> **Migration not (V1-S3-01 commit):** `api/models/q.py:70` — `Q1Response.papers` field'ında `Field(max_length=5)` → `Field(max_length=12)`. `QResponse.papers` (Q endpoint, `api/models/q.py:52`) `max_length=5` KORUNUR (Q anon=3, authed=5 sözleşmesi değişmiyor).

**Akış (authed-only — V1-S5 canon: `/api/q1` anon=401):**
1. `tier_gate` check → quota (anon → 401; frontend fixture path tetiklenir, backend hiç çağırılmaz)
2. OpenAlex search (limit=12)
3. Tek Gemini Flash call → structured output `{summary_text, citations, used_paper_ids}` → validator (`citations[i].paper_ids ⊆ used_paper_ids ⊆ rank_strings_we_provided`)
4. Validator FAIL → 1 retry; ikinci FAIL → 502 `empty_llm_output`

> **KD-V1-S3-02 — anon-path backend YOK:** Q1 endpoint anon kabul etmez (V1-S5 canon korunur). Anon Q1 sayfasında `<PaywallPlaceholder>` + V1-S2 fixture (3 kart) gösterir; `useLiteratureSummary` hook `enabled = tier !== "anon"` ile fetch atmaz.

**Prompt template (TR örnek):**
```
Aşağıdaki K akademik makaleyi sorgu "{query}" bağlamında değerlendirip
~400 kelimelik akademik literatür özeti yaz. Türkçe yaz.

Her cümle en az bir makaleye dayanmalı; cümle sonunda [01]..[12] formatında
rank-alıntısı koy. Halüsinasyon yasak — abstract'larda olmayan iddia yazma.

[01] {title_1}\nAbstract: {abs_1}\n\n[02] ...

JSON şemasında dön: { summary_text, citations, used_paper_ids }
```

**LLM service tarafı:** `llm_service.call(...)` zaten `mode="vitrin_literature"` desteklemiyor — yeni mode + role_module dosyası eklenir (`api/services/role_modules/vitrin_literature.py`). Pattern referansı: mevcut `vitrin_summary.py`.

---

## §5 — Frontend sözleşme

```typescript
// web/src/lib/q1-api.ts (yeni)
export type Q1LiteratureRequest = { query: string; lang: "tr" | "en" | "id"; year_from?: number; year_to?: number };
export type Q1LiteratureResponse = {
  papers: PaperPreview[];
  summary_text: string | null;
  citations: { sentence_idx: number; paper_ids: string[] }[] | null;
  used_paper_ids: string[] | null;
  quota_remaining: number;
  quota_reset: string;
};
export async function fetchQ1Literature(req: Q1LiteratureRequest): Promise<Q1LiteratureResponse>;

// web/src/hooks/useLiteratureSummary.ts (yeni)
export function useLiteratureSummary(args: { query: string; lang: string; enabled: boolean }) {
  return useQuery({ queryKey: ["q1-literature", args.query, args.lang], queryFn: () => fetchQ1Literature(...), enabled, staleTime: 5*60*1000 });
}
```

Q1 page.tsx değişiklik:
- `qid` URL paramı → `query` URL paramı (q.md envanter ile uyum: Q sayfası `/q1?q={query}` yönlendirir)
- **Authed path:** fixture import'ları sil → `useLiteratureSummary({ query, lang, enabled: tier !== "anon" })`; loading/error state Suspense + Error boundary'e bırakılır
- **Anon path:** hook `enabled=false` → backend'e fetch atmaz; `<PaywallPlaceholder>` + V1-S2 fixture (`Q1_FIXTURE_PAPERS` 3 kart) korunur. KD-V1-S3-02 gereği backend anon-path YOK.

**Fixture dosyaları:** silinmez, integration test kaynağı olarak `tests/fixtures/q1_v1.json`'a taşınır (Vitest'te hook mock kaynağı).

---

## §6 — Test piramidi

| Katman | Dosya | Senaryo |
|---|---|---|
| **Backend unit** | `tests/unit/test_q1_validator.py` (yeni, ~30 LOC) | citation rank ⊆ used_paper_ids; rank dışı reject; min/max length |
| **Backend integration** | `tests/integration/test_q1_routes.py` (yeni, ~80 LOC) | (a) anon → papers+summary=null, (b) authed mock LLM → full response, (c) LLM fail → 502, (d) tier_gate 401/403/429 path'leri |
| **Backend smoke** | `tests/fixtures/q1_v1.json` (yeni) | Canlı Gemini Flash TR+EN+ID 3 fixture (regresyon koruması, manuel re-record) |
| **Frontend** | `web/src/hooks/useLiteratureSummary.test.ts` (yeni) | TanStack mock — anon vs authed response render |
| **Manuel browser** | `/q1?q=akıllı şehir trafik` (TR), `/q1?q=transformer attention` (EN) | Sol panel kartları + sağ özet + citation hover/click sync |

---

## §7 — Sınırlar (kapsam DIŞINDA)

- ❌ Redis Q havuzu cache (canon Scope B — V2)
- ❌ 2-stage rerank (canon Scope B — V2)
- ❌ `query_id` miras mekanizması (V1'de query string yeniden çağırılır)
- ❌ `/api/q/literature` ayrı endpoint adı (V1'de `/api/q1` korunur, V2'de rename)
- ❌ Multi-LLM ayrışması (Cosmos/Qwen) — V2
- ❌ PaywallModal Stripe akışı — `handleTrialClick` console.info kalır
- ❌ CaptureModal — `handleCaptureClick` mevcut WaitlistModal'a (V1-S4) bağlanır mı? **EVET — bonus**, ek 5 LOC

---

## §8 — Riskler

| # | Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|---|
| 1 | Gemini Flash structured output JSON malformed (markdown fence vb) | Orta | Orta | `llm_service.call` zaten global fence strip yapıyor (V1-S5 dersi); validator FAIL→1 retry |
| 2 | Citation grounding zayıf — model rank dışı paper id uydurur | Düşük | Düşük | Validator reject + retry; pilot feedback ile prompt iterasyon |
| 3 | OpenAlex 12 paper rate limit (polite pool 100K/gün) | Çok düşük | Düşük | Pilot 5 user × 50 query/gün = 250 << 100K |
| 4 | TanStack `enabled=false` anon path için bug — anon sayfasında network call atılır | Düşük | Düşük | Hook test ile kanıt |
| 5 | Q1 page'in `qid` → `query` paramı geçişi Q sayfasının link'ini bozar | Yüksek | Düşük | Q sayfasını da güncelle: `/q1?q={query}&lang={lang}` |

---

## §9 — Onay sinyali

Plan onaylandı sayılır:
- Omer "V1-S3 başla" der **veya**
- Omer "Scope A onaylı" der

Aksi halde plan revize.

---

## §10 — Kapanış kriterleri

- [ ] V1-S3-01 commit + tests PASS + canlı Gemini smoke (TR+EN+ID 3 fixture)
- [ ] V1-S3-02 commit + Vitest hook PASS + manuel browser smoke (anon paywall path + authed full path)
- [ ] V1-S3-03 commit + V1_vitrin_sprint.md §A "V1-S3 ✅ KAPANDI" işareti
- [ ] PR açık + CI yeşil + merge
- [ ] V1 vitrin sprint TAMAMEN KAPALI (S2 + S3 + S4 + S5 + S6/S7 hepsi merged)
