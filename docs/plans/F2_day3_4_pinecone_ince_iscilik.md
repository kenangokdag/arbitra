# F2 Day 3-4 — Pinecone Sonrası İnce İşçilik (Backend Sprint)

> **Kapsam:** B-012 ✅ KAPANDI sonrası F2 backend "Pinecone-bağımlı parçaları concrete'e dönüştürme + Day 4 wrap" alt-sprint planı.
> **Önkoşul:** F2 Day 1 (B-014, 8 commit lokal) + F2 Day 2 (B-018, 6 atomic commit + 121/121 PASS) + B-012 (mdv1 ns 24,866,945 vec × 8-meta).
> **Hedef:** Day 4 wrap sonunda F2 sprint (Master plan §9 4-5 gün) **kod tarafından %100 KAPANDI**, sadece Sercan post-hoc PR review batch kalır.
> **Süre:** 2 gün × ~8h aktif kod = ~16h. ~6-7 atomic commit, ~1100 LOC.
> **Plan-first:** Bu manifest §0..§10 yapısıyla yazılmıştır. Plan dışı edit yasak — gerekiyorsa bu dosya revize edilir, kullanıcı `plan revize onaylandı` der, sonra kod.

---

## §0 Bağlam ve plan mantığı

F2 Day 1+2'de Pinecone-bağımsız tüm parçalar concrete halde: P000-P005 + P007 + P009 + P010 search route + P008 iskelet + 6 endpoint 501-stub + faithfulness_gate ortak servis level=SEARCH aktif. Day 3-4'te eksik 4 parça (Pinecone-bağımlı):

1. **P006 HybridPoolRouter concrete** — 3-havuz RRF k=60, Pinecone metadata 8-field HARD filter (`$in` D/F/S, `$gte` year/q_weak/v_conf), Postgres title FTS lexical, theme dim_theme_embedding pgvector. **Engelleyiciydi: B-012 metadata patch koşumu** → şimdi açık (mdv1 ns).
2. **P008 LVR validate gerçek** — Curator citation neighbor distance Pinecone query ile (mock 0.85 yerine canlı). Ortak servis `faithfulness_gate.py` LVR placeholder dolar.
3. **F3 6 TODO concrete** — `/api/chat` (P020 SSE) + `/api/summarize` POST+GET (P022) + `/api/enrich` (P031) + `/api/reading-list` 4 metod (P035) + `/api/onboarding` (P046) + `/api/top5` (P050). 501→200, Pydantic forbid + happy path + Sercan handoff TODO yorumları.
4. **P011-P015 resilience patches** (2026-05-01 plan-revize, Council 39) — dış servis dayanıklılığı: timeout + retry+jitter native asyncio (tenacity/pybreaker yeni dep yasak — Council 39 K4 YELLOW), Pinecone+Supabase wrapper, search route try/except 503/504 mapping + gate_warnings "degraded_mode", runbook 4 iskelet. P014 circuit breaker KD-36 olarak F7 P065'e ertelendi (1-kişi MVP'de erken).
5. **Faithfulness calibration fixture + Sercan handoff packet** — Day 4 wrap.

**Hibrit workflow** (Council 22, B-014): atomic lokal commit-per-slice; push timing Omer kontrolünde. Sprint sonu Sercan PR review batch'inde GitHub'a push.

---

## §1 Önkoşullar (kod başlamadan doğrulanır)

