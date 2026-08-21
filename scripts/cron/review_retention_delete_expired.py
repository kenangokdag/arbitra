"""Cron job: KVKK hakemlik retention silme (F14 review_job).

Bozuk söz kapatma: web/src/app/(app)/review/page.tsx UI'si "bu süre sonunda
yüklenen dosya silinir" vaat eder; retention_days api/routes/review.py'de
yakalanıp review_job.privacy JSONB'sine yazılır. Migration 0044 delete_after
eşiğini açar (= created_at + retention_days); bu cron süresi geçen işi siler.
manuscript + report satır içinde (inline JSONB) tutulduğundan satırı silmek
yüklenen içeriği de siler — ayrı object storage yok (0041).

completion_delete_expired.py deseninin birebir aynası; FARK: review IZOLE
Supabase client'ı (get_review_supabase_admin — review_service ile AYNI),
tablo = review_job.

Çalışma (Render schedule: günde 1 kez 04:30 UTC — 04:00 completion ile çakışmaz):
    DELETE FROM public.review_job WHERE delete_after < :cutoff;
    -- cutoff = Python'da hesaplanan ISO timestamp (datetime.now(UTC).isoformat());
    -- PG 'now()' literal-string parser'ına bağlı kalmaz (_insert_job ile aynı yazım).
    -- (RLS bypass: service-role admin client)

Dry-run: silinecek satır sayısını yazar, DELETE yapmaz.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from typing import Any

from scripts.cron._common import (
    bootstrap_repo_path,
    build_cron_arg_parser,
    cron_logger,
)

bootstrap_repo_path()

JOB = "review_retention_delete_expired"
logger = cron_logger(JOB)


def _count_expired(client: Any, cutoff: str) -> int:
    resp = (
        client.table("review_job")
        .select("job_id", count="exact")
        .lt("delete_after", cutoff)
        .execute()
    )
    count = getattr(resp, "count", None)
    if count is None:
        return len(resp.data or [])
    return int(count)


def _delete_expired(client: Any, cutoff: str) -> int:
    resp = (
        client.table("review_job")
        .delete()
        .lt("delete_after", cutoff)
        .execute()
    )
    return len(resp.data or [])


def main() -> int:
    parser = build_cron_arg_parser(JOB)
    args = parser.parse_args()

    from api.db.supabase_client import get_review_supabase_admin

    client = get_review_supabase_admin()
    # Cutoff'u Python'da bir kez hesapla (PG 'now()' parser'ına bağlanma).
    cutoff = datetime.now(UTC).isoformat()
    if args.dry_run:
        n = _count_expired(client, cutoff)
        logger.info("dry_run: %d expired review_job satırı silinecek", n)
        return 0

    n = _delete_expired(client, cutoff)
    logger.info(
        "deleted %d expired review_job rows (delete_after < %s)", n, cutoff
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
