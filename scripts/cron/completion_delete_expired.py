"""F13-S14 cron job: KVKK 3-ay otomatik silme (S2 Proje Tamamlama).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S14
Sayfa: Page_Design/Sayfa_Plani_v2/S2_proje_tamamlama.rtf §Felsefe
RTF: "Kullanıcı silene kadar hafızada bekler (3 ay), sonrasında silinir."

Çalışma (Render schedule: günde 1 kez 04:00 UTC önerilen):
    DELETE FROM public.project_completion WHERE delete_after < now();
    -- (RLS bypass: service-role admin client)

Dry-run: silinecek satır sayısını yazar, DELETE yapmaz.
"""

from __future__ import annotations

import sys
from typing import Any

from scripts.cron._common import (
    bootstrap_repo_path,
    build_cron_arg_parser,
    cron_logger,
)

bootstrap_repo_path()

JOB = "completion_delete_expired"
logger = cron_logger(JOB)


def _count_expired(client: Any) -> int:
    resp = (
        client.table("project_completion")
        .select("id", count="exact")
        .lt("delete_after", "now()")
        .execute()
    )
    count = getattr(resp, "count", None)
    if count is None:
        return len(resp.data or [])
    return int(count)


def _delete_expired(client: Any) -> int:
    resp = (
        client.table("project_completion")
        .delete()
        .lt("delete_after", "now()")
        .execute()
    )
    return len(resp.data or [])


def main() -> int:
    parser = build_cron_arg_parser(JOB)
    args = parser.parse_args()

    from api.db.supabase_client import get_supabase_admin

    client = get_supabase_admin()
    if args.dry_run:
        n = _count_expired(client)
        logger.info("dry_run: %d expired completion satırı silinecek", n)
        return 0

    n = _delete_expired(client)
    logger.info("deleted %d expired completion rows (delete_after < now())", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
