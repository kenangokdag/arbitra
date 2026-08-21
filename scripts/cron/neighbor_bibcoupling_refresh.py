"""F13-S14 cron job: neighbor_bibcoupling periyodik recompute trigger.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S14
Migration: db/migrations/0008_neighbor_bibcoupling.sql (V1 türetilmiş tablo)

method_centrality_refresh ile aynı desen: tazelik kontrol + log. Recompute
Colab notebook'ta yapılır; bu job Render schedule'da konuşlanır ve >21 gün
eskime durumunda uyarı log üretir.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from scripts.cron._common import (
    bootstrap_repo_path,
    build_cron_arg_parser,
    cron_logger,
)

bootstrap_repo_path()

JOB = "neighbor_bibcoupling_refresh"
logger = cron_logger(JOB)
_STALENESS_DAYS = 21


def _check_freshness(client: Any) -> tuple[bool, str | None]:
    resp = (
        client.table("neighbor_bibcoupling")
        .select("computed_at")
        .order("computed_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        return False, None
    last = rows[0].get("computed_at")
    if not isinstance(last, str):
        return False, None
    last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
    age = datetime.now(UTC) - last_dt
    return age <= timedelta(days=_STALENESS_DAYS), last


def main() -> int:
    parser = build_cron_arg_parser(JOB)
    parser.parse_args()

    from api.db.supabase_client import get_supabase_admin

    try:
        fresh, last = _check_freshness(get_supabase_admin())
    except Exception as exc:
        logger.warning("freshness_check_failed reason=%s — TRIGGER skipped", exc)
        return 0
    if fresh:
        logger.info("neighbor_bibcoupling fresh (last=%s)", last)
        return 0
    logger.info(
        "neighbor_bibcoupling stale last=%s threshold=%dd — Colab notebook"
        " manual refresh önerilir",
        last,
        _STALENESS_DAYS,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
