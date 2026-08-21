# Release Gate — Arbitra World-Class Release Checklist

Her release candidate için zorunlu.

## 1. Scope

- [ ] Release içindeki task ID’leri listelendi.
- [ ] P0/P1/P2 ayrımı belli.
- [ ] Açık riskler release notes’a yazıldı.

## 2. Tests

- [ ] Backend unit tests.
- [ ] Backend integration tests.
- [ ] Frontend tests.
- [ ] Typecheck/lint.
- [ ] Eval smoke/release mode.
- [ ] Manual review flow smoke: upload -> job -> report -> export/delete.

## 3. Security/privacy

- [ ] SECURITY_PRIVACY_GATE yeşil.
- [ ] Authz negative tests geçti.
- [ ] Confidential mode smoke geçti.
- [ ] Audit events kontrol edildi.

## 4. Academic quality

- [ ] ACADEMIC_QUALITY_GATE yeşil.
- [ ] High severity findings action item taşıyor.
- [ ] No fake citations.
- [ ] Degraded states visible.

## 5. UX

- [ ] FRONTEND_PREMIUM_GATE yeşil.
- [ ] Loading/error/degraded states görüldü.
- [ ] Mobile/responsive smoke.

## 6. Ops

- [ ] Env validation passed.
- [ ] Migration dry run.
- [ ] Rollback plan.
- [ ] Runbook links.
- [ ] Observability smoke.

## 7. Final decision

- [ ] Ship.
- [ ] Do not ship; blocker:
