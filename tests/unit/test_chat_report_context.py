"""Plan: docs/plans/DANISMAN_REPORT_GROUNDING_PERSONA_2026-08-16.md §5.

Coverage: _build_report_context (LookupError → silent None, BOLA reuse) +
_cache_key report_id ayrımı (cache-karışması regresyon guard'ı) + uçtan uca
/api/chat'in report_id verildiğinde review_service.get_report'u çağırıp rapor
özetini prompt'a enjekte ettiği.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from api.models.chat import ChatMessage, ChatRequest
from api.models.review import ManuscriptMeta, ReviewProvenance, ReviewReport

pytestmark = pytest.mark.unit


def _make_report() -> ReviewReport:
    return ReviewReport(
        mode="author",
        language="tr",
        manuscript_meta=ManuscriptMeta(title="T"),
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


# --- _build_report_context ---------------------------------------------------


async def test_build_report_context_none_when_no_report_id() -> None:
    from api.routes.chat import _build_report_context

    result = await _build_report_context("user-1", None)
    assert result is None


async def test_build_report_context_returns_report(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.routes import chat as chat_module

    report = _make_report()
    report_id = uuid4()

    async def fake_get_report(user_id: str, job_id: UUID) -> ReviewReport:
        assert user_id == "user-1"
        assert job_id == report_id
        return report

    monkeypatch.setattr(chat_module.review_service, "get_report", fake_get_report)

    result = await chat_module._build_report_context("user-1", report_id)
    assert result is report


async def test_build_report_context_lookup_error_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BOLA-safe: review_service.get_report başka kullanıcının raporu için
    LookupError fırlatır (review_service.py:723-730) — chat sohbeti çökmemeli,
    sessizce bağlamsız devam etmeli (_build_paper_context deseniyle TUTARLI)."""
    from api.routes import chat as chat_module

    async def boom(user_id: str, job_id: UUID) -> ReviewReport:
        raise LookupError("review job not found")

    monkeypatch.setattr(chat_module.review_service, "get_report", boom)

    result = await chat_module._build_report_context("user-1", uuid4())
    assert result is None


# --- _cache_key ---------------------------------------------------------------


def _req(report_id: UUID | None) -> ChatRequest:
    return ChatRequest(
        session_id="s1",
        messages=[ChatMessage(role="user", content="soru")],
        language="tr",
        mode="review_advisor",
        report_id=report_id,
    )


def test_cache_key_differs_by_report_id() -> None:
    """report_id cache-key'e dahil edilmezse iki farklı rapor bağlamlı istek
    aynı cache-key'i üretir → yanlış rapordan cevap servis edilir (sessiz
    veri-karışması). Bu regresyon guard'ı bunu önlüyor."""
    from api.routes.chat import _cache_key

    key_a = _cache_key(_req(uuid4()))
    key_b = _cache_key(_req(uuid4()))
    key_none = _cache_key(_req(None))

    assert key_a != key_b
    assert key_a != key_none


# --- uçtan uca /api/chat -------------------------------------------------------


def _fake_llm_response(content: str = "rapora göre cevap") -> Any:
    class _Msg:
        def __init__(self, c: str) -> None:
            self.content = c

    class _Choice:
        def __init__(self, c: str) -> None:
            self.message = _Msg(c)

    class _Usage:
        prompt_tokens = 80
        completion_tokens = 40

    class _Resp:
        def __init__(self, c: str) -> None:
            self.choices = [_Choice(c)]
            self.usage = _Usage()

    return _Resp(content)


@pytest.fixture
def report_chat_client(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, dict[str, Any], ReviewReport, UUID]:
    seen: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> Any:
        seen.update(kwargs)
        return _fake_llm_response()

    report = _make_report()
    report_id = uuid4()

    async def fake_get_report(user_id: str, job_id: UUID) -> ReviewReport:
        seen["get_report_user_id"] = user_id
        seen["get_report_job_id"] = job_id
        return report

    monkeypatch.setattr("api.services.llm_service.acompletion", fake_acompletion)
    monkeypatch.setattr("api.routes.chat.review_service.get_report", fake_get_report)
    monkeypatch.setattr("api.routes.chat.cache_get", lambda *a, **kw: None)
    monkeypatch.setattr("api.routes.chat.cache_set", lambda *a, **kw: None)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from api.main import create_app

    client = TestClient(create_app())
    token = jwt.encode({"sub": "user-report-1"}, "x", algorithm="HS256")
    client.headers["Authorization"] = f"Bearer {token}"
    return client, seen, report, report_id


def test_chat_route_injects_report_context(
    report_chat_client: tuple[TestClient, dict[str, Any], ReviewReport, UUID],
) -> None:
    client, seen, report, report_id = report_chat_client
    resp = client.post(
        "/api/chat",
        json={
            "session_id": "s1",
            "messages": [{"role": "user", "content": "bu makale kabul mü?"}],
            "language": "tr",
            "mode": "review_advisor",
            "report_id": str(report_id),
        },
    )
    assert resp.status_code == 200, resp.text
    assert seen["get_report_user_id"] == "user-report-1"
    assert seen["get_report_job_id"] == report_id
    system = seen["messages"][0]["content"]
    assert "accept" in system
    assert "hakem-raporu danışmanısın" in system


def test_chat_route_no_report_id_skips_report_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> Any:
        seen.update(kwargs)
        return _fake_llm_response()

    def fail_if_called(*a: Any, **kw: Any) -> Any:
        raise AssertionError("get_report report_id yokken çağrılmamalı")

    monkeypatch.setattr("api.services.llm_service.acompletion", fake_acompletion)
    monkeypatch.setattr("api.routes.chat.review_service.get_report", fail_if_called)
    monkeypatch.setattr("api.routes.chat.cache_get", lambda *a, **kw: None)
    monkeypatch.setattr("api.routes.chat.cache_set", lambda *a, **kw: None)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from api.main import create_app

    client = TestClient(create_app())
    token = jwt.encode({"sub": "user-report-2"}, "x", algorithm="HS256")
    client.headers["Authorization"] = f"Bearer {token}"

    resp = client.post(
        "/api/chat",
        json={
            "session_id": "s2",
            "messages": [{"role": "user", "content": "merhaba"}],
            "language": "tr",
        },
    )
    assert resp.status_code == 200, resp.text
    system = seen["messages"][0]["content"]
    assert "Verdict:" not in system
