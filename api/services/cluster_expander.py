"""V1-S17 P001 — cluster_expander Stage C iskelet (RC4 cascade origin).

Plan: docs/plans/V1_S17_cascade_5rc.md §3 KD-V1-S17-01 (v1.1 BackgroundTask)

Pipeline:
  1. project_anchor.anchor_paper_id + papers.title/abstract fetch (K-031 zırh route
     katmanında; bu modül DB Client ile çağrıldığı için trust eder).
  2. Anchor metni encode (BGE-M3) — Pinecone client fetch desteklemiyor, Stage B
     paternine paralel re-encode.
  3. Paralel fan-out:
       a) Pinecone vec(anchor_embedding) top-200, filter=None (B-012 patch sonrası).
       b) Supabase lexical(anchor_title+abstract keywords) top-200 — pool_router
          `lexical_tsvector_pool` reuse.
  4. RRF k=60 (Cormack 2009 SIGIR) — `_rrf_merge` reuse → top-100.
  5. `_enrich_cluster_candidates`: papers + fact_paper_id_card + fact_paper_quality_v3
     HARD filter `is_suspicious=false` (Stage B aynası).
  6. BGE-reranker-v2-m3 cross-encoder → top-50 (`_FINAL_TOP_K`).
  7. Her aday için `signals_13(rerank_score)` (curator._signals_13 reuse).
  8. DB persist: `project_cluster` (0016 mevcut). idempotent delete-then-insert.
  9. `project_anchor.cluster_status='ready'`.

NOTE — signals_13 jsonb persist:
  project_cluster mevcut şeması (0016): paper_id, source, rrf_score, q_weak,
  estra_score, rank_final. signals_13 jsonb kolonu V1-S17 P002 migration 0037 ile
  eklenecek; iskelet P001'de en azından Q_weak / MQ_Tier1 / CD5 / sentence_role_RES
  q_weak ve estra_score kolonlarına map edilir, kalan 8 placeholder + diğer 1 kanıt
  jsonb gelene kadar log + return body üzerinden expose edilir.

Hatalar:
- AnchorNotFoundError: project_anchor satırı yok / başkasının.
- ClusterPoolEmptyError: hem vec hem lex pool boş → 'failed' set + raise.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field
from supabase import Client

from api.services.curator import _signals_13
from api.services.pool_router import _QueryEncoder, _rrf_merge, lexical_tsvector_pool
from api.services.reranker import Reranker

logger = logging.getLogger(__name__)

# KD-V1-S17-01 (v1.1) — Stage C fan-out sabitleri (Stage B 80/80/50/3'ün 2.5x'i).
_VEC_TOP_K = 200
_LEX_TOP_K = 200
_RRF_TOP_K = 100
_FINAL_TOP_K = 50
_LEX_KEYWORD_LIMIT = 12  # anchor title+abstract'tan max keyword (Stage B 5-8 ile uyumlu)
_LEX_TOKEN_MIN_LEN = 4  # tek-harfli stopword ekartesi


class AnchorNotFoundError(Exception):
    """project_anchor satırı yok veya `anchor_paper_id` boş."""


class ClusterPoolEmptyError(Exception):
    """Pinecone + tsvector birleşimi boş veya HARD filter sonrası boş."""


class ClusterExpandResponse(BaseModel):
    """Sync response — test path ve admin endpoint için. Production'da route
    BackgroundTasks içine alıp 202 döndürür; status `/cluster/status` poll ile."""

    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1)
    anchor_paper_id: str = Field(min_length=1, max_length=64)
    cluster_size: int = Field(ge=0, le=_FINAL_TOP_K)
    cluster_status: str = Field(min_length=1)  # "ready" | "failed"


async def _fetch_anchor(db: Client, project_id: str) -> dict[str, str]:
    """project_anchor + papers.title/abstract — anchor metadata yükle."""
    from api.db.supabase_client import supabase_call_async

    anchor_resp = await supabase_call_async(
        lambda: db.table("project_anchor")
        .select("anchor_paper_id")
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    anchor_rows = cast(list[dict[str, Any]], anchor_resp.data or [])
    if not anchor_rows:
        raise AnchorNotFoundError(f"no anchor for project {project_id}")
    anchor_paper_id_raw = anchor_rows[0].get("anchor_paper_id")
    if not isinstance(anchor_paper_id_raw, str) or not anchor_paper_id_raw.strip():
        raise AnchorNotFoundError(f"anchor_paper_id empty for project {project_id}")
    anchor_paper_id = anchor_paper_id_raw.strip()

    papers_resp = await supabase_call_async(
        lambda: db.table("papers")
        .select("paper_id,title,abstract")
        .eq("paper_id", anchor_paper_id)
        .limit(1)
        .execute()
    )
    papers_rows = cast(list[dict[str, Any]], papers_resp.data or [])
    title = ""
    abstract = ""
    if papers_rows:
        title = str(papers_rows[0].get("title") or "")
        abstract = str(papers_rows[0].get("abstract") or "")

    return {
        "anchor_paper_id": anchor_paper_id,
        "title": title,
        "abstract": abstract,
    }


def _extract_lex_keywords(
    title: str,
    abstract: str,
    *,
    limit: int = _LEX_KEYWORD_LIMIT,
    min_len: int = _LEX_TOKEN_MIN_LEN,
) -> list[str]:
    """Minimal keyword extractor — title+abstract token split + dedupe.

    Production TF-IDF KD-V1-S17-03'te `concept_graph` için kullanılır; burada
    `lexical_tsvector_pool` Postgres `plainto_tsquery('simple', kw)` ile zaten
    tokenize ediyor → basit split fan-out keyword listesi yeterli.

    Anchor title boşsa fallback: paper_id'yi keyword olarak gönder (lex 0 dönecek,
    vec pool taşır).
    """
    text = f"{title} {abstract}"
    seen: set[str] = set()
    out: list[str] = []
    for raw in text.split():
        tok = raw.strip(".,;:()[]{}\"'`/\\| \t\n").lower()
        if len(tok) < min_len:
            continue
        if tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
        if len(out) >= limit:
            break
    if not out:
        # Fallback: title varsa onu tek string olarak, yoksa boş list (caller graceful)
        if title.strip():
            return [title.strip()[:80]]
        return []
    return out


async def _anchor_vec_pool(
    encoder: _QueryEncoder,
    anchor_text: str,
    *,
    top_k: int = _VEC_TOP_K,
) -> list[tuple[str, float]]:
    """Anchor metnini BGE-M3 ile encode + Pinecone top-k. Hata → boş liste (graceful)."""
    from api.db.pinecone_client import PineconeQueryError, get_pinecone_index
    from api.utils.resilience import ResilienceTimeoutError

    if not anchor_text.strip():
        return []
    vectors = await asyncio.to_thread(encoder.encode, [anchor_text])
    vec = vectors[0]
    idx = get_pinecone_index()
    try:
        result = await idx.query_async(
            vector=vec, top_k=top_k, filter=None, include_metadata=False
        )
    except (ResilienceTimeoutError, PineconeQueryError) as exc:
        logger.warning("anchor_vec_pool degraded error=%s", exc.__class__.__name__)
        return []
    matches = result.get("matches") or []
    out: list[tuple[str, float]] = []
    for m in matches:
        pid = getattr(m, "id", None)
        score = getattr(m, "score", None)
        if isinstance(pid, str) and isinstance(score, (int, float)):
            out.append((pid, float(score)))
    return out


async def _enrich_cluster_candidates(
    db: Client, paper_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """papers + fact_paper_id_card + fact_paper_quality_v3 batch JOIN.

    Stage B `_enrich_candidates` aynası — yalnızca `is_suspicious=false` HARD filter
    aynı kuralla uygulanır (Plan §11 satır 418 + RISK_7 v1.2).
    """
    from api.db.supabase_client import supabase_call_async

    if not paper_ids:
        return {}

    papers_resp = await supabase_call_async(
        lambda: db.table("papers")
        .select("paper_id,title,abstract,year,lang")
        .in_("paper_id", paper_ids)
        .execute()
    )
    papers_rows = cast(list[dict[str, Any]], papers_resp.data or [])

    card_resp = await supabase_call_async(
        lambda: db.table("fact_paper_id_card")
        .select("paper_id,language,year,is_suspicious")
        .in_("paper_id", paper_ids)
        .eq("is_suspicious", False)
        .execute()
    )
    card_rows = cast(list[dict[str, Any]], card_resp.data or [])
    safe_ids = {r["paper_id"] for r in card_rows if isinstance(r.get("paper_id"), str)}
    card_map: dict[str, dict[str, Any]] = {
        r["paper_id"]: r for r in card_rows if isinstance(r.get("paper_id"), str)
    }

    quality_resp = await supabase_call_async(
        lambda: db.table("fact_paper_quality_v3")
        .select("paper_id,q_weak")
        .in_("paper_id", paper_ids)
        .execute()
    )
    quality_rows = cast(list[dict[str, Any]], quality_resp.data or [])
    q_map: dict[str, float | None] = {}
    for r in quality_rows:
        pid = r.get("paper_id")
        if isinstance(pid, str):
            qw = r.get("q_weak")
            q_map[pid] = float(qw) if isinstance(qw, (int, float)) else None

    enriched: dict[str, dict[str, Any]] = {}
    for row in papers_rows:
        pid = row.get("paper_id")
        if not isinstance(pid, str):
            continue
        if pid not in safe_ids:
            continue  # is_suspicious=true filtrelendi
        card = card_map.get(pid, {})
        title = row.get("title") or ""
        abstract = row.get("abstract") or ""
        enriched[pid] = {
            "paper_id": pid,
            "title": title,
            "abstract_preview": abstract[:1200] if abstract else "",
            "rerank_text": (title + " " + abstract)[:2000].strip(),
            "language": row.get("lang") or card.get("language"),
            "year": row.get("year") or card.get("year"),
            "q_weak": q_map.get(pid),
        }
    return enriched


async def _persist_cluster(
    db: Client,
    project_id: str,
    anchor_paper_id: str,
    ranked: list[tuple[str, float, dict[str, Any], dict[str, float]]],
) -> None:
    """project_cluster idempotent delete-then-insert + project_anchor terminal transition.

    ranked tuple: (paper_id, rerank_score, enriched_row, signals_13_dict).

    Migration 0037 ile gelen ek kolonlar: signals_13 jsonb (13-anahtar tam sözlük) +
    anchor_paper_id text (cluster'ı doğuran çapa snapshot'ı).
    """
    from datetime import UTC, datetime

    from postgrest.types import JSON

    from api.db.supabase_client import supabase_call_async

    rows: list[dict[str, Any]] = []
    for rank_idx, (pid, rerank_score, e, signals) in enumerate(ranked, start=1):
        rows.append(
            {
                "project_id": project_id,
                "paper_id": pid,
                # source='vec': hibrit RRF (vec+lex) sonrası reranker output;
                # 0016 CHECK enum ('vec','bib','theme') içinde semantic-vec'e en
                # yakın bucket. 'bib' (bibcoupling) ve 'theme' Stage C v2'de
                # 3 ayrı kanal source ayrımı için P003 sonrası.
                "source": "vec",
                "rrf_score": float(rerank_score),
                "q_weak": float(e.get("q_weak") or 0.0),
                "estra_score": float(signals.get("Q_weak", 0.0)),
                "rank_final": rank_idx,
                "signals_13": dict(signals),  # 0037 jsonb — 13 anahtar tam set
                "anchor_paper_id": anchor_paper_id,  # 0037 snapshot
            }
        )

    # Idempotent re-run: önce mevcut cluster sil, sonra insert (composite PK
    # (project_id, paper_id) çakışmasını upsert yerine delete+insert pattern ile çöz).
    await supabase_call_async(
        lambda: db.table("project_cluster")
        .delete()
        .eq("project_id", project_id)
        .execute()
    )
    if rows:
        await supabase_call_async(
            lambda: db.table("project_cluster")
            .insert(cast(JSON, rows))
            .execute()
        )

    completed_at = datetime.now(UTC).isoformat()
    await supabase_call_async(
        lambda: db.table("project_anchor")
        .update(
            {
                "cluster_status": "ready",
                "cluster_completed_at": completed_at,
                "cluster_error": None,
            }
        )
        .eq("project_id", project_id)
        .execute()
    )


async def _mark_failed(db: Client, project_id: str, reason: str) -> None:
    """project_anchor.cluster_status='failed' + cluster_error damgası + log.

    HK-1: hata yutma yasak — `cluster_error` jsonb (reason+timestamp).
    """
    from datetime import UTC, datetime

    from postgrest.types import JSON

    from api.db.supabase_client import supabase_call_async

    logger.error(
        "cluster_expander failed project=%s reason=%s", project_id, reason
    )
    now_iso = datetime.now(UTC).isoformat()
    payload: dict[str, Any] = {
        "cluster_status": "failed",
        "cluster_completed_at": now_iso,
        "cluster_error": {"reason": reason, "at": now_iso},
    }
    await supabase_call_async(
        lambda: db.table("project_anchor")
        .update(cast(JSON, payload))
        .eq("project_id", project_id)
        .execute()
    )


async def run(
    *,
    db: Client,
    project_id: str,
    encoder: _QueryEncoder | None = None,
    reranker: Reranker | None = None,
) -> ClusterExpandResponse:
    """Stage C iskelet — V1-S17 P001.

    `cluster_status='expanding'` set (in-progress marker) → pipeline → 'ready'/'failed'.
    BackgroundTasks wiring P002'de yapılır; bu modül sync test edilebilir.
    """
    from datetime import UTC, datetime

    anchor = await _fetch_anchor(db, project_id)
    anchor_paper_id = anchor["anchor_paper_id"]

    # In-progress marker — `cluster_started_at` 0037 ile damgalanır; poll endpoint
    # 'pending' (lock sonrası, henüz Stage C başlamamış) ile 'expanding' (Stage C
    # akıyor) ayrımını cluster_started_at NOT NULL ile yapar.
    started_at = datetime.now(UTC).isoformat()
    from api.db.supabase_client import supabase_call_async
    await supabase_call_async(
        lambda: db.table("project_anchor")
        .update(
            {
                "cluster_status": "expanding",
                "cluster_started_at": started_at,
                "cluster_error": None,
            }
        )
        .eq("project_id", project_id)
        .execute()
    )

    anchor_text = (anchor["title"] + " " + anchor["abstract"]).strip()
    keywords = _extract_lex_keywords(anchor["title"], anchor["abstract"])

    vec_task: asyncio.Task[list[tuple[str, float]]]
    if anchor_text:
        enc = encoder or _QueryEncoder()
        vec_task = asyncio.create_task(_anchor_vec_pool(enc, anchor_text))
    else:

        async def _empty_vec() -> list[tuple[str, float]]:
            return []

        vec_task = asyncio.create_task(_empty_vec())

    lex_task: asyncio.Task[list[tuple[str, float]]]
    if keywords:
        lex_task = asyncio.create_task(
            lexical_tsvector_pool(db, keywords, _LEX_TOP_K)
        )
    else:

        async def _empty_lex() -> list[tuple[str, float]]:
            return []

        lex_task = asyncio.create_task(_empty_lex())

    vec_results, lex_results = await asyncio.gather(
        vec_task, lex_task, return_exceptions=True
    )

    if isinstance(vec_results, BaseException):
        logger.warning("anchor_vec_pool failed (graceful): %s", vec_results)
        vec_results = []
    if isinstance(lex_results, BaseException):
        logger.warning("anchor_lex_pool failed (graceful): %s", lex_results)
        lex_results = []

    pools = [p for p in (vec_results, lex_results) if p]
    if not pools:
        await _mark_failed(db, project_id, "both pools empty (vec+lex)")
        raise ClusterPoolEmptyError(
            f"both pools empty for project {project_id}"
        )

    merged = _rrf_merge(*pools)[:_RRF_TOP_K]
    # Anchor kendisi cluster'a girmesin (PK çakışması ve UX gürültüsü).
    candidate_ids = [pid for pid, _ in merged if pid != anchor_paper_id]

    enriched = await _enrich_cluster_candidates(db, candidate_ids)
    if not enriched:
        await _mark_failed(
            db, project_id, "all RRF candidates filtered (is_suspicious=true)"
        )
        raise ClusterPoolEmptyError(
            f"all candidates filtered for project {project_id}"
        )

    if reranker is None:
        from api.services.reranker import BgeReranker

        reranker = BgeReranker()
    rerank_query = anchor["title"][:600] if anchor["title"] else anchor_paper_id
    candidate_texts = {pid: enriched[pid]["rerank_text"] for pid in enriched}
    top = await reranker.rerank(
        candidates=list(enriched.keys()),
        query=rerank_query,
        top_k=_FINAL_TOP_K,
        candidate_texts=candidate_texts,
    )

    ranked: list[tuple[str, float, dict[str, Any], dict[str, float]]] = []
    for pid, score in top:
        e = enriched.get(pid)
        if e is None:
            continue
        # KD-V1-S17-01 step 6: signals_13 curator reuse (5 kanıt + 8 placeholder).
        # Stage C aynı sözleşme; LightGBM Aşama 3 sonrası placeholder'lar dolar.
        signals = _signals_13(float(score))
        ranked.append((pid, float(score), e, signals))

    if not ranked:
        await _mark_failed(db, project_id, "reranker returned no candidates")
        raise ClusterPoolEmptyError(
            f"reranker empty for project {project_id}"
        )

    await _persist_cluster(db, project_id, anchor_paper_id, ranked)

    return ClusterExpandResponse(
        project_id=project_id,
        anchor_paper_id=anchor_paper_id,
        cluster_size=len(ranked),
        cluster_status="ready",
    )


__all__ = [
    "AnchorNotFoundError",
    "ClusterExpandResponse",
    "ClusterPoolEmptyError",
    "run",
]
