"""Global app teması servisi (FAZ 4A) — tek-satır oku/yaz.

Desen: dim route ile AYNI (api/routes/dim.py:38) — `_supabase()` config yoksa
None döner, `supabase_call_async` ile thread-offload. Tablo: app_theme_settings
(migration 0043), tek satır (id=1).

Observability (CANON): hata-yutma yok.
  - get_theme: Supabase yoksa (dev) VEYA satır yoksa → kod-varsayılanı (beklenen
    durum, sessiz değil — config yokluğu normal). Transport hatası → LOGLANIR
    (görünür) + kod-varsayılanı (public açılış okuması 500 ile patlamaz). ASLA çökme.
  - set_theme: admin yazma. Supabase yoksa/yazma hata verirse YÜKSELİR (sahte
    "kaydedildi" YASAK — yutma yok).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, cast

from supabase import Client

from api.models.theme import ThemeSettings, default_theme

logger = logging.getLogger(__name__)

_TABLE = "app_theme_settings"


def _supabase() -> Client | None:
    """Service-role client; Supabase config yoksa (dev/test) None (dim deseni)."""
    from api.config import get_settings

    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SECRET_KEY:
        return None
    from api.db.supabase_client import get_supabase_admin

    return get_supabase_admin()


def _row_to_model(row: dict[str, Any]) -> ThemeSettings:
    """DB satırını sözleşmeye çevir (yalnız bilinen alanlar; extra='forbid' uyumu)."""
    return ThemeSettings(
        accent_color=row["accent_color"],
        bg_color=row["bg_color"],
        ink_color=row["ink_color"],
        font_sans=row["font_sans"],
        font_serif=row["font_serif"],
        updated_by=row.get("updated_by"),
        updated_at=row.get("updated_at"),
    )


async def get_theme() -> ThemeSettings:
    """Tek satır temayı oku; yoksa kod-varsayılanı (ASLA çökme).

    Supabase yoksa (dev) → varsayılan (degraded değil). Transport hatası →
    loglanır + varsayılan (public açılış okuması kesintisiz). Satır yoksa → varsayılan."""
    db = _supabase()
    if db is None:
        return default_theme()

    from api.db.supabase_client import SupabaseQueryError, supabase_call_async

    try:
        result = await supabase_call_async(
            lambda: db.table(_TABLE)
            .select("*")
            .eq("id", 1)
            .limit(1)
            .execute()
        )
    except SupabaseQueryError as exc:
        # Görünür (loglanır), yutulmaz; ama public açılış okuması 500 olmasın →
        # kod-varsayılanına düş (tema ayarlanmamış gibi davran).
        logger.warning("theme read failed → code default: %s", exc)
        return default_theme()

    rows = cast(list[dict[str, Any]], result.data or [])
    if not rows:
        return default_theme()
    return _row_to_model(rows[0])


async def set_theme(settings: ThemeSettings, user_id: str) -> ThemeSettings:
    """Admin upsert (id=1) → güncel temayı döndür. Yazma hatası YÜKSELİR (yutma yok).

    updated_by/updated_at server-side yazılır (body değeri göz ardı edilir)."""
    db = _supabase()
    if db is None:
        # Dev/test'te Supabase yoksa sahte "kaydedildi" döndürmek YASAK — dürüst hata.
        raise RuntimeError("theme persistence unavailable: SUPABASE not configured")

    from api.db.supabase_client import supabase_call_async

    now = datetime.now(UTC)
    row: dict[str, Any] = {
        "id": 1,
        "accent_color": settings.accent_color,
        "bg_color": settings.bg_color,
        "ink_color": settings.ink_color,
        "font_sans": settings.font_sans,
        "font_serif": settings.font_serif,
        "updated_by": user_id,
        "updated_at": now.isoformat(),
    }

    await supabase_call_async(lambda: db.table(_TABLE).upsert(row).execute())
    logger.info("app theme updated by %s", user_id)

    return settings.model_copy(update={"updated_by": user_id, "updated_at": now})


__all__ = ["get_theme", "set_theme"]
