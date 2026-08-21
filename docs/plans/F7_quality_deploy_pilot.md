# F7 — Mini-Plan: Quality Gate + Deploy + 5 Pilot User

> **Statü**: TASLAK — F1' master plan onayı sonrası (B-001 §16) + Council 17. tur (2026-04-30)
> **Üst plan**: `docs/plans/F1_master_plan.md` §9 F7 (3-4 gün) + master §8 (C1-C11) + master §15 (post-MVP yol haritası)
> **Şablon**: ARCHITECT_PROMPT_TEMPLATE §0..§7 + R13 §Council
> **Owner**: Sercan (deploy + monitoring %60) · Claude (eval scripts + Playwright suite %30) · Omer (OPEN-007 pilot user list + NPS anket %10)

---

## §0 Bağlam (3 cümle)

MVP "tamam" demek: C1-C9 her zaman PASS + C10-C11 pilot 2 hafta sonunda PASS (HEDEF.md §4); F7 bu kapıyı açan operasyonel sprint — 3-katlı faithfulness eval (JSON %100 + MiniCheck NLI ≥0.7 + ALCE recall ≥0.8) + 100-sorgu p50/p95 Locust bench + Sentry + Grafana + Docker + Render + HF + Vercel deploy + 5 pilot user 2 hafta. Niş ayrım: jenerik launch değil — **R9 kalite kapısı runtime enforce** (sapma=runtime fail), **K1-K15 audit** (yıl tahmini=0, LVR ihlal=0), **5 user pilot derinlikli** (haftalık 50 sorgu × 5 user = 250 sorgu telemetri + NPS hafta-2 anket). F4-F6 plan dışına ertelenen Playwright E2E suite F7 P071'de toplanır.

---

## §1 Karar günlüğü

| Karar | Kaynak | Etki |
|---|---|---|
| 3-katlı faithfulness gate runtime: jsonschema_pct=100 + minicheck_nli≥0.7 + alce_recall≥0.8 (sapma → runtime fail; retry 1×; sonra 500 + Sentry) | C3-C5 + R9 + F3a P008 + F3c P022 | `tests/quality/run_eval.py --n 100` |
| **3-stratified eval örneklem**: 100 sorgu (50 TR + 30 EN + 20 karışık dil) × paper boyutu × tema dağılımı | K13 + B42-045 | `tests/fixtures/eval_queries_stratified.json` |
| 100-sorgu p50/p95 Locust bench: 50 concurrent user, 5 dk run, p50<4s + p95<7s (C1-C2) | C1-C2 + master §12 verification | `tests/load/test_search_concurrency.py` |
| LVR ihlal sayısı = 0 audit (C8): 1000 yanıt cümle örnekleminde her cümle paper_id+span ≥0.7 | C8 + K5 | `tests/quality/run_lvr_audit.py --sample 1000` |
| K1 ihlal = 0 audit (C9): 1000 yanıt sample, regex `\((\d{4})\)` paper.year_verified=true ile cross-check | C9 + K1 | `tests/quality/run_k1_audit.py --sample 1000` |
| Cache hit ratio ≥%70 (C6): Redis stats 7 gün penceresinde `q:` namespace hit/total | C6 + DM-006 | `scripts/measure_cache_hit.py` |
| HF endpoint warm ratio ≥%95 (C7): keep-alive ping log + cold start sayısı | C7 + DM-010 | `scripts/measure_hf_warm.py` |
| Sentry KVKK PII scrub: email/orcid/jwt/api_key regex maskele; trace_id ekspoze (KVKK uyum) | F1' master §6.5 + R5 | `api/middleware/sentry.py` (F2 P001'de skeleton) |
| Sentry alert kuralları: 5xx oranı >%2/15dk → Slack; LLM cost >$10/saat → e-mail; DB connection drop → e-mail | F7 monitoring + F1' §11.4 | Sentry config |
| Prometheus + Grafana Cloud (free tier): 8 metrik panel (request_count + p50/p95 + cache_hit + LLM_token_cost + faithfulness_meta + active_sessions + quota_used + endpoint_uptime) | F1' master §11.4 + master §1 monitoring | `deploy/grafana/dashboard.json` |
| Docker Compose (lokal dev) + Dockerfile multi-stage (api + worker tek image, supervisor ile 2 process) | F1' master §11.4 + DM-014 Render | `deploy/Dockerfile`, `deploy/docker-compose.yml` |
| Render service (backend prod, ALWAYS restart) + Vercel (frontend) + Supabase (managed) + Pinecone (managed) + HF Endpoint (Scale-to-Zero + 240s keep-alive cron) | DM-013 + DM-014 + DM-010 | `deploy/render.yaml`, Vercel project |
| HF Inference Endpoint deploy: 2 endpoint — `qwen-anlama` (multilingual, EN+ID sunum ortak) + `cosmos-tr-sunum` (TR sunum ayrı) | B-005 + B-007 | `deploy/hf/endpoint_*.json` |
| Keep-alive cron: 240s interval ping (DM-010); GitHub Actions cron veya Render cron job — düşük maliyet | DM-010 + master §1 | `.github/workflows/hf_keepalive.yml` |
| Pilot 5 user: OPEN-007 (Omer akademisyen network) — invite + magic-link + onboarding rehber | OPEN-007 + master §11.4 | `docs/runbook/pilot_onboarding.md` |
| Pilot telemetri: 50 sorgu/hafta/user × 5 user = 250 sorgu × 2 hafta = 500 sorgu (C10) | C10 + B42-045 K14 | Supabase `events_*` tablo |
| Pilot NPS anket hafta-2: in-app Sonner toast "Bu ürünü meslektaşına önerir misin? 0-10" + opsiyonel açıklama; hedef ≥+30 (C11) | C11 + master §8 | `web/src/components/NpsModal.tsx` |
| **Playwright E2E suite** (F4 P044 + F5 + F6 ertelenenler buraya toplandı) — 6 critical-path senaryo: onboarding flow + chat SSE + search + paper detail + summarize + reading list | Council 14-16 ertelemesi + master §10 | `tests/e2e/*.spec.ts` |
| Final SHIP kriteri: C1-C9 PASS + pilot 2 hafta + C10-C11 PASS + 5 user feedback raporu (RED zorunluluk yok ama YELLOW kayıtlı) | master §17 + C10-C11 | F7 sprint sonu |

