"""V1-S15.pre A1-P001 — LockRequest/LockResponse Pydantic kontrat testleri.

Plan: docs/plans/MVP_TOMORROW_EXECUTION_PLAN.md §A1 P001
- HK-1 (extra=forbid): bilinmeyen alan reddedilir
- paper_id 1-64 char, boş/whitespace ValidationError
- cluster_status Literal — default 'pending'
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.models.research_area import LockRequest, LockResponse

pytestmark = pytest.mark.unit


# ── 1. LockRequest empty paper_id → ValidationError ──────────────────────────


@pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
def test_lock_request_empty_paper_id_raises(bad: str) -> None:
    with pytest.raises(ValidationError):
        LockRequest(paper_id=bad)


# ── 2. LockRequest paper_id 65 char → ValidationError ────────────────────────


def test_lock_request_paper_id_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        LockRequest(paper_id="W" + "1" * 64)


# ── 3. LockRequest extra alan (HK-1) → ValidationError ───────────────────────


def test_lock_request_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        LockRequest.model_validate({"paper_id": "W123", "ghost": "boom"})


# ── 4. LockResponse default cluster_status='pending' + extra=forbid ──────────


def test_lock_response_default_cluster_status_pending() -> None:
    resp = LockResponse(
        anchor_paper_id="W123",
        locked_at="2026-05-26T10:00:00+00:00",
    )
    assert resp.cluster_status == "pending"

    with pytest.raises(ValidationError):
        LockResponse.model_validate(
            {**resp.model_dump(), "rogue": 1}
        )

    with pytest.raises(ValidationError):
        LockResponse(
            anchor_paper_id="W123",
            locked_at="2026-05-26T10:00:00+00:00",
            cluster_status="invalid",  # type: ignore[arg-type]
        )
