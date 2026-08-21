"""P006 HybridPoolRouter unit tests.

RRF merge + mock encoder + mock Pinecone + mock Supabase.
sentence_transformers / Pinecone SDK gercek yuklemeden test edilir.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services._mocks import MockPoolRouter
from api.services.pool_router import (
    HybridPoolRouter,
    _QueryEncoder,
    _rrf_merge,
)

# --- RRF merge unit tests ---


class TestRrfMerge:
    def test_single_list(self) -> None:
        ranked = [("A", 0.9), ("B", 0.8), ("C", 0.7)]
        result = _rrf_merge(ranked, k=60)
        assert result[0][0] == "A"
        assert result[1][0] == "B"
        assert result[2][0] == "C"

    def test_two_lists_overlap(self) -> None:
        list1 = [("A", 0.9), ("B", 0.8)]
        list2 = [("B", 0.95), ("C", 0.7)]
        result = _rrf_merge(list1, list2, k=60)
        # B appears in both lists -> highest RRF score
        ids = [pid for pid, _ in result]
        assert ids[0] == "B"

    def test_empty_lists(self) -> None:
        result = _rrf_merge([], [], k=60)
        assert result == []

    def test_disjoint_lists(self) -> None:
        list1 = [("A", 0.9)]
        list2 = [("B", 0.8)]
        result = _rrf_merge(list1, list2, k=60)
        ids = [pid for pid, _ in result]
        assert "A" in ids
        assert "B" in ids
        # Both rank=0 in their list, so 1/(60+1) each -> equal score
        assert abs(result[0][1] - result[1][1]) < 1e-9

    def test_rrf_k_parameter(self) -> None:
        ranked = [("A", 0.9), ("B", 0.8)]
        result_k10 = _rrf_merge(ranked, k=10)
        result_k60 = _rrf_merge(ranked, k=60)
        # Scores differ but ranking preserved
        assert result_k10[0][0] == "A"
        assert result_k60[0][0] == "A"
        # k=10: 1/11 vs 1/12; k=60: 1/61 vs 1/62
        assert result_k10[0][1] > result_k60[0][1]

    def test_three_lists(self) -> None:
        list1 = [("A", 0.9), ("B", 0.7)]
        list2 = [("B", 0.8), ("C", 0.6)]
        list3 = [("A", 0.5)]  # anchor boost
        result = _rrf_merge(list1, list2, list3, k=60)
        ids = [pid for pid, _ in result]
        # A: 2 listede (list1 rank0 + list3 rank0)
        # B: 2 listede (list1 rank1 + list2 rank0)
        assert ids[0] in ("A", "B")


# --- MockPoolRouter tests ---


class TestMockPoolRouter:
    @pytest.mark.asyncio
    async def test_mock_returns_tuples(self) -> None:
        router = MockPoolRouter()
        results = await router.fan_out(["test query"], ["ANC1"], top_k=10)
        assert isinstance(results, list)
        assert len(results) > 0
        assert isinstance(results[0], tuple)
        assert len(results[0]) == 2

    @pytest.mark.asyncio
    async def test_mock_includes_anchor_ids(self) -> None:
        router = MockPoolRouter()
        results = await router.fan_out(["q"], ["ANC1", "ANC2"], top_k=20)
        ids = [pid for pid, _ in results]
        assert "ANC1" in ids
        assert "ANC2" in ids

    @pytest.mark.asyncio
    async def test_mock_respects_top_k(self) -> None:
        router = MockPoolRouter()
        results = await router.fan_out(["q"], [], top_k=5)
        assert len(results) <= 5


# --- HybridPoolRouter tests (mocked dependencies) ---


def _make_mock_encoder(dim: int = 1024) -> _QueryEncoder:
    """Encoder mock: returns deterministic vectors."""
    encoder = MagicMock(spec=_QueryEncoder)
    encoder.encode.return_value = [[0.1] * dim]
    return encoder


class TestHybridPoolRouter:
    @pytest.mark.asyncio
    async def test_empty_queries(self) -> None:
        router = HybridPoolRouter(encoder=_make_mock_encoder())
        results = await router.fan_out([], [], top_k=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_semantic_pool_called(self) -> None:
        encoder = _make_mock_encoder()
        router = HybridPoolRouter(encoder=encoder)

        mock_result = {
            "matches": [
                MagicMock(id="W001", score=0.95),
                MagicMock(id="W002", score=0.85),
            ]
        }
        fake_idx = MagicMock()
        fake_idx.query_async = AsyncMock(return_value=mock_result)

        with patch("api.db.pinecone_client.get_pinecone_index", return_value=fake_idx):
            results = await router.fan_out(["test query"], [], top_k=10)

        ids = [pid for pid, _ in results]
        assert "W001" in ids
        assert "W002" in ids

    @pytest.mark.asyncio
    async def test_anchor_boost(self) -> None:
        encoder = _make_mock_encoder()
        router = HybridPoolRouter(encoder=encoder)

        mock_result = {"matches": [MagicMock(id="W001", score=0.5)]}
        fake_idx = MagicMock()
        fake_idx.query_async = AsyncMock(return_value=mock_result)

        with patch("api.db.pinecone_client.get_pinecone_index", return_value=fake_idx):
            results = await router.fan_out(["test"], ["ANCHOR1"], top_k=10)

        ids = [pid for pid, _ in results]
        assert "ANCHOR1" in ids
        anchor_score = next(s for pid, s in results if pid == "ANCHOR1")
        assert anchor_score > 0

    @pytest.mark.asyncio
    async def test_semantic_pool_failure_graceful(self) -> None:
        encoder = _make_mock_encoder()
        router = HybridPoolRouter(encoder=encoder)

        with patch.object(
            router,
            "_semantic_pool",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Pinecone down"),
        ):
            # Should not raise, returns anchor only
            results = await router.fan_out(
                ["test"], ["ANC1"], top_k=10
            )

        ids = [pid for pid, _ in results]
        assert "ANC1" in ids

    @pytest.mark.asyncio
    async def test_filter_passed_to_pinecone(self) -> None:
        encoder = _make_mock_encoder()
        router = HybridPoolRouter(encoder=encoder)

        fake_idx = MagicMock()
        fake_idx.query_async = AsyncMock(return_value={"matches": []})

        with patch("api.db.pinecone_client.get_pinecone_index", return_value=fake_idx):
            test_filter = {"D": {"$in": ["med"]}, "year": {"$gte": 2020}}
            await router.fan_out(["test"], [], top_k=10, filter=test_filter)

            call_args = fake_idx.query_async.call_args
            assert call_args is not None
            assert call_args.kwargs.get("filter") == test_filter

    @pytest.mark.asyncio
    async def test_multi_query_merge(self) -> None:
        encoder = MagicMock(spec=_QueryEncoder)
        encoder.encode.return_value = [[0.1] * 1024, [0.2] * 1024]
        router = HybridPoolRouter(encoder=encoder)

        call_count = 0

        async def mock_query_async(**_kwargs: Any) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "matches": [
                        MagicMock(id="W001", score=0.9),
                        MagicMock(id="W002", score=0.8),
                    ]
                }
            return {
                "matches": [
                    MagicMock(id="W002", score=0.95),
                    MagicMock(id="W003", score=0.7),
                ]
            }

        fake_idx = MagicMock()
        fake_idx.query_async = mock_query_async

        with patch("api.db.pinecone_client.get_pinecone_index", return_value=fake_idx):
            results = await router.fan_out(["query1", "query2"], [], top_k=10)

        ids = [pid for pid, _ in results]
        assert "W001" in ids
        assert "W002" in ids
        assert "W003" in ids
