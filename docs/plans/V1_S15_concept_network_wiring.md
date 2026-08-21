# V1-S15 — ConceptNetwork FE Wiring (mock → canlı Supabase warehouse)

**Sub-sprint kodu:** V1-S15
**Önkoşullar:**
- V1-S14 ✅ (`feat/V1-S14-mock-to-live` — bibliometric pattern referansı: `api/routes/project_bibliometrics.py` + `api/services/bibliometric_service.py`)
- 2026-05-13 veri katmanı ✅ (`scripts/colab_load_concept_terms.ipynb` Cell 12 PASS):
  - `fact_term_arm_static` 297,855 satır · `fact_term_arm_temporal` 547,824 satır · `dim_term_community` 4,516 satır
  - 5 index + 3 ANALYZE OK · migration `0033_fix_term_arm_temporal_pk.sql` apply edildi
**Plan tarihi:** 2026-05-13 (canlı Supabase sorgularıyla doğrulanmış)
**Branch (önerilen):** `feat/V1-S15-concept-network-wiring` (off main HEAD)
**Onay:** ⏳ Omer — "plan onaylandı" denmeden kod yazma yasak (CLAUDE.md §0)

---

## §0 — Amaç

`web/src/components/project/ConceptNetworkPage.tsx` içindeki 20 hardcoded NODES + 29 hardcoded EDGES → canlı Supabase warehouse'tan anchor-merkezli alt-graf. Route slug: `gapatlas-5`. Sayfa spec: `Page_Design/Sayfa_Plani_v2/2.5_kavram_agi.rtf`.

**Pilot scope V1 minimum:**
1. anchor-centered subgraph (1-hop, NPMI desc top-50 edge)
2. community color coding (Leiden `dim_term_community.community_id`, 11 distinct community → 4 sabit Tableau renk modulo)
3. trending markers (Δlift > 0 yeşil ▲ / Δlift < 0 kırmızı ▼) — opsiyonel (LEFT JOIN, null = marker yok)
4. selected node sağ panel (D6 Lite görsel, mevcut UI korunur)

**Scope dışı (V2):** 2-hop, Flash micro-commentary (LLM), 11-category ontology, full betweenness centrality, D6 Lite kart 4 button davranışı (Detay/Liste/Özetle/Sohbet).

---

## §1 — Veri envanteri (kanıt seviyesi A — 2026-05-13 canlı sorgu sonuçları)

### Tablo şemaları (`information_schema.columns` ile doğrulandı)

```
fact_term_arm_static:
  term_a       text          ← integer-as-string ("2213", "295")
  term_b       text          ← integer-as-string
  lift         double precision
  npmi         double precision
  support      double precision
  conviction   double precision  ← NULL (notebook Cell 4 CORE_COLS'tan çıkartıldı, kolon kalır)
  extra        jsonb         ← term_a_code, term_a_name, field_a, domain_a, subfield_a, n_a, support_count, confidence_a_to_b, ... (16 alt-alan)

fact_term_arm_temporal (post-0033):
  term_a       text
  term_b       text
  delta_lift   double precision
  extra        jsonb         ← cnt_recent, cnt_prev, support_recent, support_prev, lift_recent, lift_prev, term_*_name/code, ...

dim_term_community:
  term         text          ← OpenAlex T-prefix kodu ("T10050", "T11872")
  community_id integer       ← 0..10 (11 distinct)
  extra        jsonb         ← term_name (insan-okunur), term_id (integer-as-string), keywords, description, field_name, domain_name, subfield_name, community_size
```

### Kritik bulgu — **İki farklı identifier space (kanıt A)**

| Tablo | Top-level identifier | Format |
|---|---|---|
| `fact_term_arm_static.term_a/b` | "2213" | integer-as-text (OpenAlex term_id) |
| `dim_term_community.term` | "T10050" | T-prefix code (OpenAlex topic ID) |

**Eşleşme** (kanıt: `Q10` sorgusu):
- `fact_term_arm_static.term_a` (text) **==** `dim_term_community.extra->>'term_id'` (text)
- `fact_term_arm_static.extra->>'term_a_code'` ("T14397") **==** `dim_term_community.term` ("T14397")