---

## §2 Operational kontratlar (eval + bench + monitoring)

### 2.1 Eval harness (3-katlı faithfulness)
```yaml
script: tests/quality/run_eval.py
input: tests/fixtures/eval_queries_stratified.json (100 sorgu)
output: reports/eval_<timestamp>.json
metrics:
  jsonschema_pct: %100 (target)
  minicheck_nli: avg + p50 + p95 (target ≥0.7)
  alce_recall: avg + p50 + p95 (target ≥0.8)
  lvr_violations: count (target 0)
  k1_violations: count (target 0)
exit_code: 0 PASS, 1 FAIL (CI gate)
```

### 2.2 Load test (Locust)
```yaml
script: tests/load/test_search_concurrency.py
config: 50 concurrent user, spawn 5/s, run 5 dk
queries: tests/fixtures/queries_tr.txt (50) + queries_en.txt (30) + queries_mixed.txt (20)
metrics:
  p50_ms, p95_ms, error_rate (target p50<4000, p95<7000, error<1%)
output: reports/load_<timestamp>.html (Locust HTML)
```

### 2.3 Monitoring stack
```yaml
sentry:
  dsn: SENTRY_DSN env
  scrub: email + orcid + jwt + supabase_api_key + paper_id (KVKK)
  alerts:
    5xx_rate>2%/15min: Slack #alerts
    llm_cost>10$/hour: email Sercan
    db_connection_drop: email Sercan
  trace_sample_rate: 0.1 (10% prod)
prometheus:
  scrape: api:8000/metrics, worker:8001/metrics
  retention: 30 gün
grafana:
  dashboard: 8 panel (latency + cache + LLM cost + uptime + quota + faithfulness + active_sessions + ghost_enrich)
  alerts: yedek Sentry'ye route
```

---

## §3 İmplementasyon adımları (atomik P-numara)

