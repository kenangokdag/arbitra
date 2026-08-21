# Plan: Soundness/quantitative_validity severity'sini study_design'a bağlamak

**Tarih:** 2026-08-13
**Durum:** PLAN — kod yazılmadı, guardian'a danışılmadan koda geçilmeyecek (CLAUDE.md plan-first kuralı).
**Kaynak:** `PDF_PIPELINE_CALISMA_GUNLUGU.md` §31 (kök nedeni ilk bulan), §44 (soundness-korelasyon bağlantısını kuran).
**Karar verici:** Kenan (Ömer artık aktif değil — bkz. [[feedback_omer_artik_yok]] hafıza notu, journal §45).

---

## 1. Problem

`role_modules/quantitative_validity.py:24`:
```
major = güç analizi/etki büyüklüğü/eksik veri raporlaması yok; varsayım testi yok.
```
Bu kural **çalışma tasarımından tamamen bağımsız, literal bir prompt talimatı** — "power analysis/effect size yok" görürse ML/deep-learning makalesi olsun, randomize kontrollü deney olsun fark etmeksizin "major" veriyor. Güç analizi/etki büyüklüğü raporlaması ampirik/deneysel nicel sosyal bilim konvansiyonu — `computational_modeling` (deep learning/ML) makalelerinde standart bir beklenti DEĞİL.

**Somut etki (§44'te ölçüldü):** 61 makalelik v8 canlı koşumunda **40/61 (%66) makale TAM AYNI soundness skorunu (7.75) aldı.** 2 makale elle incelendi, ikisinde de aynı desen: `sample_and_power` (major) + `effect_size_and_uncertainty` (major, varsa) hemen her makalede tetikleniyor, geri kalan alt-boyutlar hep "info" boilerplate. Skor makaleler arası neredeyse hiç değişmiyor → insan yargısıyla korelasyon matematiksel olarak imkansıza yakın (soundness r=0.15, çeşitli 11-makalelik örneklemde bile; §44).

**Ölçek:** goldset'in **53/61'i (%87) `study_design="computational_modeling"`** (v8 verisinde `document_classification.study_design` alanından doğrulandı) — yani bu tek kural goldset'in ezici çoğunluğunu etkiliyor.

## 2. Mevcut mimari — nerede ne var, nerede boşluk var

**Zaten var, kullanılmıyor:**
- `engine/academic/classifier.py` her makale için `document_type`/`study_design`'ı zaten hesaplıyor (`DocumentClassification`, `api/models/review.py:471-483`).
- `rubric_registry.py::select_rubric()` bu classification'ı kullanarak hangi boyutun hangi motora (`QuantitativeValidityEngine` vb.) yönleneceğine karar veriyor (`_METHODOLOGY_ENGINE_BY_DESIGN`, satır 47-64) — `computational_modeling` → `_QUANTITATIVE_ENGINE` (satır 54).
- **`Rubric.study_design: str` zaten `assess_manuscript()`'in aldığı `rubric` parametresinin bir alanı** (`rubric_registry.py`, `Rubric` şeması) — yani `assessment.py::assess_manuscript()` içinde `rubric.study_design` HİÇBİR YENİ PLUMBING GEREKMEDEN erişilebilir.

**Boşluk:** `assessment.py:158`'de `assess_quantitative(manuscript, evidence, allow_external_ai=...)` çağrılırken `rubric.study_design` hiç geçilmiyor. `quantitative_validity.py`'nin prompt brief'i de tamamen statik — hiçbir koşullu dal yok. LLM'in ürettiği `Finding[]` severity'si hiçbir post-hoc kontrolden geçmeden doğrudan rapora gidiyor.

## 3. Kanıtlanmış emsal (aynı dosyada, aynı teknik zaten var)

`assessment.py:84-114` — `_downgrade_ungrounded_citation_findings()` (çağrı noktası `assessment.py:188`) — §38'de tam bu şekilde bir sorunu (citation_integrity/literature_positioning'de LLM'in prompt talimatına rağmen kanıtsız critical/major üretmesi) **deterministik kod-seviyesi guard** ile çözdü: LLM'in kararına GÜVENMEDİ, `EvidencePack`'teki gerçek olguya bakıp severity'yi kod içinde indirdi. Bu, canlı koşumda doğrulandı (SS33/38), guardian onayladı, hâlâ üretimde çalışıyor.

**Bu plan aynı deseni tekrarlıyor** — CLAUDE.md §3.3 "boundary'de validate et, içeride trust et": prompt'u tekrar güçlendirmek (§41b'de tam bu denendi, sonucu KANITLANMADI, bkz. §41b) yerine, LLM'in ürettiği `Finding.severity`'i `rubric.study_design`'a bakarak kod içinde deterministik olarak düzelt.

