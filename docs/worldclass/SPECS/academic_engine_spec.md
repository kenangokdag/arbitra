# Academic Engine Spec — Belge ve Çalışma Türüne Özel Hakemlik

## Amaç

Arbitra'nın akademik motoru generic “iyi/kötü” yorumu üretmemelidir. Her review önce dosyanın ne olduğunu anlamalı, sonra doğru rubrikleri seçmeli, sonra akademik eleştirileri kanıta bağlamalıdır.

## Pipeline

```text
ParsedDocument
  -> ManuscriptTypeClassifier
  -> StudyDesignClassifier
  -> RubricRegistry
  -> GuidelineSelector
  -> Domain Engines
  -> ReviewerCouncil
  -> EditorSynthesis
  -> ReportV2
```

## Manuscript type

```python
DocumentType = Literal[
  "journal_article",
  "conference_paper",
  "thesis",
  "grant_proposal",
  "preprint",
  "technical_report",
  "book_chapter",
  "unknown",
]
```

## Study design

```python
StudyDesign = Literal[
  "qualitative",
  "quantitative",
  "mixed_methods",
  "systematic_review",
  "meta_analysis",
  "scoping_review",
  "theoretical",
  "conceptual",
  "design_science",
  "computational_modeling",
  "dataset_resource",
  "software_tool",
  "replication",
  "registered_report",
  "case_study",
  "protocol",
  "unknown",
]
```

## RubricRegistry

Rubric seçimi şu inputlarla yapılır:

- document_type
- study_design
- discipline/subfield
- target venue/call if provided
- review_mode
- strictness
- language_config

Çıktı:

```json
{
  "rubric_id": "article.qualitative.v1",
  "version": "1.0",
  "dimensions": [
    {
      "id": "methodology_design_fit",
      "weight": 0.15,
      "required": true,
      "engine": "QualitativeRigorEngine"
    }
  ]
}
```

## Belge türüne göre temel rubrik

### Journal article

- Contribution/originality
- Research question fit
- Theoretical framing
- Literature positioning
- Methodology fit
- Data/sample adequacy
- Analysis validity
- Claim-evidence alignment
- Citation integrity
- Reporting guideline compliance
- Ethics and reproducibility
- Writing/structure
- Venue fit

### Conference paper

- Track fit
- Novelty-to-length ratio
- Technical correctness
- Reproducibility artifact
- Presentation clarity
- Contribution clarity
- Ethics and limitations
- Reviewer confidence

### Thesis/dissertation

- Problem statement
- Research questions/hypotheses
- Chapter coherence
- Literature depth
- Theoretical framework
- Methodological justification
- Analysis depth
- Original contribution
- Defense readiness
- Committee question risk
- Publication potential

### Grant/project proposal

- Problem significance
- Objectives
- Work packages
- Feasibility
- Team competence
- Timeline realism
- Budget coherence
- Risk mitigation
- Impact pathway
- Dissemination
- Ethics/data management
- Sustainability

## Engine output contract

Her engine şu schema ile bulgu döndürür:

```json
{
  "finding_id": "...",
  "dimension": "methodology_design_fit",
  "severity": "critical | major | moderate | minor | info",
  "confidence": 0.82,
  "summary": "Sampling strategy is named but not justified.",
  "manuscript_anchors": ["methods.p4"],
  "evidence_anchors": [],
  "reasoning_public": "A qualitative study must justify why selected participants can illuminate the phenomenon.",
  "action_items": [
    {
      "priority": "P0",
      "instruction": "Add a short justification for purposive sampling and explain inclusion/exclusion criteria.",
      "target_section": "Methods",
      "effort": "medium",
      "expected_gain": "high"
    }
  ],
  "limitations": ["Participant details were partially available; confidence may improve with appendices."]
}
```

## Minimum viable academic coverage

P03 bitmeden en az şu engine’ler çalışmalıdır:

1. QualitativeRigorEngine
2. QuantitativeValidityEngine
3. ReportingGuidelineSelector
4. ClaimEvidenceAlignmentEngine
5. CitationIntegrityEngine
6. EthicsTransparencyEngine
7. StructureClarityEngine

## Başarı kapısı

- Makale, bildiri, tez, proje aynı raporu almıyor.
- Nitel çalışma nitel rigor başlıklarıyla inceleniyor.
- Nicel çalışma istatistik/method validity başlıklarıyla inceleniyor.
- High-severity eleştiriler anchor + action item içeriyor.
- Rubrik ve model versiyonları report provenance içinde yer alıyor.
