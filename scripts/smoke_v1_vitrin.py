"""V1 Vitrin canlı smoke testi (HK-3 + R13.11 + R13.13).

kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md (V1-S10-01: Q4/Q5 sections silindi;
        V1-S10-02 lit-review smoke ekleyecek)

Çalıştırma:
    cd ~/Desktop/papermind-app
    uv run python scripts/smoke_v1_vitrin.py

Çıktı (tests/fixtures/):
    openalex_search.json        — Q + Q1 backend (OpenAlex polite-pool)
    gemini_vitrin_summary.json  — Q1 (vitrin_summary brief, Gemini Flash)

Maliyet:
    OpenAlex polite       free
    Gemini Flash 1 inference ≈ $0.0001

HK-3: Mock-only commit yasak; her servis için canlı snapshot şart.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures"
FIXTURES.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO))


def _load_env() -> dict[str, str]:
    env_path = REPO / ".env"
    if not env_path.exists():
        sys.exit(f"FAIL: .env yok ({env_path})")
    out: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    # Inject into os.environ so pydantic-settings picks them up
    for k, v in out.items():
        os.environ.setdefault(k, v)
    return out


def _save(name: str, payload: dict[str, Any]) -> None:
    payload["_captured_at"] = datetime.now(UTC).isoformat()
    path = FIXTURES / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    print(f"   ✅ {path.relative_to(REPO)}")


# ───── 1. OpenAlex (Q + Q1) ─────


async def smoke_openalex() -> bool:
    from api.services.openalex_polite import search_papers

    query = "metaheuristic optimization"
    t0 = time.monotonic()
    try:
        papers = await search_papers(query, limit=3, year_from=2018)
    except Exception as exc:
        _save("openalex_search.json", {"ok": False, "error": repr(exc)})
        return False
    elapsed = round(time.monotonic() - t0, 3)

    _save(
        "openalex_search.json",
        {
            "service": "openalex_polite",
            "query": query,
            "elapsed_seconds": elapsed,
            "result_count": len(papers),
            "first_paper": (
                {
                    "openalex_id": papers[0].openalex_id,
                    "title": papers[0].title[:120],
                    "year": papers[0].year,
                    "authors_count": len(papers[0].authors),
                    "abstract_present": bool(papers[0].abstract),
                    "cited_by_count": papers[0].cited_by_count,
                }
                if papers
                else None
            ),
            "ok": len(papers) > 0,
        },
    )
    return len(papers) > 0


# ───── 2. Gemini Flash — vitrin_summary (Q1 brief) ─────


async def smoke_gemini_summary(env: dict[str, str]) -> bool:
    if not env.get("GEMINI_API_KEY"):
        print("   ⏭  GEMINI_API_KEY yok — atlandı")
        _save("gemini_vitrin_summary.json", {"skipped": True, "reason": "no_api_key"})
        return False

    from api.services.llm_service import call as llm_call

    prompt = (
        "Başlık: Highly accurate protein structure prediction with AlphaFold\n"
        "Abstract: AlphaFold uses neural networks based on a novel architecture "
        "to predict protein structures from amino acid sequences with high accuracy "
        "approaching experimental methods.\n\n"
        "Bu makaleyi 2 cümleyi geçmeyecek şekilde özetle."
    )
    t0 = time.monotonic()
    try:
        resp = await asyncio.wait_for(
            llm_call(prompt, tier="flash", mode="vitrin_summary"),
            timeout=20.0,
        )
        snapshot = {
            "service": "gemini_vitrin_summary",
            "mode": "vitrin_summary",
            "model_used": resp.model_used,
            "latency_ms": resp.latency_ms,
            "tokens_in": resp.tokens_in,
            "tokens_out": resp.tokens_out,
            "text": resp.text,
            "sentence_count_estimate": resp.text.count(".") if resp.text else 0,
            "ok": bool(resp.text and resp.text.strip()),
        }
    except Exception as exc:
        snapshot = {
            "service": "gemini_vitrin_summary",
            "elapsed_seconds": round(time.monotonic() - t0, 2),
            "error": repr(exc),
            "ok": False,
        }
    _save("gemini_vitrin_summary.json", snapshot)
    return snapshot.get("ok", False)


# ───── orchestrator ─────


async def main_async(env: dict[str, str]) -> int:
    print("PaperMind V1 Vitrin canlı smoke (HK-3 fixture üreteci)")
    print(f"Repo: {REPO}\nFixtures: {FIXTURES}\n")

    results: list[tuple[str, bool]] = []

    print("— OpenAlex (Q/Q1 backend) —")
    results.append(("OpenAlex", await smoke_openalex()))

    print("\n— Gemini Flash · vitrin_summary (Q1) —")
    results.append(("Gemini Summary", await smoke_gemini_summary(env)))

    print("\n" + "=" * 60)
    failed = [name for name, ok in results if not ok]
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'} {name}")
    if failed:
        print(f"\nFAIL ({len(failed)}): {', '.join(failed)}")
        return 1
    print("\nPASS — tüm V1 vitrin smoke fixture'ları yazıldı.")
    return 0


def main() -> int:
    env = _load_env()
    return asyncio.run(main_async(env))


if __name__ == "__main__":
    sys.exit(main())
