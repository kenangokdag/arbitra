"""V1-S18-P014 pilot allowlist servisi.

Plan: docs/plans/MVP_TOMORROW_EXECUTION_PLAN.md §B3

AuthMiddleware'in JWT-verify sonrası kullandığı tek fonksiyon:
`is_email_allowed(email, db)` → True/False.

Felsefe: dev/test'te `WAITLIST_BYPASS=true` ile bu modül hiç çağrılmaz
(middleware kısa-devre yapar). Production'da SUPABASE_* envleri set
edildikten sonra `WAITLIST_BYPASS=false` ile aktifleşir.

Kontrol kuralı: waitlist.status ∈ {invited, active} → izinli. Aksi
(yok, pending, declined) → reddet.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from supabase import Client

from api.db.supabase_client import supabase_call_async

logger = logging.getLogger(__name__)

_ALLOWED_STATUSES: frozenset[str] = frozenset({"invited", "active"})


async def is_email_allowed(email: str, db: Client) -> bool:
    """waitlist.status ∈ {invited, active} ise True. Aksi False.

    Boş email veya satır yoksa False (whitelist semantiği).
    SUPABASE hatalarında False (fail-closed — pilot dönemi konservatif).
    """
    email = (email or "").strip().lower()
    if not email:
        return False

    try:
        resp = await supabase_call_async(
            lambda: db.table("waitlist")
            .select("status")
            .eq("email", email)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # SupabaseQueryError / ResilienceTimeoutError
        logger.warning("waitlist_gate query failed: %s", exc.__class__.__name__)
        return False

    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        return False
    status = str(rows[0].get("status") or "")
    return status in _ALLOWED_STATUSES


__all__ = ["is_email_allowed"]
