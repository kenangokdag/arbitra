# Plan: Hakem raporu dil desteği — i18n mimarisi (yeni dil eklemeyi ucuzlaştırma)

> Bu plan KOD İÇERMİYOR — sadece mimari. Onay sonrası uygulanacak.
> Kök keşif (bu oturumda, kanıt A — file:line): `ReviewLang` ve etiket
> sözlükleri kod tabanında **3 ayrı yerde bağımsız, senkronsuz** kopyalanmış.
> Yeni dil eklemek şu an 3 dosyayı elle, tutarlı tutarak güncellemeyi
> gerektiriyor — bu plan bunu **tek kaynağa** indirip 1 dosyaya düşürüyor.

---

## 1. Kapsam (araştırma bulgusu, önceki turda kanıtlandı)

**Sorun — 3 bağımsız hardcoded Türkçe etiket sözlüğü, senkron garantisi yok:**

| # | Dosya | İçerik | Dil |
|---|---|---|---|
| 1 | `web/src/lib/review-api.ts:663-681` | `VERDICT_LABELS` + `DIMENSION_LABELS` (FE render) | sadece TR |
| 2 | `api/services/report_export_service.py:37-53` | `VERDICT_LABELS_TR` + `DIMENSION_LABELS_TR` (DOCX export) | sadece TR |
| 3 | `web/src/lib/review-api.ts:~650-660` | job status/step etiketleri (6+ giriş) | sadece TR |
| 4 | `api/services/review_service.py:409,563` | step_label hardcode ("Belge ve çalışma türü belirlendi" vb.) — #3'ü BACKEND'den de bağımsız kopyalıyor | sadece TR |

**Ayrıca dil kümesi kapalı, 2 yerde ayrı tanımlı:**
- `api/models/review.py:29` — `ReviewLang = Literal["tr", "en"]`
- `web/src/lib/review-api.ts:14` — `export type ReviewLang = "tr" | "en"`

**LLM çıktı dili zaten parametrik (dokunulmayacak, çalışıyor):**
`api/services/review_orchestration.py:219-222` `_lang_instruction()` — writer/editor/critic prompt'larının başına eklenen tek satır. Bu doğru çalışıyor, plan bunu KORUYOR, sadece genişletiyor (2→N branch yerine dict lookup).

**Codebase'de zaten kanıtlanmış emsal (kopyalanacak desen):**
`api/services/presenter.py:63` — `_SUPPORTED_LANGS = frozenset({"tr","en","id"})`, farklı bir özellik (`/q` literatür-özet) için 3-dil desteği. Bu plan, review pipeline'ı bu OLGUNLAŞMIŞ deseni kendi (daha zengin — etiket çevirisi de gerektiren) ihtiyacına uyarlıyor.

**Hedef:** Yeni bir dil (örn. Çince) eklemek → **1 dosyada 1 giriş** + `ReviewLang` type'a 1 değer eklemek yeterli olsun. Etiket çevirisi unutulamasın (tip sistemi zorlasın — TypeScript/Python'da eksik çeviri derleme hatası versin).

---

## 2. Backend

