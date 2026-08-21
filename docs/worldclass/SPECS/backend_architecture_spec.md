# Backend Architecture Spec — Arbitra Scientific Review OS

## Amaç

Backend, 10 yıl sonra provider/model/framework değişse bile review domain'ini ayakta tutacak şekilde tasarlanmalıdır. FastAPI route'ları iş mantığı içermez; sadece request validation, authz, idempotency ve service çağrısı yapar.

## Hedef domain yapısı

```text
api/
  domains/
    identity/
    tenant/
    document/
    ingestion/
    evidence/
    review/
    rubric/
    workflow/
    audit/
    evaluation/
  providers/
    scholarly/
      base.py
      models.py
      errors.py
    openalex/
    crossref/
    semantic_scholar/
    llm/
    storage/
  shared/
    config/
    authz/
    errors/
    observability/
```

Mevcut repo bu yapıya tek seferde taşınmayacak. Önce review domain etrafında adapter'lar oluşturulacak; sonra eski `api/services/*` modülleri aşamalı migrate edilecek.

## Katman kuralları

### Route layer

Allowed:

- Pydantic request/response validation.
- Auth principal alma.
- Idempotency key alma.
- Service çağırma.
- HTTP exception mapping.

Forbidden:

- Provider URL/param inşası.
- LLM prompt çalıştırma.
- DB query business logic.
- User ownership kontrolünü atlama.
- Long-running işi request içinde yapmak.

### Service layer

Allowed:

- Domain orchestration.
- Authz policy çağırma.
- Workflow enqueue/cancel/retry.
- Report assembly.
- Degraded state üretme.

Forbidden:

- Raw HTTP provider call.
- Frontend-specific format üretme.
- Exception swallow.

### Provider layer

Allowed:

- Raw external API call.
- Retry/rate-limit/backoff.
- Provider-specific response parse.
- ProviderSnapshot üretme.

Forbidden:

- Akademik karar vermek.
- Kullanıcı authorization bilmek.
- Review report generate etmek.

### Model/schema layer

Allowed:

- Pydantic models.
- Versioned schemas.
- Enum definitions.
- Backward compatibility adapters.

Forbidden:

- Side effect.
- External call.

## Review domain aggregate

```text
ReviewJob
  - id
  - owner_user_id
  - tenant_id
  - status
  - stage_statuses[]
  - document_id
  - manuscript_type
  - study_design
  - privacy_config
  - language_config
  - review_config
  - evidence_pack_id
  - report_id
  - created_at
  - updated_at

ReviewReport
  - schema_version
  - executive_verdict
  - risk_radar
  - reviewer_council
  - evidence_map
  - action_plan
  - section_reviews
  - exports
  - limitations
  - provenance
```

## Error taxonomy

Her hata şu sınıflardan birine map edilmelidir:

- `AUTH_REQUIRED`
- `FORBIDDEN_OBJECT`
- `TENANT_BOUNDARY_VIOLATION`
- `INVALID_FILE`
- `PARSER_FAILED`
- `PROVIDER_AUTH_MISSING`
- `PROVIDER_RATE_LIMITED`
- `PROVIDER_DEGRADED`
- `LLM_CONSENT_REQUIRED`
- `LLM_OUTPUT_SCHEMA_INVALID`
- `WORKFLOW_STAGE_FAILED`
- `EXPORT_FAILED`

## Production environment contract

Production'da eksik env durumları:

| Env alanı | Eksikse davranış |
|---|---|
| Auth provider config | boot fail |
| Redis/queue config | boot fail veya review endpoint disabled |
| Storage config | boot fail |
| OpenAlex API key | literature/citation feature degraded; fake result yok |
| LLM provider key | LLM features disabled/degraded; confidential mode external AI kapalı |
| Sentry/observability | warning ama audit logs yine zorunlu |

## Backwards compatibility

Mevcut frontend eski ReviewReport bekliyorsa adapter eklenir:

```python
class ReviewReportV1Adapter:
    def to_v2(v1: ReviewReportV1) -> ReviewReportV2: ...
    def to_legacy(v2: ReviewReportV2) -> ReviewReportV1: ...
```

Ancak yeni development sadece v2 schema üzerinden yapılır.

## Test gereklilikleri

- Route authz integration tests.
- Service unit tests with fake repositories/providers.
- Provider contract tests with fixtures.
- Migration tests.
- Schema serialization tests.
- Negative tests for missing env and degraded states.

## Başarı ölçütü

Backend dünya klası sayılırsa:

- Long-running review işi durable workflow’a teslim edilir.
- Provider değişimi business logic kırmaz.
- User object boundary testlidir.
- Her major output provenance taşır.
- Her degraded state kullanıcıya görünür.
- Production fake/mock path çalıştıramaz.
