# P09 — Launch, Operasyon ve 10 Yıl Dayanıklılık

## Amaç

Observability, runbook, incident, cost/performance, release ve model/provider değişim operasyonu oturur.

## Faz kapısı

Production readiness checklist yeşil; runbook ve rollback planları var.

## İlgili spec dosyaları

- `docs/worldclass/SPECS/observability_runbook_spec.md`

## Görevler

### P09-T01_OBSERVABILITY_AND_AUDIT_RUNBOOKS — Review OS observability, audit ve runbook seti

**Öncelik:** P0  
**Bağımlılıklar:** P02-T02_DURABLE_WORKFLOW_ADAPTER, P01-T03_CONFIDENTIALITY_AND_EXTERNAL_AI_CONSENT

**Dokunulacak dosyalar:**
- `api/middleware/sentry.py`
- `api/services/review_service.py`
- `docs/runbook/*`
- `docs/worldclass/SPECS/observability_runbook_spec.md`

**Uygulama adımları:**
1. Metrics: review latency by stage, provider errors, degraded rate, LLM cost, citation resolution rate.
2. Audit events: create, upload, parse, external_provider_call, report_view, export, delete.
3. Runbooks: provider down, queue stuck, auth incident, data deletion, eval regression.
4. Correlation id/debug id kullanıcı hata ekranına bağlansın.

**Test/doğrulama:**
- unit: audit event emitted
- manual runbook drill
- metrics smoke

**Başarı tanımı:**
- Production incident olduğunda neye bakılacağı belli.

**Bir sonraki adıma geçiş:** Her review job trace/audit/log ile izlenebiliyorsa.

**Durdurma koşulları:**
- External provider call audit logsuz yapılıyorsa.

---

### P09-T02_PRODUCTION_READINESS_AND_LAUNCH_GATE — Production readiness ve launch gate

**Öncelik:** P0  
**Bağımlılıklar:** P07-T02_RELEASE_EVAL_GATE, P09-T01_OBSERVABILITY_AND_AUDIT_RUNBOOKS, P05-T03_LIVE_REVIEW_COCKPIT_PROGRESS

**Dokunulacak dosyalar:**
- `docs/worldclass/CHECKLISTS/RELEASE_GATE.md`
- `deploy/render.yaml`
- `Dockerfile`
- `web/Dockerfile`
- `.env.example`

**Uygulama adımları:**
1. Release checklist tüm P0 gate’lerini toplasın.
2. Rollback plan, migration plan, env validation, eval report, security checklist zorunlu olsun.
3. Launch smoke: create review, process, view report, export, delete.
4. Cost/performance budget belirle.

**Test/doğrulama:**
- release smoke script
- migration dry run
- production env validation test

**Başarı tanımı:**
- Launch kararı sezgiyle değil gate raporuyla veriliyor.

**Bir sonraki adıma geçiş:** Tüm P0 gate’ler yeşil, P1 açıklar launch notes’ta belgeli.

**Durdurma koşulları:**
- P0 security/privacy/eval açık kalırsa launch yok.

---
