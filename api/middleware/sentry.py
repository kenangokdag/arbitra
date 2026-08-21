"""Sentry init + KVKK PII scrub.

P001: init helper (no-op if DSN empty) + scrub patterns (e-mail/ORCID/JWT/Supabase keys/API keys).
N-16: breadcrumb hook + event.request (headers/body/cookies) scrubbing.
"""

import re
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.types import Breadcrumb, BreadcrumbHint, Event, Hint

from api.config import Settings

# Header allow-list approach: drop anything not in this set rather than
# trying to enumerate sensitive header names. Defense-in-depth on top of regex.
_HEADER_ALLOW: frozenset[str] = frozenset(
    {"content-type", "content-length", "user-agent", "accept", "accept-encoding", "host"}
)

_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b"), "[REDACTED_ORCID]"),
    (
        re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
        "[REDACTED_JWT]",
    ),
    (re.compile(r"sb_(publishable|secret)_[A-Za-z0-9_-]{20,}"), "[REDACTED_SUPABASE_KEY]"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "[REDACTED_API_KEY]"),
]


def scrub_pii(value: str) -> str:
    """Apply KVKK PII regex masking."""
    for pattern, replacement in _PII_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def _scrub_value(v: Any) -> Any:
    """Recursive scrub for str / list / dict; non-str passed through."""
    if isinstance(v, str):
        return scrub_pii(v)
    if isinstance(v, list):
        return [_scrub_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _scrub_value(val) for k, val in v.items()}
    return v


def _scrub_request(request: dict[str, Any]) -> dict[str, Any]:
    """Strip non-allowlisted headers and run PII regex on URL/body/cookies."""
    headers = request.get("headers")
    if isinstance(headers, dict):
        request["headers"] = {
            k: ("[REDACTED]" if k.lower() not in _HEADER_ALLOW else v) for k, v in headers.items()
        }
    if "cookies" in request:
        request["cookies"] = "[REDACTED]"
    for key in ("url", "query_string", "data"):
        if key in request:
            request[key] = _scrub_value(request[key])
    return request


def _before_send(event: Event, _hint: Hint) -> Event | None:
    """Sentry before_send hook: scrub PII from event payload + request."""
    msg = event.get("message")
    if isinstance(msg, str):
        event["message"] = scrub_pii(msg)
    exc = event.get("exception")
    if isinstance(exc, dict):
        for value in exc.get("values", []):
            v: Any = value.get("value")
            if isinstance(v, str):
                value["value"] = scrub_pii(v)
    req = event.get("request")
    if isinstance(req, dict):
        event["request"] = _scrub_request(req)
    return event


def _before_breadcrumb(crumb: Breadcrumb, _hint: BreadcrumbHint) -> Breadcrumb | None:
    """Scrub PII from breadcrumb URL/message/data (e.g. httplib URLs with tokens)."""
    msg = crumb.get("message")
    if isinstance(msg, str):
        crumb["message"] = scrub_pii(msg)
    data = crumb.get("data")
    if isinstance(data, dict):
        crumb["data"] = {k: _scrub_value(v) for k, v in data.items()}
    return crumb


def init_sentry(settings: Settings) -> None:
    """Initialize Sentry with KVKK scrub. No-op if SENTRY_DSN empty."""
    if not settings.SENTRY_DSN:
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[FastApiIntegration(), StarletteIntegration()],
        before_send=_before_send,
        before_breadcrumb=_before_breadcrumb,
        send_default_pii=False,
    )
