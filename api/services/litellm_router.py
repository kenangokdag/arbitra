"""F8 LiteLLM Router singleton — alias resolution chokepoint (DM-LLM-1).

Tek doğru kaynak: `config/litellm_models.yaml` (model_list + router_settings).
Tüm LLM çağrıları (LLMService, Presenter) bu modülün `acompletion()` fonksiyonu
üzerinden geçer; `model="gemini-flash-tr"` gibi alias'lar Router tarafından
`gemini/gemini-2.5-flash` provider model'ine resolve edilir.

Env var substitution: yaml'daki `${GEMINI_API_KEY}` runtime'da
`os.environ`'dan çözülür.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from litellm.router import Router

from api.config import get_settings

_ENV_VAR_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _substitute_env(value: Any, fallback: dict[str, str]) -> Any:
    """`${VAR}` → os.environ[VAR] || fallback[VAR] || "" (avoid leaking placeholder)."""
    if isinstance(value, str):
        return _ENV_VAR_RE.sub(
            lambda m: os.environ.get(m.group(1)) or fallback.get(m.group(1), ""),
            value,
        )
    if isinstance(value, dict):
        return {k: _substitute_env(v, fallback) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_env(v, fallback) for v in value]
    return value


def _apply_vertex_provider(
    model_list: list[dict[str, Any]], settings: Any
) -> list[dict[str, Any]]:
    """LLM_PROVIDER=vertex: `gemini/<m>` alias'larını `vertex_ai/<m>`'e çevir.

    - `api_key` düşülür (Vertex kullanmaz); `vertex_project`/`vertex_location` eklenir.
    - Kimlik ADC üzerinden: `GOOGLE_APPLICATION_CREDENTIALS` (SA JSON yolu) env'e
      yazılır; yaml'a secret gömülmez (DM-VTX-1).
    - Alias adları (gemini-flash-tr ...) ve LLMService kodu değişmez (DM-VTX-3).

    Fail-closed: provider=vertex ama `VERTEX_PROJECT` boşsa sessizce yanlış
    çağrı yapmak yerine net hata ver.
    """
    if not settings.VERTEX_PROJECT:
        raise ValueError(
            "LLM_PROVIDER=vertex ama VERTEX_PROJECT boş. "
            ".env'de VERTEX_PROJECT ve GOOGLE_APPLICATION_CREDENTIALS ayarla."
        )
    cred = settings.GOOGLE_APPLICATION_CREDENTIALS
    if cred:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred

    transformed: list[dict[str, Any]] = []
    for entry in model_list:
        params = dict(entry.get("litellm_params", {}))
        model = params.get("model", "")
        # Yalnız Gemini alias'larını dönüştür; Claude (anthropic/...) fallback
        # girdileri olduğu gibi kalır — api_key'lerini KORU (F14-S2 bug guard).
        if not model.startswith("gemini/"):
            transformed.append(entry)
            continue
        params["model"] = "vertex_ai/" + model[len("gemini/"):]
        params.pop("api_key", None)
        params["vertex_project"] = settings.VERTEX_PROJECT
        params["vertex_location"] = settings.VERTEX_LOCATION
        transformed.append({**entry, "litellm_params": params})
    return transformed


# F14-S2: hangi Gemini alias'ı hangi Claude yedek model_name'ine düşer (DM-VTX-5).
_FALLBACK_MAP: dict[str, str] = {
    "gemini-flash-tr": "claude-flash-fallback",
    "gemini-flash-en": "claude-flash-fallback",
    "gemini-flash-id": "claude-flash-fallback",
    "gemini-pro-tiebreak": "claude-pro-fallback",
}


def _build_router_config(
    model_list: list[dict[str, Any]], settings: Any
) -> tuple[list[dict[str, Any]], list[dict[str, list[str]]] | None]:
    """Vertex toggle + Claude fallback uygula → (model_list, fallbacks).

    Fallback yalnız LLM_FALLBACK_ENABLED + ANTHROPIC_API_KEY varken aktif.
    Pasifken `*-fallback` girdileri model_list'ten düşürülür (boş key'li ölü
    girdi Router'a verilmez) ve fallbacks=None döner.
    """
    if settings.LLM_PROVIDER == "vertex":
        model_list = _apply_vertex_provider(model_list, settings)

    fallback_active = settings.LLM_FALLBACK_ENABLED and bool(settings.ANTHROPIC_API_KEY)
    if not fallback_active:
        model_list = [
            m for m in model_list if not str(m.get("model_name", "")).endswith("-fallback")
        ]
        return model_list, None

    fallbacks = [{primary: [fb]} for primary, fb in _FALLBACK_MAP.items()]
    return model_list, fallbacks


@lru_cache(maxsize=1)
def get_router() -> Router:
    settings = get_settings()
    fallback: dict[str, str] = {
        "GEMINI_API_KEY": settings.GEMINI_API_KEY,
        "ANTHROPIC_API_KEY": settings.ANTHROPIC_API_KEY,
    }
    cfg_path = Path(settings.LITELLM_CONFIG_PATH)
    if not cfg_path.is_absolute():
        cfg_path = Path.cwd() / cfg_path
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    model_list = _substitute_env(raw.get("model_list", []), fallback)
    model_list, fallbacks = _build_router_config(model_list, settings)
    if fallbacks:
        return Router(model_list=model_list, fallbacks=fallbacks)
    return Router(model_list=model_list)


async def acompletion(**kwargs: Any) -> Any:
    return await get_router().acompletion(**kwargs)


__all__ = ["acompletion", "get_router"]
