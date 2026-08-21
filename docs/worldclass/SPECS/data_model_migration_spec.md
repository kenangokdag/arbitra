# Data Model & Migration Spec

## Amaç

Review domain büyürken migration güvenli, geri alınabilir, versioned ve frontend/backend contract ile uyumlu olmalıdır.

## Yeni tablolar / genişletmeler

### review_jobs

- id
- owner_user_id
- tenant_id
- document_id
- status
- current_stage
- manuscript_type
- study_design
- language_config jsonb
- privacy_config jsonb
- review_config jsonb
- idempotency_key
- created_at
- updated_at

### review_job_stages

- id
- job_id
- stage
- status
- progress
- started_at
- completed_at
- error_code
- degraded_reason
- metadata jsonb

### review_reports

- id
- job_id
- schema_version
- report jsonb
- provenance jsonb
- created_at

### review_audit_events

- id
- job_id
- actor_user_id
- tenant_id
- event_type
- metadata jsonb
- created_at

### review_exports

- id
- job_id
- format
- storage_path
- created_by
- created_at

## Migration kuralları

1. Additive migration önce.
2. Backfill gerekiyorsa ayrı script.
3. Destructive migration minimum iki release sonra.
4. Rollback planı migration dosyasında yorum olarak yazılır.
5. RLS/owner policy migration ile birlikte gelir.
6. Tests migration sonrası çalışır.

## JSONB contract

JSONB alanları versioned olmalıdır:

```json
{
  "version": "privacy_config.v1",
  "confidentiality_mode": "author_owned | reviewer_confidential",
  "external_ai_consent": false,
  "retention_days": 7
}
```

## Başarı kapısı

- Migration veri kaybı yaratmıyor.
- Authz/RLS/owner columns var.
- App eski raporları adapter ile okuyabiliyor.
- Migration rollback veya mitigation notu içeriyor.
