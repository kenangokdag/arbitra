# Plan: Rapor sayfası için 4-adımlı onboarding turu

**Tarih:** 2026-08-17
**Durum:** UYGULANDI (Kenan onayı sonrası) — sonuçlar §6'da.
**Kaynak:** Kenan'ın bu oturumdaki isteği — 4 adım (editör sorumluluk uyarısı, yükleme akışı, yeni rapor öğeleri, Danışman varlığı), sadece ilk girişte, tercih saklı.
**Guardian gerekmiyor** — saf UI/onboarding içeriği, motor/rubric'e dokunmuyor.
**Karar verici:** Kenan.

---

## 1. Araştırma sonucu

**Hazır bir tur/onboarding bileşeni YOK.** `package.json`'da tur kütüphanesi (react-joyride/driver.js/shepherd/intro.js) yok. `web/src/app/(app)/onboarding/page.tsx` var ama bu TAMAMEN FARKLI bir şey — F5-S2 kullanıcı-profili kurulumu (ad/tier/alan-taksonomisi), pre-pivot "papermind-app" dönemi, bu işe UYGUN DEĞİL/reuse edilemez.

**Modal a11y deseni VAR, ama paylaşılan bir temel bileşen YOK.** `ConfirmDialog.tsx` (`web/src/components/ui/`) iyi bir a11y referansı (role=dialog, aria-modal, Escape, Tab focus-trap, focus-restore, backdrop-click) AMA yıkıcı-eylem-onayına özel (confirm/cancel + phrase-typing + async akış) — 4 adımlı bilgilendirme turuna UYMUYOR. `AnchorDrawer` (ReviewReportView.tsx) da BENZER a11y mantığını KENDİ İÇİNDE ayrıca yazmış — yani bu kod tabanında paylaşılan bir Dialog primitive'i YOK, her modal kendi a11y'sini yazıyor. Yeni tur bileşeni de AYNI deseni (kendi a11y'si) izleyecek — bu planın kapsamında bir Dialog-primitive refactor'ü YOK.

**Tercih saklama — localStorage, backend GEREKMİYOR.** `db/migrations`'da hiçbir kullanıcı-tercih/onboarding-seen kolonu yok. Mevcut, doğrudan kopyalanabilir bir desen VAR: `web/src/lib/defenseSession.ts` (SSR-safe `typeof window === "undefined"` guard + try/catch + sessiz-geç). Yeni tur tercihi AYNI deseni izleyecek — backend/migration GEREKMİYOR.

**"Editör modu sorumluluk uyarısı" — backend'de SABİT bir metin, LLM-üretilmiyor.** `api/services/review_orchestration.py:62-73` — `_ETHICS_NOTICE_EDITOR`/`_ETHICS_NOTICE_AUTHOR` SABİT string sabitleri (rapor-özel değil, LLM üretmiyor). Tur adım 1'i bu metni (ya da BİREBİR yakın bir versiyonunu) önizleyebilir — **bilinçli bir küçük tekrar** (iki yerde aynı metin, sync-drift riski düşük çünkü hukuki/etik metin nadiren değişir) — plan bunu açıkça not ediyor, sessizce YAPILMIYOR.

**Adım 4 dikkat — Danışman'ın "varlığı" doğru ama "rapor-farkındalığı" henüz YANLIŞ olur.** `Topbar.tsx` her sayfada (rapor sayfası dahil) genel bir Danışman tetikleyicisi zaten açıyor — yani "Danışman panelinin varlığı" iddiası DOĞRU. AMA `DANISMAN_REPORT_GROUNDING_PERSONA_2026-08-16.md` planı, rapor sayfasına ÖZEL bir tetikleyici (`report_id` geçen) mount etmeyi BİLİNÇLİ olarak kapsam dışı bırakmıştı — yani Danışman panelinin ŞU AN bu raporun bulgularını "bildiği" iddia edilemez. Tur metni **SADECE varlığı belirtecek** ("sağ üstte bir Danışman paneli var, sorularını sorabilirsin"), rapor-özel akıllılık iddia ETMEYECEK — Kenan'ın orijinal isteğiyle ZATEN uyumlu ("varlığının belirtilmesi", "ne yapabildiği" değil).

## 2. Önerilen yaklaşım — TEK, statik 4-adımlı modal (spotlight/in-context tur DEĞİL)

**Neden modal, in-context spotlight değil:** 4 adımdan 3'ü (yükleme akışı, yeni rapor öğeleri, Danışman) FARKLI SAYFALARA ait (upload sayfası vs. rapor sayfası) ve rapor sayfasındaki gerçek elemanlar (öncelikli liste, sınırlayıcı boyut vurgusu) SADECE bir rapor işlendikten SONRA var olur — "ilk giriş"te (henüz hiçbir şey yüklenmemişken) gerçek elemanlara "spotlight" ile işaret etmek mümkün DEĞİL. Bunun yerine: TEK bir statik içerik-modalı, upload sayfasında (`/review`, akışın gerçek giriş noktası) mount olunca `hasSeenReviewTour()` false ise otomatik açılır. 4 adımın hepsi STATİK metin/örnek (canlı veriye bağımlı DEĞİL) — basit, düşük riskli, hızlı.

**Alternatif (daha pahalı, kapsam dışı):** rapor sayfasındaki GERÇEK elemanlara (öncelikli liste bölümü, sınırlayıcı boyut kutusu, Danışman butonu) noktalayan bir spotlight-tur — çok daha ilgi çekici ama: (a) elemanlar sadece BAZI raporlarda var (örn. dimension_scores boşsa sınırlayıcı-boyut kutusu hiç render edilmiyor), (b) 2 sayfaya yayılan tur-state senkronizasyonu gerektirir, (c) DOM-pozisyon takibi (ResizeObserver vb.) gerektirir. Kenan isterse AYRI bir plan olarak ele alınabilir.

## 3. Uygulama

### 3.1 `web/src/lib/reviewTourPreference.ts` (yeni)
`hasSeenReviewTour(): boolean`, `markReviewTourSeen(): void` — `defenseSession.ts` deseniyle BİREBİR aynı (SSR-safe + try/catch). Key: `"arbitra:review-onboarding-seen"`.

### 3.2 `web/src/components/review/ReviewOnboardingTour.tsx` (yeni)
4 statik adım (aşağıdaki içerik TASLAK, kod aşamasında netleşir):
1. **Editör modu sorumluluk uyarısı** — `_ETHICS_NOTICE_EDITOR`'a yakın metin (§1'deki bilinçli-tekrar notuyla).
2. **Yükleme akışı tanıtımı** — dosya seç/sürükle → mod+dil → gizlilik ayarları → sonuç bekle (mevcut `/review` sayfasının 3-adım yapısını ÖZETLER, aynı metni tekrar üretmez).
3. **Yeni rapor öğeleri** — öncelikli düzeltme listesi (P0/P1/P2), sınırlayıcı boyut vurgusu, karar güveni (`ConfidenceMeter`) — üçü için birer cümle.
4. **Danışman'ın varlığı** — SADECE varlık, rapor-farkındalığı İDDİA ETMEDEN (§1'deki uyarı).

