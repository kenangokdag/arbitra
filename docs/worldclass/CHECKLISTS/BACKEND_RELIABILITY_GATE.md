# Backend Reliability Gate

## Workflow

- [ ] Long-running work route içinde değil.
- [ ] Job state DB’de checkpoint ediliyor.
- [ ] Stage failure/retry/degraded durumları modelde var.
- [ ] Idempotency duplicate job üretmiyor.

## Provider

- [ ] Provider errors domain error’a map ediliyor.
- [ ] Timeout/rate-limit retry policy var.
- [ ] Provider failure fake result üretmiyor.
- [ ] ProviderSnapshot provenance’a giriyor.

## Data

- [ ] Migration additive veya rollback planlı.
- [ ] Backward compatibility adapter gerekiyorsa var.
- [ ] Schema versioning var.

## Tests

- [ ] Unit tests.
- [ ] Integration or smoke test.
- [ ] Negative/failure test.

## Son karar

- [ ] Gate passed.
- [ ] Gate failed.
