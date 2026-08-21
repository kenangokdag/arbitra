"""FAZ C1 — anchor verification tests (deterministic, no network/LLM).

Closes the FAZ-B carry-forward: a finding's claimed verbatim quote is CHECKED
against the real manuscript. Quotes are never fabricated; unverified anchors are
honestly flagged.
"""

from __future__ import annotations

import pytest

from api.models.review import Finding, Manuscript, ManuscriptAnchor, ManuscriptMeta
from engine.academic.anchoring import (
    UNVERIFIED_ANCHORS_LIMITATION,
    finding_evidence_is_weak,
    verify_anchor,
    verify_finding_anchors,
)

pytestmark = pytest.mark.unit


_FULL_TEXT = (
    "Introduction. This study examines purposive sampling in field research.\n\n"
    "Methods.   The   sampling strategy was named but not justified in detail.\n\n"
    "Results. We found a significant effect across all conditions."
)


def _manuscript(full_text: str = _FULL_TEXT, sections: list[str] | None = None) -> Manuscript:
    return Manuscript(
        meta=ManuscriptMeta(
            title="A test paper",
            section_titles=sections if sections is not None else ["Introduction", "Methods", "Results"],
        ),
        full_text=full_text,
    )


def _finding(
    fid: str,
    *,
    anchors: list[ManuscriptAnchor] | None = None,
    severity: str = "moderate",
    global_issue: bool = False,
    action_item_ids: list[str] | None = None,
) -> Finding:
    return Finding(
        finding_id=fid,
        dimension="methodology_fit",
        severity=severity,  # type: ignore[arg-type]
        title=f"Finding {fid}",
        manuscript_anchors=anchors or [],
        global_issue=global_issue,
        action_item_ids=action_item_ids or [],
    )


def test_verify_anchor_present_quote_is_verified() -> None:
    m = _manuscript()
    anchor = ManuscriptAnchor(
        anchor_id="x", section="Methods", quote="sampling strategy was named but not justified"
    )
    assert verify_anchor(m, anchor) is True


def test_verify_anchor_absent_quote_is_unverified() -> None:
    m = _manuscript()
    anchor = ManuscriptAnchor(
        anchor_id="x", section="Methods", quote="the authors fabricated their entire dataset"
    )
    assert verify_anchor(m, anchor) is False


def test_verify_anchor_whitespace_and_case_variation_still_matches() -> None:
    m = _manuscript()
    # multiple spaces + different case vs the manuscript's "The   sampling strategy"
    anchor = ManuscriptAnchor(
        anchor_id="x", section="Methods", quote="THE SAMPLING   strategy WAS named"
    )
    assert verify_anchor(m, anchor) is True


def test_verify_anchor_empty_quote_is_unverified() -> None:
    m = _manuscript()
    assert verify_anchor(m, ManuscriptAnchor(anchor_id="x", quote=None)) is False
    assert verify_anchor(m, ManuscriptAnchor(anchor_id="x", quote="")) is False
    assert verify_anchor(m, ManuscriptAnchor(anchor_id="x", quote="  a ")) is False  # too short


def test_all_unverified_records_limitation_not_deletes_finding() -> None:
    m = _manuscript()
    f = _finding(
        "F1",
        anchors=[ManuscriptAnchor(anchor_id="orig", section="Methods", quote="not present at all here xyz")],
    )
    res = verify_finding_anchors([f], m)
    assert len(res.findings) == 1  # finding retained
    assert UNVERIFIED_ANCHORS_LIMITATION in res.findings[0].limitations
    assert res.findings[0].manuscript_anchors[0].quote == "not present at all here xyz"  # quote not faked
    assert all(v is False for v in res.anchor_verified.values())


def test_verified_anchor_no_limitation_added() -> None:
    m = _manuscript()
    f = _finding(
        "F1",
        anchors=[ManuscriptAnchor(anchor_id="orig", section="Methods", quote="significant effect across all conditions")],
    )
    res = verify_finding_anchors([f], m)
    assert UNVERIFIED_ANCHORS_LIMITATION not in res.findings[0].limitations
    assert any(v is True for v in res.anchor_verified.values())


def test_partial_verification_one_verified_no_limitation() -> None:
    m = _manuscript()
    f = _finding(
        "F1",
        anchors=[
            ManuscriptAnchor(anchor_id="a", section="Methods", quote="significant effect across all conditions"),
            ManuscriptAnchor(anchor_id="b", section="Methods", quote="totally absent quote zzz"),
        ],
    )
    res = verify_finding_anchors([f], m)
    # at least one verified → NOT flagged as all-unverified
    assert UNVERIFIED_ANCHORS_LIMITATION not in res.findings[0].limitations
    assert finding_evidence_is_weak(res.findings[0]) is False


def test_anchor_ids_deterministic_and_stable_across_runs() -> None:
    m = _manuscript()
    findings = [
        _finding("F1", anchors=[
            ManuscriptAnchor(anchor_id="o1", section="Methods", quote="significant effect across all conditions"),
            ManuscriptAnchor(anchor_id="o2", section="Methods", quote="purposive sampling in field research"),
        ]),
        _finding("F2", anchors=[
            ManuscriptAnchor(anchor_id="o3", section="Results", quote="found a significant effect"),
        ]),
    ]
    r1 = verify_finding_anchors(findings, m)
    r2 = verify_finding_anchors(findings, m)
    ids1 = [a.anchor_id for f in r1.findings for a in f.manuscript_anchors]
    ids2 = [a.anchor_id for f in r2.findings for a in f.manuscript_anchors]
    assert ids1 == ids2  # reproducible
    assert ids1 == ["methods.a0", "methods.a1", "results.a0"]  # section + ordinal scheme
    assert r1.anchor_verified == r2.anchor_verified


def test_global_issue_only_finding_is_weak_evidence() -> None:
    f = _finding("F1", severity="major", global_issue=True, action_item_ids=["A1"])
    assert finding_evidence_is_weak(f) is True