### 2.1 Yeni tek-kaynak modül: `engine/academic/i18n_labels.py` (yeni, pure/deterministik, LLM yok)
- `SUPPORTED_REVIEW_LANGS: tuple[ReviewLang, ...]` — TEK yer, dil listesi buradan türetilir.
- `DIMENSION_LABELS: dict[ReviewLang, dict[DimensionKey, str]]` — tam matris (TR + EN dolu; EN şu an eksik, bu plan doldurur — 10 boyut × mevcut 2 dil).
- `VERDICT_LABELS: dict[ReviewLang, dict[Verdict, str]]` — 4 verdict × 2 dil.
- `get_dimension_label(key: DimensionKey, lang: ReviewLang) -> str` / `get_verdict_label(v: Verdict, lang: ReviewLang) -> str` — fallback: dil eksikse `en`'e düş (sessiz Türkçe göstermek yerine dürüst ikinci-en-iyi seçenek), `_DIMENSION_LABELS[lang]`'de key yoksa raw key döner (mevcut export service'in `_humanize_*` davranışına sadık — hata fırlatmaz, gösterge bozulmaz).
- **Test:** her `ReviewLang` değeri için her `DimensionKey`/`Verdict`'in çevirisi VAR mı diye bir "tamlık" testi (`test_i18n_labels.py`) — yeni dil eklenip çeviri unutulursa test kırılır (tip sistemi + test = çift zırh, K-031 deseniyle tutarlı).

### 2.2 `api/models/review.py` — `ReviewLang` TEK yerde kalır (zaten burada), değişmez; sadece yeni değer eklenecekse (örn. `"zh"`) BURADA eklenir.

### 2.3 `report_synthesis.py` (veya rapor derlenen nokta) — `DimensionScore`'a `label: str` alanı eklenir
- Rapor derlenirken `i18n_labels.get_dimension_label(key, report.language)` çağrılıp `label` alanına yazılır.
- `ReviewReport`'a `verdict_label: str` eklenir (aynı mantık).
- **Neden burada:** `language` zaten raporun bir alanı — çeviri, raporun ÜRETİLDİĞİ anda, TEK yerde yapılır. Frontend artık "hangi dil, hangi sözlük" bilmek zorunda kalmaz — API'den hazır string gelir.

### 2.4 `api/services/report_export_service.py` — `VERDICT_LABELS_TR`/`DIMENSION_LABELS_TR` + `_humanize_*` SİLİNİR
- Yerine `i18n_labels.get_dimension_label`/`get_verdict_label` çağrılır (rapor zaten `language` taşıyor — export DA doğru dilde üretilir, bugüne kadar hep TR üretiyordu, bu YAN-DÜZELTME de olur).

### 2.5 `api/services/review_service.py:409,563` — hardcoded step_label'lar
- **Açık karar noktası (§2.6'ya bakın):** step_label'ların dili de mi çevrilsin, yoksa iç-gözlem/loglama amaçlı sabit mi kalsın? Bkz aşağıda.

### 2.6 AÇIK SORU (uygulamadan önce karar gerekli)
Job status/step etiketleri (`step_label`, "Belge ayrıştırılıyor" gibi) şu an HEM backend'de (`review_service.py`) HEM frontend'de (`review-api.ts`) bağımsız hardcoded — hangisi asıl kaynak, biri ölü kod mu, kontrol edilmedi (bu turda kapsam dışı bırakıldı, ayrı keşif gerekir). Bu step_label'lar rapor içeriği DEĞİL, yükleme SIRASINDAKİ ilerleme metni — kullanıcı raporu Çince istese bile "Belge ayrıştırılıyor" ekranı görmesi kabul edilebilir mi (uygulama arayüzü zaten Türkçe, rapor dili ayrı bir kavram)? **Öneri: bu turda dokunma, kapsam dışı bırak** — review pipeline'ın progress UI'ı, app'in genel arayüz diliyle (Türkçe) tutarlı kalsın; sadece RAPOR İÇERİĞİ (boyut adları, verdict, LLM metni) çok-dilli olsun. Onaylarsanız §3'te frontend job-status sözlüğüne dokunulmaz.

---

## 3. Frontend

### 3.1 `web/src/lib/review-api.ts`
- `DIMENSION_LABELS` / `VERDICT_LABELS` sabit sözlükleri **SİLİNİR** (artık backend'den `label`/`verdict_label` geliyor).
- `ReviewLang` type'ı backend'le senkron kalmaya devam eder (2 dosya, elle senkron — §4'te bir tutarlılık testiyle korunur, tam birleştirme mümkün değil çünkü Python/TS ayrı derleme birimleri).
- Job status etiketleri: §2.6 kararına göre DOKUNULMAZ (öneri) ya da aynı desenle taşınır.

### 3.2 `web/src/components/review/ReviewReportView.tsx`
- `DIMENSION_LABELS[dimension.key]` çağrıları → `dimension.label` (API'den gelen alan) ile değiştirilir. 2 kullanım yeri (satır ~1678, ~2073 — önceki keşifte bulundu).

### 3.3 `web/src/app/(app)/review/page.tsx` (upload sayfası, dil seçici dropdown)
- Bu, RAPOR içeriği değil, bir SEÇİCİ UI'ı ("Türkçe"/"English" gibi dil adlarının KENDİSİ, hangi dilde gösterileceği). Küçük, ayrı bir statik sözlük olarak KALIR (`{value:"tr",label:"Türkçe"}` deseni) — yeni dil eklenince buraya da 1 satır eklenir, i18n_labels'tan bağımsız (bu doğru bir ayrım: "dil seçme arayüzü" vs "rapor içeriği çevirisi").

---

## 4. Test planı
- `tests/unit/test_i18n_labels.py` (yeni): her `ReviewLang` × her `DimensionKey`/`Verdict` kombinasyonu için çeviri var mı (tamlık testi) + fallback davranışı (bilinmeyen key → raw key, bilinmeyen dil → `en`).
- `tests/unit/test_report_synthesis.py` (mevcut, genişlet): rapor derlenince `DimensionScore.label` ve `ReviewReport.verdict_label` doğru dilde dolduğunu doğrula (TR ve EN, 2 senaryo).
- `tests/unit/test_report_export_service.py` (mevcut, güncelle): `_humanize_*` yerine `i18n_labels` çağrıldığını + export'un artık `language="en"` raporlarda İngilizce boyut adı ürettiğini doğrula (bugüne kadarki TR-hep-sabit davranışını kıran, kasıtlı düzeltme).
- FE: `ReviewReportView.test.tsx` (mevcut) — `DIMENSION_LABELS` sabit sözlüğüne bağımlı assertion'lar varsa, API fixture'ından `label` alanı okuyacak şekilde güncellenir.
- **Dil-tutarlılık testi (yeni, küçük ama kritik):** backend `ReviewLang` (Python Literal) ile frontend `ReviewLang` (TS type) senkron mu — otomatik doğrulanamıyorsa (ayrı derleme birimleri), en azından bir yorum+checklist ile "yeni dil eklerken 2 dosya" hatırlatması `i18n_labels.py`'nin docstring'ine yazılır.

---

## 5. Kapsam dışı (bu plan bunları ÇÖZMÜYOR, bilerek)
- Job status/step etiketlerinin çevirisi (§2.6 — ayrı karar/plan).
- Prompt iskeletinin (`review_orchestration.py`'deki "MAKALE BAŞLIĞI:" gibi sabit Türkçe talimat metinleri) çevirisi — LLM'ler buna toleranslı, gerçek bir kullanıcı-görünür sorun değil, dokunulmuyor.
- Genel uygulama arayüzü dili (sidebar, butonlar, "Detay"/"İndir" vb.) — bu ayrı, çok daha büyük bir tam-app-i18n kararı, bu planın kapsamı SADECE rapor içeriği.
- Gerçek Çince (veya başka) çeviri metinlerinin YAZILMASI — bu plan sadece MİMARİYİ kurar (dict yapısı, fallback, tek kaynak); yeni dilin gerçek çevirilerini bir insan/çevirmen sağlamalı, ben uydurmam (halüsinasyon yasağı — akademik terim çevirisi hassas, glossary onayı gerekir).
- `presenter.py`'nin (`/q` özelliği) kendi dil mekanizmasıyla birleştirme — farklı bir servis, bu plan ona dokunmuyor, sadece deseninden ilham alıyor.

---

## 6. Guardian notu (uygulama zamanı için, şimdi değil)
`engine/academic/i18n_labels.py` yeni dosyası `engine/academic/` içinde — CLAUDE.md kuralı gereği uygulamadan (kod yazımından) SONRA, kullanıcıya sunmadan ÖNCE `arbitra-moat-guardian`'a danışılacak. Beklenti: nötr/güçlendirici (saf gösterim katmanı, skorlama/fabricated-tespiti mantığına dokunmuyor) ama teyit uygulama turunda yapılacak, burada varsayılmıyor.
