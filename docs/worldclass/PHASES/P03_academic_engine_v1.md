# P03 — Akademik Engine v1

## Amaç

Generic review biter; belge türü, çalışma türü, rubrik ve reporting guideline’a göre akademik değerlendirme başlar.

## Faz kapısı

Makale/bildiri/tez/proje ve nitel/nicel/sistematik çalışma farklı rubriklerle değerlendiriliyor.

## İlgili spec dosyaları

- `docs/worldclass/SPECS/academic_engine_spec.md`
- `docs/worldclass/SPECS/qualitative_rigor_engine_spec.md`
- `docs/worldclass/SPECS/quantitative_validity_engine_spec.md`

## Görevler

### P03-T01_MANUSCRIPT_TYPE_CLASSIFIER — Belge türü sınıflandırıcı: makale/bildiri/tez/proje

**Öncelik:** P0  
**Bağımlılıklar:** P02-T05_DEGRADED_MODE_AND_PROVENANCE_PIPELINE

**Dokunulacak dosyalar:**
- `api/models/review.py`
- `api/services/review_orchestration.py`
- `engine/ingestion/builder.py`
- `tests/unit/test_review_orchestration.py`

**Uygulama adımları:**
1. DocumentType enum ekle: journal_article, conference_paper, thesis, grant_proposal, preprint, technical_report, unknown.
2. Classifier input: sections, title, abstract, headings, metadata, file hints.
3. Confidence ve rationale üret.
4. User override alanı ekle; model tahminini kullanıcı seçimiyle reconcile et.

**Test/doğrulama:**
- fixtures: thesis detected
- fixtures: grant detected
- low confidence => ask/unknown behavior

**Başarı tanımı:**
- Review job belge türünü confidence ile saklıyor ve rubrik seçimi buna bağlanıyor.

**Bir sonraki adıma geçiş:** Unknown durumunda generic değil, safe minimal review akışı seçiliyorsa.

**Durdurma koşulları:**
- Belge türü yanlış olsa bile kullanıcı override edemiyorsa.

---

### P03-T02_STUDY_DESIGN_CLASSIFIER — Çalışma türü sınıflandırıcı

**Öncelik:** P0  
**Bağımlılıklar:** P03-T01_MANUSCRIPT_TYPE_CLASSIFIER

**Dokunulacak dosyalar:**
- `api/models/review.py`
- `api/services/review_orchestration.py`
- `engine/checklist/*`
- `tests/unit/test_review_orchestration.py`

**Uygulama adımları:**
1. StudyDesign enum ekle: qualitative, quantitative, mixed_methods, systematic_review, meta_analysis, scoping_review, theoretical, design_science, computational, dataset, software, replication, protocol, unknown.
2. Section cues ve method terms ile classifier yaz.
3. Confidence/rationale ve multi-label destekle.
4. Study design rubrik ve guideline selector’a input olsun.

**Test/doğrulama:**
- qualitative fixture
- systematic review fixture
- mixed methods fixture
- unknown/low confidence fixture

**Başarı tanımı:**
- Aynı belge türü altında farklı çalışma türleri farklı review path’e gidiyor.

**Bir sonraki adıma geçiş:** Qualitative ve quantitative en az iki fixture ile ayrışıyorsa.

**Durdurma koşulları:**
- Her dosya article+generic review’e düşüyorsa.

---

### P03-T03_RUBRIC_REGISTRY_AND_DIMENSION_SCHEMA — RubricRegistry ve genişletilmiş akademik dimension schema

**Öncelik:** P0  
**Bağımlılıklar:** P03-T02_STUDY_DESIGN_CLASSIFIER

**Dokunulacak dosyalar:**
- `api/models/review.py`
- `engine/checklist/makale_tr.json`
- `engine/checklist/tez_tr.json`
- `api/services/review_orchestration.py`

**Uygulama adımları:**
1. AcademicDimension enum/model tasarla: contribution, theory, literature, methods, data, analysis, claims, citation, guideline, ethics, reproducibility, writing, venue_fit.
2. RubricRegistry belge+study_type kombinasyonuna göre dimension weights döndürsün.
3. Her dimension severity/confidence/action_items/evidence_anchors taşısın.
4. Mevcut DimensionKey geriye uyumluluk adapter’ı yaz.

**Test/doğrulama:**
- unit: article qualitative rubric selected
- unit: thesis rubric selected
- schema backwards compatibility test

**Başarı tanımı:**
- ReviewReport generic DimensionScore yerine zengin academic dimension taşıyabiliyor.

