"""F5-S2 Translation service — user-language → academic English.

PROMPT #4 §1.A. Brain.md:
- K-010 (system internal language = English)
- K-014 (production LLM = Gemini 2.5 Flash via LiteLLM)
- K-015 (graceful fallback, 502 yasak — onboarding tıkanmaz)
- K-016 (cache YOK, MVP)

Sözleşme:
  translate_to_academic_en(text_raw, source_lang_hint=None) → TranslationResult
    - LiteLLM router (`gemini-flash-tr` alias → gemini/gemini-2.5-flash)
    - 5sn timeout (asyncio.wait_for)
    - timeout / provider fail / boş response → fallback=True, text_en=text_raw
    - empty input → ValueError (caller validate etmeli)

HK-1 Pydantic forbid; HK-6 strict types; HK-2 model alias config'den
(`config/litellm_models.yaml` → gemini-flash-tr).
"""

from __future__ import annotations

import asyncio
import logging
import time

from pydantic import BaseModel, ConfigDict, Field

from api.services.litellm_router import acompletion

logger = logging.getLogger(__name__)

_TRANSLATION_TIMEOUT_SECONDS = 5.0
_TRANSLATION_MODEL = "gemini-flash-tr"
_TRANSLATION_MAX_TOKENS = 600
_TRANSLATION_TEMPERATURE = 0.1

_SYSTEM_PROMPT = (
    "Sen akademik bir çevirmensin. Verilen metni akademik İngilizce'ye çevir. "
    "SADECE çeviri döndür, açıklama yapma, markdown kullanma, soru sorma."
)


class TranslationResult(BaseModel):
    """Translation output — onboarding `metadata.translation_meta` jsonb kanon."""

    model_config = ConfigDict(extra="forbid")

    text_en: str = Field(min_length=1)
    source_lang: str = Field(min_length=2, max_length=16)
    duration_ms: int = Field(ge=0)
    fallback: bool


def _build_user_prompt(text_raw: str, source_lang_hint: str | None) -> str:
    if source_lang_hint:
        return f"Kaynak dil: {source_lang_hint}\n\nMetin:\n{text_raw}"
    return text_raw


def _fallback(
    text_raw: str, source_lang_hint: str | None, duration_ms: int
) -> TranslationResult:
    return TranslationResult(
        text_en=text_raw,
        source_lang=source_lang_hint or "unknown",
        duration_ms=duration_ms,
        fallback=True,
    )


async def translate_to_academic_en(
    text_raw: str,
    source_lang_hint: str | None = None,
) -> TranslationResult:
    """Translate user-language text to academic English (graceful fallback).

    Args:
        text_raw: Source text (non-empty after strip).
        source_lang_hint: ISO 639-1 hint (e.g. "tr"); None → Gemini auto-detect.

    Returns:
        TranslationResult with fallback=True on any failure path
        (text_en=text_raw kept). Never raises on Gemini errors.

    Raises:
        ValueError: text_raw is empty/whitespace (caller-side bug).
    """
    if not text_raw or not text_raw.strip():
        raise ValueError("text_raw cannot be empty")

    user_prompt = _build_user_prompt(text_raw, source_lang_hint)
    t0 = time.perf_counter()

    try:
        response = await asyncio.wait_for(
            acompletion(
                model=_TRANSLATION_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=_TRANSLATION_TEMPERATURE,
                max_tokens=_TRANSLATION_MAX_TOKENS,
            ),
            timeout=_TRANSLATION_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.warning(
            "translator.timeout duration_ms=%d hint=%s text_len=%d — fallback",
            duration_ms,
            source_lang_hint or "auto",
            len(text_raw),
        )
        return _fallback(text_raw, source_lang_hint, duration_ms)
    except Exception as e:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.warning(
            "translator.fail duration_ms=%d hint=%s err=%s — fallback",
            duration_ms,
            source_lang_hint or "auto",
            type(e).__name__,
        )
        return _fallback(text_raw, source_lang_hint, duration_ms)

    duration_ms = int((time.perf_counter() - t0) * 1000)
    raw_content = response.choices[0].message.content
    text_en = (raw_content or "").strip()
    if not text_en:
        logger.warning(
            "translator.empty_response duration_ms=%d hint=%s — fallback",
            duration_ms,
            source_lang_hint or "auto",
        )
        return _fallback(text_raw, source_lang_hint, duration_ms)

    return TranslationResult(
        text_en=text_en,
        source_lang=source_lang_hint or "auto",
        duration_ms=duration_ms,
        fallback=False,
    )


__all__ = ["TranslationResult", "translate_to_academic_en"]
