"""F5-PRE /api/dim/* Pydantic schemas (PROMPT #4-PRE).

Plan: PROMPT #4-PRE brief §1.A (DimField + DimSubfield response shapes).
Brain: K-007 (taxonomy), K-010/K-011 (DB EN-only — name_tr UI'da statik dictionary, K-012),
       K-019 (level-1 ~26 satır), K-019 ext (level-2 ~252 satır).
DM_RULES: HK-1 (extra=forbid), HK-6 (no Any), R4 (zero-hallucination).

Migration kolonları (0011_create_dim_field, 0013_create_dim_subfield):
- dim_field:    field_id PK · name_en UNIQUE · slug UNIQUE · paper_count_total int
- dim_subfield: (subfield_id, field_id) composite PK · name_en · slug · paper_count_total
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DimField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_id: str = Field(min_length=1, max_length=120)
    name_en: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=200)
    paper_count_total: int = Field(default=0, ge=0)


class DimFieldListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[DimField]


class DimSubfield(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subfield_id: str = Field(min_length=1, max_length=120)
    field_id: str = Field(min_length=1, max_length=120)
    name_en: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=200)
    paper_count_total: int = Field(default=0, ge=0)


class DimSubfieldListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subfields: list[DimSubfield]
