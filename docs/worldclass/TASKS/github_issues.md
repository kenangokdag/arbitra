# Arbitra World-Class Roadmap Issues

## P00-T01_BRAND_AND_PRODUCT_CONTRACT — Arbitra/PaperMind marka ve ürün sözleşmesini tekilleştir

- Phase: P00
- Priority: P0
- Dependencies: None

### Touchpoints
- `web/src/lib/brand.ts`
- `web/src/components/review/ArbitraWordmark.tsx`
- `web/src/app/(marketing)/landing/page.tsx`
- `README.md`
- `docs/ARCHITECTURE.md`

### Implementation steps
1. Arbitra ana ürün, PaperMind suite/platform varsayımını kod ve docs içinde sözleşmeye bağla.
2. brand.ts içinde tek source-of-truth oluştur: productName, suiteName, tagline, confidentiality promise, review modes.
3. Landing ve review sayfalarındaki PaperMind/Arbitra karışıklığını inventory çıkarıp düzelt.
4. Docs içinde eski marka iddialarını yeni sözleşmeye göre güncelle.

### Tests
- [ ] brand contract unit/snapshot test
- [ ] landing text smoke test

### Done when
- [ ] Tek marka sözleşmesi var.
- [ ] UI copy çelişmiyor.
- [ ] Agent ve insan aynı product definition ile ilerliyor.

---

## P00-T02_REPO_REALITY_DOC_SYNC — README/ARCHITECTURE/SECURITY gerçek kodla eşitlensin

- Phase: P00
- Priority: P0
- Dependencies: P00-T01_BRAND_AND_PRODUCT_CONTRACT

