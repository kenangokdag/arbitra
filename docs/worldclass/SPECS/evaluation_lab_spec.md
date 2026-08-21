# Evaluation Lab Spec

## Amaç

Arbitra AI kalitesi sezgiyle değil ölçümle yönetilmelidir. Prompt/model/provider değişikliği akademik kaliteyi düşürürse release engellenmelidir.

## Goldset categories

- Journal article — qualitative
- Journal article — quantitative
- Mixed methods article
- Systematic review
- Conference paper
- Thesis
- Grant proposal
- Low-quality manuscript
- Good-quality manuscript
- Confidential reviewer scenario
- Multilingual samples

## Label schema

```json
{
  "sample_id": "qual_001",
  "document_type": "journal_article",
  "study_design": "qualitative",
  "known_issues": [
    {
      "dimension": "reflexivity",
      "severity": "major",
      "anchor": "methods.p7",
      "acceptable_actions": ["Add researcher positionality statement"]
    }
  ],
  "citation_truth": [],
  "must_not_claim": [],
  "expert_notes": []
}
```

## Metrics

### Schema validity

Report must validate 100%.

### Hallucination rate

Findings with no manuscript anchor/evidence and not marked as limitation.

### Actionability score

High-severity findings with concrete action item / all high-severity findings.

### Citation precision

Correct citation support classifications / all citation support classifications.

### Rubric agreement

Overlap between expected issue dimensions and report issue dimensions.

### Severity calibration

Critical/major/minor labels compared with expert labels.

### Degraded honesty

Provider missing/failure reflected in report limitations.

## Release thresholds MVP

- Schema validity: 100%
- High severity actionability: >= 95%
- No fake citations: 100%
- Degraded honesty: 100%
- Hallucination rate: <= agreed threshold

## Eval command

```bash
python -m eval.review.run_eval --goldset eval/review/goldset.json --reports eval/review/sample_reports.json --mode release
```

## Başarı kapısı

- Eval sadece demo değil CI’da çalışır.
- Model/prompt değişikliği benchmark raporu üretir.
- İnsan uzman feedback’i goldset’e girebilir.