İki join yolu var; **plan: anchor query param T-code** (`?anchor=T10050` insan-okunur), backend `dim_term_community.term == anchor`'dan `term_id`'ye resolve eder, sonra `fact_term_arm_static.term_a/b == term_id` üzerinden 1-hop sorgu.

### Asimetri doğrulaması — **iki-yön sorgu zorunlu (kanıt A)**

Sorgu `Q11` (anchor = MCDM, term_id="2213"):
```
SELECT count(*) FROM fact_term_arm_static WHERE term_a='2213';  →  120
SELECT count(*) FROM fact_term_arm_static WHERE term_b='2213';  →  118
```

**Sonuç:** Tek-yön sorgu kullansaydık 1-hop edge'lerin **~%50'sini kaçırırdık**. Backend service iki ayrı sorgu + UNION + dedup yapmalı.

### Anchor adayları — gerçek MCDM kavramları (`Q6` sorgusu)

| T-code | term_id | term_name | community_id | field_name |
|---|---|---|---|---|
| **T10050** | 2213 | **Multi-Criteria Decision Making** | 2 | Decision Sciences |
| T14174 | (lookup) | Artificial Intelligence and Decision Support Systems | 2 | Computer Science |
| T13832 | (lookup) | Advanced Decision-Making Techniques | 2 | Computer Science |
| T11810 | (lookup) | Complex Systems and Decision Making | 2 | Decision Sciences |
| T14465 | (lookup) | Leadership, Behavior, and Decision-Making Studies | 3 | Decision Sciences |

**Anchor default V1-S15 = `T10050` (Multi-Criteria Decision Making)** — mock UI tema devamı.

**Mock vs canlı veri çakışma uyarısı:** Mock'taki "TOPSIS"/"AHP"/"VIKOR" gibi spesifik method node label'ları canlı warehouse'da **ayrı topic değil**; OpenAlex topic taksonomisinde aggregate isimler altında ("Multi-Criteria Decision Making", "Fuzzy Systems and Optimization", "Rough Sets and Fuzzy Logic", "Quality Function Deployment in Product Design"). FE label'ları canlı `term_name` kullanır — mock'taki kısa method isimleri görsel olarak hayat bulmayacak ama domain anlamlı, gerçek partner topic'ler render edilecek (`Q12` sorgusu top-10 partner):

```
2213 ↔ 2831  npmi=0.715  Multi-Criteria DM ↔ Optimization and Mathematical Programming
2213 ↔ 2579  npmi=0.696  Multi-Criteria DM ↔ Fuzzy Systems and Optimization
1762 ↔ 2213  npmi=0.599  Rough Sets and Fuzzy Logic ↔ Multi-Criteria DM
2213 ↔ 4096  npmi=0.572  Multi-Criteria DM ↔ Fuzzy and Soft Set Theory
 433 ↔ 2213  npmi=0.560  Quality Function Deployment ↔ Multi-Criteria DM
2213 ↔ 3608  npmi=0.553  Multi-Criteria DM ↔ Fuzzy Logic and Control Systems
1592 ↔ 2213  npmi=0.548  Intuitionistic Fuzzy Systems ↔ Multi-Criteria DM
1187 ↔ 2213  npmi=0.478  Advanced Algebra and Logic ↔ Multi-Criteria DM
2213 ↔ 2693  npmi=0.468  Multi-Criteria DM ↔ Cognitive Science and Mapping
  60 ↔ 2213  npmi=0.447  Bayesian Modeling and Causal Inference ↔ Multi-Criteria DM
```