**Bir sonraki adıma geçiş:** Mevcut ReviewReportView yeni schema’yı en az degrade olmadan render ediyorsa.

**Durdurma koşulları:**
- Frontend/backend schema drift oluşuyorsa.

---

### P03-T04_QUALITATIVE_RIGOR_ENGINE — Nitel araştırma hakemlik motoru

**Öncelik:** P0  
**Bağımlılıklar:** P03-T03_RUBRIC_REGISTRY_AND_DIMENSION_SCHEMA

**Dokunulacak dosyalar:**
- `api/services/review_orchestration.py`
- `api/services/role_modules/reviewer_yontemci.py`
- `engine/checklist/*`
- `tests/unit/test_review_orchestration.py`

**Uygulama adımları:**
1. QualitativeRigorEngine oluştur.
2. Kontrol boyutları: paradigm, design fit, sampling, context, data collection, coding, theme development, quotes, reflexivity, trustworthiness, ethics, transferability, limitations.
3. Her boyut için evidence anchor ve action item üret.
4. Nitel çalışma tespitinde bu engine zorunlu çalışsın.

**Test/doğrulama:**
- unit: missing reflexivity detected
- unit: unsupported theme claim flagged
- eval fixture qualitative report

**Başarı tanımı:**
- Nitel çalışma raporu generic yöntem eleştirisi değil, nitel rigor boyutları içeriyor.

**Bir sonraki adıma geçiş:** En az 3 nitel kırılma exact anchor ile raporlanıyorsa.

**Durdurma koşulları:**
- Nitel engine LLM text’ini schema’sız serbest bırakıyorsa.

---

### P03-T05_QUANTITATIVE_VALIDITY_ENGINE — Nicel/istatistiksel geçerlilik motoru MVP

**Öncelik:** P0  
**Bağımlılıklar:** P03-T03_RUBRIC_REGISTRY_AND_DIMENSION_SCHEMA

**Dokunulacak dosyalar:**
- `engine/statcheck/multilingual.json`
- `api/services/review_orchestration.py`
- `api/models/review.py`
- `tests/unit/test_review_eval.py`

**Uygulama adımları:**
1. QuantitativeValidityEngine oluştur veya mevcut statcheck’i genişlet.
2. p-value, CI, effect size, sample size, power, missing data, model assumptions, multiple comparisons, causal language kontrollerini schema’ya bağla.
3. Tablo/metin çelişkisi için MVP numeric extractor ekle.
4. Bulguları severity/confidence ile dön.

**Test/doğrulama:**
- unit: causal wording in observational study flagged
- unit: missing effect size warning
- unit: p-value text pattern consistency

**Başarı tanımı:**
- Nicel review yöntem/istatistik alanında uygulanabilir, anchor’lı riskler üretiyor.

**Bir sonraki adıma geçiş:** High severity quantitative claims exact manuscript anchor taşıdığında.

**Durdurma koşulları:**
- Statistical finding confidence alanı yoksa.

---

### P03-T06_REPORTING_GUIDELINE_SELECTOR — Reporting guideline selector ve checklist engine

**Öncelik:** P1  
**Bağımlılıklar:** P03-T04_QUALITATIVE_RIGOR_ENGINE, P03-T05_QUANTITATIVE_VALIDITY_ENGINE

**Dokunulacak dosyalar:**
- `engine/checklist/*`
- `api/services/review_orchestration.py`
- `api/models/review.py`
- `web/src/components/review/ReviewReportView.tsx`

**Uygulama adımları:**
1. GuidelineProfile modeli oluştur: id, name, applies_to, checklist_items, severity, evidence_required.
2. StudyDesign’e göre PRISMA/STROBE/CONSORT/COREQ/SRQR-like/TRIPOD/STARD/SPIRIT/ARRIVE vb. registry yapısı kur.
3. MVP’de public checklist text kopyalamadan kendi compliance item schema’nı kullan.
4. Rapor içinde guideline compliance bölümü göster.

**Test/doğrulama:**
- unit: systematic_review => PRISMA-like profile
- unit: qualitative_interview => qualitative reporting profile
- frontend guideline checklist render

**Başarı tanımı:**
- Çalışma türüne göre guideline uyumu ayrı bölüm olarak raporlanıyor.

**Bir sonraki adıma geçiş:** Guideline not applicable/unknown durumları doğru gösterildiğinde.

**Durdurma koşulları:**
- Guideline isimleri iddia edilip checklist maddeleri boş kalıyorsa.

---
