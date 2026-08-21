# F3c — Mini-Plan: POST /api/summarize

> **STATUS: SUPERSEDED** (2026-05-04) — F8 LLM Provider Unification (DM-035..044 = DM-LLM-1..10) ile production LLM tek = **Gemini 2.5 Flash/Pro 2-tier via LiteLLM router** kanon oldu. Bu plan'daki `huggingface/tgi` + `claude-haiku-4-5` model_chain ve "Qwen draft → Claude rötuş" 2-kademeli akış **artık geçerli değil**. Aşağıdaki içerik tarihsel kayıt amaçlıdır; gerçek implementasyon F8 plan'ına bakar.
>
> Kanıt: `docs/DECISIONS.md` DM-035..044 + `docs/plans/F8_llm_provider_unification.md` + commit `2ede251` (DM-010+DM-015 drift kapatma).

> **Statü**: TASLAK — F1' master plan onayı sonrası (B-001 §16)
> **Üst plan**: `docs/plans/F1_master_plan.md`
> **Şablon**: ARCHITECT_PROMPT_TEMPLATE §0..§7 + WhatsApp checklist
> **Owner**: Sercan (backend code) · Claude (LVR + faithfulness audit) · Omer (TR rötuş kalite onayı)

---

## §0 Bağlam (3 cümle)

E5 "Detay" ekranındaki on-demand özet — kullanıcı paper kartından "Özet üret" tıkladığında Celery worker arkada Qwen ile draft üretir, Claude Haiku TR akademik dilinde rötuşlar, LVR validator cümle-düzey atıf doğrular, sonuç `summary_cache` 24h saklanır. Niş ayrım: jenerik LLM özeti değil — her cümlede `paper_id+span+lvr_distance≥0.7` zorunlu (K5), boş/uydurma yıl yasak (K1), MiniCheck NLI ≥0.7 + ALCE recall ≥0.8 gate. DM-012 "corpus için mevcut abstract direkt göster" kuralıyla MVP'de **default = abstract direkt**; özet sadece `mode=detailed` istenirse Celery'e atılır (LLM token tasarrufu).

---

## §1 Karar günlüğü

| Karar | Kaynak | Etki |
|---|---|---|
| 2 mode: `abstract` (no LLM, abstract direkt) ve `detailed` (Celery + LLM 2-kademeli) | DM-012 + master §3 | branch logic |
| Async (202 + task_id + poll endpoint) | master §4.3 | Celery + Redis broker |
| 2-kademeli LLM: Qwen draft → Claude Haiku TR akademik rötuş | DM-003 + DM-015 | LiteLLM router |
| LVR validator zorunlu (K5, ≥0.7 cümle-düzey) | B42-045 K5 | curator post-process |
| `summary_cache` Supabase tablo + Redis 24h paralel | DM-006 + master §5 | 2-katlı cache |
| Faithfulness gate: jsonschema=100% + minicheck≥0.7 + alce≥0.8 — fail ise retry 1× | C3-C5 + R9 | quality gate |
| Token budget: Qwen 4K input + 1K output; Claude 1K input + 800 output | DM-010 + master §6.4 | cost cap |
| Tier quota: detailed mode LLM token saymalı (Öğrenci 50K/ay) | B42-049 §1 | user_quota update |
| K1 enforce: özet metninde `(YYYY)` yıl ifadesi sadece `year_verified=true` paper'lar için | B42-045 K1 | post-process scrub |
| `is_ghost=true` paper için detailed mode → 503 ghost_summary_unavailable | DM-005 (ghost dar kullanım) | guard |

---

## §2 Endpoint sözleşmesi (tam OpenAPI)