### Touchpoints
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/STATE.md`
- `docs/NEXT_ACTION.md`
- `pyproject.toml`
- `web/package.json`

### Implementation steps
1. README’de Next/FastAPI/worker/env iddialarını gerçek package ve kodla karşılaştır.
2. Celery/worker varsa gerçek implementation path yaz; yoksa roadmap olarak işaretle.
3. Docs içindeki outdated provider, env, deployment ve mock ifadelerini güncelle.
4. docs/worldclass/STATE.md içine mevcut gerçeklik snapshot’ı yaz.

### Tests
- [ ] docs grep check for obsolete claims
- [ ] manual docs/code consistency checklist

### Done when
- [ ] Ana docs gerçek kodu yansıtıyor.
- [ ] Hayali worker/provider iddiası yok.

---

## P00-T03_AUTONOMOUS_STATE_AND_LEDGER — Otonom ilerleme state/ledger dosyalarını aktifleştir

- Phase: P00
- Priority: P0
- Dependencies: P00-T02_REPO_REALITY_DOC_SYNC

### Touchpoints
- `docs/worldclass/STATE.md`
- `docs/worldclass/TASKS/backlog.csv`
- `docs/worldclass/TEMPLATES/pr_template.md`

### Implementation steps
1. STATE.md içinde active task, completed tasks, verification commands alanlarını agent için güncelle.
2. Backlog CSV/YAML task status alanını kullanılır hâle getir.
3. PR template ile task ID zorunluluğu getir.

### Tests
- [ ] Manual: agent can pick next task from ROADMAP.yaml

### Done when
- [ ] Her task sonunda güncellenecek tek state dosyası var.

---

## P01-T01_KILL_PRODUCTION_MOCK_AUTH — Production mock auth ve dev token üretimini imkânsız yap

- Phase: P01
- Priority: P0
- Dependencies: P00-T03_AUTONOMOUS_STATE_AND_LEDGER

### Touchpoints
- `web/src/lib/auth.ts`
- `api/middleware/auth.py`
- `api/config.py`
- `.env.example`
- `.github/workflows/polish_gate.yml`

### Implementation steps
1. Dev auth yalnız APP_ENV=development ve localhost şartında çalışacak şekilde ayır.
2. Production build’de dev-mock-signature, mock token, fake user id bundle’a girerse CI fail.
3. Backend production’da dev token kabul etmeyecek.
4. Env validation: APP_ENV=production ve auth provider eksikse boot fail.

### Tests
- [ ] unit test: dev token production rejected
- [ ] frontend grep/build guard test
- [ ] middleware auth tests

### Done when
- [ ] Production build mock auth ile alınamaz.
- [ ] Dev auth local developer deneyimini kırmadan izole.

---

## P01-T02_OBJECT_LEVEL_AUTHORIZATION_MATRIX — Review domain için object-level authorization matrisi ve testleri

- Phase: P01
- Priority: P0
- Dependencies: P01-T01_KILL_PRODUCTION_MOCK_AUTH

### Touchpoints
- `api/routes/review.py`
- `api/services/review_service.py`
- `api/db/supabase_client.py`
- `tests/unit/test_middleware.py`
- `tests/integration/test_review_routes.py`

### Implementation steps
1. ReviewJob, ReviewReport, EvidencePack, export ve audit objeleri için owner/tenant kuralları yaz.
2. Her GET/POST/PATCH/DELETE endpoint’te user_id/tenant_id kontrolünü servis seviyesine indir.
3. User A cannot access User B senaryolarını integration test yap.
4. Admin role için RBAC boundary oluştur; string allowlist kullanma.

### Tests
- [ ] integration: user_a cannot read user_b job
- [ ] unit: service rejects mismatched owner
- [ ] admin RBAC negative tests

### Done when
- [ ] Kritik review endpointlerinin tamamında BOLA testi var.

---

## P01-T03_CONFIDENTIALITY_AND_EXTERNAL_AI_CONSENT — Confidential manuscript mode ve external AI consent gate

- Phase: P01
- Priority: P0
- Dependencies: P01-T02_OBJECT_LEVEL_AUTHORIZATION_MATRIX

### Touchpoints
- `api/models/review.py`
- `api/routes/review.py`
- `api/services/review_service.py`
- `web/src/app/(app)/review/page.tsx`
- `web/src/lib/review-api.ts`
- `db/migrations/0041_review_domain.sql`

### Implementation steps
1. ReviewCreateRequest içine document_ownership_mode, confidentiality_mode, external_ai_consent, retention_policy alanları ekle.
2. Editor/reviewer mode’da external_ai_consent=false default yap.
3. LLM/provider çağrılarından önce consent gate middleware/service check ekle.
4. Frontend wizard’da “dosya size mi ait / gizli hakemlik dosyası mı?” adımı ekle.
5. Rapor metadata’sında AI usage disclosure oluştur.

### Tests
- [ ] unit: confidential mode blocks external LLM without consent
- [ ] frontend wizard contract test
- [ ] db migration test

### Done when
- [ ] Confidential flow external AI kullanmadan çalışabiliyor veya açıkça degraded gösteriyor.

---

## P01-T04_FAIL_CLOSED_RATE_LIMIT_AND_QUOTA — Production rate-limit/quota fail-closed davranışı

- Phase: P01
- Priority: P0
- Dependencies: P01-T01_KILL_PRODUCTION_MOCK_AUTH

### Touchpoints
- `api/middleware/rate_limit.py`
- `api/middleware/tier_gate.py`
- `api/db/redis_client.py`
- `api/config.py`
- `.env.example`

### Implementation steps
1. Redis yoksa development dışında expensive endpointleri fail-closed yap.
2. Review create/export/provider endpoints için tier-aware quota tanımla.
3. Quota error response kullanıcıya açık ve retry-after taşısın.
4. Silent bypass envleri production’da yasakla.

### Tests
- [ ] unit: production redis missing => fail closed
- [ ] integration: quota exceeded response
- [ ] env validation test

### Done when
- [ ] Production quota Redis/real backing olmadan bypass olmuyor.

---

## P01-T05_FILE_SECURITY_AND_RETENTION_BASELINE — Dosya güvenliği, parser sandbox ve retention baseline

- Phase: P01
- Priority: P0
- Dependencies: P01-T03_CONFIDENTIALITY_AND_EXTERNAL_AI_CONSENT

### Touchpoints
- `engine/ingestion/zip_handler.py`
- `engine/ingestion/pdf_parser.py`
- `engine/ingestion/docx_parser.py`
- `engine/ingestion/latex_parser.py`
- `api/services/manuscript_service.py`
- `db/migrations/0041_review_domain.sql`

### Implementation steps
1. Magic-byte + MIME + extension üçlü doğrulama ekle.
2. ZIP path traversal, nested archive, zip bomb limitlerini testle.
3. Parser timeout, max page/token/size limitlerini config’e taşı.
4. Retention policy alanlarını storage/delete flow’a bağla.
5. Audit event: file_uploaded, file_parsed, file_deleted.

### Tests
- [ ] unit: malicious zip fixtures rejected
- [ ] unit: mime mismatch rejected
- [ ] integration: delete/retention event emitted

### Done when
- [ ] Untrusted file parser sınırları ve delete flow testli.

---

## P02-T01_REVIEW_JOB_STAGE_SCHEMA — Review job stage/progress schema genişletmesi

- Phase: P02
- Priority: P0
- Dependencies: P01-T05_FILE_SECURITY_AND_RETENTION_BASELINE

### Touchpoints
- `api/models/review.py`
- `db/migrations/0041_review_domain.sql`
- `web/src/lib/review-api.ts`
- `web/src/hooks/useReview.ts`

### Implementation steps
1. ReviewJob status modelini queued/running/stage_failed/completed/cancelled olarak genişlet.
2. Stage enum ekle: security_scan, parse, classify, references, evidence, guidelines, council, synthesis, export.
3. Stage progress, started_at, completed_at, error_code, degraded_reason alanları ekle.
4. Frontend type contract güncelle.

### Tests
- [ ] model serialization test
- [ ] migration test
- [ ] frontend type/contract test

### Done when
- [ ] Job progress tek numeric bar değil stage-based contract taşıyor.

---

## P02-T02_DURABLE_WORKFLOW_ADAPTER — BackgroundTasks yerine durable workflow adapter interface

- Phase: P02
- Priority: P0
- Dependencies: P02-T01_REVIEW_JOB_STAGE_SCHEMA

### Touchpoints
- `api/routes/review.py`
- `api/services/review_service.py`
- `api/services/review_orchestration.py`
- `api/services/progress_service.py`
- `pyproject.toml`
- `docs/backend/celery_setup.md`

### Implementation steps
1. WorkflowClient protocol tanımla: enqueue, cancel, retry, get_status.
2. Development için in-memory/dev runner, production için queue adapter tasarla.
3. FastAPI BackgroundTasks kullanımını review route dışına çıkar.
4. Idempotency key ve job dedupe ekle.
5. Worker function her stage’i DB’ye checkpoint etsin.

### Tests
- [ ] unit: enqueue creates durable job
- [ ] unit: duplicate idempotency key returns same job
- [ ] integration/smoke: worker resumes failed stage

### Done when
- [ ] API process restart senaryosu job kaybına yol açmayacak şekilde tasarlandı/uygulandı.

---

## P02-T03_PROVIDER_ABSTRACTION_FOUNDATION — Scholarly provider abstraction temeli

- Phase: P02
- Priority: P0
- Dependencies: P02-T01_REVIEW_JOB_STAGE_SCHEMA

### Touchpoints
- `api/services/openalex_polite.py`
- `api/services/papers_hydration_service.py`
- `api/services/citation_service.py`
- `api/config.py`
- `tests/fixtures/openalex_search.json`

### Implementation steps
1. api/providers/scholarly/base.py içinde ScholarlyProvider Protocol oluştur.
2. Provider errors: RateLimited, AuthMissing, Timeout, Degraded, NotFound tanımla.
3. Work, Author, Venue, CitationEdge, ProviderSnapshot modelleri yaz.
4. Mevcut OpenAlex kullanım noktalarını inventory çıkar.

### Tests
- [ ] unit: provider protocol model serialization
- [ ] unit: provider error mapping

### Done when
- [ ] Review/citation servisleri provider-specific parametre bilmeden çalışabilecek interface’e sahip.

---

## P02-T04_OPENALEX_API_KEY_MIGRATION — OpenAlex mailto/polite mirasını API-key provider client’a taşı

- Phase: P02
- Priority: P0
- Dependencies: P02-T03_PROVIDER_ABSTRACTION_FOUNDATION

### Touchpoints
- `api/services/openalex_polite.py`
- `api/providers/openalex/client.py`
- `api/config.py`
- `.env.example`
- `tests/unit/test_openalex_polite.py`

### Implementation steps
1. OPENALEX_EMAIL/mailto/polite pool kullanımını deprecated wrapper’a al veya kaldır.
2. OPENALEX_API_KEY env tanımla ve production’da required/degraded policy belirle.
3. Rate limit, retry, cache ve auth-missing davranışlarını provider error olarak döndür.
4. Eski testleri yeni client’a taşı.

### Tests
- [ ] unit: API key header/param behavior
- [ ] unit: auth missing => degraded state
- [ ] unit: rate limit retry/backoff

### Done when
- [ ] OpenAlex provider yeni abstraction ile çalışıyor, mailto/polite production path’te yok.

---

## P02-T05_DEGRADED_MODE_AND_PROVENANCE_PIPELINE — Silent fallback yerine görünür degraded/provenance pipeline

- Phase: P02
- Priority: P0
- Dependencies: P02-T04_OPENALEX_API_KEY_MIGRATION

### Touchpoints
- `api/models/review.py`
- `api/services/review_service.py`
- `api/services/review_orchestration.py`
- `web/src/components/review/ReviewReportView.tsx`

### Implementation steps
1. EvidencePack içine provider_snapshots, degraded_features, unavailable_checks ekle.
2. Her stage kendi confidence ve limitation metadata’sını yazsın.
3. Frontend raporda “bu bulgu sınırlı doğrulandı” badge’i göstersin.
4. Mock/fallback pathler production’da error veya degraded state üretsin.

### Tests
- [ ] unit: provider down creates degraded evidence
- [ ] frontend render degraded badge test
- [ ] eval fixture with missing provider

### Done when
- [ ] Sistem hiçbir akademik bulguyu sessiz fallback ile tam güvenilir gibi sunmuyor.

---

## P03-T01_MANUSCRIPT_TYPE_CLASSIFIER — Belge türü sınıflandırıcı: makale/bildiri/tez/proje

- Phase: P03
- Priority: P0
- Dependencies: P02-T05_DEGRADED_MODE_AND_PROVENANCE_PIPELINE

### Touchpoints
- `api/models/review.py`
- `api/services/review_orchestration.py`
- `engine/ingestion/builder.py`
- `tests/unit/test_review_orchestration.py`

### Implementation steps
1. DocumentType enum ekle: journal_article, conference_paper, thesis, grant_proposal, preprint, technical_report, unknown.
2. Classifier input: sections, title, abstract, headings, metadata, file hints.
3. Confidence ve rationale üret.
4. User override alanı ekle; model tahminini kullanıcı seçimiyle reconcile et.

### Tests
- [ ] fixtures: thesis detected
- [ ] fixtures: grant detected
- [ ] low confidence => ask/unknown behavior

### Done when
- [ ] Review job belge türünü confidence ile saklıyor ve rubrik seçimi buna bağlanıyor.

---

## P03-T02_STUDY_DESIGN_CLASSIFIER — Çalışma türü sınıflandırıcı

- Phase: P03
- Priority: P0
- Dependencies: P03-T01_MANUSCRIPT_TYPE_CLASSIFIER

### Touchpoints
- `api/models/review.py`
- `api/services/review_orchestration.py`
- `engine/checklist/*`
- `tests/unit/test_review_orchestration.py`

### Implementation steps
1. StudyDesign enum ekle: qualitative, quantitative, mixed_methods, systematic_review, meta_analysis, scoping_review, theoretical, design_science, computational, dataset, software, replication, protocol, unknown.
2. Section cues ve method terms ile classifier yaz.
3. Confidence/rationale ve multi-label destekle.
4. Study design rubrik ve guideline selector’a input olsun.

### Tests
- [ ] qualitative fixture
- [ ] systematic review fixture
- [ ] mixed methods fixture
- [ ] unknown/low confidence fixture

### Done when
- [ ] Aynı belge türü altında farklı çalışma türleri farklı review path’e gidiyor.

---

## P03-T03_RUBRIC_REGISTRY_AND_DIMENSION_SCHEMA — RubricRegistry ve genişletilmiş akademik dimension schema

- Phase: P03
- Priority: P0
- Dependencies: P03-T02_STUDY_DESIGN_CLASSIFIER

### Touchpoints
- `api/models/review.py`
- `engine/checklist/makale_tr.json`
- `engine/checklist/tez_tr.json`
- `api/services/review_orchestration.py`

### Implementation steps
1. AcademicDimension enum/model tasarla: contribution, theory, literature, methods, data, analysis, claims, citation, guideline, ethics, reproducibility, writing, venue_fit.
2. RubricRegistry belge+study_type kombinasyonuna göre dimension weights döndürsün.
3. Her dimension severity/confidence/action_items/evidence_anchors taşısın.
4. Mevcut DimensionKey geriye uyumluluk adapter’ı yaz.

### Tests
- [ ] unit: article qualitative rubric selected
- [ ] unit: thesis rubric selected
- [ ] schema backwards compatibility test

### Done when
- [ ] ReviewReport generic DimensionScore yerine zengin academic dimension taşıyabiliyor.

---

## P03-T04_QUALITATIVE_RIGOR_ENGINE — Nitel araştırma hakemlik motoru

- Phase: P03
- Priority: P0
- Dependencies: P03-T03_RUBRIC_REGISTRY_AND_DIMENSION_SCHEMA

### Touchpoints
- `api/services/review_orchestration.py`
- `api/services/role_modules/reviewer_yontemci.py`
- `engine/checklist/*`
- `tests/unit/test_review_orchestration.py`

### Implementation steps
1. QualitativeRigorEngine oluştur.
2. Kontrol boyutları: paradigm, design fit, sampling, context, data collection, coding, theme development, quotes, reflexivity, trustworthiness, ethics, transferability, limitations.
3. Her boyut için evidence anchor ve action item üret.
4. Nitel çalışma tespitinde bu engine zorunlu çalışsın.

### Tests
- [ ] unit: missing reflexivity detected
- [ ] unit: unsupported theme claim flagged
- [ ] eval fixture qualitative report

### Done when
- [ ] Nitel çalışma raporu generic yöntem eleştirisi değil, nitel rigor boyutları içeriyor.

---

## P03-T05_QUANTITATIVE_VALIDITY_ENGINE — Nicel/istatistiksel geçerlilik motoru MVP

- Phase: P03
- Priority: P0
- Dependencies: P03-T03_RUBRIC_REGISTRY_AND_DIMENSION_SCHEMA

### Touchpoints
- `engine/statcheck/multilingual.json`
- `api/services/review_orchestration.py`
- `api/models/review.py`
- `tests/unit/test_review_eval.py`

### Implementation steps
1. QuantitativeValidityEngine oluştur veya mevcut statcheck’i genişlet.
2. p-value, CI, effect size, sample size, power, missing data, model assumptions, multiple comparisons, causal language kontrollerini schema’ya bağla.
3. Tablo/metin çelişkisi için MVP numeric extractor ekle.
4. Bulguları severity/confidence ile dön.

### Tests
- [ ] unit: causal wording in observational study flagged
- [ ] unit: missing effect size warning
- [ ] unit: p-value text pattern consistency

### Done when
- [ ] Nicel review yöntem/istatistik alanında uygulanabilir, anchor’lı riskler üretiyor.

---

## P03-T06_REPORTING_GUIDELINE_SELECTOR — Reporting guideline selector ve checklist engine

- Phase: P03
- Priority: P1
- Dependencies: P03-T04_QUALITATIVE_RIGOR_ENGINE, P03-T05_QUANTITATIVE_VALIDITY_ENGINE

### Touchpoints
- `engine/checklist/*`
- `api/services/review_orchestration.py`
- `api/models/review.py`
- `web/src/components/review/ReviewReportView.tsx`

### Implementation steps
1. GuidelineProfile modeli oluştur: id, name, applies_to, checklist_items, severity, evidence_required.
2. StudyDesign’e göre PRISMA/STROBE/CONSORT/COREQ/SRQR-like/TRIPOD/STARD/SPIRIT/ARRIVE vb. registry yapısı kur.
3. MVP’de public checklist text kopyalamadan kendi compliance item schema’nı kullan.
4. Rapor içinde guideline compliance bölümü göster.

### Tests
- [ ] unit: systematic_review => PRISMA-like profile
- [ ] unit: qualitative_interview => qualitative reporting profile
- [ ] frontend guideline checklist render

### Done when
- [ ] Çalışma türüne göre guideline uyumu ayrı bölüm olarak raporlanıyor.

---

## P04-T01_CLAIM_EXTRACTION_MODEL — Claim extraction ve manuscript anchor modeli

- Phase: P04
- Priority: P0
- Dependencies: P03-T03_RUBRIC_REGISTRY_AND_DIMENSION_SCHEMA

### Touchpoints
- `api/models/review.py`
- `engine/ingestion/common.py`
- `api/services/anchor_finder.py`
- `tests/unit/test_anchor_finder.py`

### Implementation steps
1. Claim model: text, section, anchor_id, claim_type, strength, evidence_needed.
2. Section/paragraph anchors ingestion’dan stable id alsın.
3. Claims introduction/results/discussion bölümlerinden çıkarılsın.
4. LLM output JSON schema validation ile sınırlandırılsın.

### Tests
- [ ] unit: stable anchor ids
- [ ] unit: claim schema validation
- [ ] fixture: claims extracted from sample manuscript

### Done when
- [ ] Rapor eleştirileri manuscript anchor id’ye bağlanabiliyor.

---

## P04-T02_REFERENCE_RESOLUTION_PIPELINE — Reference extraction ve DOI/provider resolution pipeline

- Phase: P04
- Priority: P0
- Dependencies: P02-T04_OPENALEX_API_KEY_MIGRATION

### Touchpoints
- `engine/ingestion/*`
- `api/services/review_citation_service.py`
- `api/providers/*`
- `tests/unit/test_review_citation.py`

### Implementation steps
1. Reference model standardize et: raw, title, authors, year, doi, source, resolution_status.
2. Crossref/OpenAlex/SemanticScholar adapter slotları oluştur.
3. Resolution confidence ve duplicate merge logic ekle.
4. Unresolved references reportta açık gösterilsin.

### Tests
- [ ] unit: DOI exact resolution
- [ ] unit: fuzzy title resolution confidence
- [ ] unit: unresolved does not fabricate

### Done when
- [ ] Atıflar provider ve confidence ile çözümleniyor.

---

## P04-T03_CLAIM_EVIDENCE_ALIGNMENT — Claim-evidence alignment ve citation support levels

- Phase: P04
- Priority: P0
- Dependencies: P04-T01_CLAIM_EXTRACTION_MODEL, P04-T02_REFERENCE_RESOLUTION_PIPELINE

### Touchpoints
- `api/models/review.py`
- `api/services/review_citation_service.py`
- `api/services/review_orchestration.py`
- `web/src/components/review/ReviewReportView.tsx`

### Implementation steps
1. SupportLevel enum: full_text_verified, abstract_only, metadata_only, unresolved, contradictory, not_applicable.
2. ClaimCitationAlignment model ekle.
3. Citation context ile claim strength uyumunu kontrol et.
4. Rapor dilinde abstract-only limitation açık yazılsın.

### Tests
- [ ] unit: abstract_only does not become verified
- [ ] unit: unsupported causal claim flagged
- [ ] frontend support level badge render

### Done when
- [ ] Citation integrity bulguları kaynak doğrulama seviyesini gösteriyor.

---

## P04-T04_LITERATURE_COVERAGE_AND_GAP_MAP — Literature coverage, seminal/recent/missing works ve gap map

- Phase: P04
- Priority: P1
- Dependencies: P04-T02_REFERENCE_RESOLUTION_PIPELINE

### Touchpoints
- `api/services/gap_profile_workshop_service.py`
- `api/services/originality_service.py`
- `api/services/review_citation_service.py`
- `web/src/components/project/GapHeatmapCard.tsx`

### Implementation steps
1. Manuscript topic/claims ile reference set arasında coverage analysis yap.
2. Recent/seminal/methodological/theoretical missing buckets oluştur.
3. Coverage confidence provider availability ile bağlansın.
4. Mevcut gap/originality modüllerini review output’a entegre et.

### Tests
- [ ] unit: missing recent works bucket
- [ ] unit: provider degraded lowers confidence
- [ ] frontend coverage section render

### Done when
- [ ] Literature critique “daha kaynak ekle” değil, hangi boşluk türü olduğunu söylüyor.

---

## P05-T01_PREMIUM_LANDING_REPOSITIONING — Landing page’i Arbitra Scientific Review OS olarak yeniden konumlandır

- Phase: P05
- Priority: P0
- Dependencies: P01-T03_CONFIDENTIALITY_AND_EXTERNAL_AI_CONSENT, P00-T01_BRAND_AND_PRODUCT_CONTRACT

### Touchpoints
- `web/src/app/(marketing)/landing/page.tsx`
- `web/src/components/marketing/WaitlistModal.tsx`
- `web/src/lib/brand.ts`
- `web/src/styles/globals.css`

### Implementation steps
1. Hero copy: hakeme gitmeden önce kırılma noktalarını görün.
2. Trust blocks: confidentiality-first, evidence-backed, methodology-aware, revision cockpit.
3. Comparison block: chatbot vs Arbitra.
4. Output preview: risk radar, reviewer objections, evidence map, action plan.
5. CTA: örnek rapor ve çalışmamı incelet.

### Tests
- [ ] component render test
- [ ] copy snapshot smoke
- [ ] accessibility landmarks manual check

### Done when
- [ ] Landing AI assistant template değil, hakemlik OS vaadi veriyor.

---

## P05-T02_REVIEW_INTAKE_WIZARD — Tek upload formunu guided review wizard’a çevir

- Phase: P05
- Priority: P0
- Dependencies: P02-T01_REVIEW_JOB_STAGE_SCHEMA, P01-T03_CONFIDENTIALITY_AND_EXTERNAL_AI_CONSENT

### Touchpoints
- `web/src/app/(app)/review/page.tsx`
- `web/src/lib/review-api.ts`
- `web/src/hooks/useReview.ts`
- `api/routes/review.py`

### Implementation steps
1. Wizard steps: file, document type, target, privacy, review depth.
2. Beginner default: Arbitra benim için seçsin.
3. Expert drawer: rubric, guideline, strictness, provider depth, locale, retention.
4. Backend create request contractını wizard state ile eşle.
5. Validation errorları kullanıcı dostu göster.

### Tests
- [ ] frontend wizard state test
- [ ] API contract test
- [ ] confidential mode wizard test

### Done when
- [ ] Yeni başlayan tek akışla review başlatır, uzman detay kontrolü alır.

---

## P05-T03_LIVE_REVIEW_COCKPIT_PROGRESS — Spinner yerine canlı review cockpit progress

- Phase: P05
- Priority: P0
- Dependencies: P02-T01_REVIEW_JOB_STAGE_SCHEMA

### Touchpoints
- `web/src/app/(app)/review/[jobId]/page.tsx`
- `web/src/hooks/useReview.ts`
- `web/src/components/review/ReviewReportView.tsx`
- `api/routes/review.py`

### Implementation steps
1. Stage timeline component oluştur.
2. Her stage için done/running/degraded/failed states.
3. İlk ara bulguları veya detected manuscript type göster.
4. Retry/cancel UI ekle.
5. Failure state çözüm önerisi ve support/debug id taşısın.

### Tests
- [ ] component test stage states
- [ ] polling hook test
- [ ] error/degraded render test

### Done when
- [ ] Kullanıcı beklerken sistemin ne yaptığını ve ne bulduğunu görüyor.

---

## P05-T04_DESIGN_SYSTEM_PREMIUM_TOKENS — Premium visual system tokens ve component kuralları

- Phase: P05
- Priority: P1
- Dependencies: P05-T01_PREMIUM_LANDING_REPOSITIONING

### Touchpoints
- `web/src/styles/globals.css`
- `web/src/components/ui/button.tsx`
- `web/src/components/Card.tsx`
- `docs/frontend/COMPONENT_RULES.md`

### Implementation steps
1. Editorial typography, spacing, elevation, surface, risk severity, evidence confidence tokenları tanımla.
2. Arbitra-specific components: RiskBadge, EvidenceBadge, ConfidenceMeter, ManuscriptAnchorLink.
3. Motion aşırı değil, anlamlı progress için kullanılsın.
4. Dark/light veya premium neutral palette tutarlı olsun.

### Tests
- [ ] visual smoke test
- [ ] component snapshot
- [ ] manual contrast check

### Done when
- [ ] UI parçaları random Tailwind değil tutarlı product language taşıyor.

---

## P06-T01_REVIEW_REPORT_SCHEMA_V2 — ReviewReport v2: verdict, risk, council, evidence, action plan

- Phase: P06
- Priority: P0
- Dependencies: P03-T03_RUBRIC_REGISTRY_AND_DIMENSION_SCHEMA, P04-T03_CLAIM_EVIDENCE_ALIGNMENT

### Touchpoints
- `api/models/review.py`
- `api/services/review_orchestration.py`
- `web/src/lib/review-api.ts`
- `web/src/components/review/ReviewReportView.tsx`

### Implementation steps
1. Report sections: executive_verdict, risk_radar, reviewer_council, evidence_map, action_plan, section_reviews, exports.
2. Backward compatibility adapter ekle.
3. Every high severity item requires anchor/action/confidence.
4. Report schema versioning ekle.

### Tests
- [ ] schema validation
- [ ] backward compatibility fixture
- [ ] frontend render report v2

### Done when
- [ ] Rapor yapısal olarak cockpit’e hizmet ediyor.

---

## P06-T02_REVIEWER_COUNCIL_ENGINE — Persona modüllerini Reviewer Council Engine’e dönüştür

- Phase: P06
- Priority: P0
- Dependencies: P06-T01_REVIEW_REPORT_SCHEMA_V2

### Touchpoints
- `api/services/review_orchestration.py`
- `api/services/role_modules/*`
- `engine/personas/review/*`

### Implementation steps
1. Council roles: methodologist, field_expert, skeptical_reviewer, constructive_reviewer, citation_auditor, ethics_reviewer, statistics_reviewer, editor_synthesizer.
2. Her role output schema’sı aynı: findings, severity, evidence, actions, confidence.
3. Editor synthesizer duplicate findings merge etsin.
4. Role weights rubric/study type’a göre değişsin.

### Tests
- [ ] unit: council role schema validation
- [ ] unit: duplicate merge
- [ ] fixture: qualitative role weighting

### Done when
- [ ] Persona outputları serbest metin değil birleşebilir structured findings üretiyor.

---

## P06-T03_ACTION_PLAN_AND_REVISION_TASKS — P0/P1/P2 revision action plan ve task modeli

- Phase: P06
- Priority: P0
- Dependencies: P06-T01_REVIEW_REPORT_SCHEMA_V2

### Touchpoints
- `api/models/review.py`
- `web/src/components/review/ReviewReportView.tsx`
- `web/src/app/(app)/review/[jobId]/page.tsx`

### Implementation steps
1. ActionItem model: priority, effort, expected_gain, target_section, instruction, acceptance_check.
2. Risk findings action item’a bağlansın.
3. Frontend’de actionable checklist ve filters.
4. Done/ignored/user note state için local/server model tasarla.

### Tests
- [ ] schema test action item required fields
- [ ] frontend checklist interaction test

### Done when
- [ ] Kullanıcı rapordan doğrudan revizyon planı çıkarabiliyor.

---

## P06-T04_EXPORTS_AND_RESPONSE_TO_REVIEWERS — PDF/DOCX/Markdown/LaTeX export ve response-to-reviewers assistant

- Phase: P06
- Priority: P1
- Dependencies: P06-T03_ACTION_PLAN_AND_REVISION_TASKS

### Touchpoints
- `api/routes/review.py`
- `api/services/review_service.py`
- `web/src/components/review/ReviewReportView.tsx`
- `web/src/lib/review-api.ts`

### Implementation steps
1. Export endpoint contract: format, sections, include_evidence, include_disclosure.
2. Markdown ilk MVP, PDF/DOCX sonra adapter.
3. Response-to-reviewers draft: issue, proposed fix, polite response, evidence.
4. Export audit event ekle.

### Tests
- [ ] unit: markdown export snapshot
- [ ] integration: export authz
- [ ] frontend export button state

### Done when
- [ ] Rapor dış dünyada kullanılabilir çıktı formatlarına dönüşüyor.

---

## P07-T01_GOLDSET_AND_EVAL_SCHEMA — Goldset ve eval schema’yı dünya klası metriklerle genişlet

- Phase: P07
- Priority: P0
- Dependencies: P06-T01_REVIEW_REPORT_SCHEMA_V2

### Touchpoints
- `eval/review/goldset.json`
- `eval/review/schema.py`
- `eval/review/metrics.py`
- `eval/review/README.md`

### Implementation steps
1. Eval labels: document_type, study_design, expected_findings, citation_truth, guideline_items, hallucination_flags, actionability score.
2. Goldset kategorileri: article, conference, thesis, grant, qualitative, quantitative, systematic.
3. Metrikleri schema’ya bağla.

### Tests
- [ ] unit: eval schema validation
- [ ] unit: metrics compute on sample_reports

### Done when
- [ ] Eval sadece skor değil akademik kalite boyutlarını ölçüyor.

---

## P07-T02_RELEASE_EVAL_GATE — Release eval gate ve regression thresholdları

- Phase: P07
- Priority: P0
- Dependencies: P07-T01_GOLDSET_AND_EVAL_SCHEMA

### Touchpoints
- `eval/review/run_eval.py`
- `.github/workflows/polish_gate.yml`
- `config/faithfulness_thresholds.yaml`

### Implementation steps
1. Eval komutu CI’da opsiyonel/required mode desteklesin.
2. Thresholdlar: hallucination max, actionability min, citation precision min, schema validity 100%.
3. Regression durumunda release fail.
4. Eval report artifact üret.

### Tests
- [ ] CI dry run
- [ ] unit: threshold failure exits nonzero

### Done when
- [ ] Yeni prompt/model değişikliği kaliteyi düşürürse yakalanıyor.

---

## P07-T03_HUMAN_EXPERT_REVIEW_LOOP — Human expert feedback loop ve calibration workflow

- Phase: P07
- Priority: P1
- Dependencies: P07-T01_GOLDSET_AND_EVAL_SCHEMA

### Touchpoints
- `eval/review/build_goldset.py`
- `docs/worldclass/TEMPLATES/eval_card_template.md`
- `api/models/review.py`

### Implementation steps
1. Expert reviewer annotation template oluştur.
2. False positive/false negative taxonomy tut.
3. Rubric weights calibration dosyasına bağla.
4. Eval dashboard için JSON report standardize et.

### Tests
- [ ] sample annotation import test
- [ ] metrics with human labels test

### Done when
- [ ] Akademik kalite insan uzman kıyasına bağlanabilir.

---

## P08-T01_LANGUAGE_CONFIG_MODEL — Source language, output language ve UI locale ayrımı

- Phase: P08
- Priority: P0
- Dependencies: P06-T01_REVIEW_REPORT_SCHEMA_V2

### Touchpoints
- `api/models/review.py`
- `web/src/lib/review-api.ts`
- `web/src/lib/i18n/*`
- `api/services/translator.py`

### Implementation steps
1. LanguageConfig model: source_language, output_language, ui_locale, citation_language_policy, rtl.
2. Review create request ve report metadata’ya ekle.
3. TR/EN literal type kısıtlarını kaldırıp BCP-47 string validation yap.
4. Bilingual quote policy: original quote + translated explanation.

### Tests
- [ ] unit: language config validation
- [ ] frontend type test
- [ ] RTL smoke where possible

### Done when
- [ ] 100 dil vizyonu teknik olarak iki literal ile sınırlı değil.

---

## P08-T02_TENANT_AND_ENTERPRISE_BOUNDARIES — Tenant/institution boundary ve enterprise deployment temeli

- Phase: P08
- Priority: P1
- Dependencies: P01-T02_OBJECT_LEVEL_AUTHORIZATION_MATRIX

### Touchpoints
- `api/models/*`
- `api/middleware/auth.py`
- `api/db/supabase_client.py`
- `db/migrations/*`

### Implementation steps
1. Tenant model ve membership roles tasarla.
2. Institution policy: retention, allowed providers, local model required, export controls.
3. Tenant-aware authz tests.
4. Future on-prem/private cloud config surface.

### Tests
- [ ] tenant A cannot access tenant B
- [ ] institution policy blocks external provider

### Done when
- [ ] Kurumsal kullanıcı için veri sınırı ve provider policy uygulanabiliyor.

---

## P09-T01_OBSERVABILITY_AND_AUDIT_RUNBOOKS — Review OS observability, audit ve runbook seti

- Phase: P09
- Priority: P0
- Dependencies: P02-T02_DURABLE_WORKFLOW_ADAPTER, P01-T03_CONFIDENTIALITY_AND_EXTERNAL_AI_CONSENT

### Touchpoints
- `api/middleware/sentry.py`
- `api/services/review_service.py`
- `docs/runbook/*`
- `docs/worldclass/SPECS/observability_runbook_spec.md`

### Implementation steps
1. Metrics: review latency by stage, provider errors, degraded rate, LLM cost, citation resolution rate.
2. Audit events: create, upload, parse, external_provider_call, report_view, export, delete.
3. Runbooks: provider down, queue stuck, auth incident, data deletion, eval regression.
4. Correlation id/debug id kullanıcı hata ekranına bağlansın.

### Tests
- [ ] unit: audit event emitted
- [ ] manual runbook drill
- [ ] metrics smoke

### Done when
- [ ] Production incident olduğunda neye bakılacağı belli.

---

## P09-T02_PRODUCTION_READINESS_AND_LAUNCH_GATE — Production readiness ve launch gate

- Phase: P09
- Priority: P0
- Dependencies: P07-T02_RELEASE_EVAL_GATE, P09-T01_OBSERVABILITY_AND_AUDIT_RUNBOOKS, P05-T03_LIVE_REVIEW_COCKPIT_PROGRESS

### Touchpoints
- `docs/worldclass/CHECKLISTS/RELEASE_GATE.md`
- `deploy/render.yaml`
- `Dockerfile`
- `web/Dockerfile`
- `.env.example`

### Implementation steps
1. Release checklist tüm P0 gate’lerini toplasın.
2. Rollback plan, migration plan, env validation, eval report, security checklist zorunlu olsun.
3. Launch smoke: create review, process, view report, export, delete.
4. Cost/performance budget belirle.

### Tests
- [ ] release smoke script
- [ ] migration dry run
- [ ] production env validation test

### Done when
- [ ] Launch kararı sezgiyle değil gate raporuyla veriliyor.

---