A11y: `ConfirmDialog`'un deseniyle (role=dialog, aria-modal, Escape, Tab focus-trap, focus-restore) TUTARLI, kendi içinde yazılır (paylaşılan primitive yok, §1). İleri/Geri/Atla + adım noktaları (1/4). Atla/Escape/backdrop-click/Bitti — HEPSİ `markReviewTourSeen()` çağırır (herhangi bir kapanış = kullanıcı kararını verdi, bir daha göstermeyiz).

### 3.3 `web/src/app/(app)/review/page.tsx`
Mount'ta `hasSeenReviewTour()` kontrolü; false ise `<ReviewOnboardingTour onClose={...} />` render edilir.

## 4. Test planı

1. `reviewTourPreference.ts` — get/set, SSR-safe, localStorage hata durumunda sessiz geçer.
2. `ReviewOnboardingTour` — adım 1'de başlar, İleri/Geri doğru gezdiriyor, adım noktaları güncelleniyor, Atla/Escape/Bitti `markReviewTourSeen()` çağırıyor + kapanıyor.
3. `/review` sayfası — tercih YOKKEN tur otomatik açılıyor, tercih VARKEN açılmıyor (mock).

## 5. Kapsam dışı

1. Sunucu-taraflı/cihazlar-arası tercih senkronizasyonu — localStorage yeterli (§1, mevcut desen).
2. Turu manuel yeniden açma (örn. bir "?" yardım butonu) — istenmedi, ayrı küçük takip olabilir.
3. Gerçek elemanlara noktalayan in-context spotlight tur — §2'de daha pahalı alternatif olarak not edildi, ayrı plan.

## 6. Sonuçlar (uygulandı, 2026-08-17)

**Kod:** `web/src/lib/reviewTourPreference.ts` (yeni, `defenseSession.ts` deseni) + `web/src/components/review/ReviewOnboardingTour.tsx` (yeni, `ConfirmDialog` a11y deseniyle tutarlı kendi modalı) + `web/src/app/(app)/review/page.tsx` (mount'ta `hasSeenReviewTour()` kontrolü, kapanışta `markReviewTourSeen()`).

**Uygulama sırasında bulunan/düzeltilen 2 şey:**
1. Kendi test dosyamdaki bir hata — `vi.spyOn(window.localStorage, "getItem")` jsdom'da GÜVENİLİR ÇALIŞMADI (ilk çağrıda hata fırlatıyor, ikinci çağrıda sessizce normal davranışa dönüyordu). `Storage.prototype` üzerinden spy etmeye geçirildi, düzeldi.
2. `web/src/app/(app)/review/page.test.tsx`'in mevcut testleri — yeni `hasSeenReviewTour()` çağrısı mock'lanmadan `undefined()` ile çökerdi (bu oturumda 3. kez aynı desendeki regresyon). `vi.mock("@/lib/reviewTourPreference", ...)` eklendi, varsayılan `true` (tur mevcut testlerde hiç açılmıyor) — tur-özel davranış AYRI bir describe bloğunda, kendi mock değeriyle test edildi.

**Testler:** `reviewTourPreference.test.ts` (4, SSR-safe + hata-durumu dahil), `ReviewOnboardingTour.test.tsx` (7, adım gezinme + tüm kapanış yolları — Atla/X/Escape/backdrop/son-adım), `page.test.tsx`'e 3 yeni (tur açılıyor/açılmıyor/kapanınca işaretleniyor).

**Regresyon:** `review/` + `review components` + `reviewTourPreference` — **71/71 PASS** (12 dosya). `tsc --noEmit` temiz.
