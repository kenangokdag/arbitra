"""SEC-1 / P01-T01·T04 — boot-time production config validation + quota fail-closed."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.config import Settings
from api.config_validation import ProductionConfigError, validate_runtime_config
from api.middleware import tier_gate


def _prod_ok() -> Settings:
    """Güvenli production yapılandırması (tüm ön-koşullar sağlanmış)."""
    return Settings(
        APP_ENV="production",
        WAITLIST_BYPASS=False,
        SUPABASE_JWKS_URL="https://x.supabase.co/jwks",
        FRONTEND_ORIGINS="https://app.example.com",
        ADMIN_USER_IDS="u-admin",
        REDIS_URL="redis://prod-redis:6379/0",
    )


def test_prod_waitlist_bypass_true_rejects_boot():
    """P01-T04: production + WAITLIST_BYPASS=true → boot reddedilir (fail-fast)."""
    s = _prod_ok().model_copy(update={"WAITLIST_BYPASS": True})
    with pytest.raises(ProductionConfigError, match="WAITLIST_BYPASS"):
        validate_runtime_config(s)


def test_prod_missing_auth_provider_rejects_boot():
    """P01-T01: production + auth provider yok → boot reddedilir (forge token riski)."""
    s = _prod_ok().model_copy(update={"SUPABASE_JWKS_URL": "", "SUPABASE_JWT_SECRET": ""})
    with pytest.raises(ProductionConfigError, match="auth provider"):
        validate_runtime_config(s)


def test_prod_missing_cors_rejects_boot():
    s = _prod_ok().model_copy(update={"FRONTEND_ORIGINS": ""})
    with pytest.raises(ProductionConfigError, match="FRONTEND_ORIGINS"):
        validate_runtime_config(s)


def test_prod_ok_boots_with_warnings_list():
    """Güvenli prod yapılandırması boot eder (fatal yok); uyarı listesi döner."""
    warnings = validate_runtime_config(_prod_ok())
    assert isinstance(warnings, list)  # fatal yok → exception yok


def test_dev_insecure_defaults_only_warn_not_fatal():
    """Dev'de WAITLIST_BYPASS=true + auth yok → boot kırılmaz, sadece uyarı (yerel dev)."""
    s = Settings(APP_ENV="development", WAITLIST_BYPASS=True)
    warnings = validate_runtime_config(s)  # raise YOK
    assert any("WAITLIST_BYPASS" in w for w in warnings)


@pytest.mark.asyncio
async def test_quota_fail_closed_in_production(monkeypatch):
    """P01-T04: production + Redis yok → pahalı uç 503 (fail-closed)."""
    monkeypatch.setattr(tier_gate, "_get_redis", lambda: None)
    monkeypatch.setattr(
        tier_gate, "get_settings", lambda: Settings(APP_ENV="production")
    )
    with pytest.raises(HTTPException) as exc:
        await tier_gate._incr_and_get_quota("k", 60)
    assert exc.value.status_code == 503
    assert exc.value.detail["error"] == "quota_backend_unavailable"


@pytest.mark.asyncio
async def test_quota_permissive_in_dev(monkeypatch):
    """Dev'de Redis yok → permissive (yerel geliştirme kırılmaz)."""
    monkeypatch.setattr(tier_gate, "_get_redis", lambda: None)
    monkeypatch.setattr(
        tier_gate, "get_settings", lambda: Settings(APP_ENV="development")
    )
    count = await tier_gate._incr_and_get_quota("k", 60)
    assert count == 1
