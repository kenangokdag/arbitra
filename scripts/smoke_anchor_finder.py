"""F9 P095 anchor_finder live smoke (R13.11/R13.13).

Bypasses Supabase project read by constructing a synthetic ParsedUnderstanding
and exercising the real pipeline:
  HyDE (Gemini Flash) → BGE-M3 encode → Pinecone vec(80) + Supabase tsvector(80)
  → RRF k=60 → enrich (papers + fact_paper_id_card + fact_paper_quality_v3)
  → uniform rerank (BGE skipped to avoid 700MB cold start)
  → save tests/fixtures/anchor_candidates_v1.json

Çalıştırma:
    cd /Users/omer/Code/papermind-app
    uv run python scripts/smoke_anchor_finder.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures"
FIXTURES.mkdir(parents=True, exist_ok=True)


def _load_env() -> None:
    env_path = REPO / ".env"
    if not env_path.exists():
        sys.exit(f"FAIL: .env yok ({env_path})")
    import os
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


async def main() -> int:
    _load_env()

    from api.db.supabase_client import get_supabase_admin
    from api.models.research_area import ParsedUnderstanding
    from api.services import anchor_finder
    from api.services.pool_router import _QueryEncoder, _rrf_merge, lexical_tsvector_pool

    parsed = ParsedUnderstanding(
        focuses=[
            "ÇKKV ile yükseköğretim akreditasyon kriterlerinin ağırlıklandırılması",
            "Akreditasyon süreçlerinde TOPSIS ve AHP karşılaştırması",
            "MCDM yöntemleriyle kalite göstergesi sıralaması",
        ],
        field="Mühendislik",
        subfield="Endüstri Mühendisliği",
        interdisc=True,
        confidence="med",
        adviser_text="Bu üç odakla devam edebilir miyiz?",
        finished=True,
    )

    db = get_supabase_admin()
    project_id = "smoke-anchor-finder-test"
    user_id = "smoke-user"

    timings: dict[str, float] = {}

    t0 = time.perf_counter()
    packet = await anchor_finder._call_hyde(
        project_id=project_id, user_id=user_id, parsed=parsed
    )
    timings["hyde_ms"] = (time.perf_counter() - t0) * 1000
    print(f"[hyde] {timings['hyde_ms']:.0f}ms keywords={packet.keywords}")

    enc = _QueryEncoder()
    t0 = time.perf_counter()
    vec_pool, lex_pool = await asyncio.gather(
        anchor_finder._vec_pool(enc, packet.pseudo_paragraph),
        lexical_tsvector_pool(db, packet.keywords, top_k=80),
    )
    timings["fanout_ms"] = (time.perf_counter() - t0) * 1000
    print(f"[fanout] {timings['fanout_ms']:.0f}ms vec={len(vec_pool)} lex={len(lex_pool)}")

    pools = [p for p in (vec_pool, lex_pool) if p]
    if not pools:
        print("FAIL: both pools empty")
        return 1
    merged = _rrf_merge(*pools)[:50]
    candidate_ids = [pid for pid, _ in merged]

    t0 = time.perf_counter()
    enriched = await anchor_finder._enrich_candidates(db, candidate_ids)
    timings["enrich_ms"] = (time.perf_counter() - t0) * 1000
    print(f"[enrich] {timings['enrich_ms']:.0f}ms safe_count={len(enriched)}")

    # Top-3 (RRF order, no real BGE rerank to keep smoke fast)
    top3 = [(pid, 1.0 - i * 0.1) for i, pid in enumerate(candidate_ids[:3]) if pid in enriched]
    candidates = []
    for pid, score in top3:
        e = enriched[pid]
        candidates.append({
            "paper_id": pid,
            "title": e["title"][:200],
            "year": e["year"],
            "language": e["language"],
            "q_weak": e["q_weak"],
            "decision_band": anchor_finder._decision_band(e["q_weak"]),
            "rerank_score": score,
        })

    timings["total_ms"] = sum(v for k, v in timings.items() if k.endswith("_ms"))

    snapshot = {
        "service": "anchor_finder_pipeline",
        "captured_at": datetime.now(UTC).isoformat(),
        "input": {
            "focuses": parsed.focuses,
            "field": parsed.field,
        },
        "hyde_packet": {
            "pseudo_paragraph": packet.pseudo_paragraph,
            "keywords": packet.keywords,
        },
        "pool_sizes": {"vec": len(vec_pool), "lex": len(lex_pool)},
        "rrf_top": len(merged),
        "enriched_after_suspicious_filter": len(enriched),
        "candidates": candidates,
        "timings_ms": timings,
        "p95_target_ms": 8000,
        "p95_pass": timings["total_ms"] < 8000,
    }
    out = FIXTURES / "anchor_candidates_v1.json"
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"\n[fixture] {out}")
    print(f"[total] {timings['total_ms']:.0f}ms (target<8000ms: {snapshot['p95_pass']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
