# Plan: Referans-bölme (`_BARE_YEAR_END_RE`) ve başlık-çıkarma (`extract_authors_year_title`) hatalarını düzeltmek

**Tarih:** 2026-08-16
**Durum:** UYGULANDI (guardian onayı sonrası) — sonuçlar §8'de.
**Kaynak:** `PDF_PIPELINE_CALISMA_GUNLUGU.md` §63-66 (canlı demo koşumunda bulundu, 61-goldset'te ölçüldü — %89/54 makale/230 girdi, `eval/review/results/reference_splitting_bug_2026-08-15/`).
**Guardian önceki değerlendirmesi:** "Acil" — `citation_integrity` moat boyutunun var olma sebebi (deterministik, insan-doğrulanabilir sahtecilik tespiti) şüpheli hale geldi.
**Karar verici:** Kenan.

---

## 1. Kök neden (kanıtlı, A-seviye — 2 gerçek örnekle doğrulanmış)

İki ayrı, art arda gelen hata:

### 1a. Girdi-sınırı kaçırma (`engine/ingestion/common.py:81-83`, `_BARE_YEAR_END_RE`)

```python
_BARE_YEAR_END_RE = re.compile(
    r"(?<!\()\b(?:19\d{2}|20\d{2})[a-z]?\.(?=\s+[A-ZÀ-ÖØ-Þ]|\s*$)"
)
```

Bu regex bir referans girdisinin SONUNU `"...YIL."` + BÜYÜK HARFLE başlayan bir sonraki kelime (yeni yazar adı) kalıbıyla arıyor. Ama ICLR/NeurIPS-tarzı kaynakçalar yıldan hemen sonra bir `"doi: ..."` / `"URL ..."` / bazen `"ISBN ..."` ek-bilgi satırı ekliyor — örn.:

> `"...In ACL, pp. 33–43, 2016. doi: 10.18653/v1/P16-1004. URL http://arxiv.org/abs/1601.01280. Gottlob Frege..."`

`"2016."`'dan sonra gelen kelime `"doi"` KÜÇÜK harfle başlıyor → regex EŞLEŞMİYOR → `group_reference_entries()` (`common.py:318-403`, strateji 3, satır 386-398) bu ve bir sonraki (hatta bazen üçüncü) referansı TEK bir "raw" girdide birleştiriyor.

### 1b. Birleşik girdiden yanlış başlık çıkarma (`common.py:411-448`, `extract_authors_year_title`)

Girdi zaten (1a yüzünden) birleşik geldiğinde, Vancouver-stili ayrıştırıcı (`body.split(".")`, satır 441) URL'lerdeki noktaları (`"arxiv.org"`, `"1409.1259v2.pdf"`) VE kısaltılmış yazar adlarındaki noktaları (`"Ronald J."`) da alan-sınırı sanıyor. Sonuç: gerçek başlık yerine bir URL parçası (`"org/pdf/ 1409"`) ya da yazar-adı parçası (`"Williams and David Zipser"`) `title` alanına yazılıyor.

**Downstream etki:** `api/services/review_citation_service.py:356` (`if ref.title:`) — DOI doğru çözülüyor (OpenAlex'te doğru esere karşılık geliyor) ama motor bu YANLIŞ `title`'ı OpenAlex'teki DOĞRU başlıkla kıyaslayıp benzerlik düşük çıkınca (`ratio < _TITLE_CONFLICT_THRESHOLD`, satır 360) `status="fabricated"` diyor (satır 396-410) — **DOI doğru, sadece ayrıştırılan başlık çöp olduğu için YANLIŞ-POZİTİF.**

**Doğrulanmış 2 örnek** (`peerread:iclr2017-400` idx 4/21, `peerread:iclr2017-487` idx 7/26/29/31 — 6 örnek toplam, hepsi aynı desen): `"ISBN 978-1-4673-8947-1"`, `"34th Annual Conference of IEEE, pp"`, `"URL http://dl"`, `"Smithson, Kaushik Boga, Arash Ardakani, Brett H"`, `"org/pdf/ 1409"`, `"Williams and David Zipser"` — HİÇBİRİ gerçek bir başlık değil.

**Yaygınlık (61-goldset, offline, LLM'siz, tekrar üretilebilir — `eval/review/results/reference_splitting_bug_2026-08-15/`):** 54/61 makale (%89), 230 şüpheli girdi.

## 2. Önerilen düzeltme A: `_BARE_YEAR_END_RE`'yi doi/URL/ISBN ek-bilgi tümcelerini "atlayacak" şekilde genişletmek

**Neden basitçe "doi:/URL de bir sınır sayılsın" YETMEZ:** `"2016."` VE `"doi: ..."` arasına da bir sınır koymak, DOI/URL bilgisini AİT OLDUĞU referanstan KOPARIR (o bilgi önceki referansın parçası, yeni bir girdi değil). Doğru çözüm: `"YIL."`'dan sonra gelen doi/URL/ISBN ek-tümcelerini "geç", GERÇEK bir sonraki yazar adı (büyük harf) ile karşılaşana kadar sınır ARAMA.

**Önerilen regex (kanıtlanmış 6 örnekle motive edildi, mükemmellik İDDİA EDİLMİYOR — bkz §5 test planı):**

```python
_BARE_YEAR_END_RE = re.compile(
    r"(?<!\()\b(?:19\d{2}|20\d{2})[a-z]?\."
    r"(?:\s+(?:doi:\s*\S+|URL\s+\S+|ISBN\s+\S+))*\."?  # bkz not
    r"(?=\s+[A-ZÀ-ÖØ-Þ]|\s*$)"
)
```

**Not (dürüstçe belirtilmeli):** Yukarıdaki taslak regex'in TAM sözdizimi (opsiyonel tekrar eden grup + trailing nokta backtracking davranışı) kodda yazılırken gerçek 6 örnek üzerinde elle test edilecek — bu plan aşamasında NİYET/YAKLAŞIM sunuluyor, regex'in son hali guardian onayı + gerçek testle netleşecek. `doi:`/`URL`/`ISBN` önek listesi KAPALI DEĞİL — 61-goldset taramasında başka ek-bilgi önekleri (örn. `"arXiv:"`, `"pp. N-M,"`) bulunursa listeye eklenecek, ilk sürüm bu 3 önekle (gözlemlenen tüm örnekleri kapsıyor) başlıyor.

## 3. Önerilen düzeltme B: `extract_authors_year_title`'ın Vancouver-split'ini URL/DOI/kısaltma noktalarına karşı sağlamlaştırmak

**3a. URL/DOI maskeleme:** `body.split(".")`'dan ÖNCE, metindeki URL (`https?://\S+`) ve DOI (`extract_doi()`'nin zaten kullandığı `_DOI_RE` deseni) alt-dizeleri geçici, nokta İÇERMEYEN yer tutucularla (örn. `\x00URL0\x00`) değiştirilir; bölme İŞLEMİNDEN SONRA orijinal metin geri konur (sadece bölme NOKTALARI için maskeleme — çıkan `title`/`authors` alanlarına orijinal metin yazılır).

**3b. Kısaltılmış-isim noktası koruması:** Tek büyük harf + nokta (`"J."`, `"A."` — yazar orta-adı kısaltması) kalıbı, ÖNCESİNDE boşluk/satır-başı varsa, bölme noktası SAYILMAZ. Öneri: `body.split(".")` yerine `re.split(r"(?<!\s[A-Z])\.\s*", body)` (negatif lookbehind — "boşluk+büyük-harf"den hemen sonra gelen nokta bölme noktası değil).

**Dürüst sınır:** Bu, tüm kısaltma-noktası biçimlerini (`"A.B."`, iki harfli kısaltmalar gibi) kapsamayabilir — kapsamlı bir NLP cümle-bölücü DEĞİL, gözlemlenen gerçek örneklere (`"Ronald J. Williams"`) dayanan hedefli bir düzeltme. §5'teki offline test bunun pratik etkisini ölçecek.

## 4. Güvenli-başarısızlık davranışı (HK-7 uyumu) — kısmen ZATEN VAR, doğrulandı

`common.py:414`'ün kendi KANUNU: *"tahmin yok. Net bir kalıp yoksa alan None / boş bırakılır."* Ama Vancouver dalı (`common.py:442-447`) bunu İHLAL ediyor — `parts[1]` sadece 8 karakterden UZUNSA `title` olarak atanıyor, İÇERİĞİNİN gerçekten bir başlığa BENZEYİP benzemediği hiç kontrol edilmiyor.

**Önerilen ek koşul:** `title` adayı, ÖNCE `_split_author_block()`'un "yazar listesi gibi görünüyor mu" testinden GEÇERSE (yani kendisi bir yazar-listesi gibiyse) VEYA bilinen çöp-kalıplara (`^(URL|ISBN|pp\.|https?://|org/|www\.)` gibi) uyuyorsa, `title=None` bırakılır — tahmin edilmez.

**KRİTİK, ÖNCEDEN DOĞRULANMIŞ kanıt (bu planı GÜVENLİ kılan şey):** `api/services/review_citation_service.py:356` (`if ref.title:`) ve satır 449 (`return _resolve_via_work(ref, work, matched_by="DOI")`) — **`title=None`/boş olduğunda downstream kod ZATEN GÜVENLİ**: fabrikasyon-karşılaştırma bloğu (356-410) hiç ÇALIŞMIYOR, DOI TEK BAŞINA `_resolve_via_work()`'e gidiyor (satır 250-276) — bu fonksiyon SADECE `is_retracted` bayrağına bakıyor, HİÇBİR başlık-kıyaslaması yapmıyor. **Yani `extract_authors_year_title()`'ı `title=None` döndürmeye zorlamak, downstream'de YENİ bir kod değişikliği GEREKTİRMİYOR — mevcut, zaten-güvenli yol otomatik devreye giriyor.** Bu, planın en düşük-riskli parçası.

## 5. Test planı

1. **Birim testler** (`tests/unit/test_ingestion.py`): §1'in 6 gerçek örneği (idx 4/21 iclr2017-400, idx 7/26/29/31 iclr2017-487) — düzeltme SONRASI doğru başlığın çıkarıldığı (ya da makul biçimde `None` bırakıldığı, çöp string DEĞİL) doğrulanacak. Ayrıca mevcut `test_ingestion.py` regresyon testleri (40/40+) korunacak.
2. **61-goldset'in TAMAMI için offline önce/sonra karşılaştırması** (`eval/review/results/reference_splitting_bug_2026-08-15/measure_merged_ref_bug.py`'nin devamı/genişletmesi olarak) — düzeltme SONRASI:
   - Kaç girdi artık "birleşik-görünümlü" DEĞİL (230'dan kaça düştü)?
   - Kaç `status="fabricated"` etiketi kalkıyor/`not_found_in_index`'e ya da `resolved`'a dönüyor (yeniden çözümleme gerektirir — LLM'siz ama OpenAlex ağ çağrısı gerektirir, `review_citation_service.resolve_all()` ile)?
   - `peerread:iclr2017-400`'ün VE `peerread:iclr2017-487`'nin `fabricated` sayısı düzeltme sonrası ne oluyor — 0'a mı düşüyor, yoksa GERÇEK bir sahtecilik kalıntısı mı var?

   **KRİTİK DÜZELTME (plan yazıldıktan HEMEN sonra doğrulandı, `eval/review/goldset.json`):** `peerread:iclr2017-487`'nin gerçek insan kararı da **"accept"** çıktı (ICLR 2017, 6 hakem, ort. 6.3/9 — `iclr2017-400` ile AYNI durum). Yani bilinen HER İKİ "count≥2 fabricated" test vakası da GERÇEKTE kabul edilmiş makaleler — `iclr2017-487`'de motorun ürettiği `verdict=reject` (§1'in "gate doğru tetiklendi" örneği sanılan vaka) muhtemelen BAŞTAN YANLIŞTI, sadece "gate'in kendi iç mantığı tasarlandığı gibi çalıştı" anlamında "doğru"ydu — GERÇEK insan kararıyla KIYASLANMAMIŞTI. **Bu, referans-bölme düzeltmesinin önceliğini DAHA DA güçlendiriyor: elimizde, mevcut `citation_integrity.fabricated` sayacının gerçek sahteciliği doğru tespit ettiğini gösteren TEK bir örnek yok, buna karşılık İKİ örnekte gerçek insan-kabul edilmiş makaleleri yanlış cezalandırdığı (biri fiilen reddedilerek, biri neredeyse) kanıtlı.**
3. **Goldset'in geri kalan (etkilenmeyen) makalelerinde regresyon YOK** doğrulanacak — düzeltme SADECE gözlemlenen çöp-başlık kalıplarını hedefliyor, gerçek/geçerli başlıkları BOZMAMALI.
4. **YENİ (guardian bulgusu, onay turunda eklendi):** §4'teki çöp-kalıp filtresinin (URL/ISBN/yazar-listesi-benzeri kontrolü) kaç ÖNCEDEN DOĞRU çıkarılmış başlığı da yanlışlıkla `None`'a çevirdiği AYRICA ölçülecek — "fabricated azaldı mı" ve "regresyon var mı" yeterli değil, filtrenin kendi YANLIŞ-NEGATİF oranı (geçerli title'ları gereksiz yere None'a çeviren) ayrı bir metrik olarak raporlanacak.
5. **YENİ (guardian bulgusu, ÖNEMLİ çerçeveleme notu):** Düzeltme SONRASI 61-goldset yeniden ölçüldüğünde, `citation_integrity.fabricated`'ın GERÇEK bir sahteciliği doğru yakaladığı EN AZ BİR örnek bulunup bulunmadığı AÇIKÇA raporlanacak. **Eğer bulunamazsa** (mimari var ama ampirik olarak sıfır doğrulanmış true-positive) — bu, "Fix A ertelendi" notuyla ÖRTÜLMEYECEK, `citation_integrity`'nin şu an "moat mimarisi var" ile "moat mimarisi çalıştığı kanıtlandı" arasındaki farkın AYRI ve AÇIK bir sınırlama olarak (devralma özeti + iş günlüğü) belgelenmesi gerekecek.

## 6. §63-64'teki moat-gate severity düzeltmesiyle (Fix A) ilişki

**Bu düzeltme (referans-bölme/başlık-çıkarma) Fix A'DAN ÖNCE gelmeli, birlikte ELE ALINMAMALI.**

Gerekçe: Fix A'nın (`docs/plans/CITATION_MOAT_GATE_SEVERITY_ASYMMETRY_2026-08-15.md`) TÜM önermesi `evidence.citation_integrity.fabricated` sayısının GÜVENİLİR bir sinyal olduğu varsayımına dayanıyordu — bu varsayım şu an ÇÖKMÜŞ durumda (§65-66). Bu planın (referans-bölme) düzeltmesi UYGULANIP 61-goldset YENİDEN ölçülmeden, Fix A'nın "count≥2 → reject" mantığının hâlâ anlamlı olup olmadığı BİLİNEMEZ — belki düzeltme sonrası `iclr2017-400`/`iclr2017-487`'nin `fabricated` sayıları 0'a düşecek (o zaman Fix A'nın orijinal kanıtı tamamen ORTADAN KALKMIŞ olur, YENİ gerçek örnekler aranmalı), belki bir kısmı GERÇEK kalacak (o zaman Fix A'nın gerekçesi GÜÇLENMİŞ olur, temiz veriyle).

**Sıra: (1) bu plan → guardian onayı → kod → 61-goldset yeniden ölçüm, (2) SONRA Fix A'nın planı (varsa) TEMİZ veriyle yeniden değerlendirilir.**

## 7. Kapsam dışı / ayrı TODO'lar

1. `_SYSTEMIC_FABRICATION_COUNT_THRESHOLD=2`'nin kalibrasyonu (Fix A planının kendi TODO'su) — bu planın kapsamı DIŞINDA, §6'daki sıralamaya göre SONRA ele alınacak.
2. §41'in n=4 moat-doğruluk ölçümü ve TÜM geçmiş `citation_integrity` canlı-koşum sonuçlarının bu düzeltmeyle YENİDEN değerlendirilmesi — büyük, ayrı bir iş, bu planın kapsamı dışında ama AÇIKÇA not edilmeli (Ömer'e/rapora "bu ölçümler eski koda göre, yeniden doğrulanmadı" caveat'i sürdürülmeli).
3. GROBID'in (şu an devre dışı) etkinleştirilmesi — yapısal/gerçek bir kaynakça ayrıştırıcısı olarak bu TÜM sınıf hatayı (heuristic regex kırılganlığı) kökten çözebilir, ama ayrı bir altyapı/maliyet kararı, bu planın kapsamı DIŞINDA.

---

## 8. Sonuçlar (uygulama sonrası, 2026-08-16)

**Guardian onayı:** Verildi (net itiraz yok, tüm teknik iddialar doğrulandı — "moat etkisi nötr, HK-7 disiplinini güçlendiriyor" değerlendirmesi). 2 iyileştirme istendi ve plana eklendi (§5.4-5.5): çöp-filtrenin yanlış-negatif oranı ölçülecek, düzeltme sonrası bile gerçek true-positive bulunamazsa bu ayrı/açık bir sınırlama olarak raporlanacak.

**Uygulanan kod (`engine/ingestion/common.py`):**
- `_BARE_YEAR_END_RE` genişletildi — `doi:`/`URL`/`ISBN` ek-tümcelerini atlayıp gerçek sonraki yazara kadar arıyor.
- `_split_on_field_periods()` (yeni) — URL/DOI aralıklarındaki VE kısaltılmış-isim baş-harfi noktalarını (`"Ronald J."`, dizi başında `"M."` dahil) alan-sınırı saymayan bölme fonksiyonu, `extract_authors_year_title`'ın Vancouver dalında `.split(".")` yerine kullanılıyor.
- `_GARBAGE_TITLE_PREFIX_RE` (yeni) — URL/ISBN/pdf/org/doi/digit-ordinal önekli adaylar `title`'a YAZILMIYOR, `None` bırakılıyor (HEM Vancouver HEM APA dalında).

**Test sonuçları:**
1. **Birim testler:** 4 yeni test (`tests/unit/test_ingestion.py`) — gerçek 6 örneğin 2'si (idx4/idx21) + 6 parametrized çöp-kalıp senaryosu. **50/50 PASS** (41 mevcut + 9 yeni, regresyon yok).
2. **61-goldset offline title-etki ölçümü** (`scratchpad/measure_title_fix_impact.py`, eski koddan bilinen 77 çöp-başlık karşılaştırıldı): **77 → 0 hâlâ-çöp.** 39 (%51) tamamen doğru başlığa döndü (gerçek makaleler: "Long short-term memory", "Deep residual learning for image recognition", "Neural machine translation by jointly learning to align and translate" — daha önce "uydurma atıf" diye işaretlenmiş ÜNLÜ, GERÇEK makaleler), 38 (%49) güvenli `None` oldu.
3. **Canlı OpenAlex doğrulaması (6/6 orijinal "fabricated" vaka, gerçek ağ çağrısı):**

| Vaka | Sonuç |
|---|---|
| iclr2017-400 idx4 | ✅ `resolved` (düzeldi) |
| iclr2017-400 idx21 | Hâlâ `fabricated` — AMA artık başlık DOĞRU, DOI gerçekten başka bir esere işaret ediyor (muhtemelen kaynak makalenin kendi bibliyografya hatası/kitap-bölümü DOI karışıklığı — **artık gürültü değil, potansiyel gerçek bir bulgu**). |
| iclr2017-487 idx7 (Eyeriss) | ✅ `resolved` (düzeldi) |
| iclr2017-487 idx26 (IECON) | ✅ `resolved` (düzeldi) |
| iclr2017-487 idx29 (ISAAC) | ✅ `resolved` (düzeldi) |
| iclr2017-487 idx31 (Smithson) | Hâlâ `fabricated` — AMA artık başlık DOĞRU; DOI yanlış çünkü bir SONRAKİ referansın (Szegedy, "Going deeper with convolutions") DOI'si araya sıkışan bir sayfa-numarası artığı ("13") yüzünden yanlış girdiye yapışmış — **bu planın kapsamı DIŞINDA, YENİ ve AYRI bir entry-boundary hatası** (stray footnote/page-number, doi:/URL/ISBN dışı bir kalıp). |

**Dürüst nihai sonuç: 4/6 orijinal vaka TAMAMEN düzeldi (artık "fabricated" değil). 2/6 hâlâ "fabricated" ama İKİSİ DE FARKLI, YENİ nedenlerle — biri muhtemelen GERÇEK bir bulgu (kaynak makalenin kendi DOI hatası), diğeri YENİ keşfedilen, bu planın kapsamı dışında ayrı bir entry-boundary hatası (sayfa-numarası artığı).** §5.5'in gerektirdiği "en az bir gerçek true-positive var mı" sorusuna kısmi bir cevap da bulundu: idx21 artık GERÇEK bir sinyal olabilir (temiz veriyle, insan kontrolü gerektirir) — ama bu KESİN doğrulanmadı (kitap-bölümü DOI ambiguity de olabilir).

**Guardian'ın istediği önemli çerçeveleme notu (uygulandı):** Bu fix, `citation_integrity`'nin "gerçek sahteciliği doğru yakaladığı kanıtlanmış" hale geldiği anlamına GELMİYOR — sadece BİLİNEN parsing-kaynaklı yanlış-pozitifleri temizledi. "Moat mimarisi var" ile "moat mimarisi çalıştığı kanıtlandı" arasındaki fark hâlâ AÇIK, ayrı bir konu (bkz. devralma özeti güncellemesi).

**Yeni, kapsam-dışı TODO (bu oturumda bulundu):** Sayfa/dipnot-numarası artıklarının (örn. "13 C. Szegedy...") da `_BARE_YEAR_END_RE`'nin entry-sınırı tespitini bozduğu — ayrı, gelecekteki bir düzeltme konusu.

**Commit:** Kod + testler + bu plan güncellemesi tek commit'te.
