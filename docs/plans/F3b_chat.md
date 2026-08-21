# F3b — Mini-Plan: POST /api/chat (SSE)

> **Statü**: TASLAK — F1' master plan onayı sonrası (B-001 §16)
> **Üst plan**: `docs/plans/F1_master_plan.md`
> **Şablon**: ARCHITECT_PROMPT_TEMPLATE §0..§7 + WhatsApp checklist
> **Owner**: Sercan (backend code) · Claude (verify + intent extraction audit) · Omer (margin eşiği OPEN-005)

---

## §0 Bağlam (3 cümle)

E2 "Kütüphaneci" ekranının arka ucu — kullanıcı doğal dil mesajı gönderir, Listener (Qwen) konuşmayı çok-turn anlar, **IntentPMID** (12-segment partial PMID) çıkarır, margin altıysa clarify event ile soru sorar, üstüyse `topic_lock` accept eder. Niş ayrım: jenerik chat değil — her token cümle-düzey atıf taşıyabilir, halüsinasyon-sıfır + topic-lock state machine (B42-049 §2.1, MVP'de 3-state). SSE first-token < 2s; mesaj başına context cap 8K token (Qwen baseline); LVR atıf zorunluluğu Curator gibi katı değil (free-text dialog) ama PMID önerisi çıkıyorsa `pmid_segments` JSON şeması Outlines ile zorunlu.

---

## §1 Karar günlüğü

| Karar | Kaynak | Etki |
|---|---|---|
| SSE (Server-Sent Events) — token streaming | so2.txt §1, FastAPI native `StreamingResponse` | `api/routes/chat.py` |
| 5 SSE event tipi: `token` / `intent_pmid` / `clarify` / `lock` / `done` | master §4.2 | response shape |
| Listener Qwen multi-turn context window 8K (DM-010 baseline) | so2.txt §1 + DM-010 | `api/services/listener.py` |
| IntentPMID 12-segment partial format `D.F.S.T1.T2.T3.Y.Q.I.L.R.V` | B42-045 K6 | extraction logic |
| Margin eşiği `pmid_match_score < OPEN-005` → clarify event | OPEN-005 (Omer) | branch logic |
| Topic-lock 3-state `suggested → accepted → released` (MVP simplified) | B42-049 §2.1 + master §6.3 | `chat_sessions.lock_state` |
| `chat_messages` Supabase tablo + RLS (`user_id = auth.uid()`) | master §5 | persist her mesaj |
| First-token < 2s (HF Endpoint warm assumption — DM-010 keep-alive 240s) | master §3 + C7 ≥%95 warm | bench bekleme |
| Faithfulness MVP'de chat'e zorunlu DEĞİL (free dialog) — sadece `intent_pmid` JSON şema enforce | K4/K5 esneklik | curator opt |

---

## §2 Endpoint sözleşmesi (tam OpenAPI)

```yaml
POST /api/chat
content-type: application/json
authorization: Bearer <supabase_jwt>
accept: text/event-stream

request:
  type: object
  required: [message]
  properties:
    session_id:  { type: string, format: uuid, nullable: true }    # null → yeni oturum oluştur
    message:     { type: string, minLength: 1, maxLength: 4000 }

response 200 (SSE stream):
  content-type: text/event-stream
  events:
    - event: session
      data: { session_id: uuid, created: bool }                    # ilk event
    - event: token
      data: { delta: string }                                       # n kez
    - event: intent_pmid
      data:
        pmid_segments:                                              # 12-segment partial
          D: string|null, F: string|null, S: string|null,
          T1: string|null, T2: string|null, T3: string|null,
          Y: string|null, Q: string|null, I: string|null,
          L: string|null, R: string|null, V: string|null
        pmid_match_score: number                                    # 0..1
    - event: clarify                                                # margin altı (< OPEN-005)
      data:
        question: string
        options:                                                    # 2-4 seçenek
          type: array
          items: { type: string }
    - event: lock                                                   # margin üstü → kabul
      data:
        topic_id: uuid
        lock_state: { type: string, enum: [suggested, accepted] }
    - event: done
      data: { latency_ms: int, tokens_emitted: int }

errors (HTTP başlık + tek event 'error'):
  422: schema_invalid                  # Pydantic
  401: jwt_expired
  429: quota_exceeded                  # tier %100 LLM token (B42-049 §1)
  503: llm_unavailable + retry_after   # HF cold start fail
```

---

## §3 İmplementasyon adımları (atomik P-numara)

| P | İş | Dosya | LOC | Test |
|---|---|---|---|---|
| **P010** | `chat_sessions` + `chat_messages` + `topic_locks` Supabase migration + RLS | `db/migrations/0002_chat.sql` | ~120 | RLS audit (anon kullanıcı OWN sessions only) |
| **P011** | Listener — Qwen multi-turn manager (8K context window + history truncation) | `api/services/listener.py` (genişletme) | ~150 | unit: 3-turn conversation + history cap |
| **P012** | IntentPMID extractor — Outlines JSON şema 12-segment partial | `api/services/intent_pmid.py` | ~140 | unit: 12-segment + null + wildcard `*` |
| **P013** | Topic-lock state machine (3-state MVP) | `api/services/topic_lock.py` | ~120 | unit: suggested→accepted→released + invalid transitions |
| **P014** | SSE route + 5 event tipi + EventStream encoding | `api/routes/chat.py` + `api/models/chat.py` | ~180 | integration: tüm 5 event sıralı yayın |
| **P015** | Margin branch logic (clarify vs lock) — OPEN-005 eşik parametrik | `api/services/chat_orchestrator.py` | ~100 | unit: score=0.45 → clarify; score=0.85 → lock |
| **P016** | Persist mesaj + LLM token usage → user_quota update | `api/services/chat_persist.py` | ~80 | integration: 100 token mesaj → user_quota +100 |

---

## §4 Verification (komut + beklenen output, 6 manuel smoke senaryosu)

```bash
# S1: Unit chat pipeline
pytest tests/unit/ -v -k "chat or listener or intent_pmid or topic_lock"
# Beklenen: ≥20 PASS; "test_pmid_segments_outlines_schema PASSED"

# S2: SSE happy path (single-turn, lock branch)
curl -N -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $JWT" \
  -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"message":"yapay zeka ile depresyon tedavisi üzerine son 5 yıllık çalışmalar"}'
# Beklenen sıra (ilk 200ms içinde):
#   event: session, data: {session_id: "...", created: true}
#   event: token, data: {delta: "Anladım, "}    (~50 kez)
#   event: intent_pmid, data: {pmid_segments: {D:"med", F:"psy", T1:"depresyon", T2:"yapay-zeka", Y:"2020-2025", ...}, pmid_match_score: 0.87}
#   event: lock, data: {topic_id: "...", lock_state: "suggested"}
#   event: done, data: {latency_ms: <5000, tokens_emitted: ...}

# S3: Margin altı → clarify
curl -N ... -d '{"message":"makine"}'   # belirsiz tek kelime
# Beklenen: pmid_match_score < OPEN-005 → event: clarify
#   data: {question: "Hangi alanda?", options: ["Tıp", "Mühendislik", "Bilgisayar Bilimi"]}
#   lock event YOK (henüz)

# S4: Multi-turn (clarify → user yanıt → lock)
SESSION_ID=$(curl ... -d '{"message":"yapay zeka"}' | grep session_id | jq -r .data.session_id)
curl -N ... -d "{\"session_id\":\"$SESSION_ID\",\"message\":\"Tıpta\"}"
# Beklenen: history Listener'a 8K içinde geçer; pmid_segments daha keskin; lock event yayınlanır

# S5: First-token latency
time curl -N ... -d '{"message":"derin öğrenme"}' | head -2
# Beklenen: ilk 'event: token' satırı < 2000ms (HF warm)

# S6: Quota exceeded (429)
# user_quota.token_used_mtd = 50000 (Öğrenci limit) varken:
curl -N ... -d '{"message":"merhaba"}'
# Beklenen: HTTP 429 + Retry-After header + body {error: "quota_exceeded", reset_at: "2026-05-01T00:00:00Z"}

# S7: HF cold start fallback (503)
docker compose stop hf-mock
curl -N ... -d '{"message":"test"}'
# Beklenen: HTTP 503 + Retry-After: 60 (Sentry trace_id)

# S8: RLS — başka user'in session'ına erişim yasak
SESSION_ALICE=...
curl ... -H "Authorization: Bearer $JWT_BOB" -d "{\"session_id\":\"$SESSION_ALICE\",\"message\":\"x\"}"
# Beklenen: 403 (RLS reject) veya 404 (Bob'un perspektifinden yok)
```

---

## §5 Critical files

### Backend touch
- `api/routes/chat.py` (SSE endpoint)
- `api/models/chat.py` (Pydantic Request + EventTypes)
- `api/services/chat_orchestrator.py` (clarify/lock branch)
- `api/services/intent_pmid.py` (Outlines 12-segment)
- `api/services/topic_lock.py` (3-state machine)
- `api/services/chat_persist.py` (chat_messages + user_quota)
- `api/services/listener.py` (multi-turn extension — F3a P004'ten devam)
- `db/migrations/0002_chat.sql` (chat_sessions + chat_messages + topic_locks RLS)

### Tests touch
- `tests/unit/test_chat.py` + `test_intent_pmid.py` + `test_topic_lock.py`
- `tests/integration/test_chat_sse.py` (S2-S6 SSE event order)
- `tests/integration/test_chat_rls.py` (S8)

### Read-only
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-045-MIMARI-V1.md` (PMID 12-segment K6)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-049-PROJECT-LIFECYCLE.md` (topic-lock state)
- `~/Desktop/papermind-app/docs/plans/F1_master_plan.md`
- `~/Desktop/papermind-app/docs/plans/F3a_search.md` (Listener + LiteLLM zaten orada)
- `~/Desktop/papermind-app/docs/HEDEF.md` (E2 ekran tanımı)

---

## §6 TODO(sercan)

### 6.1 Infrastructure
- [ ] Supabase migration 0002_chat (chat_sessions + chat_messages + topic_locks)
- [ ] RLS policy: `auth.uid() = user_id` her satırda
- [ ] `user_quota.token_used_mtd` increment trigger (chat sonrası)

### 6.2 Code
- [ ] P010-P016 sırasıyla atomik commit
- [ ] SSE EventStream encoding (Python `yield f"event: {type}\ndata: {json}\n\n"`)
- [ ] Outlines JSON şema `intent_pmid.json` (12-segment + null + `*` enum)
- [ ] OPEN-005 margin eşiği `.env` değişkeni (varsayılan 0.7, Omer onayı sonrası net)
- [ ] Listener history truncation: en eski 1-2 turn drop, system prompt + last 6 turn + current message ≤ 8K token
- [ ] LLM token sayımı tiktoken (Qwen tokenizer eşdeğer)

### 6.3 Tests + Quality
- [ ] Unit ≥20 PASS
- [ ] SSE integration: 5 event sıralı + content-type doğru
- [ ] First-token < 2s bench (10 örnek medyan)
- [ ] RLS audit: cross-user session erişim → 403/404 (S8)
- [ ] LLM token usage `user_quota` tablosuna doğru artıyor mu (5 mesaj × 200 token = 1000)

### 6.4 Auth + Observability
- [ ] JWT verify aynı F3a middleware
- [ ] Rate limit: tier-bazlı sliding window (Öğrenci 30 chat req/saat)
- [ ] Sentry breadcrumb: listener_ms, intent_extract_ms, sse_total_ms
- [ ] `X-Trace-Id` header her response

---

## §7 Commit disiplini

- **Branch**: `feat/F3-chat-sse`
- **Atomic commit boundary**: P010..P016 ayrı commit + ayrı PR
- **Pre-flight Read**: §5 Read-only + B42-049-PROJECT-LIFECYCLE.md (topic-lock)
- **Test gate**: §4 S1-S8 PASS olmadan PR merge **YASAK**
- **Co-Authored-By**: Claude Opus 4.7
- **Commit message**: `[P0XX] api/chat: <kısa öz>` (örn. `[P014] api/chat: SSE 5-event endpoint`)
- **PR template**: master §13 standart

---

## §8 Önkoşullar — GÜNCEL DURUM (2026-04-30)

### ✅ Kapanmış
| Önkoşul | Kapanış |
|---|---|
| OPEN-001 LLM model | ✅ B-005 + B-006 + B-007 (anlama Qwen, sunum Cosmos TR / Qwen EN+ID) |
| Supabase init + schema_v1 | ✅ B-002 (12 tablo + 19 RLS + 9 trigger) |
| PaperCard + GhostCard upload | ✅ B-008 (24.86M + 31.85M ≈ 28 GB) |

### ⏳ F3a bağımlı (sırayla merge olunca açılır)
| Önkoşul | Statü |
|---|---|
| F3a P001 (auth middleware) merge edilmiş | ⏳ F3a PR |
| F3a P004 (Listener + LiteLLM router) merge edilmiş | ⏳ F3a PR |

### ⏳ Aktif engelleyiciler
| Önkoşul | Statü | Kim |
|---|---|---|
| OPEN-005 margin eşiği (default 0.7, F5 öncesi netleşir) | ⏳ | Omer F5 öncesi |
| HF Inference Endpoint warm (Qwen + keep-alive 240s) | ⏳ | Sercan setup |
| Supabase migration `0005_chat.sql` (chat_sessions + chat_messages + topic_locks RLS) | ⏳ | F3b P010 |

---

**Final commitment**: F3a tamamlandıktan sonra bu mini-plan üzerine F3 sprint başlar; P010..P016 4-5 günde curl SSE ile çalışır (master §9 F3 süresi).