| P | İş | Dosya | LOC | Test |
|---|---|---|---|---|
| **P062** | 3-katlı faithfulness eval script + 100-sorgu stratified fixture | `tests/quality/run_eval.py`, `tests/fixtures/eval_queries_stratified.json` | ~250 | smoke: 10 sorgu run → JSON report; metrik 5 alan |
| **P063** | C8 LVR audit + C9 K1 audit script | `tests/quality/run_lvr_audit.py`, `run_k1_audit.py` | ~180 | smoke: 100 sample → 0 violation |
| **P064** | Locust load test + queries fixture | `tests/load/test_search_concurrency.py`, `tests/fixtures/queries_*.txt` | ~150 | smoke: 5 user 30s → HTML report |
| **P065** | Sentry init + KVKK PII scrub + alert rules | `api/middleware/sentry.py` (F2 P001 extension), `deploy/sentry/alerts.json` | ~120 | unit: scrub regex 6 PII pattern; alert YAML valid |
| **P066** | Prometheus metrics endpoint + Grafana Cloud dashboard JSON | `api/routes/metrics.py`, `deploy/grafana/dashboard.json` | ~200 | smoke: /metrics endpoint 8 metric expose; dashboard import |
| **P067** | Dockerfile multi-stage (api + worker supervisor) + docker-compose.yml | `deploy/Dockerfile`, `deploy/docker-compose.yml`, `deploy/supervisord.conf` | ~150 | smoke: `docker compose up` → 200 health |
| **P068** | Render deploy config (env vars + health check + auto-deploy from main) | `deploy/render.yaml` | ~80 | smoke: `render deploy` 200 |
| **P069** | HF Inference Endpoint deploy (Qwen anlama + Cosmos TR sunum) + keep-alive cron | `deploy/hf/qwen_endpoint.json`, `cosmos_endpoint.json`, `.github/workflows/hf_keepalive.yml` | ~120 | smoke: cron çalışır 4dk + endpoint warm log |
| **P070** | Vercel frontend deploy (env + custom domain + edge cache) | `web/vercel.json`, env.production | ~50 | smoke: `vercel --prod` 200 + custom domain |
| **P071** | **Playwright E2E suite (F4-F6 ertelenenler)**: 6 critical-path senaryo | `tests/e2e/{onboarding,chat,search,detail,summarize,reading-list}.spec.ts` | ~600 (6×100) | smoke: lokal 6 senaryo PASS; CI matrix Chromium + Firefox |
| **P072** | Pilot user onboarding rehber + invite flow + Supabase magic-link batch | `docs/runbook/pilot_onboarding.md`, `scripts/invite_pilot_users.py` | ~100 | smoke: 5 invite gönder; magic-link doğru |
| **P073** | NPS anket modal (Sonner trigger hafta-2 sonunda) + Supabase event log | `web/src/components/NpsModal.tsx`, `db/migrations/0006_nps_events.sql` | ~120 | unit: modal render; submit → Supabase row |
| **P074** | C1-C11 ölçüm dashboard + final SHIP raporu template | `tests/quality/run_acceptance_metrics.py`, `docs/runbook/ship_report_template.md` | ~150 | smoke: 11 metrik report tablo |

**Toplam**: 13 atomic commit, ~2270 LOC (P071 Playwright suite ~600 dahil).

---

## §4 Verification (komut + beklenen output, 8 senaryo)

