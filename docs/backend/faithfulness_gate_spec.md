# Faithfulness Gate — Ortak Servis Spec (B Grubu, 2026-04-30)

> **Statü**: TASLAK — Council 18. tur (B Grubu)
> **Bağlam**: F3a Curator (P008 search) + F3c summarize (P022) **aynı 3-katlı kalite kapısını** çağırır — DRY refactor, tek modül `api/services/faithfulness_gate.py`
> **Owner**: Sercan (impl) · Claude (audit + LVR matematik) · Omer (eşik onayı)

---

## §0 Bağlam (3 cümle)

R9 + C3-C5 + B42-045 K4/K5 ortak runtime kuralları **iki endpoint'te de gerekiyor**: `/api/search` Curator (P008) JSON çıktısını LVR ≥0.7 + jsonschema=100 ile kapatır, `/api/summarize` SummaryDoc (P021/P022) aynı kapı + ek MiniCheck NLI ≥0.7 + ALCE recall ≥0.8'i geçer. F3a + F3c iki yerde paralel kod yazmak yerine **tek `faithfulness_gate.py` modülü** soyutlar; sapma kayıt + retry + Sentry breadcrumb tek yerden gelir, eşik değişikliği tek satır revize. Niş ayrım: jenerik validator değil — paper_id+span span-level LVR doğrulama (corpus 24.87M Pinecone neighbor query) + Outlines `rank` field yasağı (K4) + K1 yıl scrub (post-process) entegre.

---

## §1 Karar günlüğü

