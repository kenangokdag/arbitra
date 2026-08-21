"""P03 Akademik motor — belge/çalışma türü sınıflandırma + rubrik seçimi.

İki bağımsız parça:
  - classifier.py    → Manuscript → DocumentClassification (LLM-destekli, consent-aware).
  - rubric_registry.py → (document_type, study_design, mode, strictness) → Rubric (PURE).

Akış (academic_engine_spec.md):
  ParsedDocument → classifier → RubricRegistry → GuidelineSelector → Domain Engines.
"""

from __future__ import annotations

from engine.academic._engine_base import EngineResult
from engine.academic.assessment import assess_manuscript
from engine.academic.classifier import classify_document
from engine.academic.dimension_engine import assess_dimension
from engine.academic.qualitative_engine import assess_qualitative
from engine.academic.quantitative_engine import assess_quantitative
from engine.academic.rubric_registry import (
    Rubric,
    RubricDimension,
    select_rubric,
)

__all__ = [
    "EngineResult",
    "Rubric",
    "RubricDimension",
    "assess_dimension",
    "assess_manuscript",
    "assess_qualitative",
    "assess_quantitative",
    "classify_document",
    "select_rubric",
]
