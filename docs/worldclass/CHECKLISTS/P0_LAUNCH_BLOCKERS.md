# P0 Launch Blockers Checklist

Bu maddeler yeşil olmadan beta/production launch yapılmaz.

## Security

- [ ] Production build mock auth üretemiyor.
- [ ] `dev-mock-signature`, fake token, mock user production bundle’da yok.
- [ ] Backend production’da dev token kabul etmiyor.
- [ ] User A, User B review job/report/export objelerine erişemiyor.
- [ ] Admin endpointleri RBAC ile korunuyor.
- [ ] Redis/queue/quota eksikse expensive endpointler fail-closed.

## Privacy

- [ ] Review create flow document ownership soruyor.
- [ ] Reviewer/editor confidential mode external AI default kapalı.
- [ ] External AI consent audit log’a yazılıyor.
- [ ] Retention policy seçilebilir veya default güvenli.
- [ ] Delete flow tasarlanmış ve testli.
- [ ] Rapor AI usage disclosure taşıyor.

## File safety

- [ ] Magic-byte/MIME/extension validation var.
- [ ] Zip bomb/path traversal testleri var.
- [ ] Parser timeout/size/page limits var.
- [ ] Upload failure user-friendly.

## Backend reliability

- [ ] Review job durable queue/workflow’a teslim ediliyor.
- [ ] Stage-based progress var.
- [ ] Retry/idempotency var.
- [ ] Provider failures degraded olarak rapora yansıyor.

## Academic quality

- [ ] Belge türü classifier var.
- [ ] Çalışma türü classifier var.
- [ ] Rubric registry var.
- [ ] Nitel engine MVP var.
- [ ] Nicel engine MVP var.
- [ ] Claim/evidence/citation support levels var.
- [ ] High severity bulgular anchor + action item taşıyor.

## Frontend

- [ ] Landing Arbitra’nın farkını anlatıyor.
- [ ] Upload wizard privacy step içeriyor.
- [ ] Live progress spinner’dan ibaret değil.
- [ ] ReportView risk/evidence/action/provenance gösteriyor.

## Eval

- [ ] Report schema validation testli.
- [ ] Eval smoke çalışıyor.
- [ ] Hallucination/fake citation gate var.

## Karar

- [ ] Tüm P0 maddeler yeşil.
- [ ] Açık P1/P2 maddeler release notes içinde belgeli.
- [ ] Rollback planı var.
