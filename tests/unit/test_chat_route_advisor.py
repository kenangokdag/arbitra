"""F8 chat route advisor mode tests (DM-LLM-3/7).

Coverage: 3 pilot ROLE_MODULE (topic/method/gap) farklı role brief inject eder +
project_id None ise project context injection skip edilir.
"""

from __future__ import annotations

from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


def _fake_response(content: str = "advice text") -> Any:
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
def chat_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, dict[str, Any]]:
    seen: dict[str, Any] = {}

    async def fake(**kwargs: Any) -> Any:
        seen.update(kwargs)
        return _fake_response()

    monkeypatch.setattr("api.services.llm_service.acompletion", fake)
    # Redis aktifken testler arası cache hit'ini engelle (session_id+mode+message kollizyonu).
    monkeypatch.setattr("api.routes.chat.cache_get", lambda *a, **kw: None)
    monkeypatch.setattr("api.routes.chat.cache_set", lambda *a, **kw: None)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from api.main import create_app

    client = TestClient(create_app())
    token = jwt.encode({"sub": "user-chat-1"}, "x", algorithm="HS256")
    client.headers["Authorization"] = f"Bearer {token}"
    return client, seen


def _post_chat(client: TestClient, mode: str, project_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "session_id": "s1",
        "messages": [{"role": "user", "content": "yardım eder misin?"}],
        "language": "tr",
        "mode": mode,
    }
    if project_id is not None:
        payload["project_id"] = project_id
    r = client.post("/api/chat", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_chat_route_advisor_mode_topic_exploration(chat_client: tuple[TestClient, dict[str, Any]]) -> None:
    client, seen = chat_client
    _post_chat(client, mode="topic_exploration")
    system = seen["messages"][0]["content"]
    assert "Topic Exploration" in system
    assert "konu kartı" in system or "gap" in system.lower()


def test_chat_route_advisor_mode_method_selection(chat_client: tuple[TestClient, dict[str, Any]]) -> None:
    client, seen = chat_client
    _post_chat(client, mode="method_selection")
    system = seen["messages"][0]["content"]
    assert "Method Selection" in system
    assert "metod" in system.lower()


def test_chat_route_advisor_mode_gap_heatmap(chat_client: tuple[TestClient, dict[str, Any]]) -> None:
    client, seen = chat_client
    _post_chat(client, mode="gap_heatmap")
    system = seen["messages"][0]["content"]
    assert "Gap Heatmap" in system
    assert "heatmap" in system.lower() or "density" in system.lower()


def test_chat_route_no_project_id_skips_context_injection(chat_client: tuple[TestClient, dict[str, Any]]) -> None:
    client, seen = chat_client
    _post_chat(client, mode="topic_exploration", project_id=None)
    system = seen["messages"][0]["content"]
    assert "Proje bağlamı" not in system
