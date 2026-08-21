"""FAZ C2 — typed reviewer council (P06-T02).

Maps the REAL adversarial reviewers produced by review_orchestration (the writer/
editor synthesis pair + the five critics: skeptik / yontemci / sempatik /
citation_critic / novelty_critic) onto the typed CouncilRole enum
(api/models/review.py:606-615) → a list[ReviewerCouncilItem].

KANUN (honesty):
  - No fake objections: a council item is built ONLY from a critic that actually
    ran (present in the critiques list) or from the editor when it produced a
    synthesis. A dropped/absent critic is OMITTED (not invented).
  - key_objection is the critic's own most-severe issue verbatim; None when the
    critic raised nothing (sempatik often) — we do NOT manufacture an objection.
  - finding_ids is a BEST-EFFORT deterministic link by role→risk-dimension overlap
    (engine findings grouped by the same dimension mapper report_synthesis uses).
    No clean overlap → empty list. We never fabricate a link.

Pure/deterministic: same critiques + findings in → byte-identical council out
(roles in critic order, finding_ids explicitly sorted). No LLM, no clock, no I/O.

v1 mapping (flagged for Omer's scientific audit):
  yontemci        → methodologist
  skeptik         → skeptical_reviewer
  sempatik        → constructive_reviewer
  citation_critic → citation_auditor
  novelty_critic  → field_expert        (closest real enum value)
  editor          → editor_synthesizer
The writer has NO faithful CouncilRole (it drafts; the editor synthesizes) so it
is intentionally NOT a separate council member. ethics_reviewer / statistics_reviewer
roles exist in the enum but no orchestration critic maps to them in v1 — those
dimensions are covered by the engine findings / risk_radar, not the LLM council.
"""

from __future__ import annotations

from api.models.review import (
    CouncilRole,
    Critique,
    Finding,
    ReviewerCouncilItem,
)
from engine.academic.report_synthesis import _map_to_risk_dimension

COUNCIL_VERSION = "reviewer_council.v1"

# --- critic key → typed CouncilRole (v1 faithful mapping; flag for Omer) ------
_CRITIC_ROLE_MAP: dict[str, CouncilRole] = {
    "yontemci": "methodologist",
    "skeptik": "skeptical_reviewer",
    "sempatik": "constructive_reviewer",
    "citation_critic": "citation_auditor",
    "novelty_critic": "field_expert",
}

_EDITOR_ROLE: CouncilRole = "editor_synthesizer"

# --- role → risk dimensions for best-effort finding linking (v1; flag for Omer)
# Dimension names are the 10 RISK_DIMENSIONS (report_synthesis.RISK_DIMENSIONS).
# Empty set = no clean dimension scope → finding_ids stays empty (honest).
_ROLE_DIMENSIONS: dict[str, frozenset[str]] = {
    "methodologist": frozenset({"methodology", "statistics"}),
    "field_expert": frozenset({"contribution", "literature"}),
    "skeptical_reviewer": frozenset({"evidence", "methodology", "contribution"}),
    "constructive_reviewer": frozenset(),  # strengths-focused, no clean dimension
    "citation_auditor": frozenset({"citation", "literature"}),
    "editor_synthesizer": frozenset(),  # synthesizes all → not dimension-scoped
    "ethics_reviewer": frozenset({"ethics", "reproducibility"}),
    "statistics_reviewer": frozenset({"statistics"}),
}

# CritiqueIssue.severity is Severity = minor|major|blocker (api/models/review.py:85).
_ISSUE_SEVERITY_RANK: dict[str, int] = {"blocker": 3, "major": 2, "minor": 1}

# worst issue severity → reviewer stance label.
_ISSUE_STANCE: dict[str, str] = {
    "blocker": "reject-leaning",
    "major": "revision-required",
    "minor": "minor-concerns",
}
_SUPPORTIVE_STANCE = "supportive"

# editor verdict → stance label.
_VERDICT_STANCE: dict[str, str] = {
    "reject": "reject",
    "major_revision": "major-revision",
    "minor_revision": "minor-revision",
    "accept": "accept",
}

# How many issue problems to surface in the council summary (keep it readable).
_SUMMARY_MAX_ISSUES = 3


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def _worst_issue(critique: Critique):  # type: ignore[no-untyped-def]
    """Highest-severity issue (ties → first as given). None if no issues."""
    if not critique.issues:
        return None
    return max(
        critique.issues,
        key=lambda i: _ISSUE_SEVERITY_RANK.get(i.severity, 0),
    )


