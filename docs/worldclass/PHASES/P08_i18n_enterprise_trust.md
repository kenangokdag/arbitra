# P08 — 100 Dil, Enterprise ve Kurumsal Güven

## Amaç

Source language/output language/UI locale ayrılır; tenant, institution, private deployment ve compliance temeli atılır.

## Faz kapısı

TR/EN dışı dil modeli teknik olarak desteklenir; confidential/enterprise deployment kararları dokümante edilir.

## İlgili spec dosyaları

- `docs/worldclass/SPECS/i18n_100_language_spec.md`
- `docs/worldclass/SPECS/security_privacy_threat_model.md`

## Görevler

### P08-T01_LANGUAGE_CONFIG_MODEL — Source language, output language ve UI locale ayrımı

**Öncelik:** P0  
**Bağımlılıklar:** P06-T01_REVIEW_REPORT_SCHEMA_V2

**Dokunulacak dosyalar:**
- `api/models/review.py`
- `web/src/lib/review-api.ts`
- `web/src/lib/i18n/*`
- `api/services/translator.py`

**Uygulama adımları:**
1. LanguageConfig model: source_language, output_language, ui_locale, citation_language_policy, rtl.
2. Review create request ve report metadata’ya ekle.
3. TR/EN literal type kısıtlarını kaldırıp BCP-47 string validation yap.
4. Bilingual quote policy: original quote + translated explanation.

**Test/doğrulama:**
- unit: language config validation
- frontend type test
- RTL smoke where possible

**Başarı tanımı:**
- 100 dil vizyonu teknik olarak iki literal ile sınırlı değil.

**Bir sonraki adıma geçiş:** TR manuscript EN report ve EN manuscript TR UI ayrışabiliyorsa.

**Durdurma koşulları:**
- Citation quotes çevrilip orijinal kayboluyorsa.

---

### P08-T02_TENANT_AND_ENTERPRISE_BOUNDARIES — Tenant/institution boundary ve enterprise deployment temeli

**Öncelik:** P1  
**Bağımlılıklar:** P01-T02_OBJECT_LEVEL_AUTHORIZATION_MATRIX

**Dokunulacak dosyalar:**
- `api/models/*`
- `api/middleware/auth.py`
- `api/db/supabase_client.py`
- `db/migrations/*`

**Uygulama adımları:**
1. Tenant model ve membership roles tasarla.
2. Institution policy: retention, allowed providers, local model required, export controls.
3. Tenant-aware authz tests.
4. Future on-prem/private cloud config surface.

**Test/doğrulama:**
- tenant A cannot access tenant B
- institution policy blocks external provider

**Başarı tanımı:**
- Kurumsal kullanıcı için veri sınırı ve provider policy uygulanabiliyor.

**Bir sonraki adıma geçiş:** Single-user flow kırılmadan tenant-aware path çalıştığında.

**Durdurma koşulları:**
- Tenant_id sadece UI’da var backend enforcement yoksa.

---
