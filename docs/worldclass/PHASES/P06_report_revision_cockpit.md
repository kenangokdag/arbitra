# P06 — Report & Revision Cockpit

## Amaç

Rapor pasif metin olmaktan çıkar; risk radar, reviewer council, evidence map, action plan ve export akışına dönüşür.

## Faz kapısı

High-severity bulgular P0/P1/P2 tasklara dönüşüyor; export ve response-to-reviewers akışı çalışıyor.

## İlgili spec dosyaları

- `docs/worldclass/SPECS/review_report_schema_spec.md`
- `docs/worldclass/SPECS/review_wizard_and_cockpit_spec.md`

## Görevler

### P06-T01_REVIEW_REPORT_SCHEMA_V2 — ReviewReport v2: verdict, risk, council, evidence, action plan

**Öncelik:** P0  
**Bağımlılıklar:** P03-T03_RUBRIC_REGISTRY_AND_DIMENSION_SCHEMA, P04-T03_CLAIM_EVIDENCE_ALIGNMENT

**Dokunulacak dosyalar:**
- `api/models/review.py`
- `api/services/review_orchestration.py`
- `web/src/lib/review-api.ts`
- `web/src/components/review/ReviewReportView.tsx`

**Uygulama adımları:**
1. Report sections: executive_verdict, risk_radar, reviewer_council, evidence_map, action_plan, section_reviews, exports.
2. Backward compatibility adapter ekle.
3. Every high severity item requires anchor/action/confidence.
4. Report schema versioning ekle.

**Test/doğrulama:**
- schema validation
- backward compatibility fixture
- frontend render report v2

**Başarı tanımı:**
- Rapor yapısal olarak cockpit’e hizmet ediyor.

**Bir sonraki adıma geçiş:** ReportView string blob yerine typed sections render ediyorsa.

**Durdurma koşulları:**
- High severity finding action item olmadan geçiyorsa.

---

### P06-T02_REVIEWER_COUNCIL_ENGINE — Persona modüllerini Reviewer Council Engine’e dönüştür

**Öncelik:** P0  
**Bağımlılıklar:** P06-T01_REVIEW_REPORT_SCHEMA_V2

**Dokunulacak dosyalar:**
- `api/services/review_orchestration.py`
- `api/services/role_modules/*`
- `engine/personas/review/*`

**Uygulama adımları:**
1. Council roles: methodologist, field_expert, skeptical_reviewer, constructive_reviewer, citation_auditor, ethics_reviewer, statistics_reviewer, editor_synthesizer.
2. Her role output schema’sı aynı: findings, severity, evidence, actions, confidence.
3. Editor synthesizer duplicate findings merge etsin.
4. Role weights rubric/study type’a göre değişsin.

**Test/doğrulama:**
- unit: council role schema validation
- unit: duplicate merge
- fixture: qualitative role weighting

**Başarı tanımı:**
- Persona outputları serbest metin değil birleşebilir structured findings üretiyor.

**Bir sonraki adıma geçiş:** Editor synthesis conflicting role outputs’u çözüyor.

**Durdurma koşulları:**
- Bir role failure tüm raporu sessiz boşa düşürüyorsa.

---

### P06-T03_ACTION_PLAN_AND_REVISION_TASKS — P0/P1/P2 revision action plan ve task modeli

**Öncelik:** P0  
**Bağımlılıklar:** P06-T01_REVIEW_REPORT_SCHEMA_V2

**Dokunulacak dosyalar:**
- `api/models/review.py`
- `web/src/components/review/ReviewReportView.tsx`
- `web/src/app/(app)/review/[jobId]/page.tsx`

**Uygulama adımları:**
1. ActionItem model: priority, effort, expected_gain, target_section, instruction, acceptance_check.
2. Risk findings action item’a bağlansın.
3. Frontend’de actionable checklist ve filters.
4. Done/ignored/user note state için local/server model tasarla.

**Test/doğrulama:**
- schema test action item required fields
- frontend checklist interaction test

**Başarı tanımı:**
- Kullanıcı rapordan doğrudan revizyon planı çıkarabiliyor.

**Bir sonraki adıma geçiş:** High severity bulguların %100’ü action item taşıyorsa.

**Durdurma koşulları:**
- Öneriler generic ve uygulanamaz kalıyorsa.

---

### P06-T04_EXPORTS_AND_RESPONSE_TO_REVIEWERS — PDF/DOCX/Markdown/LaTeX export ve response-to-reviewers assistant

**Öncelik:** P1  
**Bağımlılıklar:** P06-T03_ACTION_PLAN_AND_REVISION_TASKS

**Dokunulacak dosyalar:**
- `api/routes/review.py`
- `api/services/review_service.py`
- `web/src/components/review/ReviewReportView.tsx`
- `web/src/lib/review-api.ts`

**Uygulama adımları:**
1. Export endpoint contract: format, sections, include_evidence, include_disclosure.
2. Markdown ilk MVP, PDF/DOCX sonra adapter.
3. Response-to-reviewers draft: issue, proposed fix, polite response, evidence.
4. Export audit event ekle.

**Test/doğrulama:**
- unit: markdown export snapshot
- integration: export authz
- frontend export button state

**Başarı tanımı:**
- Rapor dış dünyada kullanılabilir çıktı formatlarına dönüşüyor.

**Bir sonraki adıma geçiş:** En az Markdown export tam ve testli olduğunda.

**Durdurma koşulları:**
- Export başka kullanıcının raporuna erişebiliyorsa.

---
