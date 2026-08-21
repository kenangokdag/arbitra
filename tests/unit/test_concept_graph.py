"""V1-S17 P003 — concept_graph unit tests.

Plan: docs/plans/V1_S17_cascade_5rc.md §4 C003 — `pytest tests/test_concept_graph.py` PASS.

Coverage:
1. compute_concept_network happy → ≥1 node + en az 1 edge cosine ≥ 0.15
2. Boş / tek-paper corpus → ([], []) graceful
3. Hepsi stopword → ([], []) graceful (empty vocabulary)
4. _slug temizliği + edge weight aralığı 0.15..1.0
"""

from __future__ import annotations

import math

import pytest

from api.services import concept_graph
from api.services.concept_graph import (
    _co_citation_edges,
    _slug,
    compute_concept_network,
)


# ── 1. Happy path — 4 abstract, en az 1 edge ──────────────────────────────────


def test_compute_concept_network_extracts_nodes_and_edges() -> None:
    abstracts = [
        "Deep learning neural networks improve medical imaging segmentation.",
        "Neural networks and transformers advance medical imaging classification.",
        "Transformer based deep learning applied to clinical decision support.",
        "Medical imaging segmentation with transformers and reinforcement learning.",
    ]
    nodes, edges = compute_concept_network(abstracts, max_features=12)
    assert nodes, "tf-idf top-k boş döndü"
    assert all(0.0 <= n.weight <= 1.0 for n in nodes)
    assert all(n.doc_count >= 1 for n in nodes)
    # Ortak kelimeler (medical/imaging/networks/transformers) eşik üstü cosine
    # üretmeli; en az 1 edge bekliyoruz.
    assert edges, f"co-citation cosine ≥ 0.15 edge bulunamadı (nodes={[n.label for n in nodes]})"
    assert all(0.15 <= e.weight <= 1.0 for e in edges)


# ── 2. < 2 paper → boş ─────────────────────────────────────────────────────


def test_compute_concept_network_empty_corpus_returns_empty() -> None:
    nodes, edges = compute_concept_network([])
    assert nodes == []
    assert edges == []

    nodes_one, edges_one = compute_concept_network(["only one abstract here."])
    assert nodes_one == []
    assert edges_one == []


# ── 3. Hepsi stopword → empty vocabulary graceful ─────────────────────────────


def test_compute_concept_network_only_stopwords_returns_empty() -> None:
    # Tüm token'lar TR+EN stopword listesinde → TfidfVectorizer empty vocab
    abstracts = [
        "ve veya ile için bir bu şu de da the and of for with a an this",
        "ama fakat ancak çünkü yani gibi the and of for with a an this that",
    ]
    nodes, edges = compute_concept_network(abstracts)
    assert nodes == []
    assert edges == []


# ── 4. _slug + edge weight aralığı ────────────────────────────────────────────


def test_slug_normalizes_and_edges_bound_to_threshold() -> None:
    assert _slug("Deep Learning") == "deep_learning"
    assert _slug("medical-imaging") == "medical_imaging"
    assert _slug("   ") == "term"  # fallback

    # 3 doc × 3 term: term0 ∩ term1 = {0,1} (cosine 1.0); term0 ∩ term2 = {0} (cosine 1/√(2·1) ≈ 0.707)
    presence = [
        [True, True, True],
        [True, True, False],
        [False, False, False],
    ]
    edges = _co_citation_edges(presence, ["alpha", "beta", "gamma"])
    weights = sorted(e.weight for e in edges)
    assert weights, "edge bulunamadı"
    assert all(w >= 0.15 for w in weights)
    # alpha-beta = 2/√(2·2) = 1.0
    # alpha-gamma = beta-gamma = 1/√(2·1) ≈ 0.7071
    assert math.isclose(max(weights), 1.0, abs_tol=1e-4)


# ── 5 (bonus). compute_concept_network public symbol kontratı ────────────────


def test_module_exports_public_api() -> None:
    for name in (
        "ClusterNotReadyError",
        "ConceptEdge",
        "ConceptNetworkResponse",
        "ConceptNode",
        "compute_concept_network",
        "run",
    ):
        assert hasattr(concept_graph, name), f"public api missing: {name}"


def test_concept_node_weight_clamped() -> None:
    """ConceptNode.weight ge=0, le=1 — pydantic kontrat."""
    with pytest.raises(Exception):
        concept_graph.ConceptNode(id="t", label="t", weight=1.5, doc_count=1)