## 3b. GÜNCELLEME (guardian 1. tur bulgusu) — hedef dimension adı YANLIŞ tahmin edilmişti, v8'in gerçek verisiyle düzeltildi

Guardian'ın bulduğu gerçek hata: bu planın ilk taslağı `effect_size_and_uncertainty` adını `quantitative_validity.py:38`'in PROMPT ÖRNEĞİNDEN (`"effect_size"`) değil, daha önceki bir analiz script'inden (`eval/review/results/severity_analysis.py:64`, kendisi de doğrulanmamış) kopyalamıştı — klasik "C-seviye kanıt" hatası.

**Düzeltme — v8'in 61 gerçek raporundaki `Finding.dimension` alanları TEK TEK sayıldı (tahmin değil, gerçek LLM çıktısı):** `dimension` alanı serbest metin (Pydantic enum DEĞİL, prompt'ta örnek olarak gösteriliyor ama LLM birebir uymuyor) — gerçekte HEM `effect_size` (7x) HEM `effect_size_and_uncertainty` (51x, baskın) HEM `uncertainty_measures` (1x) görülüyor. `sample_and_power` ise tutarlı, tek isim (59x).

**Kritik ek bulgu — kapsam daraltıldı:** `sample_and_power` → `_DIMENSION_KEYWORD_MAP`'te `"sample"` anahtar kelimesiyle `"methodology"` kovasına (→ Stanford `soundness`) doğru gidiyor. Ama `effect_size*` HİÇBİR anahtar kelimeye çarpmıyor, `_DEFAULT_RISK_DIMENSION="evidence"`'e düşüyor (→ Stanford `claims_supported`, **soundness DEĞİL**). v8 verisiyle doğrulandı: **7.75 alan 40 makalenin %100'ünde `sample_and_power=major` var, sadece %90'ında `effect_size*=major` var (korelasyon ama nedensellik değil — aynı "ML makalesi" profiline işaret ediyor)**; 7.75 ALMAYAN 21 makalenin sadece %19'unda `sample_and_power=major` var. **`sample_and_power` TEK BAŞINA saturasyonun neredeyse tamamını açıklıyor.**

**Kapsam revizyonu:** Bu plan artık SADECE `sample_and_power`'ı hedefliyor (soundness-saturasyon problemi için yeterli VE doğru risk_radar kovasını vuran tek dimension). `effect_size`/`effect_size_and_uncertainty`/`uncertainty_measures` AYRI, isteğe bağlı bir ikinci iyileştirme olarak not edildi — bunlar düzeltilirse `claims_supported`/`evidence` etkilenir, `soundness` DEĞİL, bu yüzden bu planın "soundness'i düzelt" hedefine gerekli değil (istenirse aynı guard fonksiyonuna 2. bir dimension kümesi olarak eklenebilir, ama bu ayrı bir karar).

## 4. Önerilen değişiklik (revize)

