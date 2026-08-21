# Plan: "Seni geride tutan boyut" — hazırlık puanının hemen altında sınırlayıcı-boyut vurgusu

**Tarih:** 2026-08-16
**Durum:** UYGULANDI (Kenan onayı sonrası) — sonuçlar §5'te.
**Kaynak:** Kenan'ın bu oturumdaki isteği — "10 boyut skorundan hangisi genel hazırlık puanını en çok geride tutuyor, bunu 'seni geride tutan bu, çünkü X' diye somut göster."
**Guardian gerekmiyor** — saf sunum katmanı, motor/rubric/skorlama mantığına dokunmuyor (DOCX export ve öncelik-listesi kararlarıyla aynı gerekçe).
**Karar verici:** Kenan.

---

## 1. Araştırma sonucu (kanıtlı, A-seviye)

### 1.1 Veri zaten var, backend değişikliği GEREKMİYOR
`report.dimension_scores: list[DimensionScore]` — her biri `key` (10 sabit `DimensionKey`), `score` (1-10), **`rationale: str`** (`api/models/review.py:309-314`). `rationale` alanı ZATEN "çünkü X" metni — yeni bir açıklama üretmeye gerek yok.

### 1.2 Kritik dürüst sınır — `overall_readiness_score`'un GERÇEK kaynağı `dimension_scores` DEĞİL
`engine/academic/report_synthesis.py:616-620`: `readiness = mean(risk_radar'daki DEĞERLENDİRİLMİŞ skorlar)` — düz/ağırlıksız ortalama, **`dimension_scores`'tan değil `risk_radar`'dan** hesaplanıyor. (Not: aynı dosyanın 98. satırındaki yorum "severity-ağırlıklı" diyor ama gerçek kod düz ortalama — küçük bir yorum/kod tutarsızlığı, bu planın kapsamı dışında, ayrıca not düşülüyor.)

`dimension_scores` ile `risk_radar` İKİ AYRI boyut sözlüğü kullanıyor (`DimensionKey` 10 sabit değer vs. risk_radar'ın serbest string'i: contribution/literature/methodology/evidence/citation/statistics/ethics/reproducibility/writing/venue_fit). `apply_deterministic_dimension_scores()` (`report_synthesis.py:715-739`) bu ikisini SADECE 7 boyutta köprüler (`_DIMENSION_KEY_TO_RISK`, satır 704-712: citation_integrity↔citation, statistical_consistency↔statistics, coverage_completeness↔literature, clarity↔writing, soundness↔methodology, claims_supported↔evidence, originality↔contribution) — risk_radar o boyutu GERÇEKTEN değerlendirdiyse (`score != None`), `dimension_scores[key].score` risk_radar skorunun ölçeklenmiş hali (`1 + score/100*9`) ile DEĞİŞTİRİLİR, `rationale` de risk_radar'ın `why_it_matters`'ını içerecek şekilde güncellenir (`"Deterministik (risk_radar/X...): {why_it_matters} [LLM'in kendi gerekçesi: ...]"`).

**Sonuç (Kenan'a açıkça belirtilmeli):**
- Kalan **3 boyut** (`importance`, `community_value`, `contextualization`) risk_radar'a HİÇ bağlı değil — SADECE LLM'in serbest yargısı, `overall_readiness_score`'u hiç etkilemiyor.
- risk_radar'da readiness'i etkileyen ama `dimension_scores`'ta HİÇ karşılığı olmayan boyutlar da var (`ethics`, `reproducibility`, `venue_fit`).
- **"En düşük `dimension_scores` değeri" → "seni geride tutan bu" demek, iyi bir YAKLAŞIK gösterge ama `overall_readiness_score`'un matematiksel olarak KANITLANMIŞ tek/baskın nedeni DEĞİL.** Gerçek nedensellik (risk_radar'ın kendisi) farklı bir sözlük kullanıyor ve kısmen dimension_scores'a hiç yansımıyor.

### 1.3 Şu an dimension_scores V2 raporda HİÇ görünmüyor
`ReviewReportView.tsx`'te `dimension_scores` SADECE `V1Report`'ta render ediliyor (`DimensionRow` listesi) — `VerdictCockpit`/V2 akışında (`grep` doğrulandı) HİÇ kullanılmıyor. Bu callout, V2 raporda dimension_scores'un ilk kez görüneceği yer olacak.

## 2. Önerilen yaklaşım

**Hesaplama:** `dimension_scores` içinden `min(score)` olan boyut = "sınırlayıcı boyut" (Kenan'ın sorduğu 2 seçenekten biri — "en düşük skor" — mevcut mimariye göre daha basit VE daha dürüst: "en çok etki eden" alternatifi §1.2'de gösterildiği gibi `overall_readiness_score`'un GERÇEK formülüne (risk_radar) bağlı, `dimension_scores` üzerinden matematiksel olarak doğru hesaplanamaz).

**Berabere durum (tie-break, deterministik):** Birden fazla boyut aynı minimum skoru paylaşırsa:
1. Önce §1.2'deki 7-radar-bağlantılı boyutlardan biri mi (deterministik/kanıta-dayalı gerekçe) — bu tercih edilir.
2. Hâlâ berabereyse `DimensionKey`'in şema sırasındaki ilk key (`api/models/review.py:79-92`'deki sabit sıra) — stabil, testable.

