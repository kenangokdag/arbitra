"""FAZ C1 — manuscript anchor verification (deterministic, no LLM).

Closes the FAZ-B audit carry-forward: a high-severity finding may CLAIM a verbatim
quote (manuscript_anchor.quote) as its evidence, but FAZ-B never checked that the
quote actually occurs in the real manuscript. Here we CHECK it deterministically.

Pure functions only — no network, no LLM, no clock, no randomness. Same input →
same output (assigned anchor_ids are deterministic, reproducible across runs).

Contract reused (api/models/review.py):
  - Finding              (api/models/review.py:557-593)
  - ManuscriptAnchor     (api/models/review.py:525-533) — fields anchor_id/section/quote
  - Manuscript           (api/models/review.py:150-158) — .full_text
The ManuscriptAnchor model is extra="forbid" and has NO 'verified' field, so the
verification result is carried OUT-OF-BAND in AnchorVerificationResult.anchor_verified
(anchor_id → bool) plus an honest limitation note on all-unverified findings. We do
NOT delete findings and we NEVER fabricate a quote to make verification pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from api.models.review import Finding, Manuscript, ManuscriptAnchor

# --- tunable v1 defaults (one place — flagged for Omer's scientific audit) ---

# A quote shorter than this (after whitespace normalization) is too weak to be a
# meaningful, locatable anchor → treated as unverified (avoids 1-2 char "matches").
MIN_ANCHOR_QUOTE_CHARS = 6

# Honest limitation appended to a finding when EVERY one of its anchors failed
# verbatim verification. This is the canonical, machine-readable signal that the
# finding's quoted evidence is UNVERIFIED; report_synthesis down-weights on it.
UNVERIFIED_ANCHORS_LIMITATION = (
    "Anchor quote(s) not found verbatim in the manuscript under "
    "whitespace-normalized, case-insensitive comparison; quoted evidence is "
    "UNVERIFIED (finding retained, quote not fabricated)."
)

_WS_RE = re.compile(r"\s+")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    """Whitespace-collapsed, case-insensitive normal form (both sides use this)."""
    return _WS_RE.sub(" ", text).strip().lower()


def _slug(section: str | None) -> str:
    """Deterministic, filesystem-safe section slug for stable anchor ids."""
    s = _SLUG_RE.sub("_", (section or "").strip().lower()).strip("_")
    return s or "unknown"


def verify_anchor(manuscript: Manuscript, anchor: ManuscriptAnchor) -> bool:
    """True iff anchor.quote occurs in manuscript.full_text.

    Comparison is whitespace-normalized (runs of any whitespace → single space,
    trimmed) and case-insensitive on BOTH sides. An empty/missing quote, or one
    shorter than MIN_ANCHOR_QUOTE_CHARS after normalization, → False.
    """
    quote = anchor.quote
    if not quote:
        return False
    norm_quote = _normalize(quote)
    if len(norm_quote) < MIN_ANCHOR_QUOTE_CHARS:
        return False
    return norm_quote in _normalize(manuscript.full_text)


@dataclass(frozen=True)
class AnchorVerificationResult:
    """Output of verify_finding_anchors.

    findings        — same findings, with deterministic anchor_ids reassigned and an
                      honest limitation note added to all-anchors-unverified findings.
    anchor_verified — anchor_id → bool (verbatim found in manuscript). The new,
                      deterministic anchor_ids are the keys.
    """

    findings: list[Finding] = field(default_factory=list)
    anchor_verified: dict[str, bool] = field(default_factory=dict)


def verify_finding_anchors(
    findings: list[Finding], manuscript: Manuscript
) -> AnchorVerificationResult:
    """Assign deterministic anchor_ids and verify each anchor against the manuscript.

    Deterministic id scheme: '<section_slug>.a<ordinal>' where ordinal is a
    per-section counter incremented in the stable order (findings as given, then
    anchors within a finding as given). Same input → identical ids and result.

    A finding whose anchors are ALL unverified gets UNVERIFIED_ANCHORS_LIMITATION
    appended (honest evidence limitation). Findings are never dropped and quotes
    are never fabricated.
    """
    out_findings: list[Finding] = []
    anchor_verified: dict[str, bool] = {}
    section_counter: dict[str, int] = {}

    for finding in findings:
        new_anchors: list[ManuscriptAnchor] = []
        verified_flags: list[bool] = []
        for anchor in finding.manuscript_anchors:
            slug = _slug(anchor.section)
            ordinal = section_counter.get(slug, 0)
            section_counter[slug] = ordinal + 1
            new_id = f"{slug}.a{ordinal}"
            ok = verify_anchor(manuscript, anchor)
            anchor_verified[new_id] = ok
            verified_flags.append(ok)
            new_anchors.append(
                ManuscriptAnchor(
                    anchor_id=new_id, section=anchor.section, quote=anchor.quote
                )
            )

        limitations = list(finding.limitations)
        if (
            verified_flags
            and not any(verified_flags)
            and UNVERIFIED_ANCHORS_LIMITATION not in limitations
        ):
            limitations.append(UNVERIFIED_ANCHORS_LIMITATION)

        out_findings.append(
            finding.model_copy(
                update={
                    "manuscript_anchors": new_anchors,
                    "limitations": limitations,
                }
            )
        )

    return AnchorVerificationResult(
        findings=out_findings, anchor_verified=anchor_verified
    )


def finding_evidence_is_weak(finding: Finding) -> bool:
    """True if a finding's evidence is NOT full-strength (FAZ-B carry-forward).

    Weak = no manuscript_anchor at all (global_issue-only or none), OR all of its
    anchors failed verbatim verification (UNVERIFIED_ANCHORS_LIMITATION present).
    Strong (False) = has at least one verified manuscript_anchor. Used by
    report_synthesis to down-weight unverified / global-only evidence.
    """
    if not finding.manuscript_anchors:
        return True
    return UNVERIFIED_ANCHORS_LIMITATION in finding.limitations


__all__ = [
    "MIN_ANCHOR_QUOTE_CHARS",
    "UNVERIFIED_ANCHORS_LIMITATION",
    "AnchorVerificationResult",
    "finding_evidence_is_weak",
    "verify_anchor",
    "verify_finding_anchors",
]