| # | Şey | Doğrulama yöntemi | Beklenen |
|---|---|---|---|
| 1 | B-012 mdv1 namespace canlı | `idx.describe_index_stats()` Console veya Colab | mdv1 = 24,866,945 |
| 2 | Day 2 8+6 commit lokal `feat/F2-search-skeleton` | `git log --oneline feat/F2-search-skeleton \| head -20` | 14 commit zinciri görünür |
| 3 | `.venv` aktif + 121/121 PASS | `make test` | 121 pass |
| 4 | `mypy strict` clean | `make typecheck` | 32 source file no issues |
| 5 | Smoke fixture'lar var | `ls tests/fixtures/{hf_qwen_tr_query,pinecone_describe,supabase_schema_migrations}.json` | 3 dosya |
| 6 | Supabase RLS schema_migrations fix | (Akşam Omer; Day 3 başlamadan ÖNCE değil — Day 4 wrap'e kadar bekleyebilir; F2 kod akışını engellemiyor) | 0006 migration veya tek satır SQL |

**Engelleyici yok.** Day 3 başlayabilir.

---

## §2 Atomik commit zinciri (6 commit, ~1100 LOC)

| # | Commit | İş | Dosya(lar) | LOC | Council |
|---|---|---|---|---|---|
| 1 | `[migration]` | 0005 papers title FTS + lazy-fill cron stub | `db/migrations/0005_papers_title_fts.sql` + `api/workers/papers_lazy_fill.py` | ~80 | (zaten Council 25 onaylı) |
| 2 | `[P011]` | resilience.py (timeout + retry+jitter native asyncio, sync+async dual API) + Pinecone client integration + PineconeIndexWrapper singleton fix (pool_router her fan_out'ta yeniden instantiate etmesin) | `api/utils/resilience.py` (yeni) + `api/db/pinecone_client.py` (delta) + `api/services/pool_router.py` (delta) + 6 unit | ~120 | 39 |
| 3 | `[P012]` | Supabase client timeout + retry wrapper (postgrest_client_timeout=10 + tenacity-free retry) | `api/db/supabase_client.py` (delta) + 4 unit | ~50 | 39 (alt) |
| 4 | `[P013]` | search route try/except + 503 pinecone_unavailable / 503 retrieval_degraded / 504 listener_timeout / 500 mapping + gate_warnings "degraded_mode" flag | `api/routes/search.py` (delta) + 4 integration | ~60 | 39 (alt) |
| 5 | `[P015]` | Runbook 4 iskelet (symptom / first-check / mitigation / rollback) | `docs/runbook/{pinecone_down,supabase_down,hf_endpoint_down,search_p95_breach}.md` | ~250 (doc) | (council yok — runbook doc) |
| 6 | `[P006]` | HybridPoolRouter concrete (3-havuz RRF + Pinecone HARD filter + Postgres FTS + theme pgvector) — sertleşmiş wrapper kullanır (P011 önceliği) | `api/services/pool_router.py` + 14 unit + 3 integration | ~280 | 35 |
| 7 | `[P008-LVR]` | Curator LVR validate gerçek (Pinecone neighbor query) + faithfulness_gate.py LVR placeholder dolar | `api/services/curator.py` + `api/services/faithfulness_gate.py` (delta) | ~120 | 36 |
| 8 | `[F3-routes]` | 6 TODO route concrete (chat SSE + summarize POST+GET + enrich + reading-list 4 method + onboarding + top5) | `api/routes/{chat,summarize,enrich,reading_list,onboarding,top5}.py` (delta her birinde) + 6 integration | ~600 | 37 (alt-§ × 6) |
| 9 | `[calibration]` | faithfulness_calibration fixture (100 paper × ground-truth) + threshold tuning script | `tests/fixtures/faithfulness_calibration.json` + `scripts/calibrate_faithfulness.py` | ~150 | 38 |
| 10 | `[handoff]` | Sercan handoff packet README + polish gate CI rule (`grep TODO(P\| -r api/ \| wc -l == 0`) | `docs/backend/sercan_handoff_F2.md` + `.github/workflows/polish_gate.yml` | ~80 | (Day 4 wrap, council yok) |

**Sıralama mantığı (2026-05-01 plan-revize):** P011-P015 commit 2-5'e alındı (P006'dan önce). Mantık: P011 PineconeIndexWrapper singleton + timeout sertleştirir, P006 (commit 6) sertleşmiş wrapper'ı tüketir. P012 Supabase wrapper'ı sağlamlaştırır, P006 theme pool zaten Supabase kullanıyor. P013 search route exception mapping'i P006/P008-LVR/F3-routes hata düzlemiyle uyumlu kalır.

**Toplam:** ~1580 LOC + 18 unit + 13 integration = 31 yeni test (Day 1+2 121 + Day 3-4 31 = **152 toplam**). P014 circuit breaker → KD-36 (F7 P065 ertelendi, Council 39 K4 YELLOW).

---

## §3 Council 35-38 (kod öncesi 4 toplantı)

Day 3 sabahı her commit öncesi council §-tablosu (R13.4 + R13.9 alan sahibi sandalyesi). Tüm council'ler R13.10 HK-1..HK-7 + R13.11 dış servis empirik kanıt zorunlu kontrolü içerir.

### §Council 35 — P006 HybridPoolRouter concrete

**Bağlam:** F3a §3 P006 satırı 3-havuz RRF k=60. Lexical havuz Council 25'te `papers.title_tsv` Postgres FTS olarak donduruldu. Pinecone metadata 8-field B-012 ✅ kanıtlı (Console smoke). theme havuz 4,516 × 256-d dim_theme_embedding pgvector cosine.

| # | Rol | Bayrak | Not |
|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟡 | Pinecone HARD filter `$in/$gte` syntax SDK 8.1.2'de doğrulanmalı (smoke fixture'da 1 örnek yazılmalı). Eğer reddedilirse P006 fail. |
| 2 | Akademik İsabet | 🟢 | 3-havuz RRF (Pinecone semantic + Postgres lexical title + theme pgvector) MVP için yeterli, sparse Plan 2'ye ertelendi DM-016. |
| 3 | Fayda-Maliyet | 🟢 | Pinecone query latency 50-150ms × 3 paralel = ~150ms total; Postgres FTS title-only ~30ms; pgvector 256-d 4,516 row ~10ms. P-tile=200ms hedef altı. |
| 4 | Daha İyisi Var Mı? | 🟡 | RRF k=60 default; tier-aware k Faz 3'e ertelendi (KD-12). Şu an MVP yeterli. |
| 5 | Global Çözüm | 🟢 | Tek `pool_router.py` modül; F3a/b/c hepsi aynı modülü kullanır. |
| 6 | Son Kullanıcı | 🟢 | 3-havuz boş kalmaz (sparse Plan 2'ye ertelendi ama 3 havuz yine var). |
| **A** | **Sercan (BAĞLAYICI, post-hoc)** | 🟡 | Pinecone 8.1.2 SDK metadata filter syntax canlı smoke + asyncio.gather ile 3 paralel havuz; httpx connection pool reuse; Pydantic `PoolRouterConfig` extra=forbid. |

**Empirik test gerekli mi?** EVET — `tests/fixtures/pinecone_metadata_filter.json` 3 query × 3 filter kombinasyonu (D=$in / year=$gte / q_weak=$gte). P006 commit öncesi smoke geçmeli.

**Karar (önerilen):** İlerle. Pinecone metadata filter smoke fail ise filter argümanı opsiyonel hale getirilir + Known Debt KD-29 kayıt.

### §Council 36 — P008 LVR validate gerçek

**Bağlam:** B-018 P008 iskelet'inde LVR placeholder 0.85. Şimdi Pinecone neighbor query ile gerçek LVR ölçülür: claim cümlesinin BGE-M3 dense embedding'i çıkarılır → mdv1 ns top-10 query → en yakın 10 sentence_role evidence ile LVR distance hesaplanır (1 - cosine_sim). Eşik 0.7 (B42-045 §1).

| # | Rol | Bayrak | Not |
|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟡 | LVR threshold 0.7 keyfi; Day 4 calibration fixture sonrası ayarlanmalı. P008'de TODO(KD-31) marker. |
| 2 | Akademik İsabet | 🟢 | LVR (Linguistic Variant Retrieval) BGE-M3 dense neighbor pratik standart. |
| 3 | Fayda-Maliyet | 🟢 | claim başına 1 BGE-M3 encode (CPU/MPS ~50ms) + 1 Pinecone query (~50ms) = ~100ms; faithfulness_gate `level=SEARCH` zaten 13-key signal aggregate'inde maliyet kabul. |
| 4 | Daha İyisi Var Mı? | 🟡 | MiniCheck v2 5B daha güçlü ama Faz 3 (KD-14). MVP'de LVR yeterli. |
| 5 | Global Çözüm | 🟢 | `faithfulness_gate.check(level=SEARCH)` LVR placeholder satırı tek yerde dolar. |
| 6 | Son Kullanıcı | 🟡 | LVR fail → G3 gate_warning gösterilir (UI'da "kanıt mesafesi yüksek" rozeti). |
| **A** | **Sercan (BAĞLAYICI, post-hoc)** | 🟢 | BGE-M3 model lazy-load (P007'deki pattern paralel); Pinecone neighbor query httpx pool reuse; LVR cache Redis 1h TTL `lvr:<sha256(claim)[:32]>`. |

**Empirik test gerekli mi?** EVET — `tests/fixtures/lvr_calibration_sample.json` 20 claim × ground-truth (yüksek/düşük LVR örnekleri).

**Karar (önerilen):** İlerle. KD-31: threshold tuning Day 4 wrap.

### §Council 37 — F3 6 TODO route concrete

**Bağlam:** B-018'de 6 endpoint 501-stub yazıldı. Şimdi her birinin happy path concrete'e dönüşür. Her endpoint için ayrı alt-§ tablosu (R13.4); 6 alt-toplantı tek council §.

**Genel kararlar (6 endpoint için ortak):**
- Pydantic `extra=forbid` (HK-1) tüm request/response modeller
- happy path + 422 validation error + 401 auth + 5xx graceful
- Redis cache anahtarları deterministik SHA-256 (B-018 P010 paralel)
- Faithfulness gate `level=SUMMARY` summarize endpoint'inde aktive (NotImplementedError → gerçek MiniCheck v2 5B HF endpoint Faz 3'e ertelendi → MVP'de jsonschema 100% + LVR cascade kullanılır, F3c spec'i KD-14)
- SSE chat endpoint'i Cosmos endpoint setup öncesi Qwen2.5 fallback kullanır (B-007 Yol A)

**Alt-§ özetleri (her biri ayrı §-toplantı, kısa form):**

| Alt | Endpoint | Concrete Highlights |
|---|---|---|
| 37a | `/api/chat` SSE | EventSource stream + Qwen2.5 endpoint (B-007); Cosmos TR endpoint hazır olmazsa Qwen TR fallback (lang routing); chat_sessions Supabase RLS write; LVR validation her token bloğunda |
| 37b | `/api/summarize` POST+GET | POST: Celery task queue (B-010 spec); GET: poll status (pending/done); cache key `sum:<paper_id>:<lang>:<mode>`; faithfulness level=SUMMARY |
| 37c | `/api/enrich` | OpenAlex API polite pool + 7d Redis TTL; ghost_card lazy-fill background; reading_list bağımlısı |
| 37d | `/api/reading-list` 4 metod | GET (paginated 50/page), POST (RLS user_id), PATCH (status enum), DELETE (soft-delete is_deleted=true) |
| 37e | `/api/onboarding` | Supabase RLS user_profiles UPSERT; magic-link SMTP (Supabase auth); B-005 onboarding lang=TR/EN/ID |
| 37f | `/api/top5` | OPEN-005 margin scoring; cache 24h `top5:<user_id>:<sha256(profile)[:16]>`; reading_list ile join |

**Empirik test gerekli mi?** EVET — her endpoint için en az 1 happy path integration test + canlı smoke (chat: HF Qwen + reading-list: Supabase RLS).

**Karar (önerilen):** İlerle. Her alt-endpoint ayrı atomic commit OPSİYONEL — pratik olarak tek `[F3-routes]` commit altında 6 endpoint birden Day 4 sabahında tamamlanır (büyük commit ama pseudocode önceden yazılmış, hızlı).

### §Council 38 — Faithfulness calibration fixture + threshold tuning

**Bağlam:** B-018 P008+P008-LVR sonrası eşikler placeholder (LVR=0.7, MiniCheck=0.7, ALCE=0.8). Day 4 wrap'te 100 paper × ground-truth fixture ile 3 eşik kalibre edilir. Yöntem: 100 paper'ın 80'i tahmini ground-truth (yüksek LVR/MiniCheck) + 20'si negatif örnek (düşük); ROC eğrisi → AUC 0.85 hedef → optimal threshold seç.

| # | Rol | Bayrak | Not |
|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟡 | 100 paper ground-truth Omer manuel etiketleme; bias riski. Mitigation: hem TR hem EN paper karışımı; 3 alan (Health/Life/Physical). |
| 2 | Akademik İsabet | 🟢 | LVR + MiniCheck + ALCE 3-katlı cascade B42-045 §1 kanonik. |
| 3 | Fayda-Maliyet | 🟢 | 100 paper × 5dk = ~8h Omer iş (Day 4 yarım gün); MiniCheck v2 5B Faz 3'e ertelendi → MVP'de LVR + jsonschema yeterli. |
| 4 | Daha İyisi Var Mı? | 🟡 | LightGBM kalibrasyon Faz 2 — MVP'de manual ROC yeterli. |
| 5 | Global Çözüm | 🟢 | `config/faithfulness_thresholds.yaml` tek dosyada üç eşik. |
| 6 | Son Kullanıcı | 🟢 | KararBant `canon/strong/frontier/risk` 4-bant kullanıcıya gösterilir; kalibre eşikler bandların doğru kapsamasını garantiler. |
| **A** | **Sercan (BAĞLAYICI, post-hoc)** | 🟢 | YAML config hot-reload Faz 3; MVP'de restart yeterli; calibration script idempotent (rerun aynı sonuç). |

**Empirik test gerekli mi?** EVET — calibration fixture'ı **kendisi empirik kanıt**.

**Karar (önerilen):** İlerle. Threshold updates `config/faithfulness_thresholds.yaml`'a yansır + commit.

### §Council 39 — P011-P015 Resilience Patches (2026-05-01 plan-revize)

**Bağlam:** B-018'de Pinecone client 3-retry envelope var ama timeout/backoff yok → hang riski; Supabase client bare singleton (retry/timeout yok); search route try/except yok → exception=500 leak (F3a §2 plan'da 503 yazıyor ama route'ta yok); runbook/ klasörü boş. R13.10 HK-3 dış servis empirik kanıt gap'i. F4-S1.5 frontend 503 UX hatlarıyla uyum gerek.

**Alan:** Backend / dış servis dayanıklılığı  
**Alan sahibi (BAĞLAYICI, post-hoc):** Sercan

| # | Üye | Oy | Gerekçe | RED/YELLOW ise |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟢 | timeout/retry/breaker peer-reviewed (Hystrix/Polly/tenacity); Pinecone SDK 8.x `requests`/`urllib3` altında timeout config var; httpx zaten dep listesinde | — |
| 2 | Akademik İsabet | 🟢 | N/A (infra), R9 SLA p95<7s korunur | — |
| 3 | Fayda-Maliyet | 🟢 | ~2.5h iş; Pinecone serverless cold-start hang riski + Supabase eu-central-1 outage gerçek (2024 1-day Frankfurt) | — |
| 4 | Daha İyisi Var Mı? | 🟡 | tenacity + pybreaker yeni dep yerine **`asyncio.wait_for` + in-house 30-LOC breaker**; Omer 1-kişi + Sercan post-hoc → minimal dep tercih | Native asyncio + tek `api/utils/resilience.py` modül; pybreaker dep eklenmesin; circuit breaker P014 olarak F7'ye ertelensin |
| 5 | Global Çözüm | 🟢 | Tek `resilience.py` modül; Pinecone+Supabase+LiteLLM hepsi kullanır | — |
| 6 | Son Kullanıcı Avukatı | 🟢 | 503 + Retry-After header → frontend doğru retry UX (F4-S1.5 hatları); şu an `/api/search` 500 leak + stacktrace exposure güvenlik riski | — |
| **A** | **Sercan (BAĞLAYICI, post-hoc)** | 🟡 (öngörü) | Timeout değerleri SLA-bazlı (Pinecone connect=3s/read=10s; Supabase=10s; HF settings.HF_TIMEOUT_SECONDS=60s zaten); exponential backoff + jitter (thundering herd); breaker open-state Sentry metric F7'de | Değerler `config/resilience.yaml` veya `Settings`'te, hard-code yasak |

**Sonuç:** 2 YELLOW (K4 + A öngörü) + 5 GREEN → R13.5 "1-2 YELLOW + 4-5 GREEN = İlerle". K4 YELLOW uygulanır: tenacity/pybreaker dep YASAK, native asyncio.wait_for + in-house resilience.py.

**Empirik test gerekli mi?** EVET — `tests/integration/test_resilience.py`: (a) Pinecone monkey-patch slow response → timeout 503; (b) Supabase 500 mock → retry 2× → 503 retrieval_degraded; (c) Listener timeout → 504; (d) Cache hit + Pinecone outage → 200 cached fallback (F3a §4 S8 senaryosunun gerçeği).

**Karar (önerilen):** İlerle. P014 circuit breaker → KD-36 F7 P065'e ertelendi.

**Alt-§ özetleri (commit 5-7-8 detay):**

| Alt | Commit | Concrete Highlights |
|---|---|---|
| 39a | `[P011]` | `resilience.py`: `with_timeout(coro, t)` + `with_retry(fn, attempts, base, max, jitter)` async/sync dual; Pinecone `requests` Timeout config + 3-retry envelope retain; **PineconeIndexWrapper singleton** (`@lru_cache` veya module-level) — pool_router.py L180 `idx = PineconeIndexWrapper()` her fan_out'ta yeni instance bug fix |
| 39b | `[P012]` | Supabase `create_client` options `postgrest_client_timeout=10`; `_with_retry` wrapper 2 attempt; structured logging `service=supabase op=<table>.<verb> attempt=N` |
| 39c | `[P013]` | search route exception katmanları: `PineconeTimeoutError → 503 pinecone_unavailable + Retry-After: 30`; `SupabaseError → 503 retrieval_degraded + gate_warnings.append("degraded_mode")`; `HFTimeoutError → 504 listener_timeout`; cache hit + downstream fail → 200 cached fallback (F3a §4 S8) |
| 39d | `[P015]` | `runbook/<endpoint>_down.md` 4 dosya: (1) symptom — what user sees + monitoring trigger; (2) first-check — Sentry trace + Pinecone Console + Supabase Dashboard; (3) mitigation — env flag, manual cache prime, rollback; (4) rollback — last-good commit hash + `git revert <hash>` template |

---

## §4 Empirik test (R13.11 dış servis kanıtı)

| Test | Dosya | Ne ölçer | Day |
|---|---|---|---|
| Pinecone metadata filter syntax | `tests/fixtures/pinecone_metadata_filter.json` | 3 query × 3 filter kombinasyonu canlı response | 3 sabah (P006 öncesi) |
| Postgres title FTS recall | `tests/fixtures/postgres_title_fts_recall.json` | 50 query × ground-truth recall@10 | 3 öğle (Migration 0005 sonrası) |
| LVR calibration sample | `tests/fixtures/lvr_calibration_sample.json` | 20 claim × yüksek/düşük LVR | 3 öğleden sonra (P008-LVR öncesi) |
| Faithfulness calibration | `tests/fixtures/faithfulness_calibration.json` | 100 paper × 3-eşik ROC | 4 öğleden sonra (Day 4 wrap) |
| **Resilience integration** | `tests/integration/test_resilience.py` | Pinecone slow-mock timeout / Supabase 500 retry / HF 504 / cache fallback 200 | 4 sabah (P011-P013 öncesi) |
| Cosmos TR endpoint smoke (Sercan setup sonrası) | `tests/fixtures/cosmos_tr_summary.json` | TR summary endpoint canlı | (Sercan setup'a bağlı, Day 4 sonrası post-hoc) |

**Polish gate CI rule:** `grep -r 'TODO(P' api/ | wc -l == 0` Day 4 wrap sonu zorunlu (`make polish-check`). Bu rule'u `.github/workflows/polish_gate.yml` içinde kontrol et.

---

## §5 LOC ve süre tahmini

| Day | İş | LOC | Süre |
|---|---|---|---|
| 3 sabah | Council 35 + Migration 0005 + P006 commit | 80 + 280 = 360 | ~4h |
| 3 öğleden sonra | Council 36 + P008-LVR commit | 120 | ~3h |
| 4 sabah | Council 37 + F3 6 TODO routes commit | 600 | ~5h |
| 4 öğle | Council 39 + P011 + P012 + P013 + P015 commits (resilience patches) | 120+50+60+250 = 480 | ~2.5h |
| 4 öğleden sonra | Council 38 + Calibration commit + Handoff packet commit | 230 | ~3h |
| 4 wrap | Polish gate + Sercan handoff README + STATE/DECISIONS update | 0 (doc) | ~1h |
| **Toplam** | **10 commit** | **~1790 LOC + 31 test** | **~18.5h (2-2.5 gün)** |

---

## §6 Bilinen Borçlar (Known Debt) — Day 3-4'te eklenir

| ID | Konu | Çözüm | Sahip | Faz |
|---|---|---|---|---|
| KD-29 | Pinecone metadata filter syntax SDK 8.1.2 doğrulaması smoke fixture'a bağımlı | Smoke fail → P006 filter optional (graceful degrade) | Sercan post-hoc | F2 |
| KD-30 | Postgres title FTS recall<70% ise Pro tier abstract'a yükseltme | recall@10 fixture sonrası karar | Sercan | F2 wrap |
| KD-31 | LVR threshold 0.7 keyfi — Day 4 calibration fixture'la güncellenir | calibrate_faithfulness.py + threshold YAML | Omer + Sercan | F2 Day 4 |
| KD-32 | F3 6 TODO route'larında Cosmos TR endpoint setup eksikse Qwen TR fallback | B-007 Yol A; Cosmos hazır olunca KD-32 kapatılır | Sercan | F3 |
| KD-33 | MiniCheck v2 5B HF endpoint Faz 3 — MVP'de level=SUMMARY jsonschema+LVR cascade yeterli | Faz 3'te HF endpoint açıldığında F3c spec'i revize | Sercan | Faz 3 |
| KD-34 | Faithfulness calibration 100 paper Omer manuel etiketleme; bias riski | TR/EN karışım + 3 alan stratifiye | Omer | F2 Day 4 |
| KD-35 | LightGBM faithfulness kalibrasyon Faz 2 (MVP manual ROC yeterli) | Faz 2 backend ML stage | Sercan | Faz 2 |
| KD-36 | **P014 circuit breaker** (Pinecone/Supabase/HF için ayrı pybreaker) Council 39 K4 YELLOW gereği F7 P065'e ertelendi — 1-kişi MVP'de pilot trafiği yokken erken; pilot N≥5 user load gözlemlendikten sonra prod-öncesi açılır | F7 P065 prod hardening | Sercan | F7 |
| KD-37 | **Resilience config YAML hot-reload** Faz 3 — MVP'de `Settings`'te hard-code timeout/retry; restart yeterli (Sercan A öngörü YELLOW) | Faz 3 config service | Sercan | Faz 3 |

---

## §7 Sercan handoff packet (Day 4 wrap çıktısı)

**Dosya:** `docs/backend/sercan_handoff_F2.md`

**İçerik:**
1. F2 commit zinciri özeti (Day 1: 8 + Day 2: 6 + Day 3-4: 6 = 20 commit)
2. PR review checklist:
   - [ ] HK-1..HK-7 her yeni servis için doğrulandı mı (Pydantic forbid + smoke fixture + runtime assert + manifest verify + type-strict + reproducibility seed + KVKK PII scrub)
   - [ ] R13.11 dış servis empirik kanıt (5 fixture: hf_qwen + pinecone_metadata + pinecone_query + postgres_fts + lvr_calibration + faithfulness_calibration)
   - [ ] mypy strict 0 issue (~50 source file)
   - [ ] ruff All checks
   - [ ] pytest 144/144
   - [ ] polish_gate (`grep TODO(P`) == 0
3. Bilinen Borçlar listesi (KD-1..KD-35 STATE.md §7'den senkron)
4. Production hardening TODO (Sercan'ın önceliği): JWT JWKS prod (KD-4), tier-aware rate limit (KD-9), Sentry runtime smoke (KD-2), HF cold-start retry empirik tuning (KD-32 Cosmos sonrası)
5. Smoke fixture refresh cadence (servis swap/version bump CI rule)

---

## §8 Day 4 wrap PASS kriterleri

**Day 4 sonu** STATE.md `F2 Day 4 PASS satırı` yazılır eğer ve sadece eğer:

- [ ] 10 commit zinciri lokal `feat/F2-search-skeleton` (push timing Omer, Sercan handoff sonrası)
- [ ] mypy strict 0 issue
- [ ] ruff All checks
- [ ] **pytest 152/152 PASS** (121 + 31 yeni)
- [ ] 5 yeni smoke fixture commit edildi (`tests/fixtures/{pinecone_metadata_filter,postgres_title_fts_recall,lvr_calibration_sample,faithfulness_calibration}.json`)
- [ ] `tests/integration/test_resilience.py` PASS — Pinecone slow timeout 503 + Supabase 500 retry + HF 504 + cache fallback 200 (F3a §4 S8 gerçeği)
- [ ] `docs/runbook/{pinecone_down,supabase_down,hf_endpoint_down,search_p95_breach}.md` 4 iskelet yazıldı
- [ ] Faithfulness threshold YAML kalibre + 3 eşik (LVR/MiniCheck-placeholder/ALCE-placeholder) commit
- [ ] `grep -r 'TODO(P' api/ | wc -l == 0` (polish gate)
- [ ] `docs/backend/sercan_handoff_F2.md` yazıldı
- [ ] STATE.md F2 Faz başlığı `F2 Day 1-4 KAPANDI ✅`
- [ ] DECISIONS B-021 entry yazıldı (F2 sprint kapanış summary, Sercan handoff hazır)
- [ ] NEXT_ACTION.md F3b chat sırada (F4-S2 zaten paralel devam eden)

**Day 4 PASS sonrası:** F4-S2 (Omer, frontend) paralel hâlâ koşuyor; F2 backend "code complete" — Sercan post-hoc PR review batch + production hardening Faz 7'de devam eder. F3-F7 plan manifest'leri (B-010) zaten dondurulmuş.

---

## §9 Risk + recovery

| Risk | Olasılık | Etki | Recovery |
|---|---|---|---|
| Pinecone metadata filter syntax fail (SDK 8.1.2) | Düşük (Pinecone docs `$in/$gte` MetadataFilter belgeli) | Yüksek (P006 fail) | KD-29: filter optional + warn log; P006 commit yine geçer; F2 işlevsel ama metadata filter Faz 2'ye |
| Postgres title FTS recall <70% (50 query smoke) | Orta | Orta | KD-30: Pro tier abstract include, $25/ay onayı (Council 25 zaten kabul ettiği fallback) |
| LVR threshold çok agresif (Day 4 calibration sonrası) | Düşük | Düşük | YAML hot-reload Faz 3'e ertelendi → MVP'de restart yeterli |
| Cosmos TR endpoint Day 4'te hazır değil | Yüksek (Sercan'ın setup'ına bağımlı) | Düşük | B-007 Yol A: Qwen2.5 TR fallback aktif kalır; Cosmos sonradan açılır |
| Omer 100 paper calibration etiketleme yetişmez | Orta | Düşük | Threshold placeholder MVP'de kabul edilir; KD-31 açık kalır F2 wrap-after |
| Day 4 wrap'e yetişmiyorsa sprint 1 gün uzar | Orta | Orta | F2 sprint Master plan §9 4-5 gün esnek; 5. güne taşmak kabul (B-014 1 + B-018 1 + Day 3-4 2 + buffer 1) |

---

## §10 Sonraki sprint pointer

**F2 PASS sonrası**: F3b chat (zaten F3 6 TODO concrete'inde alt-endpoint işlendi → tekrar sprint açmaya gerek yok, F3 plan manifest'leri B-010'da dondurulmuş, P-numara takibi F3a/b/c/d/e mini-planlardan). Pratik olarak F2 PASS = F3 backend kod tarafından "code complete".

**Sıradaki büyük sprint**: **F4-S3** (frontend Sohbet+Liste, Omer'in F4-S2 sonrası 2026-05-XX civarı), **F7 Pilot** (Sercan production hardening sonrası 2026-05-XX civarı, master plan §9 hedef ~2026-05-30).

---

## §11 Plan-first kontrolü

Bu manifest'i okuyup onayladıktan sonra Omer söyler:

```
plan onaylandı, F2 Day 3 başla
```

Sonra Day 3 sabahı sırayla:
1. `make test` → 121 PASS doğrulanır
2. Council 35 §-tablosu canlı yapılır + onay alınır
3. Migration 0005 commit + P006 commit
4. Council 36 + P008-LVR commit
5. (Day 4) Council 37 + F3-routes commit
6. Council 38 + Calibration commit + Handoff packet commit
7. Day 4 wrap STATE/DECISIONS güncelleme

Plan dışı edit denenirse **STOP** + bu dosya revize.

---

**Son revize:** 2026-05-01 akşam (P011-P015 resilience patches plan-revize: Council 39 + commit 5-7-8 + KD-36/37; Omer "plana yaz, zamanı gelince yapalım" yazılı onayı).
**Yazar:** Claude Code (Omer plan-first protokolü gereği).
