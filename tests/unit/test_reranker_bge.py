"""P007 BgeReranker unit tests — scorer injection (transformers/torch yok).

Coverage: degraded fallback (no texts), concrete scoring, top_k cut, sort
descending, mixed missing/present texts, empty candidates.
"""

from __future__ import annotations

import pytest

from api.config import Settings
from api.services.reranker import BgeReranker

pytestmark = pytest.mark.unit


def _settings() -> Settings:
    return Settings(  # type: ignore[arg-type]
        RERANKER_MODEL_ID="BAAI/bge-reranker-v2-m3",
        RERANKER_DEVICE="cpu",
        RERANKER_BATCH_SIZE=4,
        RERANKER_MAX_LEN=128,
    )


async def test_bge_reranker_empty_candidates_returns_empty() -> None:
    rr = BgeReranker(settings=_settings(), scorer=lambda q, d: [])
    result = await rr.rerank([], "query", top_k=5)
    assert result == []


async def test_bge_reranker_degraded_when_no_texts() -> None:
    rr = BgeReranker(settings=_settings(), scorer=lambda q, d: [])
    result = await rr.rerank(["W1", "W2", "W3"], "query", top_k=2)
    assert len(result) == 2
    assert all(s == 0.5 for _, s in result)
    assert result[0][0] == "W1"


async def test_bge_reranker_with_texts_invokes_scorer_and_sorts() -> None:
    seen: dict[str, object] = {}

    def fake_scorer(q: str, docs: list[str]) -> list[float]:
        seen["query"] = q
        seen["docs"] = list(docs)
        # Skor: doc içinde "yüksek" geçiyorsa yüksek, "düşük" geçiyorsa düşük
        return [3.0 if "yüksek" in d else 0.1 for d in docs]

    rr = BgeReranker(settings=_settings(), scorer=fake_scorer)
    texts = {"W1": "düşük alaka", "W2": "yüksek alaka", "W3": "yüksek alaka 2"}
    result = await rr.rerank(["W1", "W2", "W3"], "akademik sorgu", top_k=3, candidate_texts=texts)

    assert seen["query"] == "akademik sorgu"
    assert seen["docs"] == ["düşük alaka", "yüksek alaka", "yüksek alaka 2"]
    assert result[0][0] == "W2"
    assert result[1][0] == "W3"
    assert result[2][0] == "W1"
    assert result[0][1] > result[2][1]


async def test_bge_reranker_top_k_cut() -> None:
    rr = BgeReranker(
        settings=_settings(),
        scorer=lambda q, d: list(range(len(d), 0, -1)),
    )
    texts = {f"W{i}": f"doc {i}" for i in range(10)}
    result = await rr.rerank(
        list(texts.keys()), "q", top_k=3, candidate_texts=texts
    )
    assert len(result) == 3


async def test_bge_reranker_mixed_missing_text_uses_uniform_for_missing() -> None:
    def scorer(q: str, docs: list[str]) -> list[float]:
        del q
        return [10.0] * len(docs)

    rr = BgeReranker(settings=_settings(), scorer=scorer)
    texts: dict[str, str] = {"W1": "doc1"}
    result = await rr.rerank(
        ["W1", "W2"], "q", top_k=2, candidate_texts=texts
    )
    score_map = dict(result)
    assert score_map["W1"] == 10.0
    assert score_map["W2"] == 0.5
    assert result[0][0] == "W1"


async def test_bge_reranker_all_empty_strings_treated_as_missing() -> None:
    rr = BgeReranker(settings=_settings(), scorer=lambda q, d: [])
    result = await rr.rerank(
        ["W1", "W2"], "q", top_k=2, candidate_texts={"W1": "", "W2": ""}
    )
    # any() over .get() returns text → bool("") False → degraded path
    assert all(s == 0.5 for _, s in result)
