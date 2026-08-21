# AGENTS.md — Arbitra World-Class Autonomous Coding Rules

Bu dosya Codex, Claude, Cursor Agent veya başka bir coding agent için bağlayıcı çalışma sözleşmesidir.

## Mission

Arbitra'yı dünya klası bilimsel hakemlik platformuna dönüştür. Ürün makale, bildiri, tez ve proje dosyalarını akademik olarak derin, güvenli, kanıt-destekli ve premium deneyimle incelemelidir.

## Non-negotiable rules

1. **No fake production.** Production'da mock auth, mock data, silent fallback, fake provider, placeholder review veya uydurma akademik bulgu yasaktır.
2. **No silent degradation.** Bir provider, parser, LLM veya citation check çalışmazsa rapor bunu `degraded_evidence` olarak açıkça göstermelidir.
3. **No user-data leak.** Kullanıcı objelerinde owner check, tenant boundary, RBAC ve audit log olmadan endpoint tamamlanmış sayılmaz.
4. **No external AI without consent.** Editor/reviewer veya confidential manuscript modunda external LLM kullanımı açık izin, disclosure ve retention policy olmadan yapılamaz.
5. **No generic academic review.** Her çıktı belge türü ve çalışma türüne göre özelleşmelidir.
6. **No UI-only premium.** Premium hissiyat; hızlı onboarding, frictionless wizard, kanıtlı rapor, açık güven göstergeleri, revision cockpit ve export akışıyla sağlanır.
7. **No schema-breaking changes without migration.** Model değişikliği varsa DB migration, API contract, frontend types ve tests birlikte güncellenir.
8. **No task is done without tests.** En az unit/integration/eval/smoke test veya açık manuel verification kaydı gerekir.
9. **No new dependency without reason.** Her yeni bağımlılık ADR veya task note içinde gerekçelendirilir.
10. **No unclear state.** Her işlem sonunda `docs/worldclass/STATE.md` güncellenir.

## Autonomous execution loop

Agent her oturumda şu sırayı izler:

1. `docs/worldclass/STATE.md` dosyasını oku.
2. `docs/worldclass/ROADMAP.yaml` içinden bağımlılıkları tamamlanmış en yüksek öncelikli görevi seç.
3. Görevin ilgili spec dosyalarını oku.
4. Repo durumunu incele; mevcut kodu silmeden önce kullanım noktalarını bul.
5. Küçük, testlenebilir değişiklik yap.
6. Test ekle veya güncelle.
7. İlgili hedefli testleri çalıştır.
8. Lint/typecheck mümkünse çalıştır.
9. Gate checklist'i doldur.
10. `STATE.md` dosyasını güncelle: yapılan, değişen dosyalar, test sonucu, açık riskler, sonraki görev.

## Stop conditions

Aşağıdaki durumlardan biri varsa ilerleme durdurulur ve `STATE.md` içine BLOCKED yazılır:

- Gerekli secret/env olmadan production davranışı doğrulanamıyor.
- Güvenlik veya gizlilik açısından veri sızıntısı riski oluşuyor.
- Migration veri kaybı yaratabilir ve geri dönüş planı yok.
- Testler kritik şekilde kırılıyor ve sebep anlaşılamıyor.
- Akademik çıktı uydurma kaynak veya yanlış provenance üretiyor.

## Default assumptions

Belirsizlik varsa işi durdurmak yerine güvenli varsayım yap:

- Marka: **Arbitra** ana ürün, PaperMind platform/suite adı.
- Auth: production'da gerçek Supabase/JWKS/cookie tabanlı akış; dev auth yalnız local.
- Workflow: başlangıçta minimal durable queue kabul, ama interface Temporal/Celery/RQ değişimine açık.
- Review depth: default `full_academic_review`.
- Privacy: default retention kısa; editor/reviewer mode'da external AI kapalı.
- Language: source language, output language ve UI locale ayrı alanlardır.

## Commit discipline

Her PR/commit tek bir task veya sıkı bağlı küçük task grubu içermelidir. PR açıklaması şu formatta olmalı:

- Task ID:
- Why:
- Changed files:
- Data model changes:
- Security/privacy impact:
- Academic impact:
- UX impact:
- Tests run:
- Known limitations:
- Gate status:

## Required touched-file awareness

Bu repoda en kritik dosyalar:

- `api/models/review.py`: review contract kalbi.
- `api/routes/review.py`: user-facing review API.
- `api/services/review_service.py`: job lifecycle ve orchestration boundary.
- `api/services/review_orchestration.py`: reviewer council/LLM chain.
- `api/services/review_citation_service.py`: citation integrity.
- `api/services/openalex_polite.py`: provider mirası; yeni provider layer'a taşınacak.
- `api/middleware/auth.py`: auth gate.
- `api/middleware/rate_limit.py`: production quota güvenliği.
- `api/config.py`: env gerçeklik sözleşmesi.
- `db/migrations/0041_review_domain.sql`: review domain DB başlangıcı.
- `engine/ingestion/*`: manuscript parsing and file security.
- `eval/review/*`: akademik kalite ölçüm yeri.
- `web/src/app/(app)/review/page.tsx`: intake wizard başlangıcı.
- `web/src/app/(app)/review/[jobId]/page.tsx`: review cockpit/report route.
- `web/src/components/review/ReviewReportView.tsx`: mevcut rapor UI; cockpit'e evrilecek.
- `web/src/lib/auth.ts`: dev/mock auth riski.
- `web/src/lib/review-api.ts`: frontend/backend contract.
- `web/src/lib/brand.ts`: marka tekilleştirme.

## Definition of world-class done

Bir parça ancak şu koşullarda dünya klası sayılır:

- Kullanıcının ne yapacağı ilk 10 saniyede anlaşılır.
- Yeni başlayan kullanıcı ayar bilmeden doğru akışa girer.
- Uzman kullanıcı kontrol kaybetmez.
- Akademik eleştiri exact manuscript anchor, gerekçe, severity, confidence ve action item içerir.
- Gizlilik ve external AI kullanımı açıkça yönetilir.
- Sistem hata/fallback durumunu saklamaz.
- Test ve eval olmadan release olmaz.
- Kod 10 yıl provider/model değişimlerine dayanacak abstraction'a sahiptir.

## Mandatory frontend reading

Before touching any `web/` file, read:

- `docs/worldclass/FRONTEND/FRONTEND_WORLDCLASS_BLUEPRINT.md`
- `docs/worldclass/FRONTEND/INFORMATION_ARCHITECTURE.md`
- `docs/worldclass/FRONTEND/LANDING_PAGE_SPEC.md`
- `docs/worldclass/FRONTEND/REVIEW_WIZARD_DETAILED_SPEC.md`
- `docs/worldclass/FRONTEND/REPORT_COCKPIT_DETAILED_SPEC.md`
- `docs/worldclass/FRONTEND/FRONTEND_AGENT_TASKS.yaml`
- `docs/worldclass/CHECKLISTS/FRONTEND_WORLDCLASS_GATE.md`

Frontend work is incomplete if it only changes colors or layout. It must improve the academic user journey: landing clarity, privacy-safe intake, live review cockpit, structured report cockpit, evidence/provenance visibility, and revision actionability.

