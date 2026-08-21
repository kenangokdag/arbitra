# DESIGN-DECISIONS — Arbitra Landing (hakemlik tanıtım yüzeyi)

> **Anti-toolbox kapısı (DESIGN-LANGUAGE §0.5).** Bu 5 cevap landing KODUNDAN ÖNCE kilitlendi.
> Hero yönü Omer onayı: **"Bağımsız hakem paneli"** (3 hakem → ortak yargı). Kimlik kopyalanmaz,
> cockpit kimliğinden (`web/DESIGN-DECISIONS.md`) TÜRETİLİR (§0.6). `frontend-excellence-audit` denetler.
>
> **Ürün gerçeği (kritik):** Arbitra = **saf hakemlik** (peer-review prova). Eski PaperMind landing'i
> "gap-analiz / araştırma aracı" satıyordu (gap×40) — bu YANLIŞ ÜRÜN. Gap-analiz bölümleri ÇIKAR;
> hakem/jüri omurgası KALIR ve merkeze gelir.

---

## 1. RUH (tek cümle)
**"Dergiye göndermeden önce, üç bağımsız hakemin önüne çık — yargıyı, kanıtı ve düzeltmeyi şimdi gör."**

Cockpit RUH'unun ("sertçe ama dürüstçe hakemlendin") tanıtım yüzüne taşınmış hâli. Duygu: adil-katı bir
hakem masasının kapısında durmak. Korku-satışı değil ("reddedilirsin!"), **hazırlık-güveni**: kararı ve
onun ne kadar güvenilir olduğunu birlikte görürsün. Sakin, otoriter, dürüst — panik değil.

## 2. SAYFANIN TEK İŞİ
Ziyaretçiyi tek bir inanca getirmek: **"Bu, göndermeden önce — dürüstçe ve kanıtla — makalemin hazır olup
olmadığını söyleyecek."** Tek dönüşüm: **waitlist'e katıl** (WAITLIST_BYPASS=false, lansman-öncesi).
İki eşit çağrı yok; her bölüm bu tek inanca hizmet eder, sonunda tek CTA.

## 3. İMZA ANI (kopyalanamaz — cockpit imzasının çalışan minyatürü)
**Hero'da yakınsayan jüri + tıklanabilir kanıt-çıpası.** Üç hakem kartı (yöntemci/şüpheci/yapıcı) ayrı ayrı
okur → tek bir **verdict**te (ör. MAJOR REVISION) birleşir. Ziyaretçi bir bulguya dokunur → cockpit imzası
minyatür olarak açılır: **(1) makaledeki cümle → (2) neden (kriter) → (3) fix.** Rakipler (SciSpace/Elicit/
Scite) yargıyı metne dürüstçe çıpalamaz ve çok-hakemli panel sunmaz. Cesaret yalnız burada; gerisi sessiz.
Demo veri **açıkça "örnek değerlendirme"** etiketli — sahte kanıt/abartı yok (dürüstlük yasası).

## 4. REDDEDİLEN 3 JENERİK (açık beyan)
1. ❌ **"Gap-analiz / araştırma aracı" landing'i** (eski PaperMind, gap×40) → ✅ saf hakemlik omurgası.
   Sebep: yanlış ürünü satmak = en büyük toolbox hatası.
2. ❌ **Jenerik SaaS hero** ("AI-powered research assistant" + 3 feature kutusu + ekran-görüntüsü) → ✅
   yakınsayan canlı jüri paneli (ürünün ÖZÜ hero'da çalışır). Sebep: "aynı brief'i alan her landing 3-kutu üretir."
3. ❌ **Abartılı sosyal-kanıt / sahte metrik bandı** ("10.000+ araştırmacı!", uydurma logo duvarı) → ✅
   dürüstlük katmanı: belirsizliği + sınırı gösteren tek örnek. Sebep: uydurma sayı = halüsinasyon yasağı ihlali.

## 5. GİZLENEN KARMAŞA (aşamalı açığa çıkarma — sayfa akışı)
| Sıra | Bölüm | Tek işi |
|---|---|---|
| **01 Hero** | Üç bağımsız hakem → tek verdict + kanıt-çıpası minyatürü | İnanç tohumu + CTA |
| **02 Nasıl çalışır** | Yükle → panel okur (parse→atıf→bağlam→kapsam→council) → verdict + çıpalı bulgu → kabule fix | Süreç şeffaflığı |
| **03 Panel (jüri derinliği)** | Mevcut JURY dark bölümü — 3 GERÇEK persona (yöntemci/şüpheci/yapıcı) ayrı bakış | Çok-hakemli titizlik kanıtı |
| **04 Dürüstlük katmanı** | confidence/limitations/"doğrulayamadık"/UNVERIFIED çıpa — sakladığımız değil, GÖSTERdiğimiz | Özgün odak / fark |
| **05 Gizlilik & KVKK** | Makalen gizli · dış-AI rıza-kapısı · retention sonunda OTO-SİL (0044 gerçek) | Güven (yüklemeden önce) |
| **06 Karşılaştırma** | vs jenerik AI sohbet / vs diğer araçlar — çıpalı verdict + dürüst belirsizlik | Neden biz |
| **07 CTA / Waitlist** | Tek dönüşüm | Kapanış |

## 6. EDİTÖRYAL OMURGA
Cockpit ile aynı dil: **başlık (verdict/iddia) → kanıt (çıpalı, katmanlı) → künye (gizlilik/dürüstlük).**
Akademik dergi tipografisi (font-display serif + Inter UI + crimson italic ölçülü vurgu). Tek aksan =
`var(--color-accent)` — **admin-konfigüre token** (cockpit §0.6: renk platform-kararı/admin-tema; şu an
indigo `#4F46E5`, koyu-zeminde `--color-accent-soft` #818CF8 AA için). Eski PaperMind turuncu `#F97316` ÇIKAR.
Hardcode hex YOK, hep token. Gradyan/glow/parıltı YOK (§8).
Sıralama tipografi + boşluk + tek-aksanla taşınır, renk gürültüsüyle değil.

## 7. DÜRÜSTLÜK & GERÇEKLİK KİLİDİ
- Hakem panelindeki tüm alıntılar/verdict'ler **"örnek/illüstratif değerlendirme"** etiketli (gerçek kullanıcı
  verisi değil; uydurma metrik yok).
- Hakem rolleri GERÇEK council'a sadık: yöntemci · şüpheci (skeptik) · yapıcı (sempatik) — `engine/academic/council.py`.
- Gizlilik bölümü gerçek özelliklere dayanır: consent-gate (SEC-2) + retention oto-sil (migration 0044). Vaat = kod.
- Marka: yalnız `BRAND`/`ArbitraWordmark`/tagline. PaperMindLogo/AnimatedLogo + #F97316 emekli.

## 8. BEŞ DURUM (landing etkileşimleri — madde 13)
Waitlist formu: alan-bazlı doğrulama (e-posta) · çift-submit kilidi · başarı/zaten-kayıtlı/hata durumları
(WaitlistModal mevcut — yeniden kullan). İmza-anı drill: hover/tık çalışır, boş/yüklenmeyen durumda statik
fallback (beyaz-ekran/ölü-buton YASAK). Animasyon `prefers-reduced-motion`'a saygılı.
