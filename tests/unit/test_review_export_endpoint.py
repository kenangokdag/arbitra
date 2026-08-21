"""Plan: docs/plans/RAPOR_DOCX_EXPORT_2026-08-16.md §4.2.

Coverage: GET /api/review/{job_id}/export.docx — Content-Type/Content-Disposition
header'ları + BOLA (başka kullanıcının/var olmayan job'ı için 404).
review.py:248-255'teki mevcut /report testinin AYNI deseni (review.py'de daha
önce hiç endpoint-testi yoktu — bu dosya review export'a özel, ilk örnek).
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


def _make_report() -> ReviewReport:
    return ReviewReport(
        mode="author",
        language="tr",
        manuscript_meta=ManuscriptMeta(title="Export Test Makalesi"),
        summary="s",
        overall_assessment="oa",
        verdict="accept",
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

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    c = TestClient(create_app())
    token = jwt.encode({"sub": "user-export-1"}, "x", algorithm="HS256")
    c.headers["Authorization"] = f"Bearer {token}"
    return c


def test_export_docx_returns_valid_docx_response(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = _make_report()
    job_id = uuid4()

    async def fake_get_report(user_id: str, jid: UUID) -> ReviewReport:
        assert user_id == "user-export-1"
        assert jid == job_id
        return report

    monkeypatch.setattr("api.routes.review.review_service.get_report", fake_get_report)

    resp = client.get(f"/api/review/{job_id}/export.docx")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert (
        resp.headers["content-disposition"]
        == f'attachment; filename="arbitra-rapor-{job_id}.docx"'
    )
    assert resp.content.startswith(b"PK")  # docx = zip paketi


def test_export_docx_not_found_returns_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BOLA: başka kullanıcının ya da var olmayan job'ı 404 (review.py:248-255
    ile AYNI davranış — sahiplik ifşa edilmez)."""

    async def boom(user_id: str, jid: UUID) -> ReviewReport:
        raise LookupError("review job not found")

    monkeypatch.setattr("api.routes.review.review_service.get_report", boom)

    resp = client.get(f"/api/review/{uuid4()}/export.docx")
    assert resp.status_code == 404