```yaml
POST /api/summarize
content-type: application/json
authorization: Bearer <supabase_jwt>

request:
  type: object
  required: [paper_id, mode]
  properties:
    paper_id:  { type: string, pattern: "^W[0-9]+$" }   # OpenAlex Work ID
    mode:      { type: string, enum: [abstract, detailed], default: abstract }

response 200 (mode=abstract — sync):
  type: object
  properties:
    paper_id:        { type: string }
    mode:            { const: abstract }
    summary:         { type: string }                  # mevcut abstract direkt
    citations_lvr:   { type: array, default: [] }      # abstract için boş
    cached:          { type: boolean }
    latency_ms:      { type: integer }

response 202 (mode=detailed — async):
  type: object
  properties:
    task_id:   { type: string, format: uuid }
    eta_s:     { type: integer }                       # tipik 25-30s
    poll_url:  { type: string }                        # /api/summarize/{task_id}

GET /api/summarize/{task_id}:
response 200:
  type: object
  properties:
    status:     { type: string, enum: [queued, running, done, failed] }
    summary:    { type: object, nullable: true }       # SummaryDoc (status=done)
    error:      { type: string, nullable: true }      # status=failed
    progress:   { type: number, minimum: 0, maximum: 1 }

SummaryDoc:
  type: object
  properties:
    text:           { type: string }                   # 200-400 kelime TR
    citations_lvr:                                     # cümle-düzey atıf (K5)
      type: array
      items:
        type: object
        required: [sentence, paper_id, span, lvr_distance]
        properties:
          sentence:      { type: string }
          paper_id:      { type: string }
          span:          { type: array, items: { type: integer }, minItems: 2, maxItems: 2 }
          lvr_distance:  { type: number, minimum: 0.7, maximum: 1 }
    faithfulness_meta:
      type: object
      properties:
        jsonschema_pct:   { const: 100 }
        minicheck_nli:    { type: number, minimum: 0.7 }
        alce_recall:      { type: number, minimum: 0.8 }
    model_chain:    { type: array, items: { type: string } }   # ["qwen2.5-7b", "claude-haiku-4-5"]
    token_usage:    { type: object }
    generated_at:   { type: string, format: date-time }

errors:
  404 paper_not_found
  422 schema_invalid
  429 quota_exceeded                  # detailed mode + user_quota %100
  503 ghost_summary_unavailable       # is_ghost=true + mode=detailed
  503 llm_unavailable                 # HF + Claude ikisi de fail (retry 1× sonrası)
  500 lvr_validation_failed           # cümle-düzey atıf <0.7 (retry 1×, sonra fail)
```

---

## §3 İmplementasyon adımları (atomik P-numara)

| P | İş | Dosya | LOC | Test |
|---|---|---|---|---|
| **P017** | Celery + Redis broker config + task base | `api/workers/celery_app.py` | ~80 | unit: task enqueue + status track |
| **P018** | `summary_cache` Supabase migration + Redis wrapper 24h | `db/migrations/0003_summary.sql` + `api/db/redis_client.py` (extension) | ~80 | unit: cache miss → fetch → cache hit |
| **P019** | `/api/summarize` route — abstract mode (sync) + detailed enqueue (async) | `api/routes/summarize.py` + `api/models/summarize.py` | ~150 | integration: 200 abstract + 202 detailed |
| **P020** | Celery task: Qwen draft → Claude Haiku TR rötuş → LVR validate | `api/workers/tasks/summarize_task.py` | ~180 | integration: end-to-end task < 30s |
| **P021** | SummaryDoc curator: Outlines JSON şema + LVR validator + K1 yıl scrub | `api/services/summary_curator.py` | ~140 | unit: LVR <0.7 → retry; year_verified=false → scrub |
| **P022** | Faithfulness gate (MiniCheck NLI + ALCE recall) | `api/services/faithfulness_gate.py` | ~120 | unit: pass + fail örneği |
| **P023** | Poll GET `/api/summarize/{task_id}` + status state machine | `api/routes/summarize.py` (extension) | ~60 | integration: queued → running → done |

---

## §4 Verification (komut + beklenen output, 6 manuel smoke senaryosu)

