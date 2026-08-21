"""V1-S11-01 unit: translate_query role module + QueryTranslationLLM schema.

kaynak: docs/plans/V1_S11_cift_dil_arama.md §6 (LLM unit)
"""

from __future__ import annotations

from typing import Any

import pytest


def _fake_response(text: str) -> Any:
    class _Msg:
        def __init__(self, content: str) -> None:
            self.content = content

    class _Choice:
        def __init__(self, content: str) -> None:
            self.message = _Msg(content)

    class _Usage:
        prompt_tokens = 10
        completion_tokens = 5

    class _Resp:
        choices = [_Choice(text)]
        usage = _Usage()

    return _Resp()


def test_translate_query_brief_registered() -> None:
    """ROLE_MODULES dict'inde 'translate_query' anahtarı + brief içeriği var."""
    from api.services.role_modules import ROLE_MODULES

    assert "translate_query" in ROLE_MODULES
    brief = ROLE_MODULES["translate_query"]
    assert "english_query" in brief
    assert "detected_lang" in brief
    # KD-V1-S11-02: girdi zaten EN ise english_query == original (skip 2. arama)
    assert "BİREBİR" in brief or "birebir" in brief or "aynı" in brief


def test_query_translation_llm_pydantic_schema() -> None:
    """QueryTranslationLLM extra=forbid + Literal lang validation."""
    from api.models.q import QueryTranslationLLM

    valid = QueryTranslationLLM(
        detected_lang="tr", english_query="transformer attention"
    )
    assert valid.detected_lang == "tr"
    assert valid.english_query == "transformer attention"

    # Geçersiz lang reddedilir
    with pytest.raises(Exception):  # pydantic ValidationError
        QueryTranslationLLM(detected_lang="de", english_query="x")  # type: ignore[arg-type]

    # extra alan reddedilir (HK-1 forbid)
    with pytest.raises(Exception):
        QueryTranslationLLM(  # type: ignore[call-arg]
            detected_lang="en", english_query="x", confidence="high"
        )


def test_query_translation_full_pydantic_schema() -> None:
    """QueryTranslation (response field) — original + detected + english."""
    from api.models.q import QueryTranslation

    t = QueryTranslation(
        original="transformer dikkat",
        detected_lang="tr",
        english_query="transformer attention",
    )
    assert t.original == "transformer dikkat"
    # frozen
    with pytest.raises(Exception):
        t.original = "x"  # type: ignore[misc]


@pytest.mark.asyncio
async def test_llm_call_translate_query_mode_injects_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """call(mode='translate_query') sistem prompt'a translate brief'ini koyar."""
    captured: dict[str, Any] = {}

    async def fake(**kwargs: Any) -> Any:
        captured["messages"] = kwargs["messages"]
        return _fake_response(
            '{"detected_lang": "tr", "english_query": "transformer attention"}'
        )

    monkeypatch.setattr("api.services.llm_service.acompletion", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from api.models.q import QueryTranslationLLM
    from api.services.llm_service import call

    resp = await call(
        prompt="transformer dikkat",
        tier="flash",
        mode="translate_query",
        structured_output_schema=QueryTranslationLLM,
    )

    system_msg = captured["messages"][0]["content"]
    assert "english_query" in system_msg  # brief inject doğrulama
    assert isinstance(resp.parsed_output, QueryTranslationLLM)
    assert resp.parsed_output.detected_lang == "tr"
    assert resp.parsed_output.english_query == "transformer attention"


@pytest.mark.asyncio
async def test_llm_call_translate_query_skip_when_already_english(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Girdi EN ise LLM english_query == original döndürür (caller 2. arama atlar)."""

    async def fake(**_: Any) -> Any:
        return _fake_response(
            '{"detected_lang": "en", "english_query": "transformer attention"}'
        )

    monkeypatch.setattr("api.services.llm_service.acompletion", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from api.models.q import QueryTranslationLLM
    from api.services.llm_service import call

    resp = await call(
        prompt="transformer attention",
        tier="flash",
        mode="translate_query",
        structured_output_schema=QueryTranslationLLM,
    )
    assert resp.parsed_output is not None
    assert resp.parsed_output.detected_lang == "en"
    assert resp.parsed_output.english_query == "transformer attention"