def _critic_item(critique: Critique) -> ReviewerCouncilItem | None:
    """Build one council item from a critic that actually ran. None if unmappable."""
    role = _CRITIC_ROLE_MAP.get(critique.critic)
    if role is None:  # unknown critic key → omit honestly (no fake role)
        return None

    issues = critique.issues
    worst = _worst_issue(critique)
    if worst is not None:
        stance = _ISSUE_STANCE.get(worst.severity, "minor-concerns")
        key_objection: str | None = worst.problem
    else:
        stance = _SUPPORTIVE_STANCE
        key_objection = None

    if issues:
        shown = [i.problem for i in issues[:_SUMMARY_MAX_ISSUES]]
        more = len(issues) - len(shown)
        summary = f"{len(issues)} concern(s): " + "; ".join(shown)
        if more > 0:
            summary += f" (+{more} more)"
    else:
        summary = "No objections raised; supports the current draft."

    # confidence proxy (v1): fraction of issues anchored to the evidence pack
    # (grounded=True). No issues → neutral 0.5. Flagged for Omer's audit.
    if issues:
        grounded = sum(1 for i in issues if i.grounded)
        confidence = _clamp_unit(grounded / len(issues))
    else:
        confidence = 0.5

    return ReviewerCouncilItem(
        role=role,
        stance=stance,
        summary=summary,
        key_objection=key_objection,
        confidence=confidence,
        finding_ids=[],  # linked later (best-effort) once engine findings exist
    )


def _editor_item(
    editor_summary: str, editor_verdict: str | None
) -> ReviewerCouncilItem | None:
    """Editor synthesis council member. None if the editor produced nothing."""
    summary = (editor_summary or "").strip()
    if not summary and not editor_verdict:
        return None
    stance = _VERDICT_STANCE.get(editor_verdict or "", "synthesis")
    return ReviewerCouncilItem(
        role=_EDITOR_ROLE,
        stance=stance,
        summary=summary or "Editor synthesis of the reviewer council.",
        key_objection=None,  # the editor synthesizes; it does not raise its own objection
        confidence=0.5,
        finding_ids=[],
    )


def link_council_to_findings(
    council: list[ReviewerCouncilItem], findings: list[Finding]
) -> list[ReviewerCouncilItem]:
    """Best-effort, deterministic finding linking by role→risk-dimension overlap.

    For each council item, link the findings whose dimension maps (via the same
    report_synthesis mapper) into the item's role dimensions. Roles with no clean
    dimension scope (constructive_reviewer, editor_synthesizer) keep an EMPTY list.
    Returns a NEW list (items are copied; inputs untouched). No fabricated links.
    """
    linked: list[ReviewerCouncilItem] = []
    for item in council:
        dims = _ROLE_DIMENSIONS.get(item.role, frozenset())
        if not dims:
            linked.append(item.model_copy(update={"finding_ids": []}))
            continue
        ids = sorted(
            f.finding_id
            for f in findings
            if _map_to_risk_dimension(f.dimension) in dims
        )
        linked.append(item.model_copy(update={"finding_ids": ids}))
    return linked


def build_council(
    critiques: list[Critique],
    *,
    editor_summary: str = "",
    editor_verdict: str | None = None,
    findings: list[Finding] | None = None,
) -> list[ReviewerCouncilItem]:
    """Build the typed reviewer council from the REAL orchestration reviewers.

    Args:
        critiques: the critics that actually ran (review_orchestration last round).
            Critics that were dropped (LLM failure) are simply absent → omitted.
        editor_summary / editor_verdict: the editor's final synthesis (→ the
            editor_synthesizer member). Empty/None on both → no editor member.
        findings: engine findings; when given, finding_ids are linked best-effort
            (role→dimension). When None, finding_ids stay empty (linked later in
            the pipeline once anchor-verified findings exist).

    Returns:
        list[ReviewerCouncilItem] in critic order, then the editor synthesizer.
    """
    council: list[ReviewerCouncilItem] = []
    for critique in critiques:
        item = _critic_item(critique)
        if item is not None:
            council.append(item)

    editor = _editor_item(editor_summary, editor_verdict)
    if editor is not None:
        council.append(editor)

    if findings is not None:
        council = link_council_to_findings(council, findings)
    return council


__all__ = [
    "COUNCIL_VERSION",
    "build_council",
    "link_council_to_findings",
]
