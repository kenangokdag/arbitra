# Observability & Runbook Spec

## Amaç

Arbitra production’da hata verdiğinde sistemin nerede bozulduğu stage, provider, user impact ve recovery açısından hızlı anlaşılmalıdır.

## Metrics

### Review metrics

- review_jobs_created_total
- review_jobs_completed_total
- review_jobs_failed_total
- review_stage_duration_ms
- review_stage_degraded_total
- review_retry_count
- review_cancel_count

### Provider metrics

- provider_request_total
- provider_error_total
- provider_rate_limited_total
- provider_latency_ms
- provider_cache_hit_ratio

### LLM metrics

- llm_calls_total
- llm_schema_invalid_total
- llm_tokens_total
- llm_cost_estimate
- llm_consent_block_total

### Academic quality metrics

- report_schema_valid_total
- high_severity_without_action_total
- citation_unresolved_ratio
- degraded_report_ratio

## Logs

Her log correlation id taşımalı:

- request_id
- job_id
- user_id hash or internal id
- tenant_id
- stage
- provider
- error_code

## Runbooks

1. Provider down.
2. Queue stuck.
3. Review stage failure spike.
4. Auth incident.
5. Data deletion request failure.
6. Eval regression.
7. Export failures.
8. LLM schema invalid spike.
9. Cost spike.
10. Confidentiality incident.

## User-facing error contract

User sees:

- what failed,
- whether data is safe,
- what can be retried,
- support/debug id,
- no raw stack trace.

## Başarı kapısı

- Her job traceable.
- Her external call auditable.
- Her failure user-friendly.
- Runbook exists before launch.
