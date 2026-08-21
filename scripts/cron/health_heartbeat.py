"""F13-S14 cron job: /healthz periyodik kontrol heartbeat.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S14

Render servisi cold-start'tan kaçınmak için 10 dakikada bir /healthz GET çağrısı
yapar. Hata durumunda log + (Sentry breadcrumb F13-S15+ bağlanır).

Çevre değişkeni: PAPERMIND_API_BASE (default https://papermind-api.onrender.com)
"""

from __future__ import annotations

import os
import sys

import httpx

from scripts.cron._common import (
    bootstrap_repo_path,
    build_cron_arg_parser,
    cron_logger,
)

bootstrap_repo_path()

JOB = "health_heartbeat"
logger = cron_logger(JOB)
_DEFAULT_BASE = "https://papermind-api.onrender.com"
_TIMEOUT = 10.0


def main() -> int:
    parser = build_cron_arg_parser(JOB)
    parser.parse_args()

    base = os.getenv("PAPERMIND_API_BASE", _DEFAULT_BASE).rstrip("/")
    url = f"{base}/healthz"
    try:
        resp = httpx.get(url, timeout=_TIMEOUT)
    except httpx.RequestError as exc:
        logger.error("heartbeat_request_failed url=%s reason=%s", url, exc)
        return 1
    if resp.status_code != 200:
        logger.error(
            "heartbeat_non_200 url=%s status=%d body=%s",
            url,
            resp.status_code,
            resp.text[:200],
        )
        return 1
    try:
        body = resp.json()
    except ValueError:
        logger.warning("heartbeat_non_json url=%s body=%s", url, resp.text[:200])
        return 0
    logger.info(
        "heartbeat ok status=%s version=%s env=%s",
        body.get("status"),
        body.get("version"),
        body.get("env"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
