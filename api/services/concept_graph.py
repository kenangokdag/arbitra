"""V1-S17 P003 — ConceptNetwork derived producer (RC4 cascade follow-up).

Plan: docs/plans/V1_S17_cascade_5rc.md §3 KD-V1-S17-03 (v1.1 revize — fact_paper_concept YOK).

Algoritma (cache-less Faz 1; cache 0019 migration ile sonra):
  1) project_cluster.paper_id → papers.abstract batch JOIN.
  2) TfidfVectorizer(max_features=20, ngram_range=(1, 2), stop_words=TR+EN)
     → en yoğun 20 anahtar kelime / öbek (node).
  3) Her keyword k için S_k = {i : tfidf[i, k] > 0} (paper kümesi).
  4) Edge ağırlığı = co-citation cosine =
        |S_i ∩ S_j| / sqrt(|S_i| · |S_j|)
     (Small 1973 SIGIR co-citation pattern; terim-bazlı uygulama burada makaleler
     aracılığıyla terim birlikteliği ölçer).
  5) cosine ≥ 0.15 filter (mock ~30 edge — orta yoğunluk hedefi).

Hatalar:
  - ClusterNotReadyError: project_anchor.cluster_status != 'ready' VEYA
    project_cluster boş (Stage C henüz koşmadı / 'failed' kaldı).

HK-1: ConfigDict(extra="forbid"); HK-6: explicit dict[str, float] (Any leak yok).
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field
from sklearn.feature_extraction.text import (
    ENGLISH_STOP_WORDS,
    TfidfVectorizer,
)
from supabase import Client

logger = logging.getLogger(__name__)

# Türkçe çekirdek stopword'ler — sklearn yerleşik TR listesi yok; akademik abstract
# yoğunluğunda işe yarar minimum sözlük.
_TR_STOPWORDS: frozenset[str] = frozenset(
    {
        "ve", "veya", "ile", "için", "bir", "bu", "şu", "de", "da",
        "mı", "mi", "mu", "mü", "ama", "fakat", "ancak", "çünkü", "yani",
        "gibi", "kadar", "göre", "sonra", "önce", "içinde", "üzere",
        "ise", "ki", "her", "hiç", "çok", "az", "daha", "en", "bütün",
        "bazı", "birçok", "kendi", "kendine", "arasında", "tarafından",
        "olarak", "olduğu", "şey", "şöyle", "böyle", "öyle", "kim", "ne",
        "nasıl", "nerede", "ben", "sen", "biz", "siz", "onlar", "benim",
        "senin", "onun", "bizim", "sizin", "onların", "var", "yok",
        "oldu", "olur", "olduğunu", "tüm", "ayrıca", "yine", "iken",
    }
)
_COMBINED_STOPWORDS: list[str] = sorted(ENGLISH_STOP_WORDS | _TR_STOPWORDS)

_MAX_FEATURES = 20
_NGRAM_RANGE = (1, 2)
_EDGE_MIN_COSINE = 0.15
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class ClusterNotReadyError(Exception):
    """Stage C henüz tamam değil veya project_cluster boş."""


class ConceptNode(BaseModel):
    """Concept graph düğümü — TF-IDF top-20 anahtar kelime / öbek."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=80)
    weight: float = Field(ge=0.0, le=1.0)
    doc_count: int = Field(ge=0)


class ConceptEdge(BaseModel):
    """Concept graph kenarı — keyword-pair co-citation cosine."""

    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=1, max_length=80)
    target: str = Field(min_length=1, max_length=80)
    weight: float = Field(ge=_EDGE_MIN_COSINE, le=1.0)


class ConceptNetworkResponse(BaseModel):
    """GET /api/project/{id}/concept-network 200 dönüşü."""

    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1)
    anchor_paper_id: str | None = Field(default=None, max_length=64)
    paper_count: int = Field(ge=0)
    nodes: list[ConceptNode]
    edges: list[ConceptEdge]


def _slug(label: str) -> str:
    """Keyword → URL-güvenli node id (graph render referansı)."""
    base = _SLUG_RE.sub("_", label.lower()).strip("_")
    return base or "term"


def _co_citation_edges(
    doc_term_presence: list[list[bool]],
    feature_names: list[str],
) -> list[ConceptEdge]:
    """Her terim-çifti (i, j) için cosine = |S_i ∩ S_j| / sqrt(|S_i| · |S_j|).

    doc_term_presence: (n_docs, n_terms) boolean — TF-IDF[i,j] > 0 ise True.
    feature_names: TfidfVectorizer.get_feature_names_out() çıktısı (n_terms).
    """
    n_docs = len(doc_term_presence)
    n_terms = len(feature_names)
    if n_docs == 0 or n_terms < 2:
        return []

    # Her terim için S_k (paper indeks kümesi) — set bazlı kesişim için bit-mask
    # alternatifi yerine açık küme kullanmak küçük N için yeterli (N ≤ 50 paper,
    # K ≤ 20 terim → 50·20 = 1000 hücre, 190 çift).
    term_sets: list[set[int]] = [set() for _ in range(n_terms)]
    for doc_idx, row in enumerate(doc_term_presence):
        for term_idx, present in enumerate(row):
            if present:
                term_sets[term_idx].add(doc_idx)

    edges: list[ConceptEdge] = []
    for i in range(n_terms):
        s_i = term_sets[i]
        if not s_i:
            continue
        for j in range(i + 1, n_terms):
            s_j = term_sets[j]
            if not s_j:
                continue
            inter = len(s_i & s_j)
            if inter == 0:
                continue
            denom = math.sqrt(len(s_i) * len(s_j))
            if denom == 0:
                continue
            cos = inter / denom
            if cos < _EDGE_MIN_COSINE:
                continue
            edges.append(
                ConceptEdge(
                    source=_slug(feature_names[i]),
                    target=_slug(feature_names[j]),
                    weight=round(cos, 4),
                )
            )
    return edges


