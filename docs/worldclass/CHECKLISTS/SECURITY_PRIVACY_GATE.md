# Security & Privacy Gate

Her security/privacy etkili PR için doldurulur.

## Auth/authz

- [ ] Bu PR production mock/auth bypass üretmiyor.
- [ ] Kullanıcıdan gelen ID ile objeye erişim varsa owner/tenant check var.
- [ ] Negative authorization test yazıldı.
- [ ] Admin yetkisi RBAC ile kontrol edildi.

## Data privacy

- [ ] Confidential manuscript flow bozulmadı.
- [ ] External provider/LLM çağrısı consent gate’ten geçiyor.
- [ ] Data retention/delete davranışı değiştiyse migration/docs güncellendi.
- [ ] Audit event eklendi veya mevcut event korunuyor.

## Secrets

- [ ] Secret frontend bundle’a sızmıyor.
- [ ] Env validation fail-closed.
- [ ] Logs secret veya manuscript içeriği basmıyor.

## File safety

- [ ] Upload/parser etkisi varsa malicious fixture test edildi.
- [ ] Resource limit var.
- [ ] Error message raw stack trace göstermiyor.

## Son karar

- [ ] Gate passed.
- [ ] Gate failed; launch blocker açıldı.