**UI metni (dürüst çerçeve, Kenan'a taslak):** *"Seni en çok [boyut adı] geride tutuyor (X/10)"* + `rationale` metni altında, ["Değerlendirilen 10 boyut arasında" gibi bir kapsam-belirten ibare — "TEK sebep" ya da "asıl neden" gibi aşırı-iddialı dil KULLANILMAYACAK, §1.2'deki dürüst sınır gereği].

**Yerleşim:** Katman 1'de, `ReadinessLine` (hazırlık puanı kartı, `ReviewReportView.tsx:322-359`) bileşeninin HEMEN ALTINA — Kenan'ın "sadece 84/100 gösterip bırakmak yerine" isteğiyle birebir örtüşüyor, kullanıcı puanı görür görmez nedenini de görür.

**Bileşen:** Yeni `LimitingDimensionCallout({ dimensionScores })` — `DIMENSION_LABELS` (zaten import edilmiş TR etiket sözlüğü, `ReviewReportView.tsx`) ile boyut adı, skor, `rationale` gösterilir. `ActionItemCard`/`ReadinessLine` ile tutarlı kart stili.

**Boş durum:** `dimension_scores.length === 0` → callout SESSİZCE render edilmez (Katman 1 zaten yoğun; boş-veri notu eklemek gürültü olur — `TopFatalRisks`/`RiskDrillSection`'ın EmptyNote deseninden BİLİNÇLİ sapma, gerekçe: bu tamamlayıcı bir vurgu, ana içerik değil).

**Kapsam:** Sadece V2 (`VerdictCockpit`). V1Report zaten TÜM `dimension_scores`'u tablo halinde gösteriyor (`DimensionRow`) — en düşük satırı vurgulamak (örn. kenarlık/renk) ayrı, küçük bir takip işi olabilir, bu planın kapsamı DIŞINDA (V1 giderek daha az kullanılıyor, öncelik değil).

## 3. Test planı

`web/src/components/review/ReviewReportView.test.tsx`'e (mevcut `REPORT_V2_DEMO` fixture'ı `soundness=6.2` (min) + `citation_integrity=7.1` içeriyor, `report-v2-demo.ts:39-42`):
1. Callout render ediliyor, "Yöntem sağlamlığı" (soundness'in TR etiketi) + skor + `rationale` metni ("Güç analizi ve örneklem gerekçesi eksik.") görünüyor.
2. `dimension_scores: []` override edilmiş varyantla → callout HİÇ render edilmiyor (crash yok).
3. Tie-break testi: 2 boyut aynı min skoru paylaşan bir varyant — 7-radar-bağlantılı olan tercih ediliyor mu.
4. Mevcut testlerin regresyon YAŞAMADIĞI (yeni bileşen mevcut testid'lerle çakışmıyor).

## 4. Kapsam dışı

1. DOCX export'a aynı vurgunun eklenmesi — ayrı, küçük takip işi, sessizce atlanmayacak.
2. V1Report'ta en-düşük-skor satırının vurgulanması — ayrı, düşük öncelikli takip işi.
3. `report_synthesis.py:98`'deki "severity-ağırlıklı" yorum/kod tutarsızlığının düzeltilmesi — bu planın kapsamı dışında, ayrıca not düşüldü.
4. 3 LLM-only boyutun (`importance`/`community_value`/`contextualization`) risk_radar'a bağlanması ya da risk_radar'ın ethics/reproducibility/venue_fit'inin dimension_scores'a eklenmesi — bu, `overall_readiness_score`'un GERÇEK nedenini dimension_scores üzerinden tam-doğru göstermenin YEGÂNE kalıcı çözümü olurdu ama büyük, ayrı bir motor işi — bu planın kapsamı DIŞINDA, açıkça not ediliyor.

## 5. Sonuçlar (uygulandı, 2026-08-16)

**Kod:** `ReviewReportView.tsx` — yeni `LimitingDimensionCallout` + `findLimitingDimension` (min-skor + 2-adımlı deterministik tie-break) + `_RADAR_LINKED_DIMENSIONS`/`DIMENSION_KEY_ORDER` sabitleri. `ExecutiveVerdictHero`'ya `dimensionScores` prop'u eklendi, `ReadinessLine`'ın hemen altına bağlandı (plan §2'deki yerleşim kararı).

**Uygulama sırasında bulunan/düzeltilen regresyon:** İlk test koşumunda 3 MEVCUT test kırıldı — yeni callout'un "Yöntem sağlamlığı" metni (soundness'in TR etiketi), risk-radar satırının AYNI metniyle çakıştı (`screen.getByText("Yöntem sağlamlığı")` artık 2 eleman buluyordu, "multiple elements" hatası). Kök neden benim yeni bileşenimdi ama düzeltme testler tarafında doğruydu: 3 testteki bare `screen.getByText(...)` çağrısını `within(screen.getByTestId("risk-radar")).getByText(...)`'e scope ettim — kapsamları zaten "risk-radar satırına tıkla" anlamına geliyordu, artık gerçekten öyle. Metni sadeleştirip çakışmayı "gizlemek" yerine testleri doğru kapsamına oturttum.

**Testler:** 3 yeni test (min-skor+rationale gösterimi, boş-dizi'de render edilmeme, berabere durumda radar-bağlantılı boyutun önceliği) + yukarıdaki 3 test düzeltmesi.

**Regresyon:** `web/src/components/review/` — **38/38 PASS** (8 dosya). `tsc --noEmit` temiz.