```bash
# S1: Unit summarize pipeline
pytest tests/unit/ -v -k "summarize or summary_curator or faithfulness"
# Beklenen: ≥15 PASS; "test_lvr_distance_07_required PASSED"; "test_year_verified_false_scrub PASSED"

# S2: Abstract mode (sync, no LLM)
curl -X POST http://localhost:8000/api/summarize \
  -H "Authorization: Bearer $JWT" \
  -d '{"paper_id":"W123","mode":"abstract"}'
# Beklenen: 200 + summary == abstract metni; cached=false (ilk çağrı); latency_ms < 200

# S3: Detailed mode (async, Celery)
TASK=$(curl ... -d '{"paper_id":"W123","mode":"detailed"}' | jq -r .task_id)
# Beklenen: 202 + task_id + eta_s ≤ 30 + poll_url

curl http://localhost:8000/api/summarize/$TASK
# t=0s:  {"status":"queued","progress":0}
# t=5s:  {"status":"running","progress":0.4}
# t=25s: {"status":"done","summary":{...},"progress":1}

# S4: Detailed mode SummaryDoc kontratı
SUMMARY=$(curl ... | jq .summary)
echo $SUMMARY | jq '.faithfulness_meta'
# Beklenen: jsonschema_pct == 100, minicheck_nli ≥ 0.7, alce_recall ≥ 0.8

echo $SUMMARY | jq '.citations_lvr | map(.lvr_distance) | min'
# Beklenen: ≥ 0.7 (K5)

echo $SUMMARY | jq '.text' | grep -oE "\([0-9]{4}\)" 
# Beklenen: sadece year_verified=true paper'lar için yıl yer alır (K1)

# S5: Ghost paper detailed mode reddi
curl ... -d '{"paper_id":"GHOST_OA_W4567","mode":"detailed"}'
# Beklenen: 503 + body {error: "ghost_summary_unavailable", reason: "DM-005"}

# S6: Cache hit (24h)
curl ... -d '{"paper_id":"W123","mode":"detailed"}'   # 2. çağrı
# Beklenen: 200 (sync, çünkü cache hit) + cached=true + latency_ms < 100

# S7: Quota exceeded (429)
# user_quota.token_used_mtd = 49500, detailed task ~1000 token → aşacak
curl ... -d '{"paper_id":"W123","mode":"detailed"}'
# Beklenen: 429 + Retry-After (next month start)

# S8: LVR validation fail → retry 1× → 500
# Mock LLM kötü atıf üretsin (lvr_distance=0.3) → ilk gen fail, retry 1× hala fail
curl ... | jq .summary
# Beklenen poll: status=failed + error="lvr_validation_failed_after_retry"; Sentry trace_id
```

---

## §5 Critical files

### Backend touch
- `api/routes/summarize.py` (POST + GET poll)
- `api/models/summarize.py` (Request + SummaryDoc Pydantic)
- `api/workers/celery_app.py` — TODO(sercan)
- `api/workers/tasks/summarize_task.py` (Qwen → Claude → curator)
- `api/services/summary_curator.py` (Outlines + LVR + K1 yıl scrub)
- `api/services/faithfulness_gate.py` (MiniCheck NLI + ALCE recall)
- `api/db/redis_client.py` (extension: `sum:` namespace 24h)
- `db/migrations/0003_summary.sql` (`summary_cache`)

### Tests touch
- `tests/unit/test_summary_curator.py` + `test_faithfulness_gate.py`
- `tests/integration/test_summarize_celery.py` (S3 end-to-end + S5 ghost reject)
- `tests/quality/test_lvr_audit.py` (10 paper × detailed → LVR ≥0.7)