| Karar | Kaynak | Etki |
|---|---|---|
| Tek modül `api/services/faithfulness_gate.py` | DRY + master §10 | F3a P008 ve F3c P022 import eder |
| 3-kat kapı: (1) JSON şema validation = 100% (Outlines) + (2) LVR cümle-düzey ≥0.7 (Pinecone neighbor) + (3) [opsiyonel] MiniCheck NLI ≥0.7 + ALCE recall ≥0.8 (sadece summarize için, K4/K5 enforce her ikisinde) | C3-C5 + R9 + K5 | `gate.check(doc, level="search"|"summary")` |
| K1 yıl scrub: regex `\((\d{4})\)` matchlerinde `paper.year_verified=false` ise drop ("(2024)" → kaldır) | K1 + master §6.1 | post-process step |
| K4 enforce: Outlines JSON şemasında `rank` field **yasak**; eğer LLM çıktısı `rank` üretirse pre-validation fail | K4 | `gate.validate_schema()` |
| Retry policy: ilk fail → 1× retry (deterministik temperature=0); ikinci fail → HTTP 500 + Sentry trace_id (P022 + P008'de aynı) | F3c §1 | `gate.with_retry()` |
| Sentry breadcrumb her gate çağrısında: jsonschema_ms + lvr_ms + minicheck_ms + alce_ms + total_ms + violations | F1' §6.5 monitoring | tracing |
| Eşik konfigürasyon: `.env` üstü değil, `config/faithfulness_thresholds.yaml` (Omer onayı sonrası değişir, default master §3 + R9'dan) | tek doğruluk kaynağı | `gate.thresholds` |
| LVR validator: paper_id+span ≥0.7 cosine; **Pinecone neighbor query** (24.87M corpus, 1024-d BGE-M3) — F3a/F3c ortak Pinecone client (DM-016 dense) | K5 + DM-016 | `gate.validate_lvr()` |
| Performance budget: gate çağrısı için p95 < 800ms (search), < 1500ms (summary 3-kat); aksi halde C1/C2 kırılır | C1-C2 + master §6.4 | budget assertion |

---

## §2 API kontratı

```python
# api/services/faithfulness_gate.py

from typing import Literal, Optional
from pydantic import BaseModel

class GateLevel(str):
    SEARCH = "search"      # 2-kat: jsonschema + LVR
    SUMMARY = "summary"    # 4-kat: jsonschema + LVR + minicheck + alce

class GateResult(BaseModel):
    passed: bool
    level: GateLevel
    metrics: dict           # jsonschema_pct, lvr_min, minicheck_nli, alce_recall
    violations: list[str]   # [] empty if passed; ["lvr<0.7", "k4_rank_field"] etc.
    retry_count: int
    latency_ms: int
    trace_id: str           # Sentry

class FaithfulnessGate:
    def __init__(self, thresholds_path: str = "config/faithfulness_thresholds.yaml"):
        self.thresholds = load_yaml(thresholds_path)
        self.pinecone = get_pinecone_client()       # F3a P002
        self.minicheck = load_minicheck_model()     # lazy F3c P022
        self.alce = AlceCitationRecall()            # lazy F3c P022

    def check(
        self,
        doc: dict,                                  # JSON output from Curator
        level: GateLevel,
        retry_on_fail: bool = True,
    ) -> GateResult: ...

    def validate_schema(self, doc: dict) -> bool:    # Outlines + K4 rank yasak
    def validate_lvr(self, doc: dict) -> tuple[bool, float]:  # paper_id+span ≥0.7
    def validate_minicheck(self, doc: dict) -> float:        # NLI score
    def validate_alce(self, doc: dict) -> float:             # citation-recall
    def scrub_k1_years(self, doc: dict) -> dict:             # regex (\d{4}) drop
```

**Kullanım F3a P008** (Curator):
```python
gate = FaithfulnessGate()
result = gate.check(curator_output, level=GateLevel.SEARCH)
if not result.passed:
    raise HTTPException(500, detail={"error": "faithfulness_failed", "violations": result.violations, "trace_id": result.trace_id})
response.faithfulness_meta = {"jsonschema_pct": result.metrics["jsonschema_pct"], "lvr_min": result.metrics["lvr_min"]}
```

**Kullanım F3c P022** (summarize_task):
```python
result = gate.check(summary_doc, level=GateLevel.SUMMARY, retry_on_fail=True)
if not result.passed:
    # retry_count=1 ise 500 + Sentry; <1 ise auto-retry
    task.update_status("failed", error=f"faithfulness_failed: {result.violations}")
```

---

## §3 İmplementasyon (tek atomic commit P008b veya P022b — F3a/F3c sprint içinde)

| Adım | İş | Dosya | LOC |
|---|---|---|---|
| 1 | `FaithfulnessGate` sınıfı + 3-kat method | `api/services/faithfulness_gate.py` | ~250 |
| 2 | `config/faithfulness_thresholds.yaml` (default değerler) | `config/` | ~30 |
| 3 | F3a P008 Curator import + check çağrısı | `api/services/curator.py` (refactor) | ~20 (değişiklik) |
| 4 | F3c P022 summarize_task import + check (with_retry) | `api/workers/tasks/summarize_task.py` (refactor) | ~30 |
| 5 | Unit test ortak gate | `tests/unit/test_faithfulness_gate.py` | ~200 |

**Toplam**: ~530 LOC; F3a + F3c sprint'lerinde **paralel çıkarılır** (tek modül, iki ayrı PR'da reuse).

---

## §4 Verification

```bash
# S1: Unit test all paths
pytest tests/unit/test_faithfulness_gate.py -v
# Beklenen: ≥15 PASS — schema_pass + schema_fail_k4_rank + lvr_pass + lvr_fail_below_07 + minicheck_pass + alce_pass + retry_pass + retry_fail_500

# S2: F3a integration — Curator → gate
pytest tests/integration/test_search_endpoint.py -v -k faithfulness
# Beklenen: response.faithfulness_meta.jsonschema_pct == 100 + lvr_min ≥ 0.7

# S3: F3c integration — summarize_task → gate (4-kat)
pytest tests/integration/test_summarize_celery.py -v -k faithfulness
# Beklenen: SummaryDoc.faithfulness_meta 4 alan dolu + minicheck ≥0.7 + alce ≥0.8

# S4: Performance budget
python tests/perf/bench_gate.py --n 100
# Beklenen: search level p95 <800ms; summary level p95 <1500ms
```

---

## §5 Edge case + retry policy

| Edge case | Davranış |
|---|---|
| LLM çıktı non-JSON | Pre-validation fail → retry 1× temperature=0 → fail ise 500 |
| LLM çıktı `rank` field içerir (K4 ihlali) | Pre-validation fail (Outlines schema yakalar); retry 1× → fail ise 500 |
| LVR <0.7 cümle var | violations.append("lvr<0.7:sentence_idx_3"); retry 1× → fail ise 500 |
| MiniCheck NLI <0.7 (sadece summary) | retry 1× → fail ise 500 |
| ALCE recall <0.8 (sadece summary) | retry 1× → fail ise 500 |
| K1 yıl scrub uygulanırsa | doc.text içindeki `(YYYY)` matchleri paper.year_verified=false ise kaldırılır; scrub log'a yazılır (audit) |
| Pinecone unavailable | LVR validate fail → retry 3× exponential → fail ise 503 (search) veya task.failed (summary) |

---

## §6 Critical files

### Backend touch (F3a/F3c sprint'lerinde paralel)
- `api/services/faithfulness_gate.py` (yeni, ~250 LOC) — TODO(sercan)
- `config/faithfulness_thresholds.yaml` (yeni) — TODO(omer onay)
- `api/services/curator.py` (F3a P008 — refactor: gate import + check call)
- `api/workers/tasks/summarize_task.py` (F3c P022 — refactor: gate import + with_retry)

### Tests touch
- `tests/unit/test_faithfulness_gate.py` (≥15 senaryo)
- `tests/perf/bench_gate.py` (p95 budget)

### Read-only
- `docs/plans/F3a_search.md` (P008 Curator)
- `docs/plans/F3c_summarize.md` (P022 faithfulness gate)
- `docs/DM_RULES.md` (R9 + R8 K4/K5)

---

## §7 TODO(sercan + omer)

### Sercan
- [ ] `FaithfulnessGate` sınıf impl (250 LOC)
- [ ] MiniCheck NLI fine-tune indir (lazy load, model cache)
- [ ] ALCE recall implementation (citation-recall metric — paper [Liu et al. 2023] formula)
- [ ] Pinecone neighbor query helper (LVR validate için)
- [ ] Sentry breadcrumb 5-aşama timing

### Omer
- [ ] `config/faithfulness_thresholds.yaml` default eşikler onayı:
  ```yaml
  jsonschema_pct: 100      # C3
  lvr_min_distance: 0.7    # K5
  minicheck_nli: 0.7       # C4
  alce_recall: 0.8         # C5
  retry_count: 1           # F3c §1
  ```

---

## §Council — R13 18. tur (Faithfulness Gate Spec, 2026-04-30)

| # | Üye | Verdict | Gerekçe |
|---|---|---|---|
| 1 | **Halüsinasyon Avcısı** | ✅ GREEN | C3-C5 + R9 + K4/K5 referansları doğrulanmış; LVR formül kaynağı F3a §1 (B42-045 K5); ALCE recall paper referansı belirtilmiş |
| 2 | **Akademik İsabet** | ✅ GREEN | MiniCheck NLI + ALCE citation-recall akademik standart; LVR cümle-düzey paper_id+span K5 ile uyumlu; K1 regex post-process scrub doğru |
| 3 | **Fayda-Maliyet Hakemi** | ✅ GREEN | Tek modül → DRY; F3a + F3c iki yerde 250 LOC paralel kod yerine tek 250 LOC + 50 LOC import refactor; bakım maliyeti net pozitif |
| 4 | **Daha İyisi Var Mı?** | ⚠️ YELLOW | 2026'da **Patronus AI Lynx** (open-source faithfulness eval) veya **Vectara HHEM** alternatif modeller var; MiniCheck Liu 2024 baseline'ı solid ama Lynx-70B daha iyi accuracy reported | İstiyor: §1'e "MiniCheck tercih gerekçesi: 5B parameter kompakt + HF Endpoint deploy edilebilir; Lynx-70B 70B parameter çok büyük + bütçe yok; Faz 2'de Lynx-8B distill değerlendirilebilir" eklensin |
| 5 | **Global Çözüm Mühendisi** | ✅ GREEN | Multilingual MiniCheck v2 (TR + EN + ID destekli — model card kanıt A); LVR Pinecone 1024-d BGE-M3 multilingual; tüm corpus + tüm dil + tüm endpoint kapsamı |
| 6 | **Son Kullanıcı Avukatı** | ✅ GREEN | Kullanıcı "%100 doğrulanmış" gördüğünde gate runtime enforce sağlar (sapma=runtime fail, hayal değil); retry 1× → 500 dürüst pozisyonlama |

**Karar (R13.5)**: 5 GREEN + 1 YELLOW; düzeltme:
- §1 MiniCheck tercih gerekçe cümlesi eklendi: "MiniCheck v2 5B kompakt + HF deploy + multilingual; Lynx-70B 70B çok büyük + bütçe yok; Faz 2 Lynx-8B distill aday"

---

**Final commitment**: Bu spec onaylanırsa F3a P008 + F3c P022 sprint'leri içinde paralel implementasyon; tek modül `api/services/faithfulness_gate.py` ortak servis; Sercan refactor 1 günde, unit test ≥15 PASS gerekir.
