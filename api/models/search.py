"""POST /api/search Pydantic schemas (F3a §2 + B42-045 §3 M31).

K1 (year_verified=false → year drop), K4 (rank field yasak), K5 (LVR ≥0.7 cümle-düzey).
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DecisionBand(StrEnum):
    """ESTRA Politikası v1.1 P1 — kullanıcıya sadece bant gösterilir, skor değil."""

    CANON = "canon"
    FRONTIER = "frontier"
    STRONG_EVIDENCE = "strong_evidence"
    RISK = "risk"


class GateId(StrEnum):
    """G1-G7 gate sistemi (B42-045 §5 + ESTRA Politikası v1.1)."""

    G1 = "G1"  # retraction
    G2 = "G2"  # predatory venue
    G3 = "G3"  # düşük taban
    G4 = "G4"  # eksik metadata
    G5 = "G5"  # çok yeni (age guard)
    G6 = "G6"  # MQ floor
    G7 = "G7"  # disiplin uyumu


class GateSeverity(StrEnum):
    INFO = "info"
    WARN = "warn"
    BLOCK = "block"


class LanguageHint(StrEnum):
    """B-005 dil seçimi: TR/EN/ID."""

    TR = "tr"
    EN = "en"
    ID = "id"


class GateWarning(BaseModel):
    """Tek gate ihlali — gate_id + severity + insan-okur message."""

    gate_id: GateId
    severity: GateSeverity
    message: str


class FaithfulnessMeta(BaseModel):
    """C3-C5 üçlü kalite: jsonschema=100% + minicheck≥0.7 + alce≥0.8."""

    jsonschema_pct: float = Field(..., ge=0, le=100)
    minicheck_nli: float = Field(..., ge=0, le=1)
    alce_recall: float = Field(..., ge=0, le=1)


class Citation(BaseModel):
    """K5 cümle-düzey atıf: paper_id + span + LVR distance."""

    sentence: str
    paper_id: str
    span: tuple[int, int]
    lvr_distance: float = Field(..., ge=0, le=1)


class PaperCard(BaseModel):
    """B42-045 §3 M31 — 13 sinyal + LVR atıf + KararBant + gate (K1/K9 enforce).

    K1: year_verified=false ise `year` field'ı response'tan düşer (Pydantic exclude_none kullan).
    K9: confidence<0.5 → segment "?" placeholder PMID rendering aşamasında.
    K4: `rank` field bilerek YOK (LLM rank yasağı).
    """

    model_config = ConfigDict(extra="allow")

    paper_id: str
    pmid: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    year_verified: bool = False
    doi: str | None = None
    abstract_excerpt: str | None = None
    journal: str | None = None
    n_cited: int = 0
    signals_13: dict[str, float] = Field(default_factory=dict)
    citations_lvr: list[Citation] = Field(default_factory=list)
    decision_band: DecisionBand
    gate_warnings: list[GateWarning] = Field(default_factory=list)
    is_ghost: bool = False
    # fact_paper_id_card metadata (Supabase lookup, MVP)
    language: str | None = None
    dominant_type: str | None = None
    is_suspicious: bool = False
    is_oa: bool | None = None


class SearchRequest(BaseModel):
    """POST /api/search request body (F3a §2)."""

    query: str = Field(..., min_length=3, max_length=512)
    k: int = Field(default=10, ge=1, le=50)
    language_hint: LanguageHint | None = None
    include_ghost: bool = False


class SearchResponse(BaseModel):
    """POST /api/search response (F3a §2)."""

    papers: list[PaperCard] = Field(..., max_length=50)
    faithfulness_meta: FaithfulnessMeta
    decision_band: DecisionBand
    gate_warnings: list[GateWarning] = Field(default_factory=list)
    latency_ms: int = Field(..., ge=0)
    pmid_match_score: float = Field(..., ge=0, le=1)
