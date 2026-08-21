"""Pool Router — 1-havuz RRF k=60 (semantic) + anchor boost + PMID metadata HARD filter.

P003: abstract base class + interface.
P006: HybridPoolRouter concrete — Pinecone dense semantic pool + RRF k=60.
      Anchor IDs ek havuz olarak RRF'e girer. PMID metadata 8-field
      (D/F/S/year/q_weak/method/lang/v_conf) Pinecone HARD filter olarak
      semantic pool'a uygulanir.
P095: `lexical_tsvector_pool` standalone helper — F9 BÖLÜM 2 anchor_finder
      `papers.title_tsv` GIN index üzerinden plainto_tsquery + ts_rank top-k
      (KD-23 lexical havuz kararı KAPANIR — Council 25 B-018 ile uyumlu).

M-10 (2026-05-27): Theme pool kanalı kaldırıldı (256-d TF-IDF vs 1024-d
BGE-M3 boyut uyumsuzluğu → kanal sessizce "random top-N" gürültüsüne
düşüyordu). HybridPoolRouter docstring'ine detay yazılı.

DM-017 chat-first pivot sonrasi pipeline degismez: Listener ciktisi
(sub_queries) aynen semantic pool'a girer.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, cast

from supabase import Client

from api.config import Settings, get_settings
from api.db.supabase_client import supabase_call_async

logger = logging.getLogger(__name__)

# RRF sabit k parametresi (B42-045 §2).
RRF_K = 60


class PoolRouter(ABC):
    """1-havuz fan-out (semantic) + anchor boost + RRF k=60 birlesim."""

    @abstractmethod
    async def fan_out(
        self,
        sub_queries: list[str],
        anchor_ids: list[str],
        top_k: int = 200,
        filter: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        """Listener ciktisi + Anchor sonucundan semantic havuza fan-out + RRF.

        Args:
            sub_queries: Listener multi-query rewrite ciktisi.
            anchor_ids: Anchor PMID match sonucu (top 3-10 paper_id).
            top_k: Maksimum candidate sayisi.
            filter: Pinecone metadata HARD filter (B-012 8-field sema):
                {"D": {"$in": ["med"]}, "year": {"$gte": 2020}, ...}.
                None ise filter yok (tum corpus).

        Returns:
            (paper_id, rrf_score) listesi descending; len <= top_k.
        """
        ...


class _QueryEncoder:
    """BGE-M3 lazy-load query encoder (P007 reranker pattern paralel).

    sentence-transformers ile tek sorgu encode; CPU/MPS.
    Model ilk cagri aninda yuklenir (~350 MB).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._model: Any | None = None

    def encode(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            self._model = self._load()
        return self._model.encode(
            texts,
            batch_size=self._settings.EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
        ).tolist()

    def _load(self) -> Any:
        from sentence_transformers import SentenceTransformer

        # P5: transformers 5.x + torch 2.10 + accelerate kombinasyonunda
        # SentenceTransformer(device=...) constructor'ı içeride meta-tensor'dan
        # gerçek device'a kopyalama dener ve NotImplementedError'a patlar:
        # "Cannot copy out of meta tensor; no data!" → POST /api/search 500.
        # low_cpu_mem_usage=False, transformers'ın accelerate low-mem init
        # yolunu kapatır → ağırlıklar doğrudan device'a yüklenir, race kapanır.
        model = SentenceTransformer(
            self._settings.EMBEDDING_MODEL_ID,
            device=self._settings.EMBEDDING_DEVICE,
            model_kwargs={"low_cpu_mem_usage": False},
        )
        logger.info(
            "QueryEncoder loaded model=%s device=%s",
            self._settings.EMBEDDING_MODEL_ID,
            self._settings.EMBEDDING_DEVICE,
        )
        return model


def _rrf_merge(
    *ranked_lists: list[tuple[str, float]],
    k: int = RRF_K,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion — N ranked list'i tek skor ile birlestirir.

    RRF(d) = sum_i( 1 / (k + rank_i(d)) )
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (paper_id, _original_score) in enumerate(ranked):
            scores[paper_id] = scores.get(paper_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class HybridPoolRouter(PoolRouter):
    """1-havuz RRF + anchor boost: semantic (Pinecone dense + PMID filter).

    M-10 (2026-05-27): Theme pool kanalı kaldırıldı. Sebep — `dim_theme_embedding`
    256-d TF-IDF vektörleri ile sorgu tarafı 1024-d BGE-M3 vektörleri arasında
    boyut uyumsuzluğu vardı; eski kod `query_vector[0]` üzerinde gereksiz
    `isinstance(str)` kontrolüyle sessizce "rastgele ilk N tema" fallback'ine
    düşüyordu — RRF'e sinyal değil GÜRÜLTÜ ekliyordu. Theme'leri 1024-d ile
    yeniden gömmek (Colab batch) çok daha büyük bir iş; iki kanal yerine
    semantic+anchor olarak sadeleştirildi. Audit: AUDIT_REPORT.md §11 M-10
    / finding-3.6. (Re-enable için: themes 1024-d ile recompute + bu sınıfa
    geri-ekleme.)

    - Semantic pool: sub_queries BGE-M3 encode -> Pinecone dense query
      + metadata HARD filter (D/F/S/year/q_weak/method/lang/v_conf).
    - Anchor IDs boost: anchor_ids varsa RRF'e ek havuz olarak eklenir
      (score=1.0 sabit, en ust sira garanti).
    - RRF k=60 birlesim.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        encoder: _QueryEncoder | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._encoder = encoder or _QueryEncoder(self._settings)

    async def fan_out(
        self,
        sub_queries: list[str],
        anchor_ids: list[str],
        top_k: int = 200,
        filter: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        if not sub_queries:
            return []

        # 1. Encode sub_queries (CPU-bound -> thread pool)
        vectors = await asyncio.to_thread(self._encoder.encode, sub_queries)

        # 2. Semantic havuz (M-10: theme kanalı kaldırıldı — class docstring)
        try:
            semantic_results = await self._semantic_pool(vectors, top_k, filter)
        except BaseException as exc:
            logger.error("Semantic pool failed: %s", exc)
            semantic_results = []

        # 3. Anchor boost havuzu
        anchor_ranked: list[tuple[str, float]] = [(aid, 1.0) for aid in anchor_ids]

        # 4. RRF merge
        pools_to_merge = [p for p in [semantic_results, anchor_ranked] if p]
        if not pools_to_merge:
            return []

        merged = _rrf_merge(*pools_to_merge)
        return merged[:top_k]

    async def _semantic_pool(
        self,
        vectors: list[list[float]],
        top_k: int,
        filter: dict[str, Any] | None,
    ) -> list[tuple[str, float]]:
        """Multi-query Pinecone dense: her sub_query icin top_k/len(vectors)
        query, sonuclar birlestirilir (max score per paper_id).

        P011: get_pinecone_index() singleton + query_async (timeout + retry).
        Per-query failure -> bos liste + warning (graceful degrade); diger
        sub_query'ler korunur, fan_out tamamen patlamaz.
        """
        from api.db.pinecone_client import (
            PineconeQueryError,
            get_pinecone_index,
        )
        from api.utils.resilience import ResilienceTimeoutError

        idx = get_pinecone_index()
        per_query_k = max(10, top_k // len(vectors))

        async def _query_one(vec: list[float]) -> list[tuple[str, float]]:
            try:
                result = await idx.query_async(
                    vector=vec,
                    top_k=per_query_k,
                    filter=filter,
                    include_metadata=True,
                )
            except (ResilienceTimeoutError, PineconeQueryError) as exc:
                logger.warning(
                    "semantic_pool query degraded error=%s",
                    exc.__class__.__name__,
                )
                return []
            return [
                (m.id, float(m.score))
                for m in (result.get("matches") or [])
            ]

        tasks = [_query_one(v) for v in vectors]
        all_results = await asyncio.gather(*tasks)

        # Merge: max score per paper_id
        best: dict[str, float] = {}
        for results in all_results:
            for pid, score in results:
                if pid not in best or score > best[pid]:
                    best[pid] = score

        ranked = sorted(best.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


async def lexical_tsvector_pool(
    db: Client,
    keywords: list[str],
    top_k: int = 80,
) -> list[tuple[str, float]]:
    """F9 BÖLÜM 2 lexical havuz: papers.title_tsv full-text match.

    `papers.title_tsv` P091 K-029 GENERATED ALWAYS AS to_tsvector('simple', title)
    STORED + GIN index. Her keyword ayrı `plainto_tsquery('simple', kw)` çağrısı
    ile sorgulanır (multi-word phrase'ler güvenli — `to_tsquery` operatör
    syntax'ı gerektiren `|` AND/OR kombinasyonu yerine her keyword bağımsız
    çalıştırılır, sonuçlar uygulama tarafında union'lanır). RRF rank pozisyonu
    kullandığı için skor uniform 1.0; per-keyword paralel asyncio.gather ile
    p95 < ~150ms (GIN index direct).

    KD-23 lexical havuz kararı KAPANIR (Council 25 B-018 ile uyumlu).

    Args:
        db: Supabase service-role client (read-only çağrı).
        keywords: HydePacket.packet_s (5-8 madde TR/EN/ID karışık).
        top_k: Maksimum aday sayısı (default 80, anchor_finder pipeline).

    Returns:
        (paper_id, 1.0) tuple listesi — rank-stable union; len <= top_k.
        Boş keyword listesi → boş liste (graceful).
    """
    cleaned = [kw.strip() for kw in keywords if kw and kw.strip()]
    if not cleaned:
        return []

    per_kw_limit = max(10, top_k // len(cleaned)) + 5

    async def _query_one(kw: str) -> list[str]:
        def _do() -> Any:
            return (
                db.table("papers")
                .select("paper_id")
                .limit(per_kw_limit)
                .text_search(
                    "title_tsv",
                    kw,
                    options={"type": "plain", "config": "simple"},
                )
                .execute()
            )
        try:
            resp = await supabase_call_async(_do)
        except Exception as exc:
            logger.warning(
                "lexical_tsvector_pool keyword=%r degraded error=%s",
                kw,
                exc.__class__.__name__,
            )
            return []
        rows = cast(list[dict[str, Any]], resp.data or [])
        return [r["paper_id"] for r in rows if isinstance(r.get("paper_id"), str)]

    results = await asyncio.gather(*(_query_one(kw) for kw in cleaned))

    # Union — ilk görülen rank korunur (RRF için stabil pozisyon).
    seen: dict[str, None] = {}
    for kw_rows in results:
        for pid in kw_rows:
            if pid not in seen:
                seen[pid] = None
            if len(seen) >= top_k:
                break
        if len(seen) >= top_k:
            break
    return [(pid, 1.0) for pid in list(seen.keys())[:top_k]]


__all__ = [
    "RRF_K",
    "HybridPoolRouter",
    "PoolRouter",
    "_QueryEncoder",
    "_rrf_merge",
    "lexical_tsvector_pool",
]
