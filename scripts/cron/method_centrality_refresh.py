"""F13-S14 cron job: method_centrality periyodik recompute trigger.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S14
Migration: db/migrations/0007_method_centrality.sql (V1 türetilmiş tablo)

method_centrality compute Colab notebook üzerinde yapılır (Drive+Colab native iş
feedback'i: lokal araç refleksi yok). Bu job sadece SON refresh timestamp'inin
> 14 gün eski olduğunu doğrular ve "TRIGGER" log üretir; Colab notebook'u
manuel veya GitHub Actions webhook ile koşturulur. Otomatik trigger F13-S15'te
incelenecek (Colab API token vs.).
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

JOB = "method_centrality_refresh"
logger = cron_logger(JOB)
_STALENESS_DAYS = 14


def _check_freshness(client: Any) -> tuple[bool, str | None]:
    resp = (
        client.table("method_centrality")
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
        logger.info("method_centrality fresh (last=%s)", last)
        return 0
    logger.info(
        "method_centrality stale last=%s threshold=%dd — Colab notebook"
        " manual refresh önerilir",
        last,
        _STALENESS_DAYS,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
