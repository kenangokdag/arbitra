"""F5-S2 translator unit tests — PROMPT #4 §4 DoD (4 senaryo).

  1. success — normal Gemini response → fallback=False, text_en=translated
  2. timeout — asyncio.wait_for timeout → fallback=True, text_en=text_raw
  3. provider failure — Gemini exception → fallback=True, text_en=text_raw
  4. empty input — ValueError (caller bug, hızlı fail)
+ bonus: empty Gemini response string → fallback=True

Router chokepoint mock'lanır: `api.services.translator.acompletion`
(LLMService unit test paterni — test_llm_service.py:51).
"""

from __future__ import annotations

import asyncio
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

    class _Resp:
        def __init__(self, c: str) -> None:
            self.choices = [_Choice(c)]

    return _Resp(content)


async def test_translator_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def fake(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return _fake_response(
            "Multi-criteria decision making for hospital staff performance evaluation"
        )

    monkeypatch.setattr("api.services.translator.acompletion", fake)

    from api.services.translator import translate_to_academic_en

    result = await translate_to_academic_en(
        "çok kriterli karar verme yöntemleriyle hastane personeli performans değerlendirmesi",
        source_lang_hint="tr",
    )

    assert result.fallback is False
    assert "decision making" in result.text_en.lower()
    assert result.source_lang == "tr"
    assert result.duration_ms >= 0

    # HK-2: model alias config'den (gemini-flash-tr → gemini/gemini-2.5-flash)
    assert captured["model"] == "gemini-flash-tr"
    assert captured["temperature"] == 0.1
    assert captured["max_tokens"] == 600
    # System prompt sıkı tutuldu (brief §1.A)
    sys_msg = captured["messages"][0]
    assert sys_msg["role"] == "system"
    assert "akademik bir çevirmensin" in sys_msg["content"]
    assert "SADECE çeviri" in sys_msg["content"]
    # User prompt'a hint inject edildi
    user_msg = captured["messages"][1]
    assert "Kaynak dil: tr" in user_msg["content"]


async def test_translator_timeout_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow(**_: Any) -> Any:
        await asyncio.sleep(10)
        return _fake_response("never reached")

    monkeypatch.setattr("api.services.translator.acompletion", slow)
    # Test hızı için timeout sabitini kısalt (modül-seviye lookup)
    monkeypatch.setattr(
        "api.services.translator._TRANSLATION_TIMEOUT_SECONDS", 0.05
    )

    from api.services.translator import translate_to_academic_en

    result = await translate_to_academic_en(
        "uzun çeviri talebi", source_lang_hint="tr"
    )

    assert result.fallback is True
    assert result.text_en == "uzun çeviri talebi"
    assert result.source_lang == "tr"
    assert result.duration_ms >= 0


async def test_translator_provider_failure_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(**_: Any) -> Any:
        raise RuntimeError("Gemini quota exceeded")

    monkeypatch.setattr("api.services.translator.acompletion", boom)

    from api.services.translator import translate_to_academic_en

    result = await translate_to_academic_en("merhaba", source_lang_hint=None)

    assert result.fallback is True
    assert result.text_en == "merhaba"
    # source_lang_hint=None → "unknown" (raw dili etiketleme)
    assert result.source_lang == "unknown"


async def test_translator_empty_input_raises() -> None:
    from api.services.translator import translate_to_academic_en

    with pytest.raises(ValueError, match="empty"):
        await translate_to_academic_en("")

    with pytest.raises(ValueError, match="empty"):
        await translate_to_academic_en("   ")


async def test_translator_empty_response_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bonus: Gemini boş string döndürse de fallback davranışı (K-015)."""

    async def empty(**_: Any) -> Any:
        return _fake_response("   ")

    monkeypatch.setattr("api.services.translator.acompletion", empty)

    from api.services.translator import translate_to_academic_en

    result = await translate_to_academic_en("test", source_lang_hint="tr")

    assert result.fallback is True
    assert result.text_en == "test"
