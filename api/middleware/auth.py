"""Supabase JWT verify middleware.

Doğrulama hiyerarşisi (B-3 audit follow-up):
  0) DEMO_AUTH_BYPASS=true    → `verify_signature=False` (2026-08-27, dar kapsamlı
     demo/beta anahtarı — APP_ENV'den bağımsız, bkz api/config.py DEMO_AUTH_BYPASS).
  1) SUPABASE_JWKS_URL set    → ES256/RS256 via PyJWKClient (production canon, Supabase ECC keyset).
  2) SUPABASE_JWT_SECRET set  → HS256 legacy/test path (Supabase classic dashboard JWT Secret).
  3) APP_ENV != production    → `verify_signature=False` dev fallback (forge serbest; SADECE dev/test).
  4) Production + (0)(1)(2) yok → 500 auth_misconfigured (zorla fail).

Önceki kod (P001/P002) prod'da da (3)'e düşüyordu; forge JWT 200 OK alıyordu → BLOCKER kapandı.
(0) o BLOCKER'ı geri açar ama bilerek, dar kapsamlı ve loglanarak — sadece imza
doğrulamasını atlar, WAITLIST_BYPASS/CORS gibi diğer prod korumalarına dokunmaz.
"""

import logging
from collections.abc import Awaitable, Callable

import jwt
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import get_settings

logger = logging.getLogger(__name__)
_demo_bypass_warned = False

# Module-level lazy cache — PyJWKClient kendi içinde signing key'leri 3600s TTL
# ile cache eder; biz client'ı per-process tek tutuyoruz.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client

PUBLIC_PATHS: frozenset[str] = frozenset(
    {"/healthz", "/docs", "/openapi.json", "/redoc", "/api/waitlist"}
)

# V1 Vitrin: tüm /api/q* path'leri — auth opsiyonel (varsa parse, yoksa anon).
# tier_gate vitrin gating'in TEK SOURCE OF TRUTH'u:
#   /api/q                       → quota counter (anon=3, authed=5)
#   /api/q/literature-review     → quota counter (anon=3, authed=10)
#                                  + endpoint anon paper_ids>3 → 403 tier_paper_limit
#   /api/q2                      → 403 tier_locked_soon (DM-054)
# kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md §3 KD-V1-S10-02
OPTIONAL_AUTH_PATHS: frozenset[str] = frozenset(
    {
        "/api/q",
        "/api/q/literature-review",
        "/api/q2",
        # V1-S12: TTS sesli dinlet — anon=1/gün, authed=5/gün (tier_gate)
        "/api/tts/literature-review",
        # FAZ 4A: global app teması — GET public (FE açılışta okur), PATCH admin
        # (_require_admin handler'da enforce eder). Opsiyonel: token varsa parse
        # (admin PATCH için user_id gerekir), yoksa anon (GET serbest).
        "/api/app/theme",
    }
)


class AuthMiddleware(BaseHTTPMiddleware):
    """Bearer JWT auth — public paths bypass; vitrin path'leri opsiyonel."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        is_optional = request.url.path in OPTIONAL_AUTH_PATHS

        if not auth_header.startswith("Bearer "):
            if is_optional:
                # anon — user_id None, tier_gate ANON olarak ele alır
                request.state.user_id = None
                request.state.user_jwt = None
                return await call_next(request)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "missing_or_invalid_authorization_header"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        settings = get_settings()

        try:
            if settings.DEMO_AUTH_BYPASS:
                # (0) Demo/beta dar-kapsamlı bypass — bkz api/config.py DEMO_AUTH_BYPASS.
                global _demo_bypass_warned
                if not _demo_bypass_warned:
                    logger.warning(
                        "DEMO_AUTH_BYPASS=true — imza doğrulaması ATLANIYOR "
                        "(sadece demo/beta faz için, gerçek Supabase login bağlanınca kaldırılmalı)"
                    )
                    _demo_bypass_warned = True
                payload = jwt.decode(
                    token,
                    options={"verify_signature": False},
                    algorithms=["ES256", "HS256", "RS256"],
                )
            elif settings.SUPABASE_JWKS_URL:
                # (1) Production canon — Supabase ECC keyset üzerinden ES256/RS256.
                signing_key = (
                    _get_jwks_client(settings.SUPABASE_JWKS_URL)
                    .get_signing_key_from_jwt(token)
                    .key
                )
                payload = jwt.decode(
                    token,
                    signing_key,
                    algorithms=["ES256", "RS256"],
                )
            elif settings.SUPABASE_JWT_SECRET:
                # (2) Legacy HS256 — test conftest bu yolu kullanıyor.
                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                )
            elif settings.APP_ENV != "production":
                # (3) Dev fallback — secret yok ama prod değil; imza atla.
                payload = jwt.decode(
                    token,
                    options={"verify_signature": False},
                    algorithms=["ES256", "HS256", "RS256"],
                )
            else:
                # (4) Production'da hiçbir doğrulama anahtarı yok → hard fail.
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": "auth_misconfigured",
                        "detail": (
                            "Production'da SUPABASE_JWKS_URL veya "
                            "SUPABASE_JWT_SECRET en az biri set olmalı."
                        ),
                    },
                )
        except jwt.PyJWTError as exc:
            if is_optional:
                # Vitrin path'inde geçersiz token → anon fallback (sertifika hatası kullanıcıyı durdurmasın)
                request.state.user_id = None
                request.state.user_jwt = None
                return await call_next(request)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "invalid_token", "detail": str(exc)},
            )

        user_id = payload.get("sub")
        if not user_id:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "missing_sub_claim"},
            )

        # V1-S18-P014 pilot allowlist gate. WAITLIST_BYPASS=true (dev/test
        # default) ise atla. Aksi: JWT email claim'i waitlist.status ∈
        # {invited, active} kontrolü; aksi 403 not_invited.
        if not settings.WAITLIST_BYPASS:
            from api.db.supabase_client import get_supabase_admin
            from api.services.waitlist_gate import is_email_allowed

            email = str(payload.get("email") or "").strip().lower()
            try:
                db = get_supabase_admin()
            except RuntimeError:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"error": "supabase_unavailable"},
                )
            allowed = await is_email_allowed(email, db)
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"error": "not_invited"},
                )

        request.state.user_id = user_id
        request.state.user_jwt = payload
        return await call_next(request)
