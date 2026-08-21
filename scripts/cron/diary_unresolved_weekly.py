"""F13-S14 cron job: 21+ gün açık defter olayları haftalık raporu (S1).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S14
Migration: db/migrations/0029_project_event.sql §22-23 (idx_project_event_user_unresolved)

Mail provider (Q4) henüz bağlanmadığından bu job şimdilik:
  - 21+ gün resolved_at IS NULL satır sayısını user_id başına grupluyor
  - Her grup için log line yazıyor

Mail entegrasyonu F13-S15+ — bu job çıktısı doğrudan mail provider'a beslenecek.
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from scripts.cron._common import (
    bootstrap_repo_path,
    build_cron_arg_parser,
    cron_logger,
)

bootstrap_repo_path()

JOB = "diary_unresolved_weekly"
logger = cron_logger(JOB)
_LOOKBACK_DAYS = 21


def _fetch_unresolved(client: Any, cutoff_iso: str) -> list[dict[str, Any]]:
    resp = (
        client.table("project_event")
        .select("user_id,project_id,page_slug,created_at")
        .is_("resolved_at", "null")
        .lt("created_at", cutoff_iso)
        .execute()
    )
    return cast(list[dict[str, Any]], resp.data or [])


def main() -> int:
    parser = build_cron_arg_parser(JOB)
    parser.parse_args()

    from api.db.supabase_client import get_supabase_admin

    cutoff = datetime.now(UTC) - timedelta(days=_LOOKBACK_DAYS)
    rows = _fetch_unresolved(get_supabase_admin(), cutoff.isoformat())
    if not rows:
        logger.info("no_unresolved_events lookback=%dd", _LOOKBACK_DAYS)
        return 0

    by_user: Counter[str] = Counter(str(r.get("user_id", "")) for r in rows)
    for user_id, count in by_user.most_common():
        logger.info(
            "unresolved_summary user_id=%s count=%d (mail provider stub)",
            user_id,
            count,
        )
    logger.info("processed %d users %d events", len(by_user), len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
