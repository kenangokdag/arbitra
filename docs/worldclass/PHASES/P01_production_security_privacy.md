# P01 — Production Güvenlik, Gizlilik ve Launch Blocker Temizliği

## Amaç

Production’da mock, silent fallback, authz, rate-limit, confidential manuscript ve external AI riskleri kapatılır.

## Faz kapısı

Security/privacy checklist yeşil; başka kullanıcı objesine erişim testleri geçiyor; mock auth production build’e giremiyor.

## İlgili spec dosyaları

- `docs/worldclass/SPECS/security_privacy_threat_model.md`
- `docs/worldclass/SPECS/backend_architecture_spec.md`

## Görevler

### P01-T01_KILL_PRODUCTION_MOCK_AUTH — Production mock auth ve dev token üretimini imkânsız yap

**Öncelik:** P0  
**Bağımlılıklar:** P00-T03_AUTONOMOUS_STATE_AND_LEDGER

**Dokunulacak dosyalar:**
- `web/src/lib/auth.ts`
- `api/middleware/auth.py`
- `api/config.py`
- `.env.example`
- `.github/workflows/polish_gate.yml`

**Uygulama adımları:**
1. Dev auth yalnız APP_ENV=development ve localhost şartında çalışacak şekilde ayır.
2. Production build’de dev-mock-signature, mock token, fake user id bundle’a girerse CI fail.
3. Backend production’da dev token kabul etmeyecek.
4. Env validation: APP_ENV=production ve auth provider eksikse boot fail.

**Test/doğrulama:**
- unit test: dev token production rejected
- frontend grep/build guard test
- middleware auth tests

**Başarı tanımı:**
- Production build mock auth ile alınamaz.
- Dev auth local developer deneyimini kırmadan izole.

**Bir sonraki adıma geçiş:** CI guard ve backend auth tests yeşil olduğunda.

**Durdurma koşulları:**
- Gerçek auth provider kararı yoksa secure fail-closed bırak.

---

### P01-T02_OBJECT_LEVEL_AUTHORIZATION_MATRIX — Review domain için object-level authorization matrisi ve testleri

**Öncelik:** P0  
**Bağımlılıklar:** P01-T01_KILL_PRODUCTION_MOCK_AUTH

**Dokunulacak dosyalar:**
- `api/routes/review.py`
- `api/services/review_service.py`
- `api/db/supabase_client.py`
- `tests/unit/test_middleware.py`
- `tests/integration/test_review_routes.py`

**Uygulama adımları:**
1. ReviewJob, ReviewReport, EvidencePack, export ve audit objeleri için owner/tenant kuralları yaz.
2. Her GET/POST/PATCH/DELETE endpoint’te user_id/tenant_id kontrolünü servis seviyesine indir.
3. User A cannot access User B senaryolarını integration test yap.
4. Admin role için RBAC boundary oluştur; string allowlist kullanma.

**Test/doğrulama:**
- integration: user_a cannot read user_b job
- unit: service rejects mismatched owner
- admin RBAC negative tests

**Başarı tanımı:**
- Kritik review endpointlerinin tamamında BOLA testi var.

**Bir sonraki adıma geçiş:** 403/404 semantics kararlı ve testli olduğunda.

**Durdurma koşulları:**
- Service-role RLS bypass ediyor ama manuel owner check yoksa.

---

### P01-T03_CONFIDENTIALITY_AND_EXTERNAL_AI_CONSENT — Confidential manuscript mode ve external AI consent gate

**Öncelik:** P0  
**Bağımlılıklar:** P01-T02_OBJECT_LEVEL_AUTHORIZATION_MATRIX

**Dokunulacak dosyalar:**
- `api/models/review.py`
- `api/routes/review.py`
- `api/services/review_service.py`
- `web/src/app/(app)/review/page.tsx`
- `web/src/lib/review-api.ts`
- `db/migrations/0041_review_domain.sql`

**Uygulama adımları:**
1. ReviewCreateRequest içine document_ownership_mode, confidentiality_mode, external_ai_consent, retention_policy alanları ekle.
2. Editor/reviewer mode’da external_ai_consent=false default yap.
3. LLM/provider çağrılarından önce consent gate middleware/service check ekle.
4. Frontend wizard’da “dosya size mi ait / gizli hakemlik dosyası mı?” adımı ekle.
5. Rapor metadata’sında AI usage disclosure oluştur.

**Test/doğrulama:**
- unit: confidential mode blocks external LLM without consent
- frontend wizard contract test
- db migration test

**Başarı tanımı:**
- Confidential flow external AI kullanmadan çalışabiliyor veya açıkça degraded gösteriyor.

**Bir sonraki adıma geçiş:** Kullanıcı hangi verinin nereye gittiğini görmeden review başlayamıyorsa.

**Durdurma koşulları:**
- Gizli dosya external providera sessiz gönderiliyorsa.

---

### P01-T04_FAIL_CLOSED_RATE_LIMIT_AND_QUOTA — Production rate-limit/quota fail-closed davranışı

**Öncelik:** P0  
**Bağımlılıklar:** P01-T01_KILL_PRODUCTION_MOCK_AUTH

**Dokunulacak dosyalar:**
- `api/middleware/rate_limit.py`
- `api/middleware/tier_gate.py`
- `api/db/redis_client.py`
- `api/config.py`
- `.env.example`

**Uygulama adımları:**
1. Redis yoksa development dışında expensive endpointleri fail-closed yap.
2. Review create/export/provider endpoints için tier-aware quota tanımla.
3. Quota error response kullanıcıya açık ve retry-after taşısın.
4. Silent bypass envleri production’da yasakla.

**Test/doğrulama:**
- unit: production redis missing => fail closed
- integration: quota exceeded response
- env validation test

**Başarı tanımı:**
- Production quota Redis/real backing olmadan bypass olmuyor.

**Bir sonraki adıma geçiş:** Expensive review endpointleri kontrolsüz çağrılamadığında.

**Durdurma koşulları:**
- WAITLIST_BYPASS veya quota bypass production’da true kalabiliyorsa.

---

### P01-T05_FILE_SECURITY_AND_RETENTION_BASELINE — Dosya güvenliği, parser sandbox ve retention baseline

**Öncelik:** P0  
**Bağımlılıklar:** P01-T03_CONFIDENTIALITY_AND_EXTERNAL_AI_CONSENT

**Dokunulacak dosyalar:**
- `engine/ingestion/zip_handler.py`
- `engine/ingestion/pdf_parser.py`
- `engine/ingestion/docx_parser.py`
- `engine/ingestion/latex_parser.py`
- `api/services/manuscript_service.py`
- `db/migrations/0041_review_domain.sql`

**Uygulama adımları:**
1. Magic-byte + MIME + extension üçlü doğrulama ekle.
2. ZIP path traversal, nested archive, zip bomb limitlerini testle.
3. Parser timeout, max page/token/size limitlerini config’e taşı.
4. Retention policy alanlarını storage/delete flow’a bağla.
5. Audit event: file_uploaded, file_parsed, file_deleted.

**Test/doğrulama:**
- unit: malicious zip fixtures rejected
- unit: mime mismatch rejected
- integration: delete/retention event emitted

**Başarı tanımı:**
- Untrusted file parser sınırları ve delete flow testli.

**Bir sonraki adıma geçiş:** Dosya işleme güvenlik checklist’i yeşil olduğunda.

**Durdurma koşulları:**
- Parser unbounded resource tüketebiliyorsa.

---
