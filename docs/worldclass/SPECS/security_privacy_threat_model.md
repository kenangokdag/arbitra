# Security & Privacy Threat Model

## En hassas varlıklar

- Unpublished manuscript.
- Reviewer/editor confidential document.
- Thesis/grant proposal.
- User identity and institution.
- Citation/literature queries revealing research idea.
- Generated report and critique.
- External provider logs.

## Ana tehditler

1. Başka kullanıcının review job’una erişim.
2. Production mock auth ile yetkisiz giriş.
3. Service-role ile RLS bypass sonrası eksik owner check.
4. Confidential manuscript’ın external LLM’e izinsiz gönderilmesi.
5. Upload üzerinden malware/parser exploit.
6. Zip bomb/path traversal.
7. Provider fallback ile fake academic output.
8. Retention/delete çalışmaması.
9. Admin rolünün zayıf tanımlanması.
10. Audit logs eksikliği.

## Güvenlik kontrolleri

### Auth

- Production mock auth yasak.
- Secure cookie veya güvenilir JWT validation.
- Dev auth yalnız development.

### Authorization

- Object-level check her endpointte.
- Tenant boundary.
- RBAC for admin.
- Tests for negative access.

### File security

- Magic-byte/MIME/extension validation.
- Size/page/token limits.
- Zip safety.
- Malware scan hook.
- Parser sandbox/timeout.

### Privacy

- Confidentiality mode.
- External AI consent gate.
- Retention policy.
- Delete/export controls.
- AI usage disclosure.

### Audit

Audit event zorunlu:

- review_created
- file_uploaded
- file_parsed
- external_provider_called
- external_ai_called
- report_generated
- report_viewed
- export_created
- document_deleted
- admin_access

## Launch blocker checklist

- [ ] Production mock auth impossible.
- [ ] User A cannot access User B review job.
- [ ] Confidential mode external AI default off.
- [ ] Upload security tests pass.
- [ ] Retention/delete flow exists.
- [ ] Audit events exist for external calls.
- [ ] Provider failures are visible.
- [ ] Secrets not leaked to frontend.

## Başarı kapısı

Security is not “no known bugs”. Security is:

- fail closed,
- explicit consent,
- tested boundaries,
- auditable access,
- visible degradation,
- minimal data retention.
