"""Plan: docs/plans/VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17.md §4.1.

Coverage: build_version_comparison — verdict/hazırlık puanı/boyut skoru diff'i,
eksik-boyut (birleşim, tahmin yok) ve eksik-executive_verdict (v1/consent-
düşürülmüş) senaryoları.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from api.models.review import (
    DimensionScore,
    ExecutiveVerdict,
    ManuscriptMeta,
    ReviewProvenance,
    ReviewReport,
)
from api.services.version_comparison_service import build_version_comparison

pytestmark = pytest.mark.unit


def _report(
    verdict: str,
    dims: list[DimensionScore],
    readiness: float | None,
) -> ReviewReport:
    return ReviewReport(
        mode="author",
        language="tr",
        manuscript_meta=ManuscriptMeta(title="T"),
        summary="s",
        overall_assessment="oa",
        verdict=verdict,  # type: ignore[arg-type]
        dimension_scores=dims,
        provenance=ReviewProvenance(
            model_used="gemini-flash-tr",
            persona_version="v1",
            engine_version="v1",
            generated_at=datetime.now(timezone.utc),
        ),
        executive_verdict=(
            ExecutiveVerdict(
                overall_readiness_score=readiness,
                recommended_decision=verdict,  # type: ignore[arg-type]
                one_sentence_diagnosis="d",
            )
            if readiness is not None
            else None
        ),
    )


def test_verdict_change_and_readiness_delta() -> None:
    previous = _report(
        "major_revision",
        [DimensionScore(key="soundness", score=5.0, rationale="r")],
        readiness=40.0,
    )
    current = _report(
        "minor_revision",
        [DimensionScore(key="soundness", score=8.0, rationale="r2")],
        readiness=75.0,
    )
    parent_job_id = uuid4()

    result = build_version_comparison(parent_job_id, previous, current)

    assert result.parent_job_id == parent_job_id
    assert result.previous_verdict == "major_revision"
    assert result.current_verdict == "minor_revision"
    assert result.verdict_changed is True
    assert result.previous_readiness_score == 40.0
    assert result.current_readiness_score == 75.0
    assert result.readiness_delta == 35.0
    assert len(result.dimension_deltas) == 1
    d = result.dimension_deltas[0]
    assert d.key == "soundness"
    assert d.previous_score == 5.0
    assert d.current_score == 8.0
    assert d.delta == 3.0


def test_same_verdict_marks_unchanged() -> None:
    previous = _report("accept", [], readiness=90.0)
    current = _report("accept", [], readiness=92.0)
    result = build_version_comparison(uuid4(), previous, current)
    assert result.verdict_changed is False


def test_missing_dimension_on_one_side_is_honest_none_not_guessed() -> None:
    """Bir boyut sadece bir tarafta varsa delta TAHMİN EDİLMEZ, None kalır."""
    previous = _report(
        "major_revision",
        [DimensionScore(key="soundness", score=5.0, rationale="r")],
        readiness=None,
    )
    current = _report(
        "major_revision",
        [
            DimensionScore(key="soundness", score=6.0, rationale="r"),
            DimensionScore(key="clarity", score=7.0, rationale="r"),
        ],
        readiness=None,
    )
    result = build_version_comparison(uuid4(), previous, current)

    by_key = {d.key: d for d in result.dimension_deltas}
    assert by_key["soundness"].delta == 1.0
    assert by_key["clarity"].previous_score is None
    assert by_key["clarity"].current_score == 7.0
    assert by_key["clarity"].delta is None


def test_missing_executive_verdict_gives_none_readiness_not_crash() -> None:
    """v1 rapor / rıza-düşürülmüş rapor: executive_verdict yok → None, çökmez."""
    previous = _report("major_revision", [], readiness=None)
    current = _report("major_revision", [], readiness=None)
    result = build_version_comparison(uuid4(), previous, current)
    assert result.previous_readiness_score is None
    assert result.current_readiness_score is None
    assert result.readiness_delta is None
