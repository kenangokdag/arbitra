# I18N & 100 Language Spec

## Problem

`tr/en` literal yaklaşımı 100 dil vizyonunu taşımaz. Akademik review’de üç dil kavramı ayrıdır:

1. Manuscript source language.
2. Report output language.
3. UI locale.

## LanguageConfig

```json
{
  "source_language": "tr",
  "output_language": "en",
  "ui_locale": "tr-TR",
  "citation_language_policy": "preserve_original | translate_summary | bilingual",
  "rtl": false,
  "terminology_profile": "social_sciences.tr.en"
}
```

## Kural

- Manuscript quote her zaman orijinal dilde saklanır.
- Açıklama output language’da yazılır.
- Çeviri varsa quote değil explanation çevrilir.
- Bilingual mode: original quote + translated explanation.
- Citation titles/original source metadata çevrilmez, ancak summary çevrilebilir.

## Frontend requirements

- ICU MessageFormat veya benzeri i18n sistemi.
- RTL layout smoke.
- Locale-aware dates/numbers.
- Static strings hardcode edilmez.
- Error messages i18n key ile gelir.

## Backend requirements

- BCP-47 validation.
- Sentence segmentation pluggable.
- Language-specific academic style dictionary.
- Multilingual method terms for classifiers.
- Report schema language metadata.

## Eval requirements

Her yeni pilot dil için:

- Parser quality sample.
- Claim extraction sample.
- Rubric output sample.
- Hallucination check.
- Human review sample.

## Başarı kapısı

- TR source -> EN report -> TR UI mümkün.
- EN source -> TR report -> EN UI mümkün.
- Quote provenance orijinal dili koruyor.
- `Literal['tr','en']` yeni code path’te kalmıyor.
