# Plan: Atıf bütünlüğü sonuçlarını grafikle görselleştirmek

**Tarih:** 2026-08-17
**Durum:** UYGULANDI (Kenan onayı sonrası) — sonuçlar §7'de.
**Kaynak:** Kenan'ın bu oturumdaki isteği — doğrulandı/indekste bulunamadı/geri çekilmiş sayılarını pasta/çubuk grafikle göster.
**Guardian gerekmiyor** — saf sunum katmanı, motor/skorlama mantığına dokunmuyor.
**Karar verici:** Kenan.

---

## 1. Veri yapısı — zaten tam, hiç backend değişikliği gerekmiyor

`EvidencePack.citation_integrity: CitationIntegritySummary` (`api/models/review.py:219-232`) — `total`/`resolved`/`not_found_in_index`/`fabricated`/`retracted` (+ `provider_errors`, gizli alt-küme). Frontend zaten bunu `CitationIntegrityBadge`'de (`ReviewReportView.tsx:~1322-1412`) 4 renkli kutucuk (icon+sayı+etiket) olarak gösteriyor — **status renkleri ZATEN doğru atanmış:** resolved→`var(--color-ok)`, not_found_in_index→`var(--color-ink-mute)` (nötr — HK-3 "yok≠uydurma" kuralı gereği UYARI DEĞİL), retracted→`var(--color-warn)`, fabricated→`var(--color-danger)`.

## 2. `dataviz` skill araştırması (yüklendi, uygulandı)

**Form kararı — çubuk, pasta DEĞİL:** Skill'in "choosing-a-form" tablosu "Parça-bütün" (part-to-whole) işi için **stacked bar** öneriyor, pasta önerilmiyor. `anti-patterns.md` açıkça: *"❌ Yakın değerleri kıyaslamak için donut/pasta → ✅ Çubuk."* Atıf sayıları arasında (örn. fabricated=1 vs retracted=2) hassas kıyaslama önemli — pasta bunu bulanıklaştırır, çubuk net gösterir.

**Renk kararı — yeni palet İCAT EDİLMİYOR:** Bu veri "status" semantiği taşıyor (iyi/nötr/uyarı/kritik), skill'in "status palette" kuralına uyuyor: *"Status colors are reserved... never reused for 'series 4', ship with icon+label."* Mevcut `CitationIntegrityBadge` ZATEN bunu doğru yapıyor (§1) — yeni çubuk AYNI 4 CSS-var token'ını reuse eder, yeni bir palet/validator turu GEREKMİYOR (mevcut token'lar zaten üretimde, kanıtlanmış).

**Mark spec (skill `marks-and-anatomy.md`):** segmentler arası 2px surface-gap, çubuk ince (≤24px), köşeler baseline'da kare/uçlarda 4px yuvarlak. **Üstte doğrudan sayı etiketi YOK** — mevcut tile grid'de sayılar zaten var, tekrar etmek gürültü olur (skill: "label selectively, never a number on every point"). Hover'da native `title` tooltip'i (basit, yeterli — stilize tooltip istenirse ayrı, küçük bir takip).

**Legend/tablo — yeni component YAZILMIYOR:** Mevcut tile grid (icon+sayı+etiket) ZATEN skill'in "legend always present for ≥2 series" + "a table view exists" kurallarını karşılıyor. Çubuk, tile grid'in ÜSTÜNE eklenir, tile grid AYNEN KALIR (silinmiyor) — çubuk bir "en üstte özet", tile'lar "detay/tablo" rolünü sürdürür.

## 3. Kütüphane kararı — YENİ BAĞIMLILIK YOK

`d3` (^7.9.0) proje bağımlılığı AMA sadece pre-pivot ("papermind-app" dönemi) karmaşık görselleştirmelerde kullanılıyor (`CitationGraphCard.tsx`, `GapHeatmapCard.tsx`, `NetworkMapCard.tsx`, `UMAPClusterCard.tsx` — kendi "zone" renk sistemleri var, Arbitra'nın CSS-var tasarım diliyle UYUMSUZ, incelendi `GapHeatmapCard.tsx:27-41`). 4 segmentlik STATİK bir yatay çubuk için d3'ü ithal etmeye gerek yok — düz SVG/flex-div ile ~30 satırda yazılabilir. **Sıfır yeni bağımlılık, mevcut ağır d3 import'unu da bu dosyaya BULAŞTIRMIYORUZ** (bundle-boyutu avantajı, "daha kolayı" kontrolü).

## 4. Uygulama

Yeni bileşen `CitationIntegrityBar({ summary })` — `ReviewReportView.tsx`, `CitationIntegritySection`/`CitationIntegrityBadge`'in (aynı dosya) hemen üstüne. Segment genişlikleri `count/total*100%` (flex-basis ya da SVG rect width), 2px surface-gap (`gap-0.5` + arka plan rengi), her segment `title="{label}: {count}"`.

**Dürüst boş durum:** `total === 0` ise çubuk render edilmez (mevcut tile grid zaten "0 kaynak incelendi" diyor, tekrar bir boş-çubuk göstermek gürültü).

## 5. Test planı

1. Segment genişlikleri orantılı mı (örn. resolved=8/10 → %80 width).
2. `total === 0` → çubuk render edilmiyor, tile grid'de regresyon yok.
3. Her segment'in `title` attribute'ünde doğru etiket+sayı var mı.
4. Mevcut `ReviewReportView.test.tsx` (41+ test) regresyon yaşamıyor.

## 6. Kapsam dışı

1. `provider_errors`'ın ayrı gösterimi — şu an tile grid'de de gösterilmiyor, bu planın kapsamı dışında.
2. DOCX export'a aynı grafiğin eklenmesi — `report_export_service.py`'de SVG/chart yazmak ayrı, küçük bir takip.
3. Stilize (native `title` yerine) hover tooltip'i — MVP native title yeterli, istenirse ayrı adım.

## 7. Sonuçlar (uygulandı, 2026-08-17)

**Kod:** `ReviewReportView.tsx` — `citationStatusItems()` (paylaşılan durum listesi, hem rozet hem çubuk reuse eder — kod tekrarı yok) + yeni `CitationIntegrityBar`. `CitationIntegritySection`'a çubuk, rozetin ÜSTÜNE eklendi (rozet SİLİNMEDİ). V1Report da AYNI `CitationIntegritySection`'ı kullandığı için (`ReviewReportView.tsx` V1 render yolu) çubuk otomatik olarak orada da görünüyor — ekstra kod gerekmedi.

**Sıfır yeni bağımlılık** — d3 import edilmedi, plan §3'teki karar doğrulandı.

**Testler:** 2 yeni — segment genişlikleri orantılı + `title` doğru (fixture: total=41, resolved=38 → %92.7 width, fabricated=0 → filtrelenip render edilmiyor), `total=0` → çubuk render edilmiyor.

**Regresyon:** `web/src/components/review/` — **47/47 PASS** (8 dosya, 22'si ReviewReportView). `tsc --noEmit` temiz.