### Read-only
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-045-MIMARI-V1.md` (K1 + K5)
- `~/Desktop/papermind-app/docs/plans/F1_master_plan.md`
- `~/Desktop/papermind-app/docs/plans/F3a_search.md` (Curator + LiteLLM ortak)
- `~/Desktop/papermind-app/docs/DM_RULES.md`

---

## §6 TODO(sercan)

### 6.1 Infrastructure
- [ ] Celery worker container (Render service ayrı veya same Dockerfile + supervisor)
- [ ] Redis broker namespace ayrımı: cache (`sum:`) vs broker (`celery_*`)
- [ ] `summary_cache` Supabase tablo + index (paper_id, mode, generated_at)

### 6.2 Code
- [ ] P017-P023 sırasıyla atomik commit
- [ ] Outlines JSON şema `summary_doc.json` (text + citations_lvr + faithfulness_meta)
- [ ] LiteLLM 2-kademeli flow: Qwen draft → Claude rötuş (`huggingface/tgi` + `claude-haiku-4-5`)
- [ ] LVR validator: her cümle için Pinecone neighbor query → distance ≥ 0.7 mi
- [ ] Faithfulness gate: MiniCheck NLI fine-tune indir + ALCE recall hesapla
- [ ] K1 yıl scrub: regex `\((\d{4})\)` → paper.year_verified yoksa drop
- [ ] Retry 1× LVR fail veya gate fail → ikinci kez aynı kötü çıkarsa 500 + sentry

### 6.3 Tests + Quality
- [ ] Unit ≥15 PASS
- [ ] Integration S2-S6 PASS
- [ ] LVR audit 10 paper × detailed mode (S8 control)
- [ ] Faithfulness pass rate ≥%95 (5 paper'da gate FAIL kabul, retry kurtarır)
- [ ] LLM token usage user_quota tablosuna doğru artıyor mu

### 6.4 Auth + Observability
- [ ] Authorization JWT aynı middleware
- [ ] Rate limit: detailed endpoint daha sıkı (Öğrenci 5 detailed/saat)
- [ ] Sentry breadcrumb: qwen_ms, claude_ms, lvr_ms, gate_ms, total_ms
- [ ] Celery flower (lokal monitoring) opsiyonel

---

## §7 Commit disiplini

- **Branch**: `feat/F3-summarize-celery`
- **Atomic commit**: P017..P023 ayrı commit + ayrı PR
- **Pre-flight Read**: §5 listesi
- **Test gate**: §4 S1-S8 PASS olmadan merge **YASAK**
- **Co-Authored-By**: Claude Opus 4.7
- **Commit message**: `[P0XX] api/summarize: <kısa>` (örn. `[P020] api/summarize: Celery task Qwen+Claude+LVR`)

---

## §8 Önkoşullar — GÜNCEL DURUM (2026-04-30)

### ✅ Kapanmış
| Önkoşul | Kapanış |
|---|---|
| OPEN-001 LLM model | ✅ B-005..B-007 (Qwen anlama + Claude Haiku 4.5 TR rötuş yedek) |
| Supabase static facts + PaperCard | ✅ B-003 + B-008 (summarize'in `papers` mirror lookup'ı için hazır) |

### ⏳ F3a bağımlı
| Önkoşul | Statü |
|---|---|
| F3a P004 (LiteLLM router) merge | ⏳ F3a PR |
| F3a P008 (Curator + LVR validator) merge | ⏳ F3a PR (faithfulness gate ortak servis — F3c P022 ile birleştirilebilir, B grubu refactor) |

### ⏳ Aktif engelleyiciler
| Önkoşul | Statü | Kim |
|---|---|---|
| HF Endpoint + Claude API key (.env) | ⏳ | Sercan setup |
| MiniCheck NLI model checkpoint indir | ⏳ | Sercan |
| ALCE eval script | ⏳ | Sercan |
| OPEN-006 Cache TTL detailed mode (24h master, 90d DM-006 L1) | ⏳ | Omer F6 öncesi |
| Supabase migration `0006_summary.sql` (summary_cache) | ⏳ | F3c P018 |

---

**Final commitment**: F3a tamamlandıktan sonra P017..P023 3-4 günde curl ile end-to-end (S3) PASS olur.
