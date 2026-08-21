"""Listener — query rewrite + multi-query expansion (B42-045 §1, F8 DM-LLM-10).

F8 unification: önceki çoklu-provider sınıfları kaldırıldı; tek implementasyon GeminiListener.
GeminiListener LLMService üzerinden Gemini 2.5 Flash kullanır (yapısal JSON output).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field

from api.services.llm_service import LLMServiceError
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)


class _ListenerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sub_queries: list[str] = Field(min_length=3, max_length=5)


class Listener(ABC):
    @abstractmethod
    async def listen(self, query: str, *, lang: str = "en") -> list[str]:
        """Original query → 3-5 alt sorgu."""


class GeminiListener(Listener):
    """Gemini 2.5 Flash ile alt-sorgu üretimi (DM-LLM-1)."""

    PROMPT_TEMPLATE = (
        "Kullanıcı sorgusunu 3-5 alt sorguya genişlet. "
        "Her alt sorgu OpenAlex'te aranabilir, kısa, semantik anlamlı olmalı. "
        "Çıktı JSON: {{\"sub_queries\": [\"...\", ...]}}\n\n"
        "Dil: {lang}\nSorgu: {query}"
    )

    async def listen(self, query: str, *, lang: str = "en") -> list[str]:
        prompt = self.PROMPT_TEMPLATE.format(lang=lang, query=query)
        try:
            resp = await llm_call(
                prompt=prompt,
                tier="flash",
                mode="listener",
                structured_output_schema=_ListenerOutput,
                max_tokens=1500,
            )
        except LLMServiceError:
            logger.warning("listener LLM call failed; fallback = [query]")
            return [query]

        if not isinstance(resp.parsed_output, _ListenerOutput):
            logger.warning("listener parsed_output invalid; fallback = [query]")
            return [query]

        return resp.parsed_output.sub_queries


__all__ = ["GeminiListener", "Listener"]
