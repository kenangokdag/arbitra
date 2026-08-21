# V1-S11 — Çift Dil OpenAlex Arama (translate + paralel + dedup)

**Sub-sprint kodu:** V1-S11
**Önkoşullar:** V1-S10 PR #25 merge sonrası (rebase main)
**Plan tarihi:** 2026-05-10
**Tek doğruluk kaynağı:** Bu manifest

---

## §0 — Amaç

`/api/q` aramasını **kullanıcı dili + İngilizce** çift query ile global recall'a açmak.

**Mevcut sorun (kanıt A — 2026-05-10 OpenAlex live test):**

| Sorgu | `language:tr` filtre | Toplam | Top sonuç (cited) |
|---|---|---|---|
| `transformer attention` | VAR (mevcut) | 356 | "Türkçe Tweetlerden Cinsiyet Tespiti" (~10) |
| `transformer attention` | YOK | 401.861 | Swin Transformer (29K), Gradient learning (57K) |

`language:tr` paper meta-etiketi (dergi konfigürasyonu); `search` parametresi
full-text. Türk akademik papers'da abstract/keywords İngilizce yazılır →
İngilizce sorgu TR papers'da eşleşir, dünya literatürü ELENİR. Recall **1000x**
düşük.

---

## §1 — Mevcut durum (envanter)

### Backend

- `api/services/openalex_polite.py:90-91` — `if lang is not None: filters.append(f"language:{lang}")`
- `api/routes/q.py:55-61` — `search_papers(req.query, lang=req.lang, ...)` tek query
- `api/models/q.py:39` — `QRequest.lang: str | None`
- `api/services/role_modules/` — translate mode YOK
- `api/services/llm_service.py` — `call(mode=...)` zaten var, mode-based dispatch hazır

### Frontend

- `web/src/app/(app)/q/page.tsx:69` — `useQ({lang: "tr", ...})` hardcoded
- `web/src/lib/q-api.ts:39-49` — `PaperPreviewApi` (translation field yok)
- `web/src/hooks/useQ.ts:23` — queryKey `[query, lang, yearFrom, yearTo]`

---

## §2 — Yeni davranış (KD-V1-S11-01..04)

### KD-V1-S11-01 — `language` filtresi default kalkar (TEMEL fix)

`search_papers`'a `lang` parametresi geçilmez (call site'lardan kaldır). OpenAlex
filter'larında `language:*` YOK. Recall 356 → 401K (1000x).

`lang` parametresi `search_papers` signature'ında **opsiyonel kalır** ama default
`None` ve V1-S11 call site'ları kullanmaz (geri uyumluluk; gelecekte explicit
"sadece TR papers" UI toggle'ı için).

### KD-V1-S11-02 — LLM translate (Gemini Flash) — kullanıcı dili → İngilizce

Yeni role module: `translate_query`. Çıktı:

```python
class QueryTranslation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    detected_lang: Literal["tr", "en", "id", "other"]
    english_query: str = Field(min_length=2, max_length=500)
```

**Prompt sözleşmesi** (örnek):
- Girdi: `transformer dikkat mekanizması`
- Çıktı: `{"detected_lang": "tr", "english_query": "transformer attention mechanism"}`
- Girdi: `transformer attention`
- Çıktı: `{"detected_lang": "en", "english_query": "transformer attention"}`

**Skip mantığı:** `detected_lang == "en"` ise 2. query atlanır (tek search yeter).

### KD-V1-S11-03 — Paralel search + dedup + cited_by_count sıralı (K1=a)

```python
# Pseudo:
trans = await translate(query)
queries = [query]
if trans.detected_lang != "en":
    queries.append(trans.english_query)

results_lists = await asyncio.gather(
    *[search_papers(q, limit=25) for q in queries],
    return_exceptions=True,
)
# dedup by openalex_id → max(cited_by_count) → top-25
merged = dedup_and_rank(results_lists, top_k=25)
```

