"""Plan: docs/plans/VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17.md §4.2.

Coverage: GET /api/review/jobs (kullanıcı-kapsamlı liste) + GET
/api/review/{job_id}/comparison (parent yok → null, parent var → dolu,
BOLA → 404).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from api.models.review import ManuscriptMeta, ReviewProvenance, ReviewReport

pytestmark = pytest.mark.unit


def _report(verdict: str) -> ReviewReport:
    return ReviewReport(
        mode="author",
        language="tr",
        manuscript_meta=ManuscriptMeta(title="T"),
        summary="s",
        overall_assessment="oa",
        verdict=verdict,  # type: ignore[arg-type]
        provenance=ReviewProvenance(
            model_used="gemini-flash-tr",
            persona_version="v1",
            engine_version="v1",
            generated_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from api.main import create_app

    c = TestClient(create_app())
    token = jwt.encode({"sub": "user-cmp-1"}, "x", algorithm="HS256")
    c.headers["Authorization"] = f"Bearer {token}"
    return c


def test_my_jobs_returns_only_caller_scoped_list(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_list_user_jobs(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        assert user_id == "user-cmp-1"
        assert limit == 20
        return [{"job_id": "j1", "source_name": "makale.pdf", "status": "done"}]

    monkeypatch.setattr(
        "api.routes.review.review_service.list_user_jobs", fake_list_user_jobs
    )

    resp = client.get("/api/review/jobs")
    assert resp.status_code == 200
    assert resp.json() == {"jobs": [{"job_id": "j1", "source_name": "makale.pdf", "status": "done"}]}


def test_comparison_no_parent_returns_null_not_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_id = uuid4()

    async def fake_get_parent_job_id(user_id: str, jid: UUID) -> UUID | None:
        assert user_id == "user-cmp-1"
        assert jid == job_id
        return None

    monkeypatch.setattr(
        "api.routes.review.review_service.get_parent_job_id", fake_get_parent_job_id
    )

    resp = client.get(f"/api/review/{job_id}/comparison")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == str(job_id)
    assert body["comparison"] is None


def test_comparison_with_parent_builds_full_diff(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_id = uuid4()
    parent_id = uuid4()
    current = _report("accept")
    previous = _report("major_revision")

    async def fake_get_parent_job_id(user_id: str, jid: UUID) -> UUID | None:
        return parent_id

    async def fake_get_report(user_id: str, jid: UUID) -> ReviewReport:
        return current if jid == job_id else previous

    monkeypatch.setattr(
        "api.routes.review.review_service.get_parent_job_id", fake_get_parent_job_id
    )
    monkeypatch.setattr("api.routes.review.review_service.get_report", fake_get_report)

    resp = client.get(f"/api/review/{job_id}/comparison")
    assert resp.status_code == 200
    body = resp.json()
    assert body["comparison"]["parent_job_id"] == str(parent_id)
    assert body["comparison"]["previous_verdict"] == "major_revision"
    assert body["comparison"]["current_verdict"] == "accept"
    assert body["comparison"]["verdict_changed"] is True


def test_comparison_job_not_found_returns_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(user_id: str, jid: UUID) -> UUID | None:
        raise LookupError("review job not found")

    monkeypatch.setattr("api.routes.review.review_service.get_parent_job_id", boom)

    resp = client.get(f"/api/review/{uuid4()}/comparison")
    assert resp.status_code == 404
