"""F9 /research-area Pydantic schemas (Stage A sohbet + Stage B çapa adayları).

Plan: docs/plans/F9_kesif_workbench.md §7 (endpoint sözleşmesi) + §8 (LLM)

Stage A (P094):
- MessageRequest / ParsedUnderstanding / MessageResponse — Kütüphaneci 2-tur

Stage B (P095):
- HydePacket — Gemini Flash structured output (HyDE pseudo-paragraph + keyword)
- AnchorCandidate — top-3 çapa adayı (Pinecone+tsvector RRF + reranker)
- AnchorCandidatesResponse — endpoint 200 dönüşü

HK-1: extra=forbid; HK-6: no Any.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Confidence = Literal["high", "med", "low"]
DecisionBand = Literal["high", "med", "low"]


class MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=2000)
    attempt_no: int = Field(default=1, ge=1, le=10)

    @field_validator("content")
    @classmethod
    def _strip_content(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("content boş olamaz")
        return s


class ParsedUnderstanding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    focuses: list[str] = Field(min_length=3, max_length=3)
    field: str = Field(min_length=1, max_length=200)
    subfield: str | None = Field(default=None, max_length=200)
    interdisc: bool = False
    confidence: Confidence = "med"
    adviser_text: str = Field(min_length=1, max_length=2000)
    finished: bool = False

    @field_validator("focuses")
    @classmethod
    def _validate_focuses(cls, v: list[str]) -> list[str]:
        cleaned = [f.strip() for f in v]
        if any(not f for f in cleaned):
            raise ValueError("focuses içinde boş satır olamaz")
        return cleaned


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turn_no: int = Field(ge=1, le=2)
    parsed_understanding: ParsedUnderstanding
    adviser_text: str
    finished: bool


class HydePacket(BaseModel):
    """Stage B HyDE çıktısı — Pinecone vec + tsvector havuzlarına input.

    Gemini Flash Tur 2 sonu parsed_understanding'i alıp:
      - pseudo_paragraph: 80-120 token akademik özet (Pinecone embedding'i için)
      - keywords: 5-8 madde TR/EN/ID karışık (Supabase tsvector lexical pool için)
    """

    model_config = ConfigDict(extra="forbid")
    pseudo_paragraph: str = Field(min_length=40, max_length=2000)
    keywords: list[str] = Field(min_length=3, max_length=12)

    @field_validator("keywords")
    @classmethod
    def _clean_keywords(cls, v: list[str]) -> list[str]:
        cleaned = [k.strip() for k in v if k and k.strip()]
        if not cleaned:
            raise ValueError("keywords boş olamaz")
        return cleaned


class AnchorCandidate(BaseModel):
    """Stage B çapa adaylarından biri — kart UI'da görünen tüm alanlar.

    V1-S17 P005: signals_13 jsonb (curator._signals_13 paterni) Q/M/Δ5/R chip
    grupları için zorunlu; min_length yok (placeholder doldurma).
    """

    model_config = ConfigDict(extra="forbid")
    paper_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=600)
    abstract_preview: str = Field(default="", max_length=1200)
    field: str | None = Field(default=None, max_length=200)
    language: str | None = Field(default=None, max_length=8)
    year: int | None = Field(default=None, ge=1500, le=2100)
    decision_band: DecisionBand = "med"
    q_weak: float = Field(ge=0.0, le=1.0)
    signals_13: dict[str, float] = Field(default_factory=dict)


class AnchorCandidatesResponse(BaseModel):
    """POST /research-area/anchor-candidates 200 dönüşü.

    V1-S17 P005 (KD-V1-S17-04): max_length 3 → 5 (Omer 1.a kararı).
    """

    model_config = ConfigDict(extra="forbid")
    candidates: list[AnchorCandidate] = Field(min_length=1, max_length=5)
    packet_p: str = Field(min_length=1)
    packet_s: list[str] = Field(min_length=1, max_length=12)


class ResetRequest(BaseModel):
    """F13-S12 — POST /research-area/reset payload (uyumsuzluk hafızası)."""

    model_config = ConfigDict(extra="forbid")
    reject_reason: str = Field(min_length=1, max_length=500)

    @field_validator("reject_reason")
    @classmethod
    def _strip_reason(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("reject_reason boş olamaz")
        return s


class ResetResponse(BaseModel):
    """F13-S12 — POST /research-area/reset 200 dönüşü.

    attempt_no: yeni Tur 1 attempt numarası (1-10, CHECK constraint).
    rejected_count: project_anchor.rejected_anchors uzunluğu (kümülatif).
    """

    model_config = ConfigDict(extra="forbid")
    attempt_no: int = Field(ge=1, le=10)
    rejected_count: int = Field(ge=0)


ClusterStatus = Literal["pending", "expanding", "ready", "failed"]


class LockRequest(BaseModel):
    """V1-S15.pre — POST /research-area/anchor/lock payload."""

    model_config = ConfigDict(extra="forbid")
    paper_id: str = Field(min_length=1, max_length=64)

    @field_validator("paper_id")
    @classmethod
    def _strip_paper_id(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("paper_id boş olamaz")
        return s


class LockResponse(BaseModel):
    """V1-S15.pre — POST /research-area/anchor/lock 202 dönüşü.

    anchor_paper_id: kilitlenen makale (project_anchor.anchor_paper_id).
    locked_at: ISO-8601 timestamptz (project_anchor.locked_at).
    cluster_status: V1-S17 P002 sonrası — BackgroundTask tetiklendi → 'expanding'
    (yeni kilit) veya idempotent re-lock'ta önceki terminal durum ('ready'/'failed').
    """

    model_config = ConfigDict(extra="forbid")
    anchor_paper_id: str = Field(min_length=1, max_length=64)
    locked_at: str = Field(min_length=1)
    cluster_status: ClusterStatus = "pending"


class ClusterStatusResponse(BaseModel):
    """V1-S17 P002 — GET /api/project/{id}/cluster/status poll endpoint.

    cluster_status: state machine durumu (project_anchor.cluster_status).
    cluster_size: project_cluster içindeki paper sayısı (0..50).
    started_at / completed_at: 0037 timestamps; pending'de ikisi de null.
    cluster_error: 'failed' iken {reason, at}; aksi null.
    """

    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1)
    anchor_paper_id: str | None = Field(default=None, max_length=64)
    cluster_status: ClusterStatus
    cluster_size: int = Field(ge=0, le=50)
    started_at: str | None = None
    completed_at: str | None = None
    cluster_error: dict[str, str] | None = None


class ClusterExpandAcceptedResponse(BaseModel):
    """V1-S17 P002 — POST /api/project/{id}/cluster/expand 202 dönüşü."""

    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1)
    anchor_paper_id: str = Field(min_length=1, max_length=64)
    cluster_status: ClusterStatus = "expanding"
    accepted_at: str = Field(min_length=1)