**Dedup formülü:** `dict[openalex_id] = paper` ilk eklemede; sonraki çakışmada
yüksek cited_by_count'lu kazanır (ama OpenAlex aynı paper için aynı cited
döndüğünden pratik olarak fark etmez).

**Sıralama:** `cited_by_count desc` (her query zaten bu sıralama, birleşim de
aynısı). Re-ranker LLM call YOK.

**Hedef:** N papers ≤ 25. Eğer translate edildi (2 query) ama dedupli total ≥ 25
ise top-25; daha az ise hepsi.

### KD-V1-S11-04 — Translate fail → graceful degrade (K3=evet)

Translate timeout (>3sn) veya Pydantic parse hatası → 1 query (sadece kullanıcı
dili) çalışır + response'a `translation: null` + `translation_error: "..."` flag.
UI banner: "İngilizce çeviri başarısız, sadece [TR/ID] arama yapıldı."

OpenAlex 1 query fail (paralel) → diğer query sonuçları yine döner. İki query
de fail → 503 (mevcut davranış).

---

## §3 — Backend kontrat

```python
# api/models/q.py — yeni QResponse alanı

class QueryTranslation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    original: str
    detected_lang: Literal["tr", "en", "id", "other"]
    english_query: str  # detected_lang == "en" ise = original

class QResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    papers: list[PaperPreview] = Field(max_length=25)
    translation: QueryTranslation | None = None  # YENİ — None = translate skip/fail
    quota_remaining: int
    quota_reset: str
```

