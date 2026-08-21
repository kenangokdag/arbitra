# Arbitra World-Class Master Roadmap

## Yol haritasının hedefi

Bu yol haritası Arbitra'yı “AI destekli review tool” seviyesinden çıkarıp **akademik hakemlik, metodoloji, atıf bütünlüğü, gizlilik, revizyon yönetimi ve premium kullanıcı deneyimi** açısından dünya klası bir platforma dönüştürür.

Yol haritası sadece ne yapılacağını değil; hangi dosyaya dokunulacağını, hangi testle geçileceğini, hangi durumda ilerlenebileceğini ve başarının nasıl anlaşılacağını tanımlar.

## Faz sırası

| Faz | İsim | Amaç | İlerleme kapısı |
|---|---|---|---|
| P00 | Ürün kimliği ve governance | Arbitra'nın ürün sözleşmesini, marka kararını ve otonom çalışma düzenini sabitlemek | North Star ve agent state net |
| P01 | Production güvenlik ve gizlilik | Mock/fallback/authz/confidentiality risklerini launch blocker olarak kapatmak | Security/privacy gate yeşil |
| P02 | Durable backend review OS | BackgroundTasks yerine durable workflow, stage model, provider abstraction | Job restart/retry güvenli |
| P03 | Akademik engine v1 | Belge türü + çalışma türü + rubrik + guideline motoru | Generic review bitmiş |
| P04 | Evidence/citation integrity | DOI/provider/literature/citation/claim-evidence katmanı | Provenance zorunlu |
| P05 | Premium frontend UX | Landing, wizard, review cockpit ve design system dönüşümü | UX gate yeşil |
| P06 | Report & revision cockpit | Raporu okunacak metinden yönetilecek revizyon sistemine çevirmek | Actionable output gate |
| P07 | Evaluation lab | Akademik doğruluğu, hallucination'ı ve actionability'yi ölçmek | Eval benchmark release gate |
| P08 | 100 dil + enterprise | i18n, tenant, institution, private deployment temeli | Locale/privacy/provider bağımsız |
| P09 | Launch & 10-year ops | Observability, runbook, release, incident, cost/performance yönetimi | Production readiness |

## Kritik bağımlılık ilkesi

P01 tamamlanmadan P05 premium frontend'e geçilmez. Çünkü güvenlik açıkken premium UI sadece makyaj olur.

P03 tamamlanmadan P06 rapor finalleştirilmez. Çünkü akademik engine generic kalırsa rapor güzel görünse de bilimsel olarak zayıf olur.

P07 olmadan agresif launch yapılmaz. Çünkü ölçülmeyen AI kalite iddiası pazarlama olur.

## Repo içi ana dönüşüm noktaları

### Backend

- `api/models/review.py`: Review contract genişletilecek.
- `api/routes/review.py`: Create/status/result/export API'leri güvenli hâle getirilecek.
- `api/services/review_service.py`: Job lifecycle ve workflow client boundary.
- `api/services/review_orchestration.py`: Reviewer council engine'e evrilecek.
- `api/services/review_citation_service.py`: Citation integrity ve claim-evidence alignment'a evrilecek.
- `api/services/openalex_polite.py`: Deprecated provider mirası ayrıştırılacak.
- `api/config.py`: Production env fail-closed contract.
- `api/middleware/auth.py`: Mock/dev auth isolation.
- `api/middleware/rate_limit.py`: Redis yoksa fail-closed.
- `engine/ingestion/*`: Secure parsing, manuscript anchors, references, section extraction.
- `db/migrations/0041_review_domain.sql`: Review domain migration genişletilecek.
- `eval/review/*`: Academic quality benchmark merkezi.

### Frontend

- `web/src/lib/brand.ts`: Arbitra marka sözleşmesi.
- `web/src/lib/auth.ts`: Production mock auth kill switch.
- `web/src/lib/review-api.ts`: Typed review API contract.
- `web/src/hooks/useReview.ts`: Wizard/job polling/cockpit state.
- `web/src/app/(marketing)/landing/page.tsx`: Premium positioning.
- `web/src/app/(app)/review/page.tsx`: Wizard.
- `web/src/app/(app)/review/[jobId]/page.tsx`: Live cockpit + report.
- `web/src/components/review/ReviewReportView.tsx`: Evidence/action/council cockpit.
- `web/src/styles/globals.css`: Visual system tokens.

## İlk 30 günlük hedef

30 gün sonunda ürün şu hâle gelmeli:

1. Production mock auth ve silent fallback kapalı.
2. OpenAlex provider yeni API-key abstraction'da.
3. Review job stage/progress modeli durable queue interface ile çalışıyor.
4. Confidentiality mode create-review akışında var.
5. Review schema anchor/confidence/severity/action item taşıyor.
6. Manuscript type + study design classifier MVP çalışıyor.
7. Article/conference/thesis/grant rubrikleri ayrıldı.
8. Qualitative rigor MVP ve quantitative validity MVP var.
9. Landing + wizard + cockpit redesign ilk versiyon canlı.
10. Eval lab minimum benchmark çalıştırıyor.

## Dünya klası başarı tanımı

Arbitra şu soruya her zaman evet diyebilmelidir:

> Kullanıcı bu raporu gerçek bir danışman, hakem, jüri veya panel üyesinin önüne koyduğunda sistemin eleştirileri akademik, izlenebilir, uygulanabilir ve güvenilir mi?

Evet değilse görev bitmemiştir.
