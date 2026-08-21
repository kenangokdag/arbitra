"""F13-S14 cron job: aylık defter digest tetikleyici (S1).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S14 + Q4
Sayfa: Page_Design/Sayfa_Plani_v2/S1_arastirma_defteri.rtf §4 (pre-advisor özet)

Bu job ayda 1 kez her aktif kullanıcı için son 30 gün defter olayı sayısını
listeler. Mail provider bağlandığında her kullanıcıya
/api/diary/pre-advisor-summary çıktısı gönderilir; şimdilik:
  - DB'den 30-günlük aktif kullanıcı listesi
  - User başına olay sayısı + page çeşitliliği
  - Log line (mail provider yok)
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from scripts.cron._common import (
    bootstrap_repo_path,
    build_cron_arg_parser,
    cron_logger,
)

bootstrap_repo_path()

JOB = "diary_monthly_digest"
logger = cron_logger(JOB)
_LOOKBACK_DAYS = 30


def _fetch_recent(client: Any, since_iso: str) -> list[dict[str, Any]]:
    resp = (
        client.table("project_event")
        .select("user_id,project_id,page_slug,created_at")
        .gte("created_at", since_iso)
        .execute()
    )
    return cast(list[dict[str, Any]], resp.data or [])


def main() -> int:
    parser = build_cron_arg_parser(JOB)
    parser.parse_args()

    from api.db.supabase_client import get_supabase_admin

    since = datetime.now(UTC) - timedelta(days=_LOOKBACK_DAYS)
    rows = _fetch_recent(get_supabase_admin(), since.isoformat())
    if not rows:
        logger.info("no_active_users lookback=%dd", _LOOKBACK_DAYS)
        return 0

    by_user: dict[str, dict[str, int]] = defaultdict(
        lambda: {"events": 0, "pages": 0}
    )
    page_sets: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        u = str(r.get("user_id", ""))
        by_user[u]["events"] += 1
        page_sets[u].add(str(r.get("page_slug", "")))
    for u, agg in by_user.items():
        agg["pages"] = len(page_sets[u])
        logger.info(
            "digest user_id=%s events=%d distinct_pages=%d (mail provider stub)",
            u,
            agg["events"],
            agg["pages"],
        )
    logger.info("processed %d active users", len(by_user))
    return 0


if __name__ == "__main__":
    sys.exit(main())