`POST /api/q` request kontratı **değişmez** (`QRequest` aynı). `lang` artık
sadece çıktı dili sinyali (literature-review mode'unda kullanılır), search
filter'ı değil.

---

## §4 — Frontend kontrat

```typescript
// web/src/lib/q-api.ts — yeni alan

export type QueryTranslationApi = {
  original: string;
  detectedLang: "tr" | "en" | "id" | "other";
  englishQuery: string;
};

export type QResponseApi = {
  papers: PaperPreviewApi[];
  translation: QueryTranslationApi | null;
  quotaRemaining: number;
  quotaReset: string;
};
```

UI (q/page.tsx) — sonuç başlığının altında subtle satır:
- Translation var + farklı: *"Aranan: TR + EN çeviri (transformer attention mechanism)"*
- Translation null + degraded: *"İngilizce çeviri atlandı, sadece TR arama"*
- detectedLang == "en": (banner gösterilmez)

---

## §5 — Atomic commit boundary

| # | Commit | Dosya | LOC |
|---|---|---|---|
| V1-S11-01 | `feat(api): translate_query role module + QueryTranslation pydantic` | `api/services/role_modules/translate_query.py` (yeni) + `__init__.py` register + `api/models/q.py` (`QueryTranslation`) + unit test | ~120 |
| V1-S11-02 | `feat(api): /api/q çift dil paralel search + dedup (KD-V1-S11-01..04)` | `api/routes/q.py` revize (translate + asyncio.gather + dedup) + `api/services/openalex_polite.py` (lang param dokümante) + integration testler (4+ scenario) | ~200 |
| V1-S11-03 | `feat(web): /q translation banner + QueryTranslationApi adapter` | `web/src/lib/q-api.ts` (translation field + adapter) + `web/src/lib/q-api.test.ts` (passthrough) + `web/src/app/(app)/q/page.tsx` (banner satırı) | ~80 |
| V1-S11-04 | `docs: V1 vitrin sprint manifest V1-S11 KAPANDI` | `docs/plans/V1_vitrin_sprint.md` (§A V1-S11 satır) | ~20 |

**Toplam:** ~420 yeni LOC.

---

## §6 — Test piramidi

| Katman | Dosya | Senaryo |
|---|---|---|
| LLM unit | `tests/unit/test_role_modules.py` | `translate_query` brief → QueryTranslation schema valid, TR sorgu → en farklı; EN sorgu → en aynı |
| Backend integration | `tests/integration/test_q_routes.py` | (a) TR sorgu → 2 paralel search çağrıldı + translation field non-null, (b) EN sorgu → 1 search + translation.detected_lang="en", (c) translate fail → 1 search + translation=null + degraded banner sinyali, (d) dedup by openalex_id (mock 2 query çakışan papers) |
| OpenAlex mock | `tests/unit/test_openalex_polite.py` | `lang` parametresi None default, filter'a eklenmez |
| Frontend adapter | `web/src/lib/q-api.test.ts` | translation snake→camel passthrough; null geçer |
| Frontend hook | `web/src/hooks/useQ.test.tsx` | translation field response'ta expose |
| Manuel browser | `/q` | (a) TR sorgu "transformer dikkat" → global papers + banner "EN çeviri: transformer attention", (b) EN sorgu "transformer attention" → global papers + banner yok, (c) translate timeout sim → degraded banner |

---

## §7 — Sınırlar (kapsam DIŞINDA)

- ❌ Yerli DB adapter (Dergipark/Garuda/SINTA) — V2 önkoşul: API discovery sprint
- ❌ 3+ paralel kaynak
- ❌ LLM-as-ranker (re-rank)
- ❌ Translate cache (Redis) — V1.5 opt
- ❌ UI dil seçici dropdown — Accept-Language veya hardcoded TR yeter (V2 i18n)
- ❌ "Aranan dilde" toggle (kullanıcı "sadece TR" diyebilsin) — V2 advanced filter
- ❌ Translate kalite onay UI'ı ("doğru mu?" diye sor) — false friction

---

## §8 — Riskler

| # | Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|---|
| 1 | Translate latency 500ms+ → UX yavaşlar | Orta | Düşük | Gemini Flash <500ms tipik; toplam ~3sn kabul edilebilir; degraded fallback |
| 2 | Translate akademik jargon yanlış çevirir (örn. "yağlanma" = obesity ≠ folksonomy) | Düşük | Orta | Banner'da çeviriyi kullanıcıya göster (transparan); yanlışsa kullanıcı düzeltir |
| 3 | Dedup yanlış (aynı paper 2 farklı openalex_id ile) | Düşük | Düşük | DOI fallback dedup (V1.5'e bırakılabilir, şu an basit) |
| 4 | OpenAlex 1 query 5xx → diğer query'nin sonuçları döner ama translation banner yanıltıcı | Düşük | Düşük | gather'da exception catch + log; response'ta query_status alanı (V1.5) |
| 5 | LLM translate +1 call → kota baskı | Düşük | Düşük | Translate cost ~$0.0001/call; mevcut quota değişmez |

---

## §9 — DoD

- [ ] V1-S11-01: `translate_query` role + QueryTranslation pydantic + unit test PASS
- [ ] V1-S11-02: `/api/q` çift query + dedup + degraded fallback + integration test PASS (4 senaryo)
- [ ] V1-S11-03: frontend banner + adapter test PASS
- [ ] V1-S11-04: sprint manifest §A V1-S11 KAPANDI satır
- [ ] tsc clean, vitest tüm suite PASS, pytest backend PASS, `npx next build` exit 0
- [ ] Manuel browser smoke (3 senaryo: TR sorgu / EN sorgu / translate fail sim)
- [ ] PR ayrı (V1-S10 #25 merge sonrası rebase) + Omer browser onayı + squash merge

---

## §10 — Onay sinyali

Plan onaylandı sayılır:
- Omer "V1-S11 başla" der **veya** "hepsini yapalım" der (2026-05-10 mesajıyla)

Tek "evet"/"tamam" plan onayı sayılmaz (CLAUDE.md §0).

---

## §11 — Sıradaki adım (onay sonrası)

V1-S11-01: yeni branch `v1-s11-cift-dil-arama` (v1-s10-vitrin-tek-sayfa'dan), önce
`translate_query` role module + QueryTranslation pydantic + unit test commit.
