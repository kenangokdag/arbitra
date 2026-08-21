# P05 — Premium Frontend, Landing ve Wizard

## Amaç

Toolbox hissi biter; landing, onboarding, upload wizard ve canlı review cockpit premium ve frictionless olur.

## Faz kapısı

Yeni kullanıcı tek tuşla review başlatır; uzman kullanıcı rubric/privacy/depth ayarlarını kontrol eder.

## İlgili spec dosyaları

- `docs/worldclass/SPECS/frontend_design_system_spec.md`
- `docs/worldclass/SPECS/review_wizard_and_cockpit_spec.md`

## Görevler

### P05-T01_PREMIUM_LANDING_REPOSITIONING — Landing page’i Arbitra Scientific Review OS olarak yeniden konumlandır

**Öncelik:** P0  
**Bağımlılıklar:** P01-T03_CONFIDENTIALITY_AND_EXTERNAL_AI_CONSENT, P00-T01_BRAND_AND_PRODUCT_CONTRACT

**Dokunulacak dosyalar:**
- `web/src/app/(marketing)/landing/page.tsx`
- `web/src/components/marketing/WaitlistModal.tsx`
- `web/src/lib/brand.ts`
- `web/src/styles/globals.css`

**Uygulama adımları:**
1. Hero copy: hakeme gitmeden önce kırılma noktalarını görün.
2. Trust blocks: confidentiality-first, evidence-backed, methodology-aware, revision cockpit.
3. Comparison block: chatbot vs Arbitra.
4. Output preview: risk radar, reviewer objections, evidence map, action plan.
5. CTA: örnek rapor ve çalışmamı incelet.

**Test/doğrulama:**
- component render test
- copy snapshot smoke
- accessibility landmarks manual check

**Başarı tanımı:**
- Landing AI assistant template değil, hakemlik OS vaadi veriyor.

**Bir sonraki adıma geçiş:** İlk ekran ürünün farkını 10 saniyede anlatıyorsa.

**Durdurma koşulları:**
- Gerçek olmayan kabiliyetler landing’de iddia ediliyorsa.

---

### P05-T02_REVIEW_INTAKE_WIZARD — Tek upload formunu guided review wizard’a çevir

**Öncelik:** P0  
**Bağımlılıklar:** P02-T01_REVIEW_JOB_STAGE_SCHEMA, P01-T03_CONFIDENTIALITY_AND_EXTERNAL_AI_CONSENT

**Dokunulacak dosyalar:**
- `web/src/app/(app)/review/page.tsx`
- `web/src/lib/review-api.ts`
- `web/src/hooks/useReview.ts`
- `api/routes/review.py`

**Uygulama adımları:**
1. Wizard steps: file, document type, target, privacy, review depth.
2. Beginner default: Arbitra benim için seçsin.
3. Expert drawer: rubric, guideline, strictness, provider depth, locale, retention.
4. Backend create request contractını wizard state ile eşle.
5. Validation errorları kullanıcı dostu göster.

**Test/doğrulama:**
- frontend wizard state test
- API contract test
- confidential mode wizard test

**Başarı tanımı:**
- Yeni başlayan tek akışla review başlatır, uzman detay kontrolü alır.

**Bir sonraki adıma geçiş:** Wizard form verisi backend schema ile typed şekilde eşleştiğinde.

**Durdurma koşulları:**
- Privacy step bypass edilebiliyorsa.

---

### P05-T03_LIVE_REVIEW_COCKPIT_PROGRESS — Spinner yerine canlı review cockpit progress

**Öncelik:** P0  
**Bağımlılıklar:** P02-T01_REVIEW_JOB_STAGE_SCHEMA

**Dokunulacak dosyalar:**
- `web/src/app/(app)/review/[jobId]/page.tsx`
- `web/src/hooks/useReview.ts`
- `web/src/components/review/ReviewReportView.tsx`
- `api/routes/review.py`

**Uygulama adımları:**
1. Stage timeline component oluştur.
2. Her stage için done/running/degraded/failed states.
3. İlk ara bulguları veya detected manuscript type göster.
4. Retry/cancel UI ekle.
5. Failure state çözüm önerisi ve support/debug id taşısın.

**Test/doğrulama:**
- component test stage states
- polling hook test
- error/degraded render test

**Başarı tanımı:**
- Kullanıcı beklerken sistemin ne yaptığını ve ne bulduğunu görüyor.

**Bir sonraki adıma geçiş:** Numeric-only progress bar artık ana deneyim değilse.

**Durdurma koşulları:**
- Stage failed durumunda kullanıcı boş ekranda kalıyorsa.

---

### P05-T04_DESIGN_SYSTEM_PREMIUM_TOKENS — Premium visual system tokens ve component kuralları

**Öncelik:** P1  
**Bağımlılıklar:** P05-T01_PREMIUM_LANDING_REPOSITIONING

**Dokunulacak dosyalar:**
- `web/src/styles/globals.css`
- `web/src/components/ui/button.tsx`
- `web/src/components/Card.tsx`
- `docs/frontend/COMPONENT_RULES.md`

**Uygulama adımları:**
1. Editorial typography, spacing, elevation, surface, risk severity, evidence confidence tokenları tanımla.
2. Arbitra-specific components: RiskBadge, EvidenceBadge, ConfidenceMeter, ManuscriptAnchorLink.
3. Motion aşırı değil, anlamlı progress için kullanılsın.
4. Dark/light veya premium neutral palette tutarlı olsun.

**Test/doğrulama:**
- visual smoke test
- component snapshot
- manual contrast check

**Başarı tanımı:**
- UI parçaları random Tailwind değil tutarlı product language taşıyor.

**Bir sonraki adıma geçiş:** Review/landing/wizard aynı görsel sistemde birleştiğinde.

**Durdurma koşulları:**
- Inline magic classes yeni component standardını bozuyorsa.

---
