"""F13-S11 4.2/4.3/4.4/4.5 Atölye Analitik — Pydantic schemas.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTFs:
  - 4.2 Boşluk Profili    → /api/workshop/gap
  - 4.3 Özgünlük          → /api/workshop/originality
  - 4.4 Çalışma Karşılaştırma → /api/workshop/compare
  - 4.5 Akademik Etki Eğrisi  → /api/workshop/impact-curve

4 endpoint tek umbrella — modeller aynı domaine ait (atölye analitik) + import
yükü düşük.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── 4.3 Özgünlük ───────────────────────────────────────────────────────────

OriginalityType = Literal["disruption", "sleeping_beauty"]


class OriginalityPaper(BaseModel):
    """Tek paper + skor metadata. Tip-bazlı kolonlar Optional."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str | None
    year: int | None
    venue: str | None
    cd_5: float | None = None
    n_a: int | None = None
    n_i: int | None = None
    n_j: int | None = None
    total_window_papers: int | None = None
    b: float | None = None
    t_m: int | None = None
    c_max: int | None = None
    total_cites: int | None = None


class OriginalityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: OriginalityType
    papers: list[OriginalityPaper]
    threshold_used: float
    threshold_source: str
    pool_size: int


# ── 4.2 Gap Profili ────────────────────────────────────────────────────────


class GapCellMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matrix_id: str
    axis_x: str
    axis_y: str
    gap_value: float
    depth: int | None
    depth_norm: float
    neighbor: float
    e_value: float
    feasibility: float
    publishability: float
    matrix_confidence_calibrated: float | None = None


class RadarPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str
    cell_value: float
    corpus_value: float


class SparklinePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: int
    paper_count: int


class NeighborCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    axis_x: str
    axis_y: str
    gap_value: float
    depth_norm: float


class JournalSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    venue: str
    paper_count: int


class GapTopPaper(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str | None
    year: int | None
    venue: str | None
    q_weak: float | None


class GapStoryLLMOutput(BaseModel):
    """4.2 LLM hikaye (Flash structured output)."""

    model_config = ConfigDict(extra="forbid")

    story: str = Field(..., min_length=10)


class GapProfileWorkshopResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell_meta: GapCellMeta
    radar_7d: list[RadarPoint]
    sparkline: list[SparklinePoint]
    neighbors: list[NeighborCell]
    journals: list[JournalSuggestion]
    top_papers: list[GapTopPaper]
    story: str | None = None


# ── 4.4 Karşılaştırma ──────────────────────────────────────────────────────


class GapCellRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matrix_id: str
    axis_x: str
    axis_y: str


class CompareWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk: float = Field(0.20, ge=0.0, le=1.0)
    disruption: float = Field(0.20, ge=0.0, le=1.0)
    virgin: float = Field(0.20, ge=0.0, le=1.0)
    sleeping_beauty: float = Field(0.20, ge=0.0, le=1.0)
    publishability: float = Field(0.20, ge=0.0, le=1.0)


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    gap_cells: list[GapCellRef] = Field(..., min_length=2, max_length=5)
    weights: CompareWeights = Field(
        default_factory=lambda: CompareWeights(
            risk=0.20,
            disruption=0.20,
            virgin=0.20,
            sleeping_beauty=0.20,
            publishability=0.20,
        )
    )


class GapAxisScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk: float
    disruption: float
    virgin: float
    sleeping_beauty: float
    publishability: float


class CompareGapRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell: GapCellRef
    axes: GapAxisScores
    weighted_score: float
    top_papers: list[GapTopPaper]


class CompareRecommendationLLMOutput(BaseModel):
    """4.4 LLM 'Hangisini önereyim?' özet."""

    model_config = ConfigDict(extra="forbid")

    recommendation_text: str = Field(..., min_length=10)


class CompareResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gaps: list[CompareGapRow]
    weights: CompareWeights
    recommendation_text: str | None = None


# ── 4.5 Impact Curve ───────────────────────────────────────────────────────

ImpactDimension = Literal["topic", "method", "keyword"]
MomentumColor = Literal["green", "yellow", "red", "unknown"]


class ImpactPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: int
    value: float


class StarPoint(BaseModel):
    """★ Yıkıcı paper noktası."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str | None
    year: int
    cd_5: float


class BeautyPoint(BaseModel):
    """♦ Sleeping beauty (uyanma çifti)."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str | None
    publication_year: int
    awakening_year: int
    b: float


class ImpactCurveLLMOutput(BaseModel):
    """4.5 LLM 1-cümle kombine yorum."""

    model_config = ConfigDict(extra="forbid")

    comment: str = Field(..., min_length=10, max_length=600)


class ImpactCurveResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: ImpactDimension
    value: str
    academic_series: list[ImpactPoint]
    trends_series: list[ImpactPoint]
    trends_available: bool
    stars: list[StarPoint]
    beauties: list[BeautyPoint]
    academic_slope_pct: float | None
    trends_slope: float | None
    momentum_color: MomentumColor
    llm_comment: str | None = None


__all__ = [
    "BeautyPoint",
    "CompareGapRow",
    "CompareRecommendationLLMOutput",
    "CompareRequest",
    "CompareResponse",
    "CompareWeights",
    "GapAxisScores",
    "GapCellMeta",
    "GapCellRef",
    "GapProfileWorkshopResponse",
    "GapStoryLLMOutput",
    "GapTopPaper",
    "ImpactCurveLLMOutput",
    "ImpactCurveResponse",
    "ImpactDimension",
    "ImpactPoint",
    "JournalSuggestion",
    "MomentumColor",
    "NeighborCell",
    "OriginalityPaper",
    "OriginalityResponse",
    "OriginalityType",
    "RadarPoint",
    "SparklinePoint",
    "StarPoint",
]
