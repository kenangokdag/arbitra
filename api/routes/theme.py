"""Global app teması /api/app/theme — public oku, admin yaz (FAZ 4A).

  GET  /api/app/theme  — PUBLIC (auth yok; FE açılışta okur). theme_service.get_theme().
  PATCH /api/app/theme — admin (review._require_admin allowlist, prod fail-closed).

Auth: GET için path OPTIONAL_AUTH_PATHS'te (auth.py) → token zorunlu değil. PATCH
_require_admin dependency'sini REUSE eder (ikinci yetki yolu açılmaz).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.models.theme import ThemeSettings
from api.routes.review import _require_admin
from api.services import theme_service

router = APIRouter(prefix="/api/app", tags=["theme"])


@router.get("/theme", response_model=ThemeSettings)
async def get_theme() -> ThemeSettings:
    """PUBLIC — güncel global temayı döndür (yoksa kod-varsayılanı)."""
    return await theme_service.get_theme()


@router.patch("/theme", response_model=ThemeSettings)
async def patch_theme(
    settings: ThemeSettings,
    admin_id: str = Depends(_require_admin),
) -> ThemeSettings:
    """Admin — temayı upsert et, güncel temayı döndür (updated_by=admin)."""
    return await theme_service.set_theme(settings, admin_id)
