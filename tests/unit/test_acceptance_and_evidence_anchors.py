"""G2 + G1 — acceptance_check boru hattı + evidence_anchors kaldırımı.

G2: LLM çıktısındaki acceptance_check, _engine_base.assess → _to_findings →
    ActionItem.acceptance_check'e DEĞİŞMEDEN akar ve build_action_plan'da korunur.
    Stub LLM (ağ/maliyet yok). LLM'i None-değil'e ZORLAYAN validator EKLENMEZ —
    yalnız boru hattının taşıdığı kanıtlanır.

G1: evidence_anchors Finding sözleşmesinden ÇIKARILDI (ölü konteyner). extra='forbid'
    altında onu vermek artık reddedilir (alan gerçekten kaldırıldı).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from api.models.review import Finding, Manuscript, ManuscriptMeta
from engine.academic import _engine_base as eb
from engine.academic.report_synthesis import build_action_plan

pytestmark = pytest.mark.unit


def _manuscript() -> Manuscript:
    return Manuscript(
        meta=ManuscriptMeta(title="X", word_count=100, reference_count=1),
        full_text="We used a randomized controlled trial design.",
    )


# --- G2: acceptance_check LLM → ActionItem → action_plan ---------------------


@pytest.mark.asyncio
async def test_acceptance_check_flows_from_llm_to_action_item(monkeypatch) -> None:
    parsed = eb._LLMFindingList(
        findings=[
            eb._LLMFinding(
                dimension="methodology",
                severity="major",
                confidence=0.8,
                title="Sampling not justified",
                manuscript_anchors=[
                    eb._LLMAnchor(
                        section="Methods",
                        quote="randomized controlled trial design",
                    )
                ],
                action_items=[
                    eb._LLMActionItem(
                        priority="P0",
                        instruction="Add a sample-size justification.",
                        acceptance_check="Reader can tell why this sample answers the RQ.",
                    )
                ],
            )
        ]
    )

    async def _fake_call(*a, **k):
        # llm_service.call dönüşü: .parsed_output taşıyan nesne (LLMResponse şekli).
        return SimpleNamespace(parsed_output=parsed)

    monkeypatch.setattr(eb, "call", _fake_call)

    result = await eb.assess(
        label="quantitative_engine",
        mode="quantitative_validity",
        criteria_block="criteria",
        manuscript=_manuscript(),
        allow_external_ai=True,
        id_prefix="quant",
    )

    # action_item acceptance_check'i LLM'den DEĞİŞMEDEN taşır
    assert len(result.action_items) == 1
    assert (
        result.action_items[0].acceptance_check
        == "Reader can tell why this sample answers the RQ."
    )
    # severity major korundu (action + anchor sağlandı → downgrade YOK)
    assert result.findings[0].severity == "major"

    # build_action_plan boru hattının sonunda da korunur
    plan = build_action_plan(result.findings, result.action_items)
    assert len(plan) == 1
    assert (
        plan[0].acceptance_check
        == "Reader can tell why this sample answers the RQ."
    )


@pytest.mark.asyncio
async def test_acceptance_check_optional_not_forced(monkeypatch) -> None:
    """LLM acceptance_check vermezse boru hattı None taşır — fabrikasyon YOK."""
    parsed = eb._LLMFindingList(
        findings=[
            eb._LLMFinding(
                dimension="writing",
                severity="moderate",
                confidence=0.5,
                title="Minor clarity issue",
                action_items=[
                    eb._LLMActionItem(
                        priority="P2",
                        instruction="Tighten the abstract.",
                        # acceptance_check verilmedi
                    )
                ],
            )
        ]
    )

    async def _fake_call(*a, **k):
        return SimpleNamespace(parsed_output=parsed)

    monkeypatch.setattr(eb, "call", _fake_call)

    result = await eb.assess(
        label="dimension_engine",
        mode="writing",
        criteria_block="c",
        manuscript=_manuscript(),
        allow_external_ai=True,
        id_prefix="dim",
    )
    assert result.action_items[0].acceptance_check is None  # zorlanmadı


# --- G1: evidence_anchors kaldırıldı ----------------------------------------


def test_finding_has_no_evidence_anchors_field() -> None:
    assert "evidence_anchors" not in Finding.model_fields


def test_finding_rejects_evidence_anchors() -> None:
    # extra='forbid' → kaldırılmış alanı vermek hata (ölü konteyner gerçekten yok).
    with pytest.raises(ValidationError):
        Finding(
            finding_id="f0",
            dimension="d",
            title="t",
            evidence_anchors=["E-001"],  # type: ignore[call-arg]
        )
