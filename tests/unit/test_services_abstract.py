"""P003 abstract base class smoke tests (5-katman pipeline contract).

Her servis için: (1) abstract instantiate raise TypeError; (2) concrete subclass çalışır.
"""

from typing import Any

import pytest

from api.services import Anchor, Curator, Listener, PoolRouter, Reranker

pytestmark = pytest.mark.unit


# ---------- Listener ----------


def test_listener_abstract_cannot_instantiate() -> None:
    with pytest.raises(TypeError, match="abstract"):
        Listener()  # type: ignore[abstract]


async def test_listener_concrete_subclass_works() -> None:
    class FakeListener(Listener):
        async def listen(
            self, query: str, k: int = 5, lang: str = "auto"
        ) -> list[str]:
            del k, lang
            return [query, f"{query} alt-1", f"{query} alt-2"]

    fake = FakeListener()
    result = await fake.listen("makine öğrenmesi")
    assert len(result) == 3
    assert result[0] == "makine öğrenmesi"


# ---------- Anchor ----------


def test_anchor_abstract_cannot_instantiate() -> None:
    with pytest.raises(TypeError, match="abstract"):
        Anchor()  # type: ignore[abstract]


def test_anchor_concrete_subclass_works() -> None:
    class FakeAnchor(Anchor):
        def match(self, query: str, top_k: int = 10) -> list[str]:
            return ["W123", "W456"][:top_k]

    fake = FakeAnchor()
    result = fake.match("derin öğrenme tıp", top_k=5)
    assert result == ["W123", "W456"]


# ---------- PoolRouter ----------


def test_pool_router_abstract_cannot_instantiate() -> None:
    with pytest.raises(TypeError, match="abstract"):
        PoolRouter()  # type: ignore[abstract]


def test_pool_router_concrete_subclass_works() -> None:
    class FakePoolRouter(PoolRouter):
        def fan_out(
            self,
            sub_queries: list[str],
            anchor_ids: list[str],
            top_k: int = 200,
            filter: dict[str, Any] | None = None,
        ) -> list[str]:
            return anchor_ids + [f"W{i}" for i in range(top_k - len(anchor_ids))]

    fake = FakePoolRouter()
    result = fake.fan_out(["q1", "q2"], ["W123"], top_k=5)
    assert len(result) == 5
    assert result[0] == "W123"


def test_pool_router_concrete_with_filter_param() -> None:
    """Council 24: filter param B-012 metadata HARD filter için."""

    class FakePoolRouterWithFilter(PoolRouter):
        def fan_out(
            self,
            sub_queries: list[str],
            anchor_ids: list[str],
            top_k: int = 200,
            filter: dict[str, Any] | None = None,
        ) -> list[str]:
            del sub_queries, anchor_ids
            applied = list(filter.keys()) if filter else []
            return [f"filtered:{','.join(applied)}:{i}" for i in range(min(top_k, 3))]

    fake = FakePoolRouterWithFilter()
    result = fake.fan_out(
        sub_queries=["q1"],
        anchor_ids=[],
        top_k=3,
        filter={"D": {"$in": ["med"]}, "year": {"$gte": 2020}},
    )
    assert len(result) == 3
    assert "D,year" in result[0] or "year,D" in result[0]


# ---------- Reranker ----------


def test_reranker_abstract_cannot_instantiate() -> None:
    with pytest.raises(TypeError, match="abstract"):
        Reranker()  # type: ignore[abstract]


async def test_reranker_concrete_subclass_works() -> None:
    class FakeReranker(Reranker):
        async def rerank(
            self,
            candidates: list[str],
            query: str,
            top_k: int = 10,
            candidate_texts: dict[str, str] | None = None,
        ) -> list[tuple[str, float]]:
            del query, candidate_texts
            return [(c, 1.0 - i * 0.1) for i, c in enumerate(candidates[:top_k])]

    fake = FakeReranker()
    result = await fake.rerank(["W1", "W2", "W3"], "test", top_k=2)
    assert len(result) == 2
    assert result[0] == ("W1", 1.0)
    assert result[1][1] < result[0][1]


# ---------- Curator ----------


def test_curator_abstract_cannot_instantiate() -> None:
    with pytest.raises(TypeError, match="abstract"):
        Curator()  # type: ignore[abstract]


async def test_curator_concrete_subclass_works() -> None:
    class FakeCurator(Curator):
        async def curate(
            self,
            scored_papers: list[tuple[str, float]],
            query: str,
            user_lang: str = "en",
        ) -> dict[str, Any]:
            return {
                "papers": [{"paper_id": pid, "score": s} for pid, s in scored_papers],
                "faithfulness_meta": {
                    "jsonschema_pct": 100,
                    "minicheck_nli": 0.85,
                    "alce_recall": 0.92,
                },
                "decision_band": "canon",
                "gate_warnings": [],
                "pmid_match_score": 0.78,
            }

    fake = FakeCurator()
    result = await fake.curate([("W1", 0.9), ("W2", 0.7)], "test", user_lang="tr")
    assert len(result["papers"]) == 2
    assert result["decision_band"] in {"canon", "frontier", "strong_evidence", "risk"}
    assert result["faithfulness_meta"]["jsonschema_pct"] == 100
