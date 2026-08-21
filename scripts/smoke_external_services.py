"""Canlı dış servis smoke testi (R13.11 zorunlu fixture üretici, F8 DM-LLM-1).

Çalıştırma:
    cd ~/Desktop/papermind-app
    uv run python scripts/smoke_external_services.py

Çıktı:
    tests/fixtures/gemini_flash_canary.json
    tests/fixtures/pinecone_describe.json
    tests/fixtures/pinecone_query_sample.json
    tests/fixtures/supabase_schema_migrations.json
    tests/fixtures/redis_ping_cycle.json

Maliyet:
    - Gemini Flash 1 inference                     ≈ $0.0001
    - Pinecone describe + 1 query                  ≈ $0.0001
    - Supabase select 1 row                        free tier
    - Redis ping + set/get/del                     free tier
    Toplam ~$0.0005.

Halüsinasyon-Kod-Seviyesi (HK-3 + R13.11):
    Bu betik gerçek response snapshot üretir. Plan/tasarım/test bu fixture'lara
    göre yazılır. Mock-only commit yasak; her servis için en az 1 canlı smoke
    şart. Servis swap/version bump'ta snapshot diff CI'da otomatik tespit eder.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures"
FIXTURES.mkdir(parents=True, exist_ok=True)


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
    return out


def _save(name: str, payload: dict[str, Any]) -> None:
    payload["_captured_at"] = datetime.now(timezone.utc).isoformat()
    path = FIXTURES / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    print(f"✅ {path.relative_to(REPO)}")


def smoke_gemini(env: dict[str, str]) -> None:
    """Gemini 2.5 Flash canary via LLMService (F8 DM-LLM-1)."""
    import asyncio

    api_key = env.get("GEMINI_API_KEY")
    if not api_key:
        print("⏭  Gemini skipped (GEMINI_API_KEY yok)")
        return

    os.environ["GEMINI_API_KEY"] = api_key
    try:
        from api.services.llm_service import call as llm_call
    except ImportError as exc:
        print(f"⏭  Gemini skipped (litellm/llm_service import fail: {exc!r})")
        return

    t0 = time.monotonic()
    try:
        resp = asyncio.run(asyncio.wait_for(llm_call(prompt="ping", tier="flash"), timeout=10.0))
        elapsed = round(time.monotonic() - t0, 2)
        snapshot = {
            "service": "gemini_flash_canary",
            "model_used": resp.model_used,
            "elapsed_seconds": elapsed,
            "latency_ms": resp.latency_ms,
            "tokens_in": resp.tokens_in,
            "tokens_out": resp.tokens_out,
            "text_first_300": (resp.text or "")[:300],
            "ok": True,
        }
    except Exception as exc:
        elapsed = round(time.monotonic() - t0, 2)
        snapshot = {
            "service": "gemini_flash_canary",
            "elapsed_seconds": elapsed,
            "error": repr(exc),
            "ok": False,
        }

    _save("gemini_flash_canary.json", snapshot)


def smoke_pinecone(env: dict[str, str]) -> None:
    """Pinecone describe_index_stats + dummy query."""
    api_key = env.get("PINECONE_API_KEY")
    index_name = env.get("PINECONE_INDEX_NAME", "papers-bgem3")
    if not api_key:
        print("⏭  Pinecone skipped (PINECONE_API_KEY yok)")
        return

    try:
        from pinecone import Pinecone
    except ImportError:
        print("⏭  Pinecone skipped (pinecone client yok — uv pip install pinecone-client)")
        return

    pc = Pinecone(api_key=api_key)
    idx = pc.Index(index_name)

    # describe
    t0 = time.monotonic()
    stats = idx.describe_index_stats()
    el_describe = round(time.monotonic() - t0, 3)

    # Stats dict olarak (Pinecone v5+ farklı dönüş tipi)
    stats_dict = stats.to_dict() if hasattr(stats, "to_dict") else dict(stats)

    _save(
        "pinecone_describe.json",
        {
            "service": "pinecone_index_stats",
            "index_name": index_name,
            "elapsed_seconds": el_describe,
            "stats": stats_dict,
            "expected_dimension": 1024,
            "expected_metric": "cosine",
        },
    )

    # dummy query (rastgele 1024-d vektör — gerçek BGE-M3 embedding değil, sadece schema kontrolü)
    import random

    random.seed(42)
    vec = [random.gauss(0, 1) for _ in range(1024)]
    norm = sum(x * x for x in vec) ** 0.5
    vec = [x / norm for x in vec]  # L2 normalize

    t0 = time.monotonic()
    qres = idx.query(vector=vec, top_k=5, include_metadata=True, include_values=False)
    el_query = round(time.monotonic() - t0, 3)
    qres_dict = qres.to_dict() if hasattr(qres, "to_dict") else dict(qres)

    matches = qres_dict.get("matches", [])
    metadata_keys_seen: set[str] = set()
    for m in matches:
        md = m.get("metadata") or {}
        metadata_keys_seen.update(md.keys())

    _save(
        "pinecone_query_sample.json",
        {
            "service": "pinecone_query",
            "index_name": index_name,
            "top_k": 5,
            "elapsed_seconds": el_query,
            "match_count": len(matches),
            "metadata_keys_in_response": sorted(metadata_keys_seen),
            "expected_metadata_keys": ["D", "F", "S", "year", "q_weak", "method", "lang", "v_conf"],
            "metadata_present": len(metadata_keys_seen) > 0,
            "first_match_redacted": (
                {
                    "id_prefix": (matches[0].get("id") or "")[:10],
                    "score": matches[0].get("score"),
                    "metadata_sample": {
                        k: matches[0].get("metadata", {}).get(k)
                        for k in sorted(metadata_keys_seen)[:5]
                    },
                }
                if matches
                else None
            ),
        },
    )


def smoke_supabase(env: dict[str, str]) -> None:
    """Supabase admin client + schema_migrations select."""
    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_SECRET_KEY") or env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("⏭  Supabase skipped (SUPABASE_URL/SECRET_KEY yok)")
        return

    try:
        from supabase import create_client
    except ImportError:
        print("⏭  Supabase skipped (supabase client yok — uv pip install supabase)")
        return

    sb = create_client(url, key)
    t0 = time.monotonic()
    res = sb.table("schema_migrations").select("*").limit(20).execute()
    elapsed = round(time.monotonic() - t0, 3)

    rows = res.data or []
    _save(
        "supabase_schema_migrations.json",
        {
            "service": "supabase_admin",
            "url_host": url.split("//")[1].split(".")[0] + ".supabase.co",
            "elapsed_seconds": elapsed,
            "row_count": len(rows),
            "row_keys_sample": list(rows[0].keys()) if rows else [],
            "first_row_id_or_version": (
                rows[0].get("version") or rows[0].get("id") if rows else None
            ),
        },
    )


def smoke_redis(env: dict[str, str]) -> None:
    """Redis ping + set/get/del cycle."""
    url = env.get("REDIS_URL")
    if not url:
        print("⏭  Redis skipped (REDIS_URL yok)")
        return

    try:
        import redis
    except ImportError:
        print("⏭  Redis skipped (redis client yok — uv pip install redis)")
        return

    r = redis.from_url(url, socket_connect_timeout=5)
    t0 = time.monotonic()
    pong = r.ping()
    el_ping = round(time.monotonic() - t0, 3)

    key = "smoke:r13.11:test"
    val = "papermind-smoke-2026-04-30"
    t0 = time.monotonic()
    r.set(key, val, ex=60)
    el_set = round(time.monotonic() - t0, 3)
    got = r.get(key)
    r.delete(key)
    got_str = got.decode("utf-8") if isinstance(got, bytes) else got

    info = r.info("server")

    _save(
        "redis_ping_cycle.json",
        {
            "service": "redis",
            "url_redacted": url.split("@")[-1] if "@" in url else url,
            "ping_pong": pong is True,
            "ping_elapsed_seconds": el_ping,
            "set_get_match": got_str == val,
            "set_elapsed_seconds": el_set,
            "redis_version": info.get("redis_version"),
            "uptime_in_seconds": info.get("uptime_in_seconds"),
        },
    )


def main() -> int:
    print("PaperMind R13.11 dış servis smoke (HK-3 fixture üreteci)")
    print(f"Repo: {REPO}\nFixtures: {FIXTURES}\n")
    env = _load_env()
    smokes = [
        ("Gemini Flash", smoke_gemini),
        ("Pinecone", smoke_pinecone),
        ("Supabase", smoke_supabase),
        ("Redis", smoke_redis),
    ]
    failures: list[str] = []
    for name, fn in smokes:
        print(f"\n— {name} —")
        try:
            fn(env)
        except Exception as e:  # noqa: BLE001 (smoke betiği — fail-tolerant, fixture'a yansır)
            print(f"❌ {name} FAIL: {e!r}")
            failures.append(name)
    print("\n" + "=" * 60)
    if failures:
        print(f"FAIL ({len(failures)}): {', '.join(failures)}")
        return 1
    print("PASS — tüm smoke fixture'ları yazıldı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