### Distinct community count (`Q13` sorgusu)
- `SELECT count(DISTINCT community_id) FROM dim_term_community → 11`
- 4 sabit Tableau-10 renk modulo cluster_idx = community_id % 4: cluster overlap kabul edilebilir (toplam 11 farklı community, anchor=T10050 1-hop subgraph'ta tipik 3-5 community).

### delta_lift coverage (`Q13` sorgusu)
- anchor=2213 için `fact_term_arm_static` 238 partner vs. `fact_term_arm_temporal` 541 partner.
- Temporal kendi sliding window output'u, partial overlap. LEFT JOIN ile match yoksa `delta_lift = null` → FE marker yok ("trend bilinmiyor").

### `_ensure_supabase` ve `_user_id` — workshop.py pattern (kanıt A)
- `api/routes/workshop.py:132-139` — `_user_id(request)` fonksiyonu `request.state.user_id` getattr; AuthMiddleware set ediyor (P093 KAPANDI miras).
- `api/routes/workshop.py:142-149` — `_ensure_supabase()` 503 guard.

---

## §2 — Yol kararları (canlı kanıtla revize edilmiş)

### KD-V1-S15-01 — Endpoint prefix = `/api/workshop/concept-network`
Kanıt A: `Grep router = APIRouter` çıktısı — 22 route'ta `/api/discovery` prefix YOK. En yakın komşu workshop (30+ atölye endpoint). Yeni prefix kurma overhead'i ≠ getiri.

### KD-V1-S15-02 — Anchor 1-hop default, 2-hop V2'ye ertelendi
Sebep: 2-hop için iki-yön + 2-derinlik self-join → ~50×50 = 2500 edge candidate, gürültü. V1 net subgraph üretir.

### KD-V1-S15-03 — Cluster mapping = community_id % 4, 4 sabit renk
Distinct 11 community + Tableau-10 4 renk = kabul edilebilir collision. Anchor=T10050 1-hop subgraph'ta tipik 3-5 community, modulo 4 yeterli ayrım sağlar.

### KD-V1-S15-04 — **İki-yön sorgu + UNION + dedup zorunlu** (REVİZE — kanıt A)
`Q11` 120 vs 118 asimetri kanıtı. Backend service iki sorgu (`WHERE term_a=$1` ve `WHERE term_b=$1`) + Python-side birleştirme + (term_a,term_b) dedup + npmi DESC sort → top-50.

### KD-V1-S15-05 — `delta_lift` opsiyonel LEFT JOIN, partial coverage
`Q13` 238 static vs 541 temporal kanıtı. Backend `fact_term_arm_temporal` iki-yön sorgu (anchor partner pair'leri için), dict lookup; FE'de null marker yok.

### KD-V1-S15-06 — Redis cache 1h (gap_heatmap pattern)
Cache key: `concept-network:{anchor}` (project_id YOK; warehouse public corpus, project_id sadece auth scope). TTL 3600s.

### KD-V1-S15-07 — Auth: workshop pattern `_user_id` + `_ensure_supabase`
`api/routes/workshop.py:132-149` kanıt A.

### KD-V1-S15-08 — Anchor query param = T-code (`?anchor=T10050`), default = `T10050`
**Sebep:** Human-friendly URL + insan onaylama kolay. Backend resolve: `dim_term_community.term == anchor` → `extra->>'term_id'` → fact arm sorgu. T-code pattern validation `^T\d{4,5}$`.

### KD-V1-S15-09 — Node label = `dim_term_community.extra->>'term_name'` (term değil)
Sebep: `dim_term_community.term` = "T10050" insan-okunaklı değil; `term_name` = "Multi-Criteria Decision Making" UI-friendly. Node `id` = T-code (DOM key), `label` = term_name.

### KD-V1-S15-10 — Anchor 404 yerine empty-state
Anchor `dim_term_community`'de yoksa: backend 404 `anchor_not_found`. FE empty-state "kavram havuzunda yok, başka deneyin" + datalist suggestion (`dim_term_community.term_name LIKE` limit 10).

### KD-V1-S15-11 — Köprü kavram (V1): `community_id_source ≠ community_id_target ∧ lift >= 2.0`
FE-only türetme; backend community_id zaten payload'da. Edge stroke amber-500 + ⭐ ikon endpoint'lerde.

---

## §3 — Atomik commit haritası (4 commit)

### P001 — Backend service + Pydantic models

**Dosyalar:**
- Yeni: `api/services/concept_network_service.py` (~200 LOC)
  - `_resolve_anchor(t_code: str) -> tuple[str, dict] | None` — `dim_term_community.term == t_code` SELECT `term_id, community_id, term_name`; None → 404 trigger
  - `_fetch_edges_two_way(term_id: str, limit: int = 50) -> list[dict]` — iki ayrı `select().eq("term_a", term_id)` + `eq("term_b", term_id)`, NPMI DESC her birinde limit 100; Python-side birleştir + (term_a, term_b) tuple dedup + npmi DESC → top-50
  - `_fetch_terms_meta(term_ids: list[str]) -> dict[str, TermMeta]` — `dim_term_community.extra->>'term_id' IN (...)` batch (100'erli, curator pattern); dict[term_id_str] = {term_code, term_name, community_id}
  - `_fetch_delta_lifts(pairs: list[tuple[str,str]]) -> dict[tuple, float]` — `fact_term_arm_temporal` her pair için iki-yön; batch 100; dict[(a,b)] = delta_lift
  - `build_concept_network(anchor_t_code: str) -> ConceptNetworkResponse` — orchestrator
- Yeni: `api/models/concept_network.py` (~60 LOC)
  - `ConceptNetworkNode(BaseModel, extra="forbid")`: `id: str  # T-code`, `term_id: str`, `label: str  # term_name`, `community_id: int`, `cluster_idx: int  # community_id % 4`, `size: float`, `degree: int`
  - `ConceptNetworkEdge(BaseModel, extra="forbid")`: `source: str  # T-code`, `target: str  # T-code`, `lift: float`, `npmi: float`, `delta_lift: float | None`
  - `ConceptNetworkResponse(BaseModel, extra="forbid")`: `anchor: str  # T-code`, `anchor_label: str`, `nodes: list[ConceptNetworkNode]`, `edges: list[ConceptNetworkEdge]`, `total_communities: int`

**Kabul:**
- mypy --strict PASS · ruff PASS
- `python -c "from api.services.concept_network_service import build_concept_network"` import-doğrulama

### P002 — Endpoint + tests + router register

**Dosyalar:**
- Edit: `api/routes/workshop.py` — yeni endpoint blok `# ── F13-S5 §2.5 Concept Network ──`
  - `@router.get("/concept-network", response_model=ConceptNetworkResponse)`
  - Query: `project_id: UUID = Query(...)`, `anchor: str = Query(default="T10050", pattern=r"^T\d{4,5}$")`
  - Auth: `_user_id(request)` + `_ensure_supabase()`
  - Redis cache `concept-network:{anchor}` TTL 3600 (gap_heatmap pattern)
  - 404 `anchor_not_found` · 503 ResilienceTimeoutError/SupabaseQueryError
- Yeni: `api/tests/test_concept_network.py` (~180 LOC) — 7 test:
  1. `test_response_schema_extra_forbid`
  2. `test_anchor_default_T10050` (mock supabase → 200, anchor=T10050)
  3. `test_anchor_pattern_validation_400` (anchor="topsis" → 422)
  4. `test_anchor_not_in_dim_returns_404`
  5. `test_two_way_query_dedup` (mock `term_a=X` 2 row + `term_b=X` 1 row overlapping → dedup'lı response)
  6. `test_edges_sorted_by_npmi_desc`
  7. `test_delta_lift_null_when_temporal_missing`
- Live smoke (CI skip, `pytest -m live`): canlı T10050 → 200 + ≥10 edge + latency<800ms; fixture `tests/fixtures/concept_network_T10050.json`

**Kabul:**
- pytest 7/7 PASS · ruff + mypy strict
- Curl smoke: `curl -H "Authorization: Bearer dev" "http://localhost:8000/api/workshop/concept-network?project_id=<uuid>&anchor=T10050" | jq '.nodes | length'` ≥ 10

### P003 — FE refactor (mock NODES/EDGES → fetch)

**Dosyalar:**
- Edit: `web/src/components/project/ConceptNetworkPage.tsx`
  - Sil: `NODES`, `EDGES` constants (satır 29-83)
  - Tut: `CLUSTER_COLORS` (4 Tableau-10), `CANVAS_W=720/H=440`
  - Ekle: `useQuery(['concept-network', anchor], () => apiFetch<ConceptNetworkResponse>('/api/workshop/concept-network?project_id=...&anchor='+anchor))`
  - State: `anchor` (default "T10050"), `selectedNode` (default backend response `anchor` = T-code), `hoveredNode`, `minLift`, `showLabels` (mevcut korunur)
  - Layout: anchor merkez `(CANVAS_W/2, CANVAS_H/2)`, komşular **polar dağılım** (radius = 160, angle = `i * 2π/n`, size = 30 + degree*1.5 clamp 30..60); V1 kabul, V1.1 d3-force
  - Loading state: shimmer iskelet (`BibliometricSummaryPageSkeleton` pattern; yoksa minimal 4-block)
  - Empty state (anchor 404): "kavram havuzunda yok" + arama input (`dim_term_community.term_name` autocomplete — backend `/api/workshop/concept-network/search` mini-endpoint V1.1, V1'de sadece text input + retry)
  - Error state: in-card error message
- Edit: `web/src/lib/types.ts` — Pydantic mirror types `ConceptNetworkNode/Edge/Response`
- Yeni (opsiyonel): `web/src/components/project/ConceptNetworkPageSkeleton.tsx` (~50 LOC)

**Kabul:**
- `npx tsc --noEmit` clean
- `npx vitest run` 0 regress
- `npm run build` 10/10 routes
- Browser smoke `/project/p1/gapatlas-5`:
  - (a) shimmer → ~300ms canlı graf
  - (b) anchor T10050 → "Multi-Criteria Decision Making" merkez, top-10 partner çevrede
  - (c) `?anchor=T11810` → refetch + yeni canvas
  - (d) Δlift markerlı edge'ler 1+ render
  - (e) `prefers-reduced-motion` flat fallback

### P004 — Köprü kavram ⭐ + DataProvenance pill + closure docs

**Dosyalar:**
- Edit: `ConceptNetworkPage.tsx`
  - Köprü kavram: edge `source.community_id ≠ target.community_id ∧ edge.lift >= 2.0` → stroke amber-500 + endpoint'lerde Lucide `Star` 12px altın
  - DataProvenance pill sağ-üst: `<DataProvenance source="fact_term_arm_static + dim_term_community" n={edges.length} method="NPMI desc · 1-hop · Leiden community" updated="2026-05-13" confidence="A" />` (kanıt: V1-S13 P005 commit `77c301c` — bileşen `web/src/components/project/DataProvenance.tsx`)
- Edit: `docs/STATE.md` — V1-S15 KAPANDI satırı
- Edit: `docs/NEXT_ACTION.md` — sıradaki sprint pointer
- Edit: `docs/SPRINT_HISTORY.md` — P001-P004 entry
- Update memory: `project_papermind_mock_audit_2026-05-11.md` — #1 ConceptNetwork ✅ KAPANDI

**Kabul:**
- vitest + tsc + build PASS
- Browser smoke: 1+ köprü kavram altın stroke + ⭐
- DataProvenance pill hover popover okunur

---

## §4 — Backend endpoint spec

**Request:**
```
GET /api/workshop/concept-network
  ?project_id=<UUID>             # zorunlu, auth scope (warehouse public, RLS placeholder)
  &anchor=<T-code>               # opsiyonel, default "T10050", regex ^T\d{4,5}$
Authorization: Bearer <jwt>
```

**Response 200:**
```json
{
  "anchor": "T10050",
  "anchor_label": "Multi-Criteria Decision Making",
  "nodes": [
    {
      "id": "T10050",
      "term_id": "2213",
      "label": "Multi-Criteria Decision Making",
      "community_id": 2,
      "cluster_idx": 2,
      "size": 60,
      "degree": 50
    },
    {
      "id": "T_optimization_code",
      "term_id": "2831",
      "label": "Optimization and Mathematical Programming",
      "community_id": 4,
      "cluster_idx": 0,
      "size": 42,
      "degree": 1
    }
  ],
  "edges": [
    {"source": "T10050", "target": "T_optimization_code", "lift": 401.79, "npmi": 0.715, "delta_lift": null}
  ],
  "total_communities": 4
}
```

**Hata:**
- 422 — anchor pattern fail (`^T\d{4,5}$`)
- 404 `{"detail": "anchor_not_found"}` — anchor `dim_term_community.term`'de yok
- 503 `{"detail": "concept_network_unavailable"}` — Supabase/Redis timeout
- 401 / 400 — auth + Supabase guard

---

## §5 — Test plan (R13.13)

### Backend (P002, 7 test)
| # | Test | Tip |
|---|---|---|
| 1 | `test_response_schema_extra_forbid` | unit |
| 2 | `test_anchor_default_T10050` | unit (mock supabase) |
| 3 | `test_anchor_pattern_validation_400` | unit (FastAPI 422) |
| 4 | `test_anchor_not_in_dim_returns_404` | integration (mock 0 row) |
| 5 | `test_two_way_query_dedup` | unit (mock overlap) |
| 6 | `test_edges_sorted_by_npmi_desc` | unit |
| 7 | `test_delta_lift_null_when_temporal_missing` | unit |
| live | `test_live_smoke_T10050` | `pytest -m live` (CI skip) |

### FE (P003-P004)
- `cd web && npx vitest run` — 0 regress
- `cd web && npx tsc --noEmit` — clean
- `cd web && npm run build` — 10/10 routes
- Browser smoke 5 kabul (P003) + 2 kabul (P004)

### Empirik kanıt
- Her commit body'sinde 5 satır R13.13 evidence
- P002 sonunda `tests/fixtures/concept_network_T10050.json` canlı snapshot

---

## §6 — Risk ve geri dönüş

**Yüksek risk:** ~~Parquet simetri varsayımı~~ → **DOĞRULANDI ASIMETRIK** (KD-V1-S15-04). İki-yön sorgu yapılmazsa edge'lerin ~%50'si kaçar. P001 başında bu mantık birim test ile (mock'ta `term_a` 2 row + `term_b` 1 row overlapping → 2 unique edge sonucu) sabitlenecek.

**Orta risk:**
- Polar layout 20+ node'da overlap (V1.1 d3-force).
- Mock UI'nın "TOPSIS/AHP/VIKOR" gibi spesifik isimleri canlı veride yok — kullanıcıya **görsel beklentinin değiştiğini** açıklayan in-card not gerek (DataProvenance pill yeterli olabilir).

**Düşük risk:**
- Redis cache miss (gap_heatmap pattern proven).
- `_user_id` dev fallback — workshop.py mevcut endpoint'ler zaten çalışıyor (P093 KAPANDI).

**Tamir senaryosu:** commit fail → `git revert HEAD`, plan revize, yeni onay.

---

## §7 — Closure kriterleri

1. P001-P004 commit'leri `feat/V1-S15-concept-network-wiring` branch'inde
2. pytest 7/7 backend + vitest regress yok + tsc clean + build 10/10
3. Live smoke fixture `tests/fixtures/concept_network_T10050.json` repo'da
4. Browser smoke 5+2 kabul onaylı
5. `docs/STATE.md` V1-S15 KAPANDI + `docs/NEXT_ACTION.md` sıradaki pointer (ResearchAreaConfirm veya ReferenceStyle)
6. Memory `project_papermind_mock_audit_2026-05-11.md` #1 ConceptNetwork ✅ KAPANDI

---

## §8 — Plan revizyon log

- **2026-05-13 v1** — İlk taslak (Omer "devam et plan yaz" sonrası). 5 açık soru ile sunuldu.
- **2026-05-13 v2 (canlı kanıt revizyonu)** — Omer "kaynağa bak, sorma" → Supabase live psql 13 sorgu çekildi. Bulgular:
  - **(a) Asimetri kanıtlandı** (120 vs 118) → KD-V1-S15-04 iki-yön sorgu + dedup zorunlu
  - **(b) Schema tipi text** (integer-as-string), conviction NULL ama kolon kalmış
  - **(c) İki identifier space**: `term_a`(text "2213") vs `dim_term_community.term`(text "T10050") — extra'da join key
  - **(d) Anchor default**: T-code human-friendly `T10050` (Multi-Criteria Decision Making, term_id=2213, community=2)
  - **(e) Mock vs canlı çakışma**: TOPSIS/AHP/VIKOR ayrı topic değil; canlı top-10 partner Optimization/Fuzzy Systems/Rough Sets/QFD/Intuitionistic Fuzzy/Bayesian — kullanıcıya görsel beklenti değişimi DataProvenance ile açıklanır
  - **(f) Distinct community = 11**, 4 sabit Tableau renk modulo OK
  - **(g) delta_lift coverage**: anchor=2213 için temporal 541 partner, static 238 — LEFT JOIN partial coverage normal
  - **(h) Open question 5 ✅ kapandı**: köprü kavram `lift >= 2.0` (mock 1.2-3.1, MCDM canlı 401-188 range — backend lift değerleri daha geniş, threshold tekrar gözden geçirilecek P004 başında ama V1 default 2.0 OK)
- **Açık soru sayısı v1→v2**: 5 → 0 (hepsi canlı sorguyla kapatıldı)
