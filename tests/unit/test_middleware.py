"""P001 middleware unit tests (auth + rate_limit + sentry scrub)."""

import jwt
import pytest
from fastapi.testclient import TestClient

from api.middleware.rate_limit import _window
from api.middleware.sentry import _before_breadcrumb, _before_send, scrub_pii

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_rate_window() -> None:
    """Her test öncesi in-memory rate window'u temizle."""
    _window.clear()


# ---------- /healthz public path ----------


def test_healthz_no_auth_required(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "env" in body


# ---------- AuthMiddleware ----------


def test_auth_missing_header_returns_401(client: TestClient) -> None:
    response = client.get("/api/anywhere")
    assert response.status_code == 401
    assert response.json()["error"] == "missing_or_invalid_authorization_header"


def test_auth_invalid_bearer_format_returns_401(client: TestClient) -> None:
    response = client.get("/api/anywhere", headers={"Authorization": "Basic xxx"})
    assert response.status_code == 401


def test_auth_invalid_jwt_returns_401(client: TestClient) -> None:
    response = client.get("/api/anywhere", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["error"] == "invalid_token"


def test_auth_jwt_without_sub_returns_401(client: TestClient) -> None:
    token = jwt.encode({"foo": "bar"}, "x", algorithm="HS256")
    response = client.get("/api/anywhere", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"] == "missing_sub_claim"


def test_auth_jwt_with_sub_passes_dev_mode(client: TestClient) -> None:
    """Dev mode: signature skipped, sub claim varsa Auth geçer (route 404)."""
    token = jwt.encode({"sub": "user-123"}, "x", algorithm="HS256")
    response = client.get("/api/anywhere", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_auth_production_without_keys_refuses_boot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-1 / P01-T01 (güçlendirildi): production + JWKS yok + JWT_SECRET yok →
    create_app() AYAĞA KALKMAZ (ProductionConfigError, fail-fast). Forge JWT bir
    yana, sistem yanlış-yapılandırmayla boot bile etmez (per-request 500'den güçlü)."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SUPABASE_JWKS_URL", "")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
    monkeypatch.setenv("WAITLIST_BYPASS", "false")
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://example.invalid")
    from api.config import get_settings
    from api.config_validation import ProductionConfigError
    from api.main import create_app

    get_settings.cache_clear()
    with pytest.raises(ProductionConfigError, match="auth provider"):
        create_app()
    get_settings.cache_clear()


def test_auth_misconfigured_per_request_500_defense_in_depth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B-3 lock-in ikinci savunma katmanı: boot validation bypass edilse bile
    (örn env boot sonrası bozulursa) AuthMiddleware production'da anahtar yokken
    forge JWT'ye 500 auth_misconfigured döner — 200 ASLA değil."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SUPABASE_JWKS_URL", "")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://example.invalid")
    # boot validation'ı noop yap → per-request auth katmanını izole test et
    monkeypatch.setattr("api.config_validation.validate_runtime_config", lambda s: [])
    from api.config import get_settings
    from api.main import create_app

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        token = jwt.encode({"sub": "user-forge"}, "x", algorithm="HS256")
        resp = c.get("/api/anywhere", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 500
    assert resp.json()["error"] == "auth_misconfigured"
    get_settings.cache_clear()


def test_auth_demo_bypass_disabled_by_default_jwks_still_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DEMO_AUTH_BYPASS default false — JWKS set olduğunda hâlâ gerçek doğrulama
    ister, imzasız forge JWT reddedilir (401)."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://example.invalid/.well-known/jwks.json")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://example.invalid")
    monkeypatch.setattr("api.config_validation.validate_runtime_config", lambda s: [])
    from api.config import get_settings
    from api.main import create_app

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        token = jwt.encode({"sub": "user-forge"}, "x", algorithm="HS256")
        resp = c.get("/api/anywhere", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    get_settings.cache_clear()


def test_auth_demo_bypass_enabled_accepts_forged_token_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2026-08-27 (Kenan onayı, demo/beta faz): DEMO_AUTH_BYPASS=true iken,
    SUPABASE_JWKS_URL set olsa bile (gerçek prod senaryosu — web/src/lib/auth.ts
    kid'siz imzasız dev-mock JWT üretiyor) sub claim'i olan forge JWT kabul
    edilir. Diğer korumalar (WAITLIST_BYPASS vb.) bu flag'den etkilenmemeli."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://example.invalid/.well-known/jwks.json")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://example.invalid")
    monkeypatch.setenv("DEMO_AUTH_BYPASS", "true")
    monkeypatch.setattr("api.config_validation.validate_runtime_config", lambda s: [])
    from api.config import get_settings
    from api.main import create_app

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        token = jwt.encode({"sub": "user-forge"}, "x", algorithm="HS256")
        resp = c.get("/api/anywhere", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404  # auth geçti (route yok, 401 değil)
    get_settings.cache_clear()


def test_auth_demo_bypass_also_skips_waitlist_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2026-08-27 düzeltme: forge token'da email claim'i yok — WAITLIST_BYPASS=false
    (prod canon) iken allowlist boş email'i asla bulamayıp 403 not_invited
    döndürüyordu (tüm endpoint'lerde). DEMO_AUTH_BYPASS=true iken allowlist
    kontrolü de atlanmalı — is_email_allowed/get_supabase_admin hiç çağrılmamalı."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://example.invalid/.well-known/jwks.json")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://example.invalid")
    monkeypatch.setenv("DEMO_AUTH_BYPASS", "true")
    monkeypatch.setenv("WAITLIST_BYPASS", "false")
    monkeypatch.setattr("api.config_validation.validate_runtime_config", lambda s: [])
    from api.config import get_settings
    from api.main import create_app

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        token = jwt.encode({"sub": "user-forge"}, "x", algorithm="HS256")  # email claim'i yok
        resp = c.get("/api/anywhere", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404  # auth + allowlist geçti (403 not_invited değil)
    get_settings.cache_clear()


# ---------- RateLimitMiddleware ----------


def test_rate_limit_under_threshold_allowed(client: TestClient) -> None:
    """60'tan az req → asla 429 olmaz."""
    token = jwt.encode({"sub": "user-rate-low"}, "x", algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(10):
        response = client.get("/api/anywhere", headers=headers)
        assert response.status_code != 429


def test_rate_limit_threshold_exceeded_returns_429(client: TestClient) -> None:
    """60 req aynı user_id sonrası → 429 + Retry-After header."""
    token = jwt.encode({"sub": "user-rate-high"}, "x", algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(60):
        client.get("/api/anywhere", headers=headers)
    response = client.get("/api/anywhere", headers=headers)
    assert response.status_code == 429
    body = response.json()
    assert body["error"] == "rate_limit_exceeded"
    assert "retry_after" in body
    assert "Retry-After" in response.headers


def test_rate_limit_per_user_isolated(client: TestClient) -> None:
    """Farklı user_id'ler ayrı window — biri tükense diğer etkilenmez."""
    token_a = jwt.encode({"sub": "user-A"}, "x", algorithm="HS256")
    token_b = jwt.encode({"sub": "user-B"}, "x", algorithm="HS256")
    for _ in range(60):
        client.get("/api/anywhere", headers={"Authorization": f"Bearer {token_a}"})
    response_b = client.get("/api/anywhere", headers={"Authorization": f"Bearer {token_b}"})
    assert response_b.status_code == 404  # Auth geçti, RateLimit user-B fresh


# ---------- Sentry PII scrub ----------


def test_scrub_email() -> None:
    assert (
        scrub_pii("contact dr.foo@university.edu.tr please")
        == "contact [REDACTED_EMAIL] please"
    )


def test_scrub_orcid() -> None:
    assert (
        scrub_pii("ORCID 0000-0002-1825-0097 belongs to X")
        == "ORCID [REDACTED_ORCID] belongs to X"
    )


def test_scrub_jwt() -> None:
    fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4eHgifQ.signaturehere"
    out = scrub_pii(f"token={fake_jwt} ok")
    assert "[REDACTED_JWT]" in out
    assert fake_jwt not in out


def test_scrub_supabase_key() -> None:
    key = "sb_secret_FAKE_TEST_DO_NOT_USE_a1b2c3d4e5"
    out = scrub_pii(f"key={key}")
    assert "[REDACTED_SUPABASE_KEY]" in out
    assert key not in out


def test_scrub_no_pii_unchanged() -> None:
    assert scrub_pii("just a regular message") == "just a regular message"


def test_before_send_strips_headers_outside_allowlist() -> None:
    event = {
        "request": {
            "url": "https://api.example.com/v1/users?email=dr.foo@x.com",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4eHgifQXXX.signaturehere",
                "Cookie": "session=abc",
                "Content-Type": "application/json",
                "User-Agent": "pytest",
            },
            "cookies": {"session": "abc"},
            "data": "user dr.foo@x.com submitted",
        },
        "message": "ok",
    }
    out = _before_send(event, {})  # type: ignore[arg-type]
    assert out is not None
    req = out["request"]
    assert req["headers"]["Authorization"] == "[REDACTED]"
    assert req["headers"]["Cookie"] == "[REDACTED]"
    assert req["headers"]["Content-Type"] == "application/json"
    assert req["headers"]["User-Agent"] == "pytest"
    assert req["cookies"] == "[REDACTED]"
    assert "[REDACTED_EMAIL]" in req["url"]
    assert "[REDACTED_EMAIL]" in req["data"]


def test_before_breadcrumb_scrubs_url_and_data() -> None:
    crumb = {
        "category": "httplib",
        "message": "GET https://api.example.com/?token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4eHgifQXXX.signaturehere",
        "data": {
            "url": "https://api.example.com/users/dr.foo@x.com",
            "method": "GET",
        },
    }
    out = _before_breadcrumb(crumb, {})  # type: ignore[arg-type]
    assert out is not None
    assert "[REDACTED_JWT]" in out["message"]
    assert "[REDACTED_EMAIL]" in out["data"]["url"]
    assert out["data"]["method"] == "GET"