**Yeni fonksiyon** `_downgrade_design_mismatched_quant_findings(engine_result, study_design)` (`assessment.py`, `_downgrade_ungrounded_citation_findings`'in hemen yanına, `assessment.py:84` civarı):

- **Hedef dimension:** `sample_and_power` (tek, v8 verisiyle doğrulandı — bkz. §3b). `effect_size*` ailesi bu turda kapsam DIŞI.
- **"Güç analizi standart konvansiyon DEĞİL" sayılan `study_design` kümesi — `rubric_registry.py:47-64`'ün gerçek routing tablosuyla doğrulandı (guardian 1. tur bulgusu: ilk taslaktaki 6 kategoriden 5'i zaten `_QUANTITATIVE_ENGINE`'e hiç yönlenmiyor, `_CLAIM_ENGINE`'e gidiyor — o kategorilerde bu guard hiçbir zaman çalışmaz, PRATİKTE tek gerçek hedef `computational_modeling`):**
  - **Pratikte etkili:** `computational_modeling` (tek, `_QUANTITATIVE_ENGINE`'e yönlenen tek "muaf" aday).
  - **Savunmacı/ileri-yönlü (şu an `_QUANTITATIVE_ENGINE`'e yönlenmiyor ama routing tablosu değişirse diye kümede TUTULUYOR, yorum satırıyla açıkça işaretlenerek — "şu an ölü kod, gelecekte routing değişirse etkinleşir"):** `design_science`, `software_tool`, `dataset_resource`, `theoretical`, `conceptual`.
  - **Hâlâ zorunlu (güç analizi standart konvansiyon):** `quantitative`, `meta_analysis`, `systematic_review`, `replication`, `registered_report`, `mixed_methods`.
- **Downgrade hedefi: `minor` (moderate DEĞİL) — guardian 1. tur gerekçesi kabul edildi.** Citation guard'ın `moderate` seçimi "kanıt YOK, LLM'in iddiası doğrulanamıyor" (epistemik belirsizlik, ~%50 ihtimal hâlâ doğru olabilir) durumuna uygun. Buradaki durum FARKLI: LLM'in gözlemi (güç analizi yok) muhtemelen DOĞRU ve gerçek — sorun gözlem değil, bu çalışma türünde bunun bir KUSUR sayılması. `RADAR_SEVERITY_PENALTY` (`report_synthesis.py:80-84`): moderate=12 puan ceza bırakır (hâlâ anlamlı), minor=5 puan (neredeyse nötr, "not edildi ama önemsiz" diyor) — niyetle daha tutarlı olan bu.
- Severity indirilirken `limitations`'a şeffaf not eklenir (tıpkı citation guard'daki gibi): *"Severity 'minor'e indirildi: bu çalışma computational_modeling/ML türünde, güç analizi/örneklem-büyüklüğü raporlaması bu türde standart akademik konvansiyon DEĞİL (ampirik nicel sosyal bilim konvansiyonu). Motor bunu classifier'ın study_design çıktısına göre otomatik ayarladı."*
- **Entegrasyon noktası — `_safe("quantitative_engine", ...)` çağrısı şu an TEK SATIRLIK zincir** (`result.extend(await _safe(...))`, `assessment.py:158-168` civarı) — citation guard'ın kullandığı ara-değişkenli yapı (`dim_result = await _safe(...)`, sonra ayrı satırda downgrade, sonra `result.extend(dim_result)`) orada YOK. Bu KÜÇÜK bir refactor gerektiriyor (guardian 2. tur bulgusu — plan ilk halinde "simetrik" dedi ama gerçek entegrasyonun küçük bir yapı değişikliği istediğini belirtmemişti): `quant_result = await _safe("quantitative_engine", assess_quantitative(...))` → `quant_result = _downgrade_design_mismatched_quant_findings(quant_result, rubric.study_design)` → `result.extend(quant_result)`.

### 4a. Confidence-gating (guardian 2. tur bulgusu — ZORUNLU, eklenmeden kod yazılmayacak)

**Guardian'ın bulduğu gerçek eksik:** `rubric.study_design` kendisi DETERMİNİSTİK bir olgu DEĞİL — classifier'ın (bir LLM çağrısının) sınıflandırma çıktısı, `study_design_confidence` alanı var (`api/models/review.py:482`). Citation guard'ın trust boundary'si gerçek deterministik veriydi (`EvidencePack.citation_integrity.fabricated`, OpenAlex'ten); bu yeni guard'ın trust boundary'si ise BAŞKA BİR LLM'in (düşük confidence'lı olabilecek) etiketi. Confidence-gating olmadan bu, "deterministik kanıta dayalı düzeltme" değil, "bir LLM'in belirsiz etiketine göre başka bir LLM'in kararını sessizce indirme" olur — CLAUDE.md §3.3'ün yasakladığı tam olarak bu.

**Karar:** Guard SADECE `study_design_confidence >= 0.7` iken çalışacak; altındaysa dokunmayacak (LLM'in orijinal severity'si korunur — belirsizlikte DEĞİŞTİRME yönünde muhafazakâr, tıpkı classifier'ın kendi "unknown + düşük confidence → güvenli-minimal" ilkesiyle (`api/models/review.py:474`) aynı ruhta). **0.7 eşiği YENİ bir v1-default** — kod tabanında borç alınacak var olan bir eşik YOK (Grep ile arandı, `study_design_confidence`'ı gerçekten tüketen hiçbir mevcut kod bulunamadı — docstring'de anılan "P03 stop_if" davranışı şu an implement EDİLMEMİŞ). 0.7 seçimi v8'in gerçek verisiyle gerekçeli: 53 `computational_modeling` sınıflandırmasının TAMAMI 0.7-0.9 aralığında (min=0.7, hiçbiri altında değil) — yani bu eşik gerçek veride guard'ı HİÇ engellemiyor (mevcut davranışı bozmuyor), ama gelecekte düşük-confidence bir sınıflandırma gelirse güvenli tarafta kalıyor. `_STRICTNESS_REQUIRED_MULTIPLIER`/`_DEFAULT_RISK_DIMENSION` gibi diğer v1-default'lar gibi kod yorumunda "v1 default, tunable" diye işaretlenecek.

## 4b. Moat/quant.* çakışma kontrolü (guardian 1. tur bulgusu — "muhtemelen yok" yerine gerçekten doğrulandı)

`sample_and_power` finding'lerinin `finding_id` alanı `quant.`  öneki taşıyor (v8'de doğrulandı) — yani moat'ın 3. boyutu `statistical_consistency`'nin (`_STATISTICS_MOAT_FINDING_ID_PREFIX="quant."`, `report_synthesis.py:182`) HAM VERİ HAVUZUYLA AYNI. **Şu an çakışma yok** çünkü moat-gate sadece `severity=="critical"`'e bakıyor (`report_synthesis.py:411,429`) ve bu guard sadece `major`'ı hedefliyor; v8'in 61 gerçek raporunda `sample_and_power` hiçbir zaman `critical` severity almamış (elle doğrulandı — sadece major/moderate/info görüldü). **Ama bu kırılgan bir gözlem, garanti değil** — LLM gelecekte `sample_and_power`'ı `critical` olarak da üretebilir. Bu risk açıkça kabul ediliyor, kod bir yorum satırıyla işaretlenecek ("bu guard critical'a dokunmuyor, moat-gate'in kapsamı bilinçli olarak korunuyor").

**Kapsam dışı bırakılan (bu turda YAPILMAYACAK, ayrı TODO):**
- `effect_size`/`effect_size_and_uncertainty`/`uncertainty_measures` ailesi (§3b) — ayrı bir iyileştirme, `claims_supported`/`evidence` boyutunu etkiler, soundness'i değil.
- `qualitative_rigor.py`'nin benzer katı kuralı ("major = reflexivity yok; örnekleme stratejisi gerekçesiz") — aynı kategori sorunu ama ayrı dosya/ayrı severity sözlüğü, bu planın kapsamı DEĞİL (istenirse ayrı bir takip planı).
- Prompt'un kendisini (quantitative_validity.py brief metnini) değiştirmek — §41b'nin öğrettiği ders: prompt-seviyesi değişikliğin severity üzerindeki etkisi güvenilir şekilde ölçülemiyor. Bu yüzden SADECE deterministik guard'a güveniliyor, prompt'a dokunulmuyor.

## 5. Açık soru — CEVAPLANDI (kod yazmadan önce kontrol edildi, plana kör başlanmadı)

**originality/importance korelasyonları da aynı mekanizmadan mı etkileniyor? HAYIR — farklı, AYRI bir mekanizma, bu planın kapsamı DEĞİL.**

v8 verisinde originality skor dağılımı kontrol edildi: **43/61 (%70) makale TAM SKOR (10.0) alıyor** — soundness'ten (7.75'te saturasyon) DAHA YÜKSEK oranda ama TERS yönde bir saturasyon. Soundness'in sorunu "katı bir kural neredeyse her makalede major tetikliyor, skor aşağı sıkışıyor" — originality'nin sorunu ise "contribution kovasında ('original'/'novel' anahtar kelimeleri, `report_synthesis.py:253-259`) neredeyse hiç ciddi bulgu üretilmiyor, skor tavana sıkışıyor" (bu, §41'in ölçtüğü "originality şişirme +3.39" bulgusuyla tutarlı). Bu **AYRI bir kök neden** — muhtemelen §32'nin guardian bulgusuyla ilişkili (`academic_dimension.py`'nin belirsiz severity tanımı, novelty/katkı iddialarına yeterince eleştirel yaklaşmıyor olabilir) ama bu planın `study_design`-bağlamlı guard'ıyla ÇÖZÜLMEYECEK (methodology kovası değil, contribution kovası; rijit-kural-fazlalığı değil, kritik-değerlendirme-azlığı).

**Karar:** originality bu planın kapsamı DIŞINDA bırakıldı — ayrı bir takip planı gerektirir (muhtemelen `academic_dimension.py`'nin novelty-değerlendirme talimatını güçlendirmek/somutlaştırmak, ya da critic-council'ın novelty eleştirisini daha sert hale getirmek). `importance` (n=5, örneklem küçük) de aynı şekilde bu planın dışında, goldset büyümeden anlamlı değerlendirilemez.

## 7. Test planı

**Adım 1 — TAMAMLANDI, sonuç DÜRÜST OLARAK BEKLENENİN AKSİNE.** v8'in 61 STORED raporuna guard offline uygulandı (`offline_soundness_guard_effect.py`, scratchpad). Saturasyon `7.75`'te 40/61 (%66) → `9.55`'te 37/61 (%61) — **saturasyon NOKTASI değişti ama ORANI neredeyse aynı kaldı, bir sabitten başka bir sabite kaydı.** Daha önemlisi — **gerçek insan-soundness skorlarına karşı Spearman/Pearson korelasyonu ÖLÇÜLDÜ, neredeyse hiç değişmedi:** Spearman -0.0695→+0.0692 (n=29, ikisi de p>0.7, istatistiksel olarak gürültüden ayrılamıyor). **Bu fix soundness-korelasyon problemini ÇÖZMÜYOR.**

**Kök neden (elle doğrulandı, 29 insan-skorlu makalenin TAMAMI incelendi):** "methodology" risk_radar kovasının diğer 2 bileşeni — `design_validity` ve `measurement_validity` — insan soundness skoru 4.0'dan 10.0'a kadar HEMEN HER makalede "info" (boilerplate-pozitif) çıkıyor, gerçek kalite farkını hiç yakalamıyor. `sample_and_power` da benzer şekilde insan skorundan bağımsız, neredeyse her makalede "major" çıkıyordu (context-blind kural). Guard `sample_and_power`'ı düzeltince kovanın SABİT TABANI değişti (7.75→9.55) ama kovanın kendisi HÂLÂ makaleler arası neredeyse hiç varyans taşımıyor — çünkü 3 bileşenin 3'ü de gerçek kaliteyle ilişkisiz bir şekilde neredeyse-sabit.

**Dürüst sonuç:** Bu guard MEŞRU ve DOĞRU bir düzeltme (context-blind, haksız bir cezayı kaldırıyor, guardian 2 tur onayladı, kod tabanına hiçbir zarar vermiyor) — ama TEK BAŞINA soundness'in insan-korelasyonunu düzeltmiyor. Asıl problem daha derin: `design_validity`/`measurement_validity` boyutlarının LLM tarafından nasıl değerlendirildiği (muhtemelen `quantitative_validity.py`'nin bu iki alt-kritere yeterince spesifik/zorlayıcı bir talimat vermemesi — `quantitative_engine.py`'de bu isimler hiç sabit kriter olarak tanımlı değil, LLM'in kendi serbest-metin ürettiği etiketler) AYRI bir araştırma gerektiriyor. **Bu fix'i "soundness'i düzeltti" diye SUNMAK YANLIŞ OLUR — "context-blind bir haksızlığı giderdi, ama asıl korelasyon problemi çözülmedi" diye çerçevelenmeli.**
**Adım 2 — regresyon testleri:** `test_academic_engines.py`'ye yeni testler (guard fonksiyonu + uçtan uca — `_downgrade_ungrounded_citation_findings`'in test desenini birebir taklit ederek: downgrade-oluyor (computational_modeling + confidence>=0.7 + major) / downgrade-olmuyor (study_design zorunlu kümede) / **confidence<0.7 iken downgrade OLMUYOR** (§4a, yeni) / `sample_and_power` DIŞINDAKİ dimension'lara dokunmuyor / critical severity'ye hiç dokunmuyor — bkz. §4b).
**Adım 3 — küçük canlı doğrulama (isteğe bağlı, adım 1 umut verici görünürse):** 3-5 `computational_modeling` makalesi canlı koşulup gerçek Finding metninin/severity'nin beklendiği gibi indiğini doğrulamak (§32'nin PwxYoMvmvy spot-check deseni).
**Adım 4 (opsiyonel, pahalı, sadece adım 1-3 net olumlu sonuç verirse):** tam 61 makale re-run — büyük maliyet, sadece güçlü ön-kanıt varsa gerekçelendirilir.

## 8. Guardian danışması — 1. tur TAMAMLANDI, bu plan revizyonu onun bulgularını yansıtıyor

**Guardian 1. tur (2026-08-13) 3 gerçek hata buldu, hepsi bu plana işlendi:**
1. Hedef dimension adı (`effect_size_and_uncertainty`) doğrulanmadan kopyalanmıştı → §3b'de v8'in gerçek verisiyle düzeltildi, kapsam `sample_and_power`'a daraltıldı.
2. Study_design muaf kümesinin 5/6'sı zaten `_QUANTITATIVE_ENGINE`'e yönlenmiyordu (ölü kod) → §4'te `rubric_registry.py`'nin gerçek routing tablosuyla düzeltildi, "pratikte etkili" vs "savunmacı" ayrımı netleştirildi.
3. Moat/quant.* çakışması hiç kontrol edilmemişti ("muhtemelen yok" varsayımı) → §4b'de gerçekten doğrulandı (şu an çakışma yok, ama kırılgan — kod yorumuyla işaretlenecek).
4. Downgrade hedefi (`moderate`→`minor`) guardian'ın epistemik-belirsizlik vs tür-uyumsuzluğu ayrımı kabul edilerek değiştirildi.

**Guardian 2. tur (2026-08-13):** Yukarıdaki 4 düzeltmenin TAMAMINI bağımsız olarak (kendi Grep/Read'iyle, plana güvenmeden) tekrar doğruladı — tüm sayılar (59/51/7/1, %100/40, %19/21, routing tablosu, satır numaraları) birebir tutarlı çıktı. **1 yeni gerçek eksik buldu:** `rubric.study_design` kendisi deterministik değil, bir LLM sınıflandırma çıktısı (`study_design_confidence` alanı var) — confidence-gating olmadan bu guard "deterministik kanıta dayalı düzeltme" değil "bir LLM'in belirsiz etiketine göre başkasının kararını indirme" olurdu (CLAUDE.md §3.3 ihlali). **Düzeltildi → §4a (yeni):** guard sadece `study_design_confidence >= 0.7` iken çalışacak, altındaysa dokunmayacak. Eşik v8 verisiyle gerekçeli (53 computational_modeling sınıflandırmasının tamamı 0.7-0.9 aralığında, mevcut davranışı bozmuyor) ama YENİ bir v1-default, kod tabanında borç alınan bir emsal yok — bu açıkça belirtildi.

Küçük, ikincil bir nokta da düzeltildi: entegrasyon noktasının citation guard'la "simetrik" olmadığı, küçük bir refactor gerektirdiği (§4 sonu) açıkça yazıldı.

**Plan artık kod yazmaya hazır sayılıyor** — guardian 2. tur onayı: "moat etkisi nötr-hafif güçlendiriyor, kopyalanabilirlik riski düşük" (rakip karşılaştırması: Stanford'un tek-prompt writer→critic→editor döngüsü bu tür çalışma-türüne-duyarlı severity kalibrasyonu yapmıyor — gerçek bir fark noktası). Kod yazılırken §4a'nın confidence-gating'i ATLANMAYACAK.
