"""P009 DilSpesifikPresenter unit tests — completion injection (LiteLLM yok).

Coverage: 3-dil routing (TR/EN/ID) + unknown lang fallback to TR + LLM error
K11 fallback (input metni döner) + Pydantic forbid + system prompt selection.
"""

from __future__ import annotations

from typing import Any

import pytest

from api.config import Settings
from api.services.presenter import DilSpesifikPresenter, Presenter

pytestmark = pytest.mark.unit


def _settings() -> Settings:
    return Settings(  # type: ignore[arg-type]
        PRESENTER_TR_MODEL="gemini-flash-tr",
        PRESENTER_EN_MODEL="gemini-flash-en",
        PRESENTER_ID_MODEL="gemini-flash-id",
        LITELLM_TIMEOUT_SECONDS=10,
    )


def _ok_response(text: str) -> dict[str, Any]:
    return {"choices": [{"message": {"content": text}}]}


async def test_presenter_abstract_cannot_instantiate() -> None:
    with pytest.raises(TypeError, match="abstract"):
        Presenter()  # type: ignore[abstract]


async def test_presenter_empty_text_returns_empty() -> None:
    presenter = DilSpesifikPresenter(
        settings=_settings(),
        completion_async=lambda **_: _async_value(_ok_response("ignored")),
    )
    result = await presenter.present("", lang="tr")
    assert result == ""


async def test_presenter_tr_routes_to_tr_model() -> None:
    seen: dict[str, Any] = {}

    async def fake(**kwargs: Any) -> dict[str, Any]:
        seen.update(kwargs)
        return _ok_response("Türkçe akademik özet.")

    presenter = DilSpesifikPresenter(settings=_settings(), completion_async=fake)
    result = await presenter.present("kaynak metin", lang="tr")
    assert result == "Türkçe akademik özet."
    assert seen["model"] == "gemini-flash-tr"
    system = seen["messages"][0]["content"]
    assert "Türkçe" in system or "akademik" in system.lower()


async def test_presenter_en_routes_to_en_model() -> None:
    seen: dict[str, Any] = {}

    async def fake(**kwargs: Any) -> dict[str, Any]:
        seen.update(kwargs)
        return _ok_response("English academic prose.")

    presenter = DilSpesifikPresenter(settings=_settings(), completion_async=fake)
    result = await presenter.present("source text", lang="en")
    assert result == "English academic prose."
    assert seen["model"] == "gemini-flash-en"


async def test_presenter_id_routes_to_id_model() -> None:
    seen: dict[str, Any] = {}

    async def fake(**kwargs: Any) -> dict[str, Any]:
        seen.update(kwargs)
        return _ok_response("Ringkasan akademik.")

    presenter = DilSpesifikPresenter(settings=_settings(), completion_async=fake)
    result = await presenter.present("teks sumber", lang="id")
    assert result == "Ringkasan akademik."
    assert seen["model"] == "gemini-flash-id"


async def test_presenter_unknown_lang_falls_back_to_tr() -> None:
    seen: dict[str, Any] = {}

    async def fake(**kwargs: Any) -> dict[str, Any]:
        seen.update(kwargs)
        return _ok_response("fallback content")

    presenter = DilSpesifikPresenter(settings=_settings(), completion_async=fake)
    await presenter.present("metin", lang="zz-unknown")
    assert seen["model"] == "gemini-flash-tr"


async def test_presenter_completion_failure_returns_input_k11_fallback() -> None:
    async def boom(**_: Any) -> dict[str, Any]:
        raise RuntimeError("LiteLLM provider down")

    presenter = DilSpesifikPresenter(settings=_settings(), completion_async=boom)
    result = await presenter.present("orijinal metin", lang="tr")
    assert result == "orijinal metin"


async def test_presenter_empty_completion_returns_input() -> None:
    async def fake(**_: Any) -> dict[str, Any]:
        return _ok_response("")

    presenter = DilSpesifikPresenter(settings=_settings(), completion_async=fake)
    result = await presenter.present("orig", lang="tr")
    assert result == "orig"


async def test_presenter_response_dict_format_works() -> None:
    async def fake(**_: Any) -> dict[str, Any]:
        return {"choices": [{"message": {"content": "ok"}}]}

    presenter = DilSpesifikPresenter(settings=_settings(), completion_async=fake)
    result = await presenter.present("x", lang="en")
    assert result == "ok"


async def test_presenter_response_object_format_works() -> None:
    class _Msg:
        content = "object format ok"

    class _Choice:
        message = _Msg()

    class _Resp:
        def __init__(self) -> None:
            self.choices = [_Choice()]

    async def fake(**_: Any) -> _Resp:
        return _Resp()

    presenter = DilSpesifikPresenter(settings=_settings(), completion_async=fake)
    result = await presenter.present("x", lang="en")
    assert result == "object format ok"


async def test_presenter_temperature_and_timeout_propagated() -> None:
    seen: dict[str, Any] = {}

    async def fake(**kwargs: Any) -> dict[str, Any]:
        seen.update(kwargs)
        return _ok_response("ok")

    presenter = DilSpesifikPresenter(settings=_settings(), completion_async=fake)
    await presenter.present("x", lang="tr", max_tokens=120)
    assert seen["temperature"] == 0.2
    assert seen["max_tokens"] == 120
    assert seen["timeout"] == 10


async def _async_value(value: Any) -> Any:
    return value
