"""Presenter — dil-spesifik son kullanıcı sunumu (B-005 + B-007 + DM-015, F8 DM-LLM-1).

F8 unification: 3-dil tek provider — Gemini 2.5 Flash (LiteLLM router):
  - TR → ${PRESENTER_TR_MODEL} (gemini-flash-tr)
  - EN → ${PRESENTER_EN_MODEL} (gemini-flash-en)
  - ID → ${PRESENTER_ID_MODEL} (gemini-flash-id)

Mimari: Curator output'unu (signals_13 dict + citations) **kullanıcı dilinde**
1-2 cümlelik PaperCard summary'ye çevirir. /api/summarize (F3c) ve /api/chat
(F3b) endpoint'lerinde de aynı servis kullanılır.

Notlar:
- Async API; LiteLLM `acompletion` (async chat-completion wrapper).
- HK-1 Pydantic forbid Output; HK-3 live smoke fixture (R13.11); HK-7 seed
  temperature=0.2; HK-2 model_id kaynağı `config/litellm_models.yaml`.
- Constructor injection: `completion` callable testlerde mock; production
  None → litellm.acompletion lazy import.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.config import Settings, get_settings

logger = logging.getLogger(__name__)


class Presenter(ABC):
    """Curator output'unu kullanıcı dilinde son metne çeviren servis."""

    @abstractmethod
    async def present(
        self,
        text: str,
        lang: str,
        *,
        max_tokens: int = 200,
    ) -> str:
        """Verilen metni `lang` diline 1-2 cümlelik akademik sunum yapar.

        K11 fallback: LLM FAIL/timeout/empty durumunda input metni geri döner
        (boş dönmez — son kullanıcı blanks görmemeli).
        """
        ...


class _PresenterOutput(BaseModel):
    """HK-1 Pydantic forbid (R13.10)."""

    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1)


_CompletionAsync = Callable[..., Awaitable[Any]]


_SUPPORTED_LANGS: frozenset[str] = frozenset({"tr", "en", "id"})


class DilSpesifikPresenter(Presenter):
    """LiteLLM 3-dil router (TR / EN / ID).

    Constructor injection: `completion_async` testlerde mock; production None
    → `litellm.acompletion` lazy import (DM-015 + B-005).
    """

    def __init__(
        self,
        settings: Settings | None = None,
        completion_async: _CompletionAsync | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._completion = completion_async

    def _resolve_model(self, lang: str) -> str:
        normalized = lang.lower().strip()
        if normalized not in _SUPPORTED_LANGS:
            logger.info(
                "Presenter unknown lang=%s → TR fallback (%s)",
                lang,
                self._settings.PRESENTER_TR_MODEL,
            )
            normalized = "tr"
        match normalized:
            case "tr":
                return self._settings.PRESENTER_TR_MODEL
            case "en":
                return self._settings.PRESENTER_EN_MODEL
            case "id":
                return self._settings.PRESENTER_ID_MODEL
            case _:
                return self._settings.PRESENTER_TR_MODEL

    async def present(
        self,
        text: str,
        lang: str,
        *,
        max_tokens: int = 200,
    ) -> str:
        if not text:
            return ""
        model = self._resolve_model(lang)
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPTS.get(lang.lower(), _SYSTEM_PROMPTS["tr"])},
            {"role": "user", "content": text},
        ]
        try:
            completion = self._completion or await self._load_default_completion()
            response = await completion(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.2,
                timeout=self._settings.LITELLM_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            # K11 fallback: kullanıcıya ham metni göster, halüsinasyon yarat ma.
            logger.warning(
                "Presenter LiteLLM fail lang=%s model=%s err=%s; K11 fallback",
                lang,
                model,
                type(exc).__name__,
            )
            return text

        try:
            content = self._extract_content(response)
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            logger.warning(
                "Presenter response parse fail err=%s; K11 fallback",
                type(exc).__name__,
            )
            return text

        if not content:
            return text
        try:
            validated = _PresenterOutput(text=content)
        except (TypeError, ValueError):
            return text
        return validated.text

    @staticmethod
    def _extract_content(response: Any) -> str:
        # LiteLLM response objesi chat-completion şemasında: response.choices[0].message.content
        if hasattr(response, "choices"):
            choices = response.choices
        elif isinstance(response, dict):
            choices = response.get("choices", [])
        else:
            return ""
        if not choices:
            return ""
        first = choices[0]
        if hasattr(first, "message"):
            message = first.message
            if hasattr(message, "content"):
                content = message.content
            elif isinstance(message, dict):
                content = message.get("content", "")
            else:
                content = ""
        elif isinstance(first, dict):
            content = first.get("message", {}).get("content", "")
        else:
            content = ""
        return str(content) if content is not None else ""

    async def _load_default_completion(self) -> _CompletionAsync:
        # Lazy import; LiteLLM ~80MB transitive deps.
        # Router singleton config/litellm_models.yaml'ı yükler + env-sub yapar.
        from api.services.litellm_router import acompletion

        completion: _CompletionAsync = acompletion
        self._completion = completion
        return completion


_SYSTEM_PROMPTS: dict[str, str] = {
    "tr": (
        "Sen akademik literatür sunum asistanısın. Verilen metni Türkçe "
        "akademik dilde 1-2 cümleyle yeniden yaz. Bilgi ekleme, çıkarma; "
        "yorum yapma; sayıları/yılları/yazarları olduğu gibi koru."
    ),
    "en": (
        "You are an academic literature presentation assistant. Rewrite the "
        "given text in concise English academic prose (1-2 sentences). "
        "Do not add or remove information; preserve numbers, years, authors."
    ),
    "id": (
        "Anda adalah asisten presentasi literatur akademik. Tulis ulang teks "
        "yang diberikan dalam bahasa Indonesia akademik singkat (1-2 kalimat). "
        "Jangan menambah atau mengurangi informasi; pertahankan angka/tahun/penulis."
    ),
}


__all__ = ["DilSpesifikPresenter", "Presenter"]
