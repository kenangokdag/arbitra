# Quantitative Validity Engine Spec

## Amaç

Nicel çalışma review’ü sadece p-value yakalama değildir. Tasarım, örneklem, değişkenler, analiz, varsayımlar, raporlama, etki büyüklüğü, eksik veri ve nedensel iddia disiplinini birlikte değerlendirmelidir.

## Trigger

- `study_design = quantitative`
- `study_design = mixed_methods` quantitative component varsa
- `study_design = meta_analysis`
- computational/modeling çalışmada numeric evaluation varsa

## Kontrol boyutları

1. **Design validity**
   - Kesitsel, deneysel, gözlemsel, longitudinal, quasi-experimental tasarım doğru tanımlanmış mı?
   - Araştırma sorusu tasarımla uyumlu mu?

2. **Sample and power**
   - Örneklem büyüklüğü gerekçeli mi?
   - Power analysis veya precision rationale var mı?
   - Attrition/missingness raporlanmış mı?

3. **Measurement validity**
   - Ölçüm araçları geçerli/güvenilir mi?
   - Değişken operasyonelleştirme açık mı?

4. **Analysis plan**
   - İstatistiksel test/model seçimi veri tipine uygun mu?
   - Varsayımlar test edilmiş mi?
   - Multiple comparisons riski var mı?

5. **Statistical consistency**
   - p-value/test statistic/df uyumu.
   - CI/p-value/effect direction uyumu.
   - Metin-tablo-figür sayı tutarlılığı.

6. **Effect size and uncertainty**
   - Etki büyüklüğü raporlanmış mı?
   - Güven aralıkları veya belirsizlik ölçüleri var mı?

7. **Missing data and outliers**
   - Missing data stratejisi açıklanmış mı?
   - Outlier handling şeffaf mı?

8. **Causal language discipline**
   - Gözlemsel tasarımda nedensel dil aşırı mı?
   - Confounding veya identification stratejisi var mı?

9. **Reproducibility**
   - Data/code availability.
   - Preregistration veya protocol uyumu.

10. **Reporting quality**
   - Ana sonuçlar effect size + uncertainty ile sunulmuş mu?
   - “Significant/non-significant” dili aşırı mı?

## Output contract

Her numeric finding:

- exact manuscript anchor
- extracted numeric values
- expected relationship/check
- observed inconsistency
- confidence
- limitation
- recommended fix

taşımalıdır.

## MVP limitations

İlk sürüm tüm istatistikleri doğrulamak zorunda değil. Ancak doğrulayamadığı yerde bunu açıkça yazmalıdır:

```text
The p-value consistency check could not be completed because the test statistic was not reported. This finding is a reporting completeness warning, not a recalculation.
```

## Başarı kapısı

- Causal overclaim detection çalışıyor.
- Missing effect size/power/missing data warnings üretiyor.
- p-value pattern consistency temel testleri var.
- Confidence/limitation alanları her numeric finding’de dolu.
