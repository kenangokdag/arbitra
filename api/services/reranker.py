"""Reranker — cross-encoder relevance scoring (B42-045 §1).

P003: abstract base class.
P007: BAAI/bge-reranker-v2-m3 cross-encoder local CPU/MPS (Council 28
      Sercan A-row: "local sentence-transformers CPU MVP; HF endpoint Faz 3").
      Pinecone candidate'larından sonra top_k=20 → top_5 fine-rank.

Notlar:
- Model lazy-load (ilk gerçek rerank çağrısında); unit testlerde scorer
  injection kullanılırsa transformers/torch hiç yüklenmez.
- candidate_texts None ise degraded mode (uniform 0.5 + warning log) —
  Pinecone metadata patch (B-012) gelene kadar route üzerinden text yok.
- Async API: ABC zorunlu await; CPU-bound iş asyncio.to_thread ile event
  loop'u bloklamaz.
- Tier-bazlı k (Öğrenci 50 / Araştırmacı 200 / Profesyonel 500) Faz 3
  (KD-12 tier-aware RRF k).
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Protocol, cast

from api.config import Settings, get_settings

logger = logging.getLogger(__name__)


class Reranker(ABC):
    """Cross-encoder reranker — (id, query) çiftine cosine/logit skor."""

    @abstractmethod
    async def rerank(
        self,
        candidates: list[str],
        query: str,
        top_k: int = 10,
        candidate_texts: dict[str, str] | None = None,
    ) -> list[tuple[str, float]]:
        """Top-k candidate (id, score) descending.

        candidate_texts: {paper_id: rerank_text}. None ise BgeReranker degraded
        moda düşer (uniform 0.5). MockReranker bu parametreyi yok sayar.
        """
        ...


class _RerankerScorer(Protocol):
    """Test injection için skor üreteci protokolü."""

    def __call__(self, query: str, documents: list[str]) -> list[float]: ...


class BgeReranker(Reranker):
    """BAAI/bge-reranker-v2-m3 cross-encoder.

    Constructor injection: `scorer` testlerde mock; production'da None →
    transformers + torch model lazy-load.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        scorer: _RerankerScorer | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._scorer: _RerankerScorer | None = scorer
        self._model: Any | None = None
        self._tokenizer: Any | None = None
        self._torch: Any | None = None

    async def rerank(
        self,
        candidates: list[str],
        query: str,
        top_k: int = 10,
        candidate_texts: dict[str, str] | None = None,
    ) -> list[tuple[str, float]]:
        if not candidates:
            return []
        if candidate_texts is None or not any(
            candidate_texts.get(c) for c in candidates
        ):
            # KD-30: Pinecone metadata (B-012 DONE) + Supabase abstract
            # lazy-fill sonrasi PoolRouter paper text doner; degraded mode
            # kalkar. HK-2 kayit: degraded uniform skor.
            logger.warning(
                "BgeReranker degraded: candidate_texts missing; "
                "returning uniform score=0.5 (count=%d)",
                len(candidates),
            )
            return [(c, 0.5) for c in candidates[:top_k]]

        with_text: list[tuple[str, str]] = []
        without_text: list[str] = []
        for cid in candidates:
            text = candidate_texts.get(cid)
            if text:
                with_text.append((cid, text))
            else:
                without_text.append(cid)

        scores = await asyncio.to_thread(
            self._score_or_load, query, [t for _, t in with_text]
        )
        scored: list[tuple[str, float]] = list(
            zip([cid for cid, _ in with_text], scores, strict=True)
        )
        scored.extend((cid, 0.5) for cid in without_text)
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def _score_or_load(self, query: str, documents: list[str]) -> list[float]:
        scorer = self._scorer
        if scorer is None:
            scorer = self._load_default_scorer()
        return list(scorer(query, documents))

    def _load_default_scorer(self) -> _RerankerScorer:
        # transformers/torch ~700MB; lazy import.
        if self._scorer is not None:
            return self._scorer
        if self._model is None or self._tokenizer is None or self._torch is None:
            import torch
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
            )

            tokenizer = AutoTokenizer.from_pretrained(  # type: ignore[no-untyped-call]
                self._settings.RERANKER_MODEL_ID
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                self._settings.RERANKER_MODEL_ID
            )
            device = self._settings.RERANKER_DEVICE
            model = model.to(device).eval()
            self._tokenizer = tokenizer
            self._model = model
            self._torch = torch
            logger.info(
                "BgeReranker loaded model=%s device=%s",
                self._settings.RERANKER_MODEL_ID,
                device,
            )

        torch_mod = self._torch
        tokenizer = self._tokenizer
        model = self._model
        device = self._settings.RERANKER_DEVICE
        max_len = self._settings.RERANKER_MAX_LEN
        batch_size = self._settings.RERANKER_BATCH_SIZE

        def _scorer(q: str, docs: list[str]) -> list[float]:
            scores: list[float] = []
            with torch_mod.no_grad():
                for i in range(0, len(docs), batch_size):
                    batch = [[q, d] for d in docs[i : i + batch_size]]
                    inputs = tokenizer(
                        batch,
                        padding=True,
                        truncation=True,
                        max_length=max_len,
                        return_tensors="pt",
                    )
                    inputs = {k: v.to(device) for k, v in inputs.items()}
                    logits = model(**inputs, return_dict=True).logits.view(-1).float()
                    scores.extend(logits.cpu().tolist())
            return scores

        scorer_typed: _RerankerScorer = cast(_RerankerScorer, _scorer)
        self._scorer = scorer_typed
        return scorer_typed


__all__ = ["BgeReranker", "Reranker"]
