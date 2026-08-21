"""Pinecone client wrapper (papers-bgem3 dense index, ns=mdv1).

P002: client init + query wrapper + 3 retry.
P011 (2026-05-01): exponential backoff + jitter; async query_async() with timeout
                   via asyncio.wait_for(asyncio.to_thread(...)); singleton getter
                   `get_pinecone_index()` (Council 39 alt-§ 39a).
B-012: D/F/S/year/q_weak/method/lang/v_conf 8-field — Pool Router HARD filter.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from functools import lru_cache
from typing import Any

from pinecone import Pinecone

from api.config import get_settings
from api.utils.resilience import ResilienceTimeoutError, with_timeout

logger = logging.getLogger(__name__)

DEFAULT_NAMESPACE = "mdv1"  # B-012 metadata patch namespace
MAX_RETRY = 3


class PineconeQueryError(Exception):
    """Pinecone query başarısızlık zarfı (retry tükendiğinde raise)."""


@lru_cache
def get_pinecone_client() -> Pinecone:
    """Pinecone SDK singleton."""
    settings = get_settings()
    if not settings.PINECONE_API_KEY:
        raise RuntimeError("PINECONE_API_KEY must be set")
    return Pinecone(api_key=settings.PINECONE_API_KEY)


class PineconeIndexWrapper:
    """`papers-bgem3` index üzerinde retry+backoff aware dense query helper."""

    def __init__(self, index_name: str | None = None) -> None:
        settings = get_settings()
        self._client = get_pinecone_client()
        self._index_name = index_name or settings.PINECONE_INDEX_NAME
        self._index = self._client.Index(self._index_name)
        self._namespace = DEFAULT_NAMESPACE
        self._timeout_seconds = settings.PINECONE_TIMEOUT_SECONDS
        self._retry_base = settings.RETRY_BASE_DELAY_SECONDS
        self._retry_max = settings.RETRY_MAX_DELAY_SECONDS
        self._retry_jitter = settings.RETRY_JITTER

    def query(
        self,
        vector: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
        include_metadata: bool = True,
    ) -> Any:
        """Sync dense query: 3 retry + exponential backoff + jitter.

        Tüm denemeler fail ederse PineconeQueryError raise eder (cause son hata).
        Timeout için `query_async` tercih edilir (event loop seviyesi sınır).
        """
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRY):
            try:
                return self._index.query(
                    vector=vector,
                    top_k=top_k,
                    namespace=self._namespace,
                    filter=filter,
                    include_metadata=include_metadata,
                )
            except Exception as exc:
                # Pinecone v5+ SDK runtime exceptions; broad-except deliberate
                last_exc = exc
                if attempt == MAX_RETRY - 1:
                    break
                delay = min(self._retry_max, self._retry_base * (2 ** attempt))
                if self._retry_jitter:
                    delay *= 0.5 + random.random() * 0.5  # noqa: S311
                logger.warning(
                    "pinecone retry attempt=%d/%d delay=%.2fs error=%s",
                    attempt + 1,
                    MAX_RETRY,
                    delay,
                    exc.__class__.__name__,
                )
                time.sleep(delay)
        assert last_exc is not None
        raise PineconeQueryError(
            f"pinecone query failed after {MAX_RETRY} retries"
        ) from last_exc

    async def query_async(
        self,
        vector: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
        include_metadata: bool = True,
        timeout_seconds: float | None = None,
    ) -> Any:
        """Async wrapper: thread-offload + asyncio timeout.

        Timeout aşılırsa ResilienceTimeoutError. Pinecone retry/backoff zaten
        sync `query()` içinde; bu sarmalayıcı tek bir mantıksal çağrıyı sınırlar.
        """
        timeout = timeout_seconds if timeout_seconds is not None else self._timeout_seconds
        coro = asyncio.to_thread(
            self.query, vector, top_k, filter, include_metadata
        )
        try:
            return await with_timeout(coro, timeout=timeout)
        except ResilienceTimeoutError:
            logger.warning(
                "pinecone query_async timeout=%.1fs top_k=%d filter=%s",
                timeout,
                top_k,
                "yes" if filter else "no",
            )
            raise


@lru_cache
def get_pinecone_index() -> PineconeIndexWrapper:
    """PineconeIndexWrapper singleton — pool_router her fan_out'ta yeniden
    instantiate etmesin diye (Council 39 alt-§ 39a)."""
    return PineconeIndexWrapper()
