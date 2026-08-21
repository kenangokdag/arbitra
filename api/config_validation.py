"""Boot-time production config validation — FAIL-FAST (SEC-1 / P01-T01·T04).

Sorun (reality scan): birçok güvenlik ayarı production'da fail-OPEN default'a sahip
(WAITLIST_BYPASS=true, APP_ENV default 'development' → forge-token dev fallback,
FRONTEND_ORIGINS boş). Uygulama bu yanlış-yapılandırmayla yine de boot ediyor ve
per-request fail ediyor; bir operatör bir env'i unutursa kapı sessizce açık kalıyor.

Çözüm: APP_ENV=production iken kritik güvenlik ön-koşulları boot'ta DOĞRULANIR;
eksikse uygulama AYAĞA KALKMAZ (fail-fast > fail-open). Dev/staging serbest
(yerel geliştirme kırılmaz). observability canon: hata yutulmaz, yükselir.
"""

from __future__ import annotations

import logging

from api.config import Settings

logger = logging.getLogger(__name__)


class ProductionConfigError(RuntimeError):
    """Production'da güvenlik-kritik env eksik/yanlış → boot reddedilir."""


def validate_runtime_config(settings: Settings) -> list[str]:
    """Boot ön-koşullarını doğrular.

    APP_ENV=production iken fatal ihlaller ProductionConfigError yükseltir
    (boot durur). Dev/staging'de yalnız uyarı listesi döner (boot devam).
    Döner: non-fatal uyarı mesajları (loglanır).
    """
    warnings: list[str] = []
    fatal: list[str] = []
    prod = settings.APP_ENV == "production"

    # --- P01-T04: kota/waitlist bypass production'da YASAK ---
    if settings.WAITLIST_BYPASS:
        msg = (
            "WAITLIST_BYPASS=true — pilot allowlist kapısı bypass ediliyor "
            "(set WAITLIST_BYPASS=false)"
        )
        (fatal if prod else warnings).append(msg)

    # --- P01-T01: auth provider production'da zorunlu (forge-token yolu kapalı) ---
    if not (settings.SUPABASE_JWKS_URL or settings.SUPABASE_JWT_SECRET):
        msg = (
            "auth provider yok — SUPABASE_JWKS_URL veya SUPABASE_JWT_SECRET "
            "set edilmeli (aksi halde dev fallback forge token kabul eder)"
        )
        (fatal if prod else warnings).append(msg)

    # --- CORS: production'da kaynak listesi zorunlu ---
    if prod and not [o for o in settings.FRONTEND_ORIGINS.split(",") if o.strip()]:
        fatal.append(
            "FRONTEND_ORIGINS boş — production'da izinli cross-origin yok "
            "(set FRONTEND_ORIGINS=https://...)"
        )

    # --- admin allowlist: prod'da boş = admin uçları kapalı (fail-closed; uyarı) ---
    if prod and not [u for u in settings.ADMIN_USER_IDS.split(",") if u.strip()]:
        warnings.append(
            "ADMIN_USER_IDS boş — admin uçları production'da kapalı (kasıtlıysa OK)"
        )

    # --- Redis: prod'da gerçek backing yoksa kota fail-closed olur (uyarı) ---
    if prod and (not settings.REDIS_URL or "localhost" in settings.REDIS_URL):
        warnings.append(
            "REDIS_URL localhost/boş — production'da kota fail-CLOSED davranır "
            "(pahalı uçlar Redis yokken 503 döner)"
        )

    for w in warnings:
        logger.warning("config: %s", w)

    if fatal:
        joined = "\n  - ".join(fatal)
        raise ProductionConfigError(
            "Production boot reddedildi — güvenlik-kritik yapılandırma eksik:\n  - "
            + joined
        )

    return warnings
