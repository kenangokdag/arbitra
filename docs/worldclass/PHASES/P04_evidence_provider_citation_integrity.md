# P04 — Evidence, Provider ve Citation Integrity Katmanı

## Amaç

Atıf çözümleme, claim-evidence alignment, literature coverage, source provenance ve provider abstraction güçlenir.

## Faz kapısı

Her major critique manuscript anchor + source/evidence state + confidence + limitation taşıyor.

## İlgili spec dosyaları

- `docs/worldclass/SPECS/evidence_provider_spec.md`
- `docs/worldclass/SPECS/review_report_schema_spec.md`

## Görevler

### P04-T01_CLAIM_EXTRACTION_MODEL — Claim extraction ve manuscript anchor modeli

**Öncelik:** P0  
**Bağımlılıklar:** P03-T03_RUBRIC_REGISTRY_AND_DIMENSION_SCHEMA

**Dokunulacak dosyalar:**
- `api/models/review.py`
- `engine/ingestion/common.py`
- `api/services/anchor_finder.py`
- `tests/unit/test_anchor_finder.py`

**Uygulama adımları:**
1. Claim model: text, section, anchor_id, claim_type, strength, evidence_needed.
2. Section/paragraph anchors ingestion’dan stable id alsın.
3. Claims introduction/results/discussion bölümlerinden çıkarılsın.
4. LLM output JSON schema validation ile sınırlandırılsın.

**Test/doğrulama:**
- unit: stable anchor ids
- unit: claim schema validation
- fixture: claims extracted from sample manuscript

**Başarı tanımı:**
- Rapor eleştirileri manuscript anchor id’ye bağlanabiliyor.

**Bir sonraki adıma geçiş:** Anchor değişmeden frontend highlight yapabiliyorsa.

**Durdurma koşulları:**
- Claim text serbest LLM output olarak doğrulanmadan kullanılıyorsa.

---

### P04-T02_REFERENCE_RESOLUTION_PIPELINE — Reference extraction ve DOI/provider resolution pipeline

**Öncelik:** P0  
**Bağımlılıklar:** P02-T04_OPENALEX_API_KEY_MIGRATION

**Dokunulacak dosyalar:**
- `engine/ingestion/*`
- `api/services/review_citation_service.py`
- `api/providers/*`
- `tests/unit/test_review_citation.py`

**Uygulama adımları:**
1. Reference model standardize et: raw, title, authors, year, doi, source, resolution_status.
2. Crossref/OpenAlex/SemanticScholar adapter slotları oluştur.
3. Resolution confidence ve duplicate merge logic ekle.
4. Unresolved references reportta açık gösterilsin.

**Test/doğrulama:**
- unit: DOI exact resolution
- unit: fuzzy title resolution confidence
- unit: unresolved does not fabricate

**Başarı tanımı:**
- Atıflar provider ve confidence ile çözümleniyor.

**Bir sonraki adıma geçiş:** Unresolved atıf uydurulmadan raporlanıyorsa.

**Durdurma koşulları:**
- Kaynak bulunamadığında fake DOI üretiliyorsa.

---

### P04-T03_CLAIM_EVIDENCE_ALIGNMENT — Claim-evidence alignment ve citation support levels

**Öncelik:** P0  
**Bağımlılıklar:** P04-T01_CLAIM_EXTRACTION_MODEL, P04-T02_REFERENCE_RESOLUTION_PIPELINE

**Dokunulacak dosyalar:**
- `api/models/review.py`
- `api/services/review_citation_service.py`
- `api/services/review_orchestration.py`
- `web/src/components/review/ReviewReportView.tsx`

**Uygulama adımları:**
1. SupportLevel enum: full_text_verified, abstract_only, metadata_only, unresolved, contradictory, not_applicable.
2. ClaimCitationAlignment model ekle.
3. Citation context ile claim strength uyumunu kontrol et.
4. Rapor dilinde abstract-only limitation açık yazılsın.

**Test/doğrulama:**
- unit: abstract_only does not become verified
- unit: unsupported causal claim flagged
- frontend support level badge render

**Başarı tanımı:**
- Citation integrity bulguları kaynak doğrulama seviyesini gösteriyor.

**Bir sonraki adıma geçiş:** Her citation critique support_level taşıdığında.

**Durdurma koşulları:**
- Abstract-only bulgu full verification gibi sunuluyorsa.

---

### P04-T04_LITERATURE_COVERAGE_AND_GAP_MAP — Literature coverage, seminal/recent/missing works ve gap map

**Öncelik:** P1  
**Bağımlılıklar:** P04-T02_REFERENCE_RESOLUTION_PIPELINE

**Dokunulacak dosyalar:**
- `api/services/gap_profile_workshop_service.py`
- `api/services/originality_service.py`
- `api/services/review_citation_service.py`
- `web/src/components/project/GapHeatmapCard.tsx`

**Uygulama adımları:**
1. Manuscript topic/claims ile reference set arasında coverage analysis yap.
2. Recent/seminal/methodological/theoretical missing buckets oluştur.
3. Coverage confidence provider availability ile bağlansın.
4. Mevcut gap/originality modüllerini review output’a entegre et.

**Test/doğrulama:**
- unit: missing recent works bucket
- unit: provider degraded lowers confidence
- frontend coverage section render

**Başarı tanımı:**
- Literature critique “daha kaynak ekle” değil, hangi boşluk türü olduğunu söylüyor.

**Bir sonraki adıma geçiş:** Coverage map action items ürettiğinde.

**Durdurma koşulları:**
- Provider sonuçları olmadan yüksek confidence coverage iddia ediliyorsa.

---
