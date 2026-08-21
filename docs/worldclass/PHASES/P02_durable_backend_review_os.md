# P02 — Durable Backend Review OS

## Amaç

Review job kalıcı, stage-based, retry/idempotency destekli, provider bağımsız ve gözlemlenebilir hâle gelir.

## Faz kapısı

Bir review job restart/retry senaryosunda kaybolmuyor; stage progress ve degraded states doğru raporlanıyor.

## İlgili spec dosyaları

- `docs/worldclass/SPECS/workflow_engine_spec.md`
- `docs/worldclass/SPECS/backend_architecture_spec.md`
- `docs/worldclass/SPECS/data_model_migration_spec.md`

## Görevler

### P02-T01_REVIEW_JOB_STAGE_SCHEMA — Review job stage/progress schema genişletmesi

**Öncelik:** P0  
**Bağımlılıklar:** P01-T05_FILE_SECURITY_AND_RETENTION_BASELINE

**Dokunulacak dosyalar:**
- `api/models/review.py`
- `db/migrations/0041_review_domain.sql`
- `web/src/lib/review-api.ts`
- `web/src/hooks/useReview.ts`

**Uygulama adımları:**
1. ReviewJob status modelini queued/running/stage_failed/completed/cancelled olarak genişlet.
2. Stage enum ekle: security_scan, parse, classify, references, evidence, guidelines, council, synthesis, export.
3. Stage progress, started_at, completed_at, error_code, degraded_reason alanları ekle.
4. Frontend type contract güncelle.

**Test/doğrulama:**
- model serialization test
- migration test
- frontend type/contract test

**Başarı tanımı:**
- Job progress tek numeric bar değil stage-based contract taşıyor.

**Bir sonraki adıma geçiş:** Frontend stage progression gerçek API contractından okuyabiliyorsa.

**Durdurma koşulları:**
- Eski response shape kırılıp frontend compile etmiyorsa.

---

### P02-T02_DURABLE_WORKFLOW_ADAPTER — BackgroundTasks yerine durable workflow adapter interface

**Öncelik:** P0  
**Bağımlılıklar:** P02-T01_REVIEW_JOB_STAGE_SCHEMA

**Dokunulacak dosyalar:**
- `api/routes/review.py`
- `api/services/review_service.py`
- `api/services/review_orchestration.py`
- `api/services/progress_service.py`
- `pyproject.toml`
- `docs/backend/celery_setup.md`

**Uygulama adımları:**
1. WorkflowClient protocol tanımla: enqueue, cancel, retry, get_status.
2. Development için in-memory/dev runner, production için queue adapter tasarla.
3. FastAPI BackgroundTasks kullanımını review route dışına çıkar.
4. Idempotency key ve job dedupe ekle.
5. Worker function her stage’i DB’ye checkpoint etsin.

**Test/doğrulama:**
- unit: enqueue creates durable job
- unit: duplicate idempotency key returns same job
- integration/smoke: worker resumes failed stage

**Başarı tanımı:**
- API process restart senaryosu job kaybına yol açmayacak şekilde tasarlandı/uygulandı.

**Bir sonraki adıma geçiş:** Review route sadece job oluşturup workflow’a teslim ediyorsa.

**Durdurma koşulları:**
- Long-running LLM work web request içinde kalıyorsa.

---

### P02-T03_PROVIDER_ABSTRACTION_FOUNDATION — Scholarly provider abstraction temeli

**Öncelik:** P0  
**Bağımlılıklar:** P02-T01_REVIEW_JOB_STAGE_SCHEMA

**Dokunulacak dosyalar:**
- `api/services/openalex_polite.py`
- `api/services/papers_hydration_service.py`
- `api/services/citation_service.py`
- `api/config.py`
- `tests/fixtures/openalex_search.json`

**Uygulama adımları:**
1. api/providers/scholarly/base.py içinde ScholarlyProvider Protocol oluştur.
2. Provider errors: RateLimited, AuthMissing, Timeout, Degraded, NotFound tanımla.
3. Work, Author, Venue, CitationEdge, ProviderSnapshot modelleri yaz.
4. Mevcut OpenAlex kullanım noktalarını inventory çıkar.

**Test/doğrulama:**
- unit: provider protocol model serialization
- unit: provider error mapping

**Başarı tanımı:**
- Review/citation servisleri provider-specific parametre bilmeden çalışabilecek interface’e sahip.

**Bir sonraki adıma geçiş:** OpenAlex implementation bu interface’e bağlanmaya hazır olduğunda.

**Durdurma koşulları:**
- Business logic içinde raw OpenAlex URL/params kalmaya devam ediyorsa.

---

### P02-T04_OPENALEX_API_KEY_MIGRATION — OpenAlex mailto/polite mirasını API-key provider client’a taşı

**Öncelik:** P0  
**Bağımlılıklar:** P02-T03_PROVIDER_ABSTRACTION_FOUNDATION

**Dokunulacak dosyalar:**
- `api/services/openalex_polite.py`
- `api/providers/openalex/client.py`
- `api/config.py`
- `.env.example`
- `tests/unit/test_openalex_polite.py`

**Uygulama adımları:**
1. OPENALEX_EMAIL/mailto/polite pool kullanımını deprecated wrapper’a al veya kaldır.
2. OPENALEX_API_KEY env tanımla ve production’da required/degraded policy belirle.
3. Rate limit, retry, cache ve auth-missing davranışlarını provider error olarak döndür.
4. Eski testleri yeni client’a taşı.

**Test/doğrulama:**
- unit: API key header/param behavior
- unit: auth missing => degraded state
- unit: rate limit retry/backoff

**Başarı tanımı:**
- OpenAlex provider yeni abstraction ile çalışıyor, mailto/polite production path’te yok.

**Bir sonraki adıma geçiş:** Citation/literature calls OpenAlex client üzerinden çalıştığında.

**Durdurma koşulları:**
- Provider yokken sahte literatür sonucu üretiliyorsa.

---

### P02-T05_DEGRADED_MODE_AND_PROVENANCE_PIPELINE — Silent fallback yerine görünür degraded/provenance pipeline

**Öncelik:** P0  
**Bağımlılıklar:** P02-T04_OPENALEX_API_KEY_MIGRATION

**Dokunulacak dosyalar:**
- `api/models/review.py`
- `api/services/review_service.py`
- `api/services/review_orchestration.py`
- `web/src/components/review/ReviewReportView.tsx`

**Uygulama adımları:**
1. EvidencePack içine provider_snapshots, degraded_features, unavailable_checks ekle.
2. Her stage kendi confidence ve limitation metadata’sını yazsın.
3. Frontend raporda “bu bulgu sınırlı doğrulandı” badge’i göstersin.
4. Mock/fallback pathler production’da error veya degraded state üretsin.

**Test/doğrulama:**
- unit: provider down creates degraded evidence
- frontend render degraded badge test
- eval fixture with missing provider

**Başarı tanımı:**
- Sistem hiçbir akademik bulguyu sessiz fallback ile tam güvenilir gibi sunmuyor.

**Bir sonraki adıma geçiş:** Report metadata tüm provider/stage sınırlamalarını taşıdığında.

**Durdurma koşulları:**
- Empty list fallback confidence artırıyorsa.

---
