"""F8 GeminiListener unit tests (DM-LLM-10).

Coverage: 3-5 sub_queries returned + LLMServiceError fallback to [query] +
parsed_output None fallback. Router chokepoint mock'lanır.
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.unit


def _fake_response(content: str) -> Any:
    class _Msg:
        def __init__(self, c: str) -> None:
            self.content = c

    class _Choice:
        def __init__(self, c: str) -> None:
            self.message = _Msg(c)

    class _Usage:
        prompt_tokens = 50
        completion_tokens = 30

    class _Resp:
        def __init__(self, c: str) -> None:
            self.choices = [_Choice(c)]
            self.usage = _Usage()

    return _Resp(content)


async def test_listener_gemini_subqueries_3_to_5(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(**_: Any) -> Any:
        return _fake_response('{"sub_queries":["q1","q2","q3","q4"]}')

    monkeypatch.setattr("api.services.llm_service.acompletion", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from api.services.listener import GeminiListener

    listener = GeminiListener()
    out = await listener.listen("burnout", lang="tr")
    assert 3 <= len(out) <= 5
    assert out == ["q1", "q2", "q3", "q4"]


async def test_listener_invalid_json_fallback_to_query(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(**_: Any) -> Any:
        raise RuntimeError("api down")

    monkeypatch.setattr("api.services.llm_service.acompletion", boom)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from api.services.listener import GeminiListener

    listener = GeminiListener()
    out = await listener.listen("burnout", lang="tr")
    assert out == ["burnout"]
