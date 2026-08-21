"""F14-S1 litellm_router Vertex provider toggle unit tests (DM-VTX-1/2/3).

_apply_vertex_provider: `gemini/<m>` → `vertex_ai/<m>`, api_key düşer,
vertex_project/location eklenir; alias adları korunur; girdi mutasyona uğramaz.
Canlı çağrı YOK — saf transform (Router kurulmaz).
"""

from __future__ import annotations

import os

import pytest

from api.services.litellm_router import (
    _FALLBACK_MAP,
    _apply_vertex_provider,
    _build_router_config,
)

pytestmark = pytest.mark.unit


class _FakeSettings:
    def __init__(
        self,
        project: str = "translate-500019",
        location: str = "europe-west4",
        cred: str = "",
        provider: str = "gemini",
        fallback_enabled: bool = True,
        anthropic_key: str = "",
    ) -> None:
        self.VERTEX_PROJECT = project
        self.VERTEX_LOCATION = location
        self.GOOGLE_APPLICATION_CREDENTIALS = cred
        self.LLM_PROVIDER = provider
        self.LLM_FALLBACK_ENABLED = fallback_enabled
        self.ANTHROPIC_API_KEY = anthropic_key


def _sample_model_list() -> list[dict]:
    return [
        {
            "model_name": "gemini-flash-tr",
            "litellm_params": {
                "model": "gemini/gemini-2.5-flash",
                "api_key": "secret-key",
                "max_tokens": 600,
                "temperature": 0.2,
            },
        },
        {
            "model_name": "gemini-pro-tiebreak",
            "litellm_params": {
                "model": "gemini/gemini-2.5-pro",
                "api_key": "secret-key",
                "max_tokens": 800,
                "temperature": 0.1,
            },
        },
    ]


def test_vertex_maps_model_prefix() -> None:
    out = _apply_vertex_provider(_sample_model_list(), _FakeSettings())
    models = {m["model_name"]: m["litellm_params"]["model"] for m in out}
    assert models["gemini-flash-tr"] == "vertex_ai/gemini-2.5-flash"
    assert models["gemini-pro-tiebreak"] == "vertex_ai/gemini-2.5-pro"


def test_vertex_drops_api_key_and_adds_project_location() -> None:
    out = _apply_vertex_provider(_sample_model_list(), _FakeSettings())
    for m in out:
        p = m["litellm_params"]
        assert "api_key" not in p
        assert p["vertex_project"] == "translate-500019"
        assert p["vertex_location"] == "europe-west4"
        assert "max_tokens" in p  # diğer paramlar korunur


def test_vertex_aliases_preserved() -> None:
    """Alias adları (DM-VTX-3) değişmez — kod resolve'u bozulmaz."""
    src = _sample_model_list()
    out = _apply_vertex_provider(src, _FakeSettings())
    assert [m["model_name"] for m in out] == [m["model_name"] for m in src]


def test_vertex_does_not_mutate_input() -> None:
    src = _sample_model_list()
    _apply_vertex_provider(src, _FakeSettings())
    assert src[0]["litellm_params"]["api_key"] == "secret-key"
    assert src[0]["litellm_params"]["model"] == "gemini/gemini-2.5-flash"


def test_vertex_credentials_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    _apply_vertex_provider(_sample_model_list(), _FakeSettings(cred="/keys/sa.json"))
    assert os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "/keys/sa.json"


def test_vertex_missing_project_raises() -> None:
    """Fail-closed: provider=vertex ama proje boşsa net hata (sessiz yanlış çağrı yok)."""
    with pytest.raises(ValueError, match="VERTEX_PROJECT"):
        _apply_vertex_provider(_sample_model_list(), _FakeSettings(project=""))


# --- F14-S2 Claude fallback ---

def _full_model_list() -> list[dict]:
    """gemini alias'ları + claude yedek girdileri (yaml'ın tam karşılığı)."""
    return [
        *_sample_model_list(),
        {
            "model_name": "claude-flash-fallback",
            "litellm_params": {
                "model": "anthropic/claude-sonnet-4-6",
                "api_key": "anthropic-key",
                "max_tokens": 600,
                "temperature": 0.2,
            },
        },
        {
            "model_name": "claude-pro-fallback",
            "litellm_params": {
                "model": "anthropic/claude-sonnet-4-6",
                "api_key": "anthropic-key",
                "max_tokens": 800,
                "temperature": 0.1,
            },
        },
    ]


def test_vertex_leaves_claude_entries_untouched() -> None:
    """Bug guard: vertex dönüşümü Claude (anthropic/) girdilerine dokunmaz."""
    out = _apply_vertex_provider(_full_model_list(), _FakeSettings())
    claude = next(m for m in out if m["model_name"] == "claude-flash-fallback")
    p = claude["litellm_params"]
    assert p["model"] == "anthropic/claude-sonnet-4-6"  # vertex_ai/'ye dönüşmedi
    assert p["api_key"] == "anthropic-key"  # api_key düşmedi
    assert "vertex_project" not in p


def test_fallback_active_builds_mapping() -> None:
    ml, fallbacks = _build_router_config(
        _full_model_list(), _FakeSettings(anthropic_key="anthropic-key")
    )
    assert fallbacks is not None
    flat = {k: v for d in fallbacks for k, v in d.items()}
    assert flat["gemini-flash-tr"] == ["claude-flash-fallback"]
    assert flat["gemini-pro-tiebreak"] == ["claude-pro-fallback"]
    assert set(flat) == set(_FALLBACK_MAP)
    # claude girdileri model_list'te korunur
    assert any(m["model_name"] == "claude-flash-fallback" for m in ml)


def test_fallback_inactive_without_key_drops_claude_entries() -> None:
    ml, fallbacks = _build_router_config(_full_model_list(), _FakeSettings(anthropic_key=""))
    assert fallbacks is None
    assert all(not m["model_name"].endswith("-fallback") for m in ml)


def test_fallback_disabled_toggle_drops_entries() -> None:
    ml, fallbacks = _build_router_config(
        _full_model_list(),
        _FakeSettings(anthropic_key="anthropic-key", fallback_enabled=False),
    )
    assert fallbacks is None
    assert all(not m["model_name"].endswith("-fallback") for m in ml)


def test_vertex_plus_fallback_compose() -> None:
    """provider=vertex + key: gemini'ler vertex'e döner, claude yedek + fallbacks durur."""
    ml, fallbacks = _build_router_config(
        _full_model_list(),
        _FakeSettings(provider="vertex", anthropic_key="anthropic-key"),
    )
    assert fallbacks is not None
    models = {m["model_name"]: m["litellm_params"]["model"] for m in ml}
    assert models["gemini-flash-tr"] == "vertex_ai/gemini-2.5-flash"
    assert models["claude-flash-fallback"] == "anthropic/claude-sonnet-4-6"