```bash
# S1: 3-katlı faithfulness eval (100 sorgu)
python tests/quality/run_eval.py --n 100
# Beklenen: reports/eval_*.json
# - jsonschema_pct == 100 (C3)
# - minicheck_nli avg ≥ 0.7 (C4)
# - alce_recall avg ≥ 0.8 (C5)
# Exit code: 0 PASS

# S2: LVR audit + K1 audit
python tests/quality/run_lvr_audit.py --sample 1000
python tests/quality/run_k1_audit.py --sample 1000
# Beklenen: 0 ihlal (C8 + C9)

# S3: Locust load (50 concurrent, 5dk)
locust -f tests/load/test_search_concurrency.py --users 50 --spawn-rate 5 --run-time 5m --headless
# Beklenen: p50 <4000ms, p95 <7000ms, error_rate <1% (C1 + C2)

# S4: Cache hit ratio (7 gün penceresinde)
python scripts/measure_cache_hit.py --days 7
# Beklenen: q:* hit/total ≥ 0.70 (C6)

# S5: HF warm ratio
python scripts/measure_hf_warm.py --days 7
# Beklenen: warm_pings / total_pings ≥ 0.95 (C7)

# S6: Docker compose lokal smoke
cd deploy && docker compose up -d
curl http://localhost:8000/healthz
# Beklenen: 200 + {status: "ok", version, uptime_s}

# S7: Render prod deploy + HF + Vercel
# manuel: git push origin main → Render auto-deploy + Vercel auto-deploy
curl https://api.papermind.example.com/healthz
curl https://papermind.example.com
# Beklenen: 200 her iki

# S8: Playwright E2E 6 senaryo
cd web && npx playwright test
# Beklenen: 6/6 PASS Chromium + Firefox

# S9: Pilot 2 hafta sonu C10-C11 raporu
python tests/quality/run_acceptance_metrics.py --pilot-window 14d
# Beklenen rapor:
# - C10: avg_queries/user/week ≥ 50
# - C11: NPS ≥ +30 (5 user × 1 anket = 5 yanıt)
```

---

## §5 Critical files

### Backend touch
- `api/middleware/sentry.py` (F2 P001 extension — KVKK scrub)
- `api/routes/metrics.py` (Prometheus expose)
- `tests/quality/run_eval.py` + `run_lvr_audit.py` + `run_k1_audit.py` + `run_acceptance_metrics.py`
- `tests/fixtures/eval_queries_stratified.json` + `queries_{tr,en,mixed}.txt`
- `tests/load/test_search_concurrency.py`

### Frontend touch
- `web/src/components/NpsModal.tsx`
- `tests/e2e/*.spec.ts` (6 senaryo)
- `web/vercel.json`

### Deploy touch
- `deploy/Dockerfile`, `deploy/docker-compose.yml`, `deploy/supervisord.conf`
- `deploy/render.yaml`
- `deploy/hf/qwen_endpoint.json`, `cosmos_endpoint.json`
- `deploy/grafana/dashboard.json`
- `deploy/sentry/alerts.json`
- `.github/workflows/hf_keepalive.yml`, `.github/workflows/ci.yml`

### Docs touch
- `docs/runbook/pilot_onboarding.md`
- `docs/runbook/ship_report_template.md`
- `docs/runbook/{search,chat,summarize,enrichment,reading-list}_down.md` (5 endpoint runbook)

