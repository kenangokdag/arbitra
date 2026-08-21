# V1-S7 — Q3 Metod Önerisi backend (saf LLM, Yol C)

**Sub-sprint kodu:** V1-S7
**Önkoşullar:** V1-S6 ✅ (Q3 frontend kabuk, PR #18 merged), V1-S5 ✅ (4-tier canon, PR #19), V1-S3 ✅ (Q1 wire, PR #22)
**Plan tarihi:** 2026-05-09
**Tek doğruluk kaynağı:** Bu manifest. (Page_Design'daki q3.md eski Yol A canon'u — bu manifest onun yerini alır.)

---

## §0 — Amaç

Q3 sayfasının fixture'ını gerçek backend'e bağla. Sorgu metnini al, Gemini Flash'a "bu konuda hangi yöntem uygulanır?" diye sor, 3 metod önerisi + alternatifli sample hint döndür. **Paper search YOK, OpenAlex YOK, Redis havuzu YOK** — saf LLM önerisi.

---

## §1 — Yol C kararı (Yol A/B karşısında)

Page_Design `q3.md` Yol A'yı tarif eder: 50→25 rerank + per-paper classification + distribution chart + suggestion grounding. Bu canon **çıkarılır**.

### KD-V1-S7-01 — Yol C onaylanmıştır (Omer 2026-05-09)

> "bunu LLM ile yapsak nasıl olur? konu belli, o konuda hangi yöntem uygulanır sorusu sormuş olalım. ardından bize 3 öneri sunsun. halüsinasyon da olsa biz sadece öneriyoruz, ama gerekçesi ile birlikte"

Sebep:
- LLM'in en güçlü olduğu soru tipi (genel akademik bilgi)
- Paper-bağımlı doğrulama (DM-049 grounding) Q3 için aşırı; vitrin "öneri" katmanı, "kanıt" değil
- 1 LLM call vs 2 LLM call (classification + suggestion); maliyet ½
- Frontend de sadeleşir: distribution chart YOK, sol paper paneli YOK
- V1-S3 (Q1) zaten bağımsız endpoint pattern'i seçti — Q3 simetrik

### KD-V1-S7-02 — Sol paper paneli kalkar

Omer: "sol panel sidebar olarak kalsın zaten. bütün iş gövdede." → SidebarD9 (global navigation) korunur; **sayfa-içi `LeftPanelPapers` kaldırılır**. Q3 paper'a bağlı çalışmıyor; sol paper kart yanıltıcı olur.

### KD-V1-S7-03 — Anon kotalı erişim

Omer: "anon olsun ama kotalı." → `/api/q3` `LOCKED_SOON_PATHS`'ten çıkar; `QUOTA`'ya eklenir: `anon=3/gün, authed=10/gün` (Q4 ile simetri). PaywallPlaceholder kaldırılır.

### KD-V1-S7-04 — DM-055 (havuz paylaşımı) V2'ye ertelenir

Q1+Q3 ortak Redis havuzu (DM-055) V1'de uygulanmaz. V2'de tek atılım olarak yapılır.

### KD-V1-S7-05 — Sample hint alternatifli

Omer: "sample size alternatifli önersin." → tek sample size yerine 2-3 alternatif (pilot/orta/büyük gibi).

---

## §2 — Mevcut durum (envanter)

**Frontend (`web/src/app/(app)/q3/page.tsx`)** — V1-S6 PR #18:
- `useTierMock()` + `useSearchParams("qid")`
- Fixture: `Q3_FIXTURE_PAPERS` (3 kart, Q1'den miras) + `Q3_FIXTURE_METHOD` (distribution + suggestions + sampleHint)
- Anon → `<PaywallPlaceholder>` + `<LeftPanelPapers>`; Pro → 3 komponent (chart + suggestions + sample) + `<LeftPanelPapers>`
- TODO satırı (`page.tsx:96`): `// TODO(V1-S7): swap fixture for fetch('/api/q/method', { qid })`

**Backend (`api/routes/q.py:224-232`)** — V1-S5 stub:
- `POST /api/q3` → `tier_gate` 403 `tier_locked_soon` (LOCKED_SOON_PATHS gereği)
- Body schema YOK, response YOK

**Tier gate (`api/middleware/tier_gate.py:65`):**
- `LOCKED_SOON_PATHS = {"/api/q2", "/api/q3"}` — `/api/q3` çıkarılacak
- `QUOTA` dict — `/api/q3` eklenecek

**Q sayfa (`web/src/app/(app)/q/page.tsx:243-249`):**
- `/q3` linki `disabled` ActionButton — açılacak ve `/q3?q={submitted}` olacak
- Mevcut: `<ActionButton href="/q3" label="Metod Önerisi" code="Q3" Icon={FlaskConical} disabled />` (wait, kontrol et — disabled flag var mı?)

---

## §3 — Atomic commit boundary

| # | Commit | Dosya | LOC | Test |
|---|---|---|---|---|
| V1-S7-01 | `feat(api): /api/q3 method suggestion (saf LLM, single-call)` | `api/middleware/tier_gate.py` (LOCKED_SOON_PATHS revize + QUOTA `/api/q3` ekle) + `api/models/q.py` (Q3Request/Q3Response/Q3Suggestion/SampleHint/SampleAlternative + 7-tag MethodTag enum) + `api/services/role_modules/vitrin_method.py` (yeni — brief) + `api/services/role_modules/__init__.py` (register) + `api/routes/q.py` (Q3 stub yerine gerçek endpoint) + `tests/unit/test_q3_validator.py` (yeni) + `tests/integration/test_q_routes.py` (Q3 anon/authed/llm-fail senaryoları) | ~180 | unit + integration mock LLM + canlı Gemini smoke (TR+EN+ID) |
| V1-S7-02 | `feat(web): Q3 useMethodSuggestion hook + page revize (qid→q, paper paneli kalkar)` | `web/src/lib/q3-api.ts` (yeni client + adapter) + `web/src/hooks/useMethodSuggestion.ts` (yeni TanStack hook) + `web/src/app/(app)/q3/page.tsx` (qid→q, LeftPanelPapers kaldır, PaywallPlaceholder kaldır, MethodDistributionChart kaldır, single-column layout) + `web/src/components/q3/SampleHintBlock.tsx` (alternatifli liste revize) + `web/src/app/(app)/q/page.tsx` (Q3 ActionButton href: `/q3?q={submitted}`, disabled→aktif) + `web/src/hooks/useMethodSuggestion.test.tsx` (yeni) | ~140 | Vitest hook + manuel browser smoke |
| V1-S7-03 | `docs(v1): mark V1-S7 KAPANDI in sprint manifest + tier matrix güncelle` | `docs/plans/V1_vitrin_sprint.md` (§A V1-S7 closure + §2 Q3 satır revize + §6 QUOTA `/api/q3` ekle) | ~5 | — |

**Atomik kuralı:** her commit'te `pytest` + `ruff` + `mypy` + `tsc` + ilgili Vitest PASS. V1-S7-01 olmadan V1-S7-02 ship edilmez (frontend backend olmadan kırılır).

---

## §4 — Backend sözleşme

### Pydantic modeller (`api/models/q.py`)

```python
class MethodTag(StrEnum):
    EXPERIMENTAL_RCT = "experimental_rct"
    OBSERVATIONAL = "observational"
    QUALITATIVE = "qualitative"
    MIXED_METHODS = "mixed_methods"
    SYSTEMATIC_REVIEW = "systematic_review"
    SIMULATION = "simulation"
    THEORETICAL = "theoretical"


class Q3Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=500)
    lang: Literal["tr", "en", "id"] = "tr"


class Q3Suggestion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    method: MethodTag
    method_label: str = Field(min_length=2, max_length=80)  # sorgu dilinde
    rationale: str = Field(min_length=80, max_length=500)   # neden uygun


class SampleAlternative(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    label: str = Field(min_length=2, max_length=40)         # ör "Pilot", "Orta ölçek", "RCT geniş"
    sample_size: str = Field(min_length=2, max_length=40)   # ör "n = 30-60"
    note: str = Field(min_length=10, max_length=200)        # ör "ön çalışma için"


class SampleHint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    alternatives: list[SampleAlternative] = Field(min_length=2, max_length=3)
    datasets_or_tools: list[str] = Field(min_length=2, max_length=5)


class Q3SuggestionLLM(BaseModel):
    """LLM structured output container."""
    model_config = ConfigDict(extra="forbid")
    suggestions: list[Q3Suggestion] = Field(min_length=3, max_length=3)
    sample_hint: SampleHint


class Q3Response(BaseModel):
    model_config = ConfigDict(extra="forbid")
    suggestions: list[Q3Suggestion]
    sample_hint: SampleHint
    quota_remaining: int
    quota_reset: str
```

### Tier gate güncelleme (`api/middleware/tier_gate.py`)

```python
# §65 LOCKED_SOON_PATHS:
LOCKED_SOON_PATHS: frozenset[str] = frozenset({"/api/q2"})  # /api/q3 ÇIKTI

# §57 QUOTA:
QUOTA: dict[str, dict[Tier, int | None]] = {
    "/api/q":  {Tier.ANON: 3, **_authed_quota(5)},
    "/api/q1": {Tier.ANON: None, **_authed_quota(5)},
    "/api/q3": {Tier.ANON: 3, **_authed_quota(10)},  # YENİ — Q4 ile simetri
    "/api/q4": {Tier.ANON: 3, **_authed_quota(10)},
    "/api/q5": {Tier.ANON: 5, **_authed_quota(20)},
}
```

### Endpoint akışı (`api/routes/q.py`)

```python
@router.post("/q3", response_model=Q3Response)
async def q3(
    req: Q3Request,
    quota: Annotated[dict[str, Any], Depends(tier_gate)],
) -> Q3Response:
    prompt = _build_method_prompt(req.query, req.lang)

    parsed: Q3SuggestionLLM | None = None
    last_err: str | None = None
    for attempt in (1, 2):
        try:
            resp = await llm_service.call(
                prompt,
                tier="flash",
                mode="vitrin_method",
                structured_output_schema=Q3SuggestionLLM,
                max_tokens=1200,
            )
        except Exception as exc:
            last_err = f"llm_call_failed:{exc}"
            continue

        candidate = resp.parsed_output
        if not isinstance(candidate, Q3SuggestionLLM):
            last_err = "structured_output_missing"
            continue

        parsed = candidate
        break

    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "empty_llm_output", "reason": last_err or "unknown"},
        )

    return Q3Response(
        suggestions=parsed.suggestions,
        sample_hint=parsed.sample_hint,
        quota_remaining=int(quota["quota_remaining"]),
        quota_reset=str(quota["quota_reset"]),
    )
```

### Prompt (`api/services/role_modules/vitrin_method.py`)

```python
VITRIN_METHOD_BRIEF = """
Sayfa: Vitrin Q3 — kullanıcı bir araştırma sorusu girdi.

Senin işin:
  - Bu konuda araştırmacılara EN UYGUN 3 farklı metodoloji öner.
  - Her öneri için: yöntem (7 enum'dan biri), kısa Türkçe/İngilizce/Indonesian etiket,
    80-500 karakterlik gerekçe (neden bu yöntem bu konuya uygun, akademik ton).
  - Belirli paper, yazar, sayı ANMA — sadece metod adı + neden uygun.
  - Sonra önerilen ANA yöntem için sample hint:
      * 2-3 alternatif: { label, sample_size, note } — ör "Pilot · n=30-60 · ön çalışma için"
      * 2-5 dataset/araç adı (genel — SPSS, R, Python sklearn, vs.)
  - Kullanıcı dili Türkçeyse TR; İngilizceyse EN; Bahasa Indonesia ise ID.
  - 7 yöntem enum: experimental_rct, observational, qualitative, mixed_methods,
    systematic_review, simulation, theoretical.
  - Çıktı SADECE JSON: { suggestions: [...], sample_hint: { alternatives, datasets_or_tools } }
"""
```

`api/services/role_modules/__init__.py` — `"vitrin_method": VITRIN_METHOD_BRIEF` register.

### Halüsinasyon kapısı

- Pydantic structured output schema 7-tag enum'u zorlar — drift yok
- Rationale `min_length=80` boş yanıt kapısı
- `len(suggestions) == 3` zorunlu (frozen Field)
- 1 retry; ikinci fail → 502 `empty_llm_output`
- **İçerik halüsinasyonunu doğrulamıyoruz** (KD-V1-S7-01 onaylı). Frontend disclaimer gösterir: *"LLM önerisi · uygulamadan önce literatür kontrolü"*

---

## §5 — Frontend sözleşme

### `web/src/lib/q3-api.ts` (yeni)

```typescript
export type Q3MethodRequest = { query: string; lang: "tr" | "en" | "id" };
export type Q3SuggestionApi = {
  method: MethodTag;
  methodLabel: string;
  rationale: string;
};
export type SampleAlternativeApi = {
  label: string;
  sampleSize: string;
  note: string;
};
export type SampleHintApi = {
  alternatives: SampleAlternativeApi[];
  datasetsOrTools: string[];
};
export type Q3MethodResponse = {
  suggestions: Q3SuggestionApi[];
  sampleHint: SampleHintApi;
  quotaRemaining: number;
  quotaReset: string;
};
export async function fetchQ3Method(req: Q3MethodRequest, signal?: AbortSignal): Promise<Q3MethodResponse>;
```

Backend snake_case → frontend camelCase adapter (Q1 ile aynı pattern).

### `web/src/hooks/useMethodSuggestion.ts` (yeni)

```typescript
export function useMethodSuggestion(args: { query: string; lang?: PaperLang; enabled: boolean }) {
  return useQuery<Q3MethodResponse, Error>({
    queryKey: ["q3-method", args.query, args.lang ?? "tr"],
    queryFn: ({ signal }) => fetchQ3Method({ query: args.query, lang: args.lang ?? "tr" }, signal),
    enabled: args.enabled && args.query.length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}
```

### `web/src/app/(app)/q3/page.tsx` (revize)

- `?qid=` → `?q=` URL paramı
- `<LeftPanelPapers>` **kaldırılır** (KD-V1-S7-02)
- `<PaywallPlaceholder>` **kaldırılır** (KD-V1-S7-03 — anon da fetch eder)
- `<MethodDistributionChart>` **kaldırılır** (Yol C — distribution YOK)
- `<MethodSuggestionList>` korunur — props revize: `suggestions: Q3SuggestionApi[]`, `examplePaperId/exampleRank` field'ları silinir, hover sync devre dışı
- `<SampleHintBlock>` revize: alternatifler liste render eder
- Tek sütun layout (md:grid-cols-[320px_1fr] kaldırılır)
- Loading/Error/Empty state komponentleri (Q1 page pattern)
- Disclaimer satırı (KD-V1-S7-01): *"LLM önerisi · uygulamadan önce literatür kontrolü öneririz."*

### `web/src/app/(app)/q/page.tsx` (Q3 link aç)

`page.tsx:243-249` — Q3 ActionButton:
- `disabled` flag kaldırılır
- `href` → `` `/q3?q=${encodeURIComponent(submitted)}` ``

### Komponent silme/revize

- `web/src/components/q3/MethodDistributionChart.tsx` — **silinir** (Yol C)
- `web/src/components/q3/MethodSuggestionList.tsx` — props revize (`onExampleClick` kaldır, `examplePaperId/exampleRank` kaldır, `methodLabel + rationale` korunur)
- `web/src/components/q3/SampleHintBlock.tsx` — props revize (`typicalSampleSize: string` → `alternatives: SampleAlternativeApi[]`)
- `web/src/components/shared/PaywallPlaceholder.tsx` — Q1 hala kullanır, dokunulmaz
- `web/src/components/shared/LeftPanelPapers.tsx` — Q1 hala kullanır, dokunulmaz

### Fixture

- `web/src/lib/q3-fixture.ts` + `q3-fixture.test.ts` — **silindi** (V1-S7-02 commit). Component rewrite sonrası import eden kalmadı; CLAUDE.md §3.4 sığınak yasakları gereği yorum satırlı/ölü kod tutulmaz. V2'de Yol A'ya dönülürse fixture yeniden yazılır.

---

## §6 — Test piramidi

| Katman | Dosya | Senaryo |
|---|---|---|
| **Backend unit** | `tests/unit/test_q3_validator.py` (yeni, ~40 LOC) | (a) Pydantic min/max constraints (suggestions=3, alternatives 2-3), (b) MethodTag enum drift reject, (c) rationale length boundary |
| **Backend integration** | `tests/integration/test_q_routes.py` (Q3 senaryoları eklenir, ~80 LOC) | (a) anon → 200 + suggestions=3, (b) authed → 200 + sampleHint.alternatives≥2, (c) LLM fail (mock) → 502 empty_llm_output, (d) tier_gate kota 429 (anon 4. çağrı), (e) lang=en → response English (mock) |
| **Backend smoke** | `tests/fixtures/q3_v1.json` (yeni) | Canlı Gemini Flash TR+EN+ID 3 fixture (manuel re-record) |
| **Frontend hook** | `web/src/hooks/useMethodSuggestion.test.tsx` (yeni) | (a) enabled=false → no-call, (b) success → data render, (c) query<2 → no-call, (d) fetch error → isError |
| **Manuel browser** | `/q3?q=akıllı şehir trafik` (TR), `/q3?q=transformer attention` (EN) | 3 öneri kart + alternatifli sample hint + dataset listesi + disclaimer |

---

## §7 — Sınırlar (kapsam DIŞINDA)

- ❌ DM-055 (Q1+Q3 havuz paylaşımı) — V2
- ❌ Method classification (per-paper 7-tag etiketleme) — Yol A scope, V2
- ❌ Distribution chart — Yol A scope, V2
- ❌ Suggestion grounding (`example_paper_id ⊆ used_paper_ids`) — paper kullanılmıyor, V2 Yol A'ya dönerse
- ❌ Multi-LLM ayrışması (Cosmos/Qwen) — V2
- ❌ Cache (Redis) — V1 prototip, query yeniden çağırılır
- ❌ `query_id` miras mekanizması — V2
- ❌ PaywallModal/CaptureModal Stripe akışı — anon kotalı, paywall YOK

---

## §8 — Riskler

| # | Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|---|
| 1 | Gemini Flash structured output JSON malformed | Orta | Orta | `llm_service.call` global fence strip + validator → 1 retry |
| 2 | LLM 3 yerine 2/4 öneri döndürür | Düşük | Düşük | Pydantic `Field(min_length=3, max_length=3)` reject + retry |
| 3 | LLM rationale çok kısa veya boş | Orta | Düşük | `Field(min_length=80)` reject + retry; prompt'ta 80-500 karakter explicit |
| 4 | LLM 7-tag dışı method üretir | Düşük | Düşük | Pydantic enum reject + retry |
| 5 | Anon kota Redis'siz dev ortamında bypass | Düşük | Düşük | tier_gate zaten Redis miss → log warn + allow (V1-S5 pattern); pilotda Redis var |
| 6 | LLM içerik halüsinasyonu (yanlış metod önerir) | Orta | Düşük | KD-V1-S7-01 onaylı; UI disclaimer + 5 user pilot feedback |
| 7 | `q3-fixture.ts` ölü kod kalır, kafa karıştırır | — | — | Çözüldü: V1-S7-02'de silindi (§5 Fixture notu). |

---

## §9 — Onay sinyali

Plan onaylandı sayılır:
- Omer "V1-S7 başla" der **veya**
- Omer "Yol C onaylı" der

Aksi halde plan revize.

---

## §10 — Kapanış kriterleri

- [ ] V1-S7-01 commit + tests PASS + canlı Gemini smoke (TR+EN+ID 3 fixture)
- [ ] V1-S7-02 commit + Vitest hook PASS + manuel browser smoke (anon kotalı + authed)
- [ ] V1-S7-03 commit + V1_vitrin_sprint.md §A "V1-S7 ✅ KAPANDI" işareti
- [ ] PR açık + CI yeşil + merge
- [ ] V1 vitrin sprint TAMAMEN KAPANIR (S2 + S3 + S4 + S5 + S6 + S7 hepsi merged)
