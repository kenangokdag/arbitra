"""SPINE-1 — worldclass v2 sözleşme kilidi.

v2 alanlarının additive olduğunu (v1 davranışı korunur), Finding mandatory
kuralının (critical/major → action + anchor|global) sözleşme düzeyinde
enforce edildiğini ve sınıflandırma/gizlilik/stage modellerinin doğru
çalıştığını kanıtlar. (P06-T01 mandatory + P03 + P01-T03 + P02-T01.)
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from api.models import review as r


def _prov() -> r.ReviewProvenance:
    return r.ReviewProvenance(
        model_used="gemini",
        persona_version="v1",
        engine_version="v1",
        generated_at=datetime.now(UTC),
    )


def _v1_report() -> r.ReviewReport:
    return r.ReviewReport(
        mode="author",
        language="tr",
        manuscript_meta=r.ManuscriptMeta(),
        summary="x",
        overall_assessment="y",
        verdict="minor_revision",
        provenance=_prov(),
    )


def test_v1_report_still_valid_with_v2_defaults():
    """Mevcut v1 üreticiler v2 alanlarını DOLDURMADAN geçerli kalır (688 garanti)."""
    rep = _v1_report()
    assert rep.schema_version == "review_report.v1"
    assert rep.findings == []
    assert rep.executive_verdict is None
    assert rep.risk_radar == []
    assert rep.reviewer_council == []


def test_v2_report_fields_populate():
    f = r.Finding(
        finding_id="F-1",
        dimension="methodology",
        severity="critical",
        confidence=0.8,
        title="Sampling not justified",
        manuscript_anchors=[r.ManuscriptAnchor(anchor_id="methods.p4", section="Methods")],
        action_item_ids=["A-1"],
    )
    ev = r.ExecutiveVerdict(
        overall_readiness_score=67,
        recommended_decision="major_revision",
        confidence=0.7,
        one_sentence_diagnosis="Plausible contribution, weak method transparency.",
    )
    rep = r.ReviewReport(
        mode="author",
        language="tr",
        manuscript_meta=r.ManuscriptMeta(),
        summary="x",
        overall_assessment="y",
        verdict="major_revision",
        provenance=_prov(),
        schema_version="review_report.v2",
        executive_verdict=ev,
        findings=[f],
        risk_radar=[r.RiskRadarItem(dimension="methodology", score=42, severity="major")],
        action_plan=[
            r.ActionItem(action_id="A-1", priority="P0", instruction="Justify sampling.")
        ],
    )
    assert rep.schema_version == "review_report.v2"
    assert rep.executive_verdict.overall_readiness_score == 67.0
    assert rep.findings[0].severity == "critical"
    assert rep.action_plan[0].priority == "P0"


def test_finding_critical_requires_action_item():
    """P06-T01 mandatory: critical/major bulgu action_item OLMADAN reddedilir."""
    with pytest.raises(ValidationError, match="action_item"):
        r.Finding(
            finding_id="F-2",
            dimension="methodology",
            severity="major",
            title="x",
            manuscript_anchors=[r.ManuscriptAnchor(anchor_id="m.p1")],
            action_item_ids=[],  # YOK → reddedilmeli
        )


def test_finding_critical_requires_anchor_or_global():
    """critical/major bulgu anchor VEYA global_issue OLMADAN reddedilir."""
    with pytest.raises(ValidationError, match="manuscript_anchor"):
        r.Finding(
            finding_id="F-3",
            dimension="methodology",
            severity="critical",
            title="x",
            action_item_ids=["A-1"],
            manuscript_anchors=[],
            global_issue=False,  # ikisi de yok → reddedilmeli
        )


def test_finding_global_issue_allows_no_anchor():
    """global_issue=True iken anchor gerekmez (global belge sorunu)."""
    f = r.Finding(
        finding_id="F-4",
        dimension="writing",
        severity="major",
        title="Document-wide structural issue",
        action_item_ids=["A-2"],
        global_issue=True,
    )
    assert f.global_issue is True


def test_finding_low_severity_no_constraint():
    """moderate/minor/info bulgular action/anchor zorunluluğu taşımaz."""
    f = r.Finding(finding_id="F-5", dimension="clarity", severity="minor", title="typo")
    assert f.action_item_ids == []


def test_classification_override():
    dc = r.DocumentClassification(
        document_type="journal_article",
        document_type_confidence=0.4,
        study_design="quantitative",
        user_document_type_override="thesis",
    )
    assert dc.effective_document_type == "thesis"  # override kazanır
    assert dc.effective_study_design == "quantitative"  # override yok → model


def test_privacy_confidential_defaults_blocked_explicit():
    """reviewer_confidential mode external_ai_consent='blocked' AÇIKÇA verilebilir."""
    p = r.PrivacyConfig(
        confidentiality_mode="reviewer_confidential", external_ai_consent="blocked"
    )
    assert p.confidentiality_mode == "reviewer_confidential"
    assert p.external_ai_consent == "blocked"
    assert p.retention_days == 30


def test_stage_state_model():
    s = r.ReviewStageState(stage="resolve_references", status="degraded",
                           degraded_reason="OpenAlex key missing", progress=0.62)
    assert s.stage == "resolve_references"
    assert s.status == "degraded"


def test_job_carries_v2_fields():
    from uuid import uuid4

    job = r.ReviewJob(
        job_id=uuid4(),
        user_id="u1",
        mode="author",
        language="tr",
        status="queued",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        privacy=r.PrivacyConfig(),
        stages=[r.ReviewStageState(stage="parse_document")],
        idempotency_key="abc",
        lifecycle="queued",
    )
    assert job.privacy.confidentiality_mode == "author_owned"
    assert job.stages[0].stage == "parse_document"
    assert job.idempotency_key == "abc"
