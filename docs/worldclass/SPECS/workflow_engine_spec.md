# Workflow Engine Spec — Durable Review Jobs

## Problem

Bilimsel review uzun süren, çok aşamalı ve dış provider/LLM çağrıları içeren bir iş akışıdır. Web request veya FastAPI `BackgroundTasks` içinde yürütülemez. Process restart, deploy, timeout veya provider kesintisi job kaybına yol açmamalıdır.

## Hedef

```text
POST /review
  -> ReviewJob(status=queued)
  -> WorkflowClient.enqueue(job_id)
  -> worker stage loop
  -> checkpoints
  -> ReviewReport completed
```

## Stage model

Zorunlu stage'ler:

1. `file_security_scan`
2. `parse_document`
3. `classify_manuscript`
4. `extract_metadata`
5. `extract_references`
6. `resolve_references`
7. `retrieve_evidence`
8. `select_guidelines`
9. `run_academic_engines`
10. `run_reviewer_council`
11. `editor_synthesis`
12. `build_report`
13. `prepare_exports`

Her stage:

```json
{
  "stage": "resolve_references",
  "status": "running | completed | degraded | failed | skipped",
  "progress": 0.62,
  "started_at": "...",
  "completed_at": "...",
  "error_code": null,
  "degraded_reason": null,
  "provider_snapshots": [],
  "summary": "42/67 references resolved"
}
```

## WorkflowClient interface

```python
class WorkflowClient(Protocol):
    async def enqueue_review(self, job_id: str, idempotency_key: str | None) -> WorkflowHandle: ...
    async def cancel_review(self, job_id: str, requested_by: Principal) -> None: ...
    async def retry_stage(self, job_id: str, stage: ReviewStage) -> None: ...
    async def get_status(self, job_id: str) -> WorkflowStatus: ...
```

## İlk implementation stratejisi

### MVP

- DB-backed job state.
- Worker process command: `python -m api.workers.review_worker`.
- Queue adapter olarak Redis/RQ/Celery/Arq seçilebilir.
- Interface provider-agnostic kalsın.

### Future

- Temporal veya durable workflow engine’e geçiş adapter ile yapılır.
- Stage implementations değişmez.

## Idempotency

Review create endpoint idempotency key desteklemelidir.

- Aynı user + document hash + config + idempotency key => aynı job.
- Aynı dosya ama farklı config => yeni job.
- Duplicate enqueue job duplication yapmaz.

## Retry policy

| Stage | Retry | Not |
|---|---:|---|
| file_security_scan | 0 | security fail retry edilmez |
| parse_document | 1 | parser transient olabilir |
| resolve_references | 3 | provider transient |
| retrieve_evidence | 3 | provider/rate-limit |
| LLM council | 2 | schema invalid retry possible |
| export | 2 | transient storage/render |

## Degraded behavior

Provider unavailable ise stage `degraded` olabilir; ancak rapor bu sınırlamayı taşımalıdır.

Örnek:

```text
Citation integrity ran in degraded mode because OpenAlex API key is missing. Claims were checked only against manuscript-internal reference metadata; confidence reduced.
```

## Cancellation

Kullanıcı review’i iptal edebilmelidir. Cancellation:

- Current stage safe checkpoint’te durur.
- Partial artifacts retention policy’ye göre silinir veya saklanır.
- Audit event yazılır.

## Observability

Her stage şu metricleri üretir:

- duration_ms
- input_size
- output_count
- provider_calls
- provider_errors
- degraded_count
- llm_tokens/cost if applicable

## Başarı kapısı

- API route long-running işi kendi içinde yürütmüyor.
- Job stage state frontend tarafından izlenebiliyor.
- Worker crash sonrası job retry/resume edilebiliyor.
- Stage failed/degraded kullanıcıya görünür.
- Idempotency duplicate job üretmiyor.