def _build_nodes(
    feature_names: list[str],
    doc_term_presence: list[list[bool]],
    n_docs: int,
) -> list[ConceptNode]:
    """TF-IDF anahtar kelimelerinden ConceptNode listesi.

    weight = doc_count / n_docs (0..1 normalize); doc_count = kaç paper'da geçtiği.
    Slug çakışmasında (örn. "deep-learning" vs "deep_learning") ilk kayıt korunur.
    """
    nodes: list[ConceptNode] = []
    seen_ids: set[str] = set()
    for term_idx, label in enumerate(feature_names):
        doc_count = sum(1 for row in doc_term_presence if row[term_idx])
        if doc_count == 0:
            continue
        node_id = _slug(label)
        if node_id in seen_ids:
            continue
        seen_ids.add(node_id)
        nodes.append(
            ConceptNode(
                id=node_id,
                label=label,
                weight=round(doc_count / n_docs, 4) if n_docs else 0.0,
                doc_count=doc_count,
            )
        )
    return nodes


def compute_concept_network(
    abstracts: list[str],
    *,
    max_features: int = _MAX_FEATURES,
) -> tuple[list[ConceptNode], list[ConceptEdge]]:
    """Salt-fonksiyonel TF-IDF + co-citation cosine — DB bağımsız (unit test giriş kapısı).

    Boş corpus / tek-paper / hepsi stopword → ([], []) graceful.
    """
    non_empty = [a for a in abstracts if a and a.strip()]
    if len(non_empty) < 2:
        return [], []

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=_NGRAM_RANGE,
        stop_words=_COMBINED_STOPWORDS,
        lowercase=True,
        token_pattern=r"(?u)\b[a-zçğıöşüA-ZÇĞİÖŞÜ][a-zçğıöşüA-ZÇĞİÖŞÜ\-]+\b",
    )
    try:
        tfidf = vectorizer.fit_transform(non_empty)
    except ValueError:
        # Empty vocabulary (hepsi stopword / tek-karakter)
        return [], []

    feature_names = list(vectorizer.get_feature_names_out())
    if not feature_names:
        return [], []

    # sparse → boolean presence matrisi
    dense = tfidf.toarray()
    doc_term_presence: list[list[bool]] = [
        [bool(v > 0) for v in row] for row in dense
    ]
    nodes = _build_nodes(feature_names, doc_term_presence, n_docs=len(non_empty))
    edges = _co_citation_edges(doc_term_presence, feature_names)
    # Edge'lerin node referanslarını koru (slug dedupe sonrası unutulanlar elenir).
    valid_ids = {n.id for n in nodes}
    edges = [e for e in edges if e.source in valid_ids and e.target in valid_ids]
    return nodes, edges


async def _fetch_cluster_paper_ids(db: Client, project_id: str) -> list[str]:
    from api.db.supabase_client import supabase_call_async

    resp = await supabase_call_async(
        lambda: db.table("project_cluster")
        .select("paper_id")
        .eq("project_id", project_id)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    out: list[str] = []
    for r in rows:
        pid = r.get("paper_id")
        if isinstance(pid, str) and pid.strip():
            out.append(pid)
    return out


async def _fetch_abstracts(db: Client, paper_ids: list[str]) -> list[str]:
    from api.db.supabase_client import supabase_call_async

    if not paper_ids:
        return []
    resp = await supabase_call_async(
        lambda: db.table("papers")
        .select("paper_id,abstract")
        .in_("paper_id", paper_ids)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return [str(r.get("abstract") or "") for r in rows]


async def _fetch_anchor(db: Client, project_id: str) -> tuple[str | None, str]:
    """project_anchor satırından (anchor_paper_id, cluster_status) döndür.

    Anchor yoksa → (None, 'pending') (caller ClusterNotReadyError raise eder).
    """
    from api.db.supabase_client import supabase_call_async

    resp = await supabase_call_async(
        lambda: db.table("project_anchor")
        .select("anchor_paper_id,cluster_status")
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        return None, "pending"
    row = rows[0]
    apid = row.get("anchor_paper_id")
    status = str(row.get("cluster_status") or "pending")
    return (apid if isinstance(apid, str) and apid.strip() else None), status


async def run(
    *, db: Client, project_id: str
) -> ConceptNetworkResponse:
    """Stage C derive katmanı — concept_graph TF-IDF + co-citation cosine.

    Pre-condition: project_anchor.cluster_status='ready' VE project_cluster boş değil.
    Aksi halde ClusterNotReadyError raise; route 409 mapler.
    """
    anchor_paper_id, status = await _fetch_anchor(db, project_id)
    if status != "ready":
        raise ClusterNotReadyError(
            f"cluster_status={status} (expected 'ready') project={project_id}"
        )

    paper_ids = await _fetch_cluster_paper_ids(db, project_id)
    if not paper_ids:
        raise ClusterNotReadyError(
            f"project_cluster empty for project {project_id}"
        )

    abstracts = await _fetch_abstracts(db, paper_ids)
    nodes, edges = compute_concept_network(abstracts)
    return ConceptNetworkResponse(
        project_id=project_id,
        anchor_paper_id=anchor_paper_id,
        paper_count=len(paper_ids),
        nodes=nodes,
        edges=edges,
    )


__all__ = [
    "ClusterNotReadyError",
    "ConceptEdge",
    "ConceptNetworkResponse",
    "ConceptNode",
    "compute_concept_network",
    "run",
]
