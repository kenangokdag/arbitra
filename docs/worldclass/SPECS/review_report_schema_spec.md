# Review Report Schema v2 Spec

## Amaç

Review report sadece uzun bir metin değil, revizyon yönetimi yapılabilen structured academic artifact olmalıdır.

## Top-level schema

```json
{
  "schema_version": "review_report.v2",
  "job_id": "...",
  "document_profile": {},
  "executive_verdict": {},
  "risk_radar": [],
  "reviewer_council": [],
  "academic_dimensions": [],
  "evidence_map": [],
  "action_plan": [],
  "section_reviews": [],
  "guideline_compliance": [],
  "exports": [],
  "limitations": [],
  "provenance": {},
  "disclosure": {}
}
```

## Executive verdict

```json
{
  "overall_readiness_score": 67,
  "recommended_decision": "major_revision",
  "confidence": 0.76,
  "top_fatal_risks": ["..."],
  "one_sentence_diagnosis": "The paper has a plausible contribution but method transparency and claim-evidence alignment are not yet submission-ready."
}
```

## Risk radar

Dimensions:

- contribution
- literature
- methodology
- evidence
- citation
- statistics
- ethics
- reproducibility
- writing
- venue_fit

Each item:

```json
{
  "dimension": "methodology",
  "score": 42,
  "severity": "major",
  "confidence": 0.82,
  "why_it_matters": "..."
}
```

## Reviewer council item

```json
{
  "role": "methodologist",
  "stance": "strict",
  "findings": ["finding_id_1"],
  "summary": "...",
  "confidence": 0.8
}
```

## Finding model

```json
{
  "finding_id": "F-001",
  "dimension": "methodology_design_fit",
  "severity": "critical | major | moderate | minor | info",
  "confidence": 0.84,
  "title": "Sampling strategy is named but not justified",
  "summary": "...",
  "manuscript_anchors": [
    {
      "anchor_id": "methods.p4",
      "section": "Methods",
      "quote": "..."
    }
  ],
  "evidence_anchors": [],
  "reasoning_public": "...",
  "limitations": [],
  "action_items": ["A-001"]
}
```

## Action item model

```json
{
  "action_id": "A-001",
  "priority": "P0 | P1 | P2",
  "effort": "low | medium | high",
  "expected_gain": "low | medium | high",
  "target_section": "Methods",
  "instruction": "Add a justification for purposive sampling...",
  "acceptance_check": "Reader can tell why this sample can answer the research question.",
  "linked_findings": ["F-001"]
}
```

## Mandatory constraints

- `severity in [critical, major]` ise en az bir `action_item` zorunlu.
- `severity in [critical, major]` ise en az bir manuscript anchor veya explicit “global document issue” gerekçesi zorunlu.
- `confidence` 0-1 arası olmalı.
- Provider/evidence eksikse limitation zorunlu.
- Confidential mode disclosure zorunlu.

## Frontend render sections

1. Executive verdict
2. Top 5 fatal risks
3. Risk radar
4. Reviewer council tabs
5. Evidence map drawer
6. P0/P1/P2 action plan
7. Section-by-section review
8. Guideline compliance
9. Provenance and limitations
10. Export/disclosure

## Başarı kapısı

- Rapor typed contract ile validate edilir.
- Frontend string parsing yapmaz.
- Her kritik eleştiri anchor/action/confidence taşır.
- Export aynı schema’dan üretilir.
