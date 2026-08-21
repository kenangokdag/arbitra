"""F9 /api/project Pydantic schemas.

Plan: docs/plans/F9_kesif_workbench.md §6 (DDL kanonik) + §7 (endpoint sözleşmesi)
- ProjectCreate: name (1-200, CHECK 0015:22 ile aynı)
- ProjectRead: full row (POST 201 + GET /{id} 200)
- ProjectListItem: GET / 200 hafif satır
- HK-1: extra=forbid; HK-6: no Any.

current_stage CHECK '^[1-5]\\.[1-6]$' DB CHECK constraint'inde tutulur (0015:26),
model layer'da regex ZORLAMAZ — DB sözleşme tek doğruluk kaynağı.

F11 Phase A:
- ProjectFromQRequest / ProjectFromQResponse: Q (vitrin) → Project köprüsü.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProjectStatus = Literal["active", "archived"]
SeedSource = Literal["q", "onboarding", "manual"]
SeedLang = Literal["tr", "en", "id", "other"]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("name boş olamaz")
        return s


class ProjectRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    status: ProjectStatus
    current_stage: str
    inherited_field_ids: list[str] = Field(default_factory=list)
    inherited_subfield_ids: list[str] = Field(default_factory=list)
    inherited_research_focus: str | None = None
    # F11 Phase A: Q (vitrin) → Project miras snapshot
    seed_query: str | None = None
    seed_lang: SeedLang | None = None
    seed_source: SeedSource = "manual"
    seed_paper_count: int = 0
    created_at: datetime
    updated_at: datetime
    # P094-P095: gerçek anchor JOIN (project_anchor + project_cluster preview).
    # Şimdilik POST 201 + GET /{id} 200 placeholder olarak None döner.
    anchor: dict[str, object] | None = None
    # V1-S16-P001: son adviser turn'unun parsed_understanding'i (2.1 confirm sayfası).
    # Stage A henüz başlamamışsa None döner. dict[str,object] çünkü ParsedUnderstanding
    # research_area.py'de — circular import önlemek için ham jsonb taşıyoruz.
    parsed_understanding: dict[str, object] | None = None


class ProjectListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    status: ProjectStatus
    current_stage: str
    updated_at: datetime


# ── F11 Phase A — Q (vitrin) → Project köprüsü ──────────────────────────────


class ProjectFromQRequest(BaseModel):
    """Q sayfasında "Projeye Dönüştür" CTA'sının gönderdiği body.

    Q evreni OpenAlex; selected_paper_ids OpenAlex W-id (text). Bizim warehouse
    papers tablosuyla FK YOK — Phase B'de cluster_expander çapaya gidince bağlanır.
    """

    model_config = ConfigDict(extra="forbid")
    q_query: str = Field(min_length=1, max_length=512)
    q_lang: SeedLang
    selected_paper_ids: list[str] = Field(min_length=1, max_length=25)

    @field_validator("q_query")
    @classmethod
    def _strip_query(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("q_query boş olamaz")
        return s

    @field_validator("selected_paper_ids")
    @classmethod
    def _unique_paper_ids(cls, v: list[str]) -> list[str]:
        # Aynı paper_id 2 kez gelmesin (PK çakışmasını HTTP 422'de yakala).
        seen: set[str] = set()
        out: list[str] = []
        for pid in v:
            s = pid.strip()
            if not s:
                raise ValueError("paper_id boş olamaz")
            if s in seen:
                raise ValueError(f"paper_id tekrar etti: {s}")
            seen.add(s)
            out.append(s)
        return out


class ProjectFromQResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    seed_query: str
    seed_paper_count: int


# ── F13 S11.0 — Proje makaleleri (hydrated metadata) ────────────────────────


class ProjectPaperItem(BaseModel):
    """Proje çapasındaki tek makale (papers tablosundan hydrate).

    `paper_id` bare W-id (OpenAlex). title NOT NULL (DB CHECK). Diğer alanlar
    OpenAlex'ten gelmeyebilir → None.
    """

    model_config = ConfigDict(extra="forbid")
    paper_id: str
    title: str
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    citations_count: int = 0


class ProjectPapersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    papers: list[ProjectPaperItem]
    hydrated_count: int = 0  # bu çağrıda yeni eklenen/güncellenen satır sayısı
