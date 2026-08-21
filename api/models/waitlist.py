"""V1-S4 waitlist Pydantic modelleri (Scope A — Minimal).

kaynak: docs/plans/V1_S4_waitlist_capture.md §1 (kontrat)
HK-1: extra="forbid" tüm dış-yüz modellerde.
HK-4: source StrEnum runtime validate.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class WaitlistSource(StrEnum):
    LANDING_HERO = "landing_hero"
    LANDING_PRICING = "landing_pricing"


class WaitlistRequest(BaseModel):
    """POST /api/waitlist payload — landing capture form."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    email: EmailStr = Field(max_length=254)  # RFC 5321
    name: str = Field(min_length=2, max_length=100)
    source: WaitlistSource
    # Honeypot: gerçek kullanıcı boş bırakır (CSS display:none); bot doldurur.
    # Doluysa endpoint 200 OK fake döner ama insert yapmaz (KD-V1-S4-02).
    website: str = Field(default="", max_length=200)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 2:
            raise ValueError("name must be at least 2 chars after trim")
        return stripped


class WaitlistResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool
    queued_at: str  # ISO-8601 UTC


__all__ = [
    "WaitlistRequest",
    "WaitlistResponse",
    "WaitlistSource",
]