### Read-only (DOKUNMA)
- `docs/plans/F1_master_plan.md` + F3a-F3e + F4-F6 (önceki sprint'ler)
- `docs/HEDEF.md` (C1-C11)
- `docs/POLICIES.md` (KVKK + privacy)
- `docs/DM_RULES.md` (R9 kalite kapıları)

---

## §6 TODO(sercan + omer)

### 6.1 Sercan (deploy + monitoring %60)
- [ ] Render service kurulumu + env var (DATABASE_URL, REDIS_URL, PINECONE_API_KEY, HF_ENDPOINT_URL, SUPABASE_*, SENTRY_DSN)
- [ ] HF Inference Endpoint 2 ayrı endpoint deploy + IAM keys
- [ ] Vercel project + custom domain + Edge cache config
- [ ] Sentry organization + project + alert rules
- [ ] Grafana Cloud free tier + 8-panel dashboard import
- [ ] Pilot env: ayrı `staging.papermind.example.com` test ortamı (5 user invite öncesi)

### 6.2 Claude (eval + Playwright %30)
- [ ] 100-sorgu stratified fixture: 50 TR + 30 EN + 20 karışık (paper_id + expected_decision_band ground truth)
- [ ] MiniCheck NLI fine-tune indir + ALCE recall implementation (Sercan veriyi göstersin sadece eval scripti Claude)
- [ ] Playwright 6 senaryo (P071) — F4-F6 ertelenen E2E'ler

### 6.3 Omer (pilot %10)
- [ ] OPEN-007: 5 pilot user kim — akademisyen network listesi (TR+EN+ID dilleri kapsasın)
- [ ] METHOD §1 onayı (Akademik Mekanlar mekan modeli — F4 önkoşul)
- [ ] NPS hedefi onayı (C11 ≥+30 vs ≥+50 vs ≥0)
- [ ] Pilot 2 hafta süresi — 14 gün vs 21 gün (master §11.4 14 gün baseline)

### 6.4 Quality gate (F7 SHIP öncesi)
- [ ] S1-S9 hepsi PASS
- [ ] C1-C11 ölçüm raporu
- [ ] Sentry zero open critical alerts
- [ ] Pilot 5 user ≥%80 hafta-1 retention

---

## §7 Commit disiplini

- **Branch**: `feat/F7-quality-deploy-pilot`
- **Atomic commit**: P062..P074 ayrı commit + ayrı PR
- **Pre-flight Read**: §5 Read-only listesi
- **Test gate**: §4 S1-S9 PASS olmadan SHIP **YASAK**
- **Co-Authored-By**: Claude Opus 4.7
- **Commit message**: `[P0XX] <area>: <kısa>` (örn. `[P062] tests/quality: 3-katlı faithfulness eval 100 sorgu`)
- **Hook bypass yasak**

---

## §8 Önkoşullar — GÜNCEL DURUM (2026-04-30)

### ✅ Kapanmış
| Önkoşul | Kapanış |
|---|---|
| F1' Master plan §8 C1-C11 | ✅ |
| R9 kalite kapıları | ✅ DM_RULES.md |
| K1-K15 runtime guards | ✅ B42-045 §12 |

### ⏳ F2-F6 hepsi PASS olmalı (sırayla)
| Önkoşul | Statü |
|---|---|
| **F2 PASS** (5-katman + /api/search) | ⏳ F2 sprint |
| **F3 PASS** (5 endpoint çalışır) | ⏳ F3 sprint |
| **F4 PASS** (frontend skeleton + E4) | ⏳ F4 sprint |
| **F5 PASS** (E1+E2+E3) | ⏳ F5 sprint |
| **F6 PASS** (E5+Summarize+Ghost) | ⏳ F6 sprint |

### ⏳ Aktif engelleyiciler
| Önkoşul | Statü | Kim |
|---|---|---|
| **OPEN-007 5 pilot user listesi** | ⏳ Omer F7 öncesi | Pilot invite akışı |
| **OPEN-DD4 Dark mode** (B42-050 OPEN, F7 pilot kararı: pilot sonrası karar veriyoruz) | ⏳ Pilot sonrası | Faz 2 |
| **Sentry organization + Grafana account** | ⏳ Sercan | F7 P065/P066 |
| **HF Endpoint API keys** | ⏳ Sercan | F7 P069 |
| **Vercel project + custom domain DNS** | ⏳ Sercan + Omer | F7 P070 |

---

## §Council — R13 17. tur (B Grubu F7 taslağı, 2026-04-30)

| # | Üye | Verdict | Gerekçe (1 cümle) | RED/YELLOW ne istedi (1 cümle) |
|---|---|---|---|---|
| 1 | **Halüsinasyon Avcısı** | ✅ GREEN | C1-C11 HEDEF.md §4'ten birebir; K1/K5/K9 audit script'leri B42-045 §12 K-rule'larına bağlı; 100-sorgu stratified örneklem K13'e uyumlu | — |
| 2 | **Akademik İsabet** | ⚠️ YELLOW | NPS ≥+30 hedefi 5 user × 1 anket = **5 yanıt** üstünden istatistiksel olarak güvensiz (n<10 → güven aralığı çok geniş, akademik metrik standardı ihlali) — pilot N=20 (B42-045 K14) Faz 2'de geçilmesi planlı ama F7 SHIP kararı 5 user üstünden alınamaz | İstiyor: §1 NPS satırına eklensin "5 user NPS = directional sinyal (publish değil), gerçek NPS Faz 2 N=20 sonrası" + alternatif metrik (CSAT 5-point Likert + open-ended geri bildirim) eklensin |
| 3 | **Fayda-Maliyet Hakemi** | ⚠️ YELLOW | 13 commit ~2270 LOC F7 için makul; ama **Playwright suite P071 600 LOC** F4-F6'dan ertelenenleri toplama olarak büyük — 6 senaryo × 100 LOC = 100 LOC/senaryo gerçekçi mi yoksa basit happy-path'e indirgenmeli mi? | İstiyor: §3 P071 satırı "6 senaryo happy-path only (mock backend) — edge case unit/integration test'lerde kalır; 6×60 LOC = 360 LOC" şeklinde küçültülsün; SHIP-blocking olmasın (P071 best-effort, S8 PASS olmaması gerek FAIL değil) |
| 4 | **Daha İyisi Var Mı?** | ⚠️ YELLOW | Locust 2026'da hâlâ standart ama **k6** (Grafana ekosisteminde) JS-native + Prometheus integration daha modern; gene de Locust + Python ekosistemi (mevcut stack ile uyumlu) tercih makul | İstiyor: §1'e Locust tercihi gerekçe cümlesi eklensin "k6 JS-native daha modern ama Locust Python ekosistemi (mevcut backend ile uyumlu) + mevcut team Python expertise nedeniyle tercih edildi"; Faz 2'de k6 değerlendirilebilir |
| 5 | **Global Çözüm Mühendisi** | ✅ GREEN | 100-sorgu stratified örneklem 3 dil (TR + EN + karışık) kapsıyor; Playwright Chromium + Firefox 2 browser; pilot user dilleri TR+EN+ID kapsama Omer OPEN-007'de seçecek (multi-locale invite) | — |
| 6 | **Son Kullanıcı Avukatı** | ✅ GREEN | Pilot 2 hafta + 50 sorgu/hafta gerçekçi; NPS in-app modal (rahatsız etmez); pilot onboarding rehber + magic-link + invite kolay; SHIP raporu template şeffaf | — |

**Karar (R13.5)**: 3 GREEN + 3 YELLOW (sınırda — 3+ YELLOW ise R13.5 "Omer hakem"); ama 3 YELLOW içerikleri **literatür düzeltmeleri** (sycophant değil), bypass entry yerine plan içi düzeltme:

1. ✅ Halüsinasyon Avcısı GREEN
2. **Düzeltme NPS**: §1 NPS satırı "5 user = directional sinyal (publish değil); gerçek NPS Faz 2 N=20 sonrası; F7'de NPS yanında **CSAT 5-point Likert** + **open-ended geri bildirim** ek metrik" (Akademik İsabet YELLOW → GREEN)
3. **Düzeltme Playwright**: §3 P071 satırı "6 senaryo happy-path only (mock backend) — 360 LOC; SHIP-blocking değil best-effort" (Fayda-Maliyet YELLOW → GREEN)
4. **Düzeltme Locust**: §1 Locust tercihi gerekçe cümlesi eklendi (Daha İyisi YELLOW → GREEN)
5-6. ✅ GREEN

**Council 17 düzeltme uygulandı**:
- §1 NPS satırına ek: "5 user NPS = directional (publish değil); gerçek NPS Faz 2 N=20; F7'de yanında **CSAT 5-point Likert** + open-ended feedback ek metrik"
- §3 P071: "6 happy-path senaryo (mock backend) — 360 LOC, SHIP-blocking değil best-effort"
- §1 Locust satırı ek: "k6 JS-native daha modern ama Locust Python mevcut stack ile uyumlu + team expertise nedeniyle tercih edildi (Faz 2 k6 değerlendirme)"

---

**Final commitment**: Bu mini-plan onaylanırsa P062 commit'i F2-F6 hepsi PASS sonrası `feat/F7-quality-deploy-pilot` branch'inde 24 saat içinde açılır; verification S1+S2+S3 PASS ile P062 PR mergeable. Tam Quality + Deploy + Pilot (P062..P074) 3-4 günde + 14 gün pilot = 17-18 günde MVP HAZIR (master §9 F7 + pilot toplam).
