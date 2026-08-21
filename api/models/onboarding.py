"""F5 /api/onboarding Pydantic schemas.

K-008/K-013/K-015/K-017/K-019 (plan F5_S1_user_profile_bridge_tier_enum.md §7.5):
- field_ids: 1-3 alan, dim_field FK (bridge tablo user_profile_fields)
- tier: 3-değer enum (ogrenci/arastirmaci/profesyonel)
- primary_language KALDIRILDI (K-017: UI dili browser/locale, DB'de tutulmaz)
- orcid_raw opsiyonel — KVKK: route'ta SHA-256 hash → orcid_hash, raw saklanmaz
- HK-1: extra=forbid; HK-6: no Any.

K-019 ext (plan F5_S1B_dim_subfield_bridge.md §7.4 / DM-9):
- subfields: opsiyonel composite (subfield_id, field_id) listesi, max 3 (OQ-C)
- SubfieldRef.extra=forbid (composite payload zırhı, HK-1)
- 8 collision (pharmacology, archeology, ...) → composite payload parent context'i kaybetmez
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

UserTier = Literal["ogrenci", "arastirmaci", "profesyonel"]


class SubfieldRef(BaseModel):
    """Subfield seçimi — composite (subfield_id, field_id).

    Aynı isimli subfield iki farklı parent field altında bulunabilir
    (örn. Pharmacology medicine + pharmacology_toxicology). Composite payload
    parent context'i kaybetmez (plan §7.4 / DM-9).
    """

    model_config = ConfigDict(extra="forbid")
    subfield_id: str = Field(min_length=1, max_length=120)
    field_id: str = Field(min_length=1, max_length=120)


class OnboardingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=120)
    tier: UserTier
    field_ids: list[str] = Field(min_length=1, max_length=3)
    subfields: list[SubfieldRef] = Field(default_factory=list, max_length=3)
    research_focus: str = Field(min_length=2, max_length=500)

    affiliation: str | None = Field(default=None, max_length=200)
    orcid_raw: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$",
        repr=False,
    )

    @field_validator("field_ids")
    @classmethod
    def _unique_field_ids(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("field_ids must be unique")
        return v

    @field_validator("subfields")
    @classmethod
    def _unique_subfields(cls, v: list[SubfieldRef]) -> list[SubfieldRef]:
        keys = [(s.subfield_id, s.field_id) for s in v]
        if len(set(keys)) != len(keys):
            raise ValueError("subfields must be unique by (subfield_id, field_id)")
        return v


class OnboardingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    tier: UserTier
    field_ids: list[str]
    subfields: list[SubfieldRef]
    profile_complete: bool
