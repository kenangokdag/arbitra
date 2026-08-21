"""FAZ C1 — 6-value SupportLevel mapping tests (deterministic).

Faithful to evidence_provider_spec.md §Support levels. The cardinal rule: an
abstract-only check is NEVER presented as full-text verified.
"""

from __future__ import annotations

import pytest

from api.services.review_citation_service import map_support_level

pytestmark = pytest.mark.unit


def test_no_citation_needed_is_not_applicable() -> None:
    assert map_support_level(claim_needs_citation=False) == "not_applicable"
    # precedence: not_applicable wins even with other signals present
    assert (
        map_support_level(
            claim_needs_citation=False,
            citation_status="resolved",
            full_text_verified=True,
        )
        == "not_applicable"
    )


def test_contradicted_context_is_contradictory() -> None:
    assert (
        map_support_level(citation_status="resolved", context_support="contradicted")
        == "contradictory"
    )


def test_not_found_is_unresolved() -> None:
    assert map_support_level(citation_status="not_found_in_index") == "unresolved"
    assert map_support_level(citation_status=None) == "unresolved"


def test_fabricated_is_unresolved_not_overclaimed() -> None:
    # fabricated DOI belongs to a different work → intended source unresolved.
    assert map_support_level(citation_status="fabricated") == "unresolved"
    assert map_support_level(citation_status="fabricated", abstract_available=True) == "unresolved"


def test_resolved_with_abstract_is_abstract_only() -> None:
    assert (
        map_support_level(citation_status="resolved", abstract_available=True)
        == "abstract_only"
    )
    # supported context at abstract level is STILL abstract_only, not full_text.
    assert (
        map_support_level(
            citation_status="resolved", abstract_available=True, context_support="supported"
        )
        == "abstract_only"
    )


def test_resolved_metadata_only() -> None:
    assert map_support_level(citation_status="resolved", abstract_available=False) == "metadata_only"


def test_full_text_verified_requires_explicit_signal() -> None:
    assert (
        map_support_level(citation_status="resolved", full_text_verified=True)
        == "full_text_verified"
    )


def test_abstract_only_never_becomes_full_text_verified() -> None:
    # No full_text signal, only abstract → must cap at abstract_only.
    for ctx in (None, "supported", "unverifiable_from_abstract"):
        assert (
            map_support_level(
                citation_status="resolved",
                abstract_available=True,
                full_text_verified=False,
                context_support=ctx,  # type: ignore[arg-type]
            )
            == "abstract_only"
        )


def test_retracted_resolves_at_evidence_depth() -> None:
    # retracted = resolved to a real work; support level reflects evidence depth.
    assert map_support_level(citation_status="retracted", abstract_available=True) == "abstract_only"
    assert map_support_level(citation_status="retracted") == "metadata_only"
