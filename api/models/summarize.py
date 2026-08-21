"""F3c /api/summarize Pydantic schemas — skeleton (B-018).

HK-1: extra=forbid; HK-2: TODO marker P022 faithfulness_gate level=SUMMARY
(MiniCheck NLI ≥0.7 + ALCE recall ≥0.8 — Sercan handoff KD-14).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SummaryMode = Literal["abstract", "tldr", "deep"]
LanguageCode = Literal["tr", "en", "id"]


class SummarizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str = Field(min_length=1, max_length=64)
    mode: SummaryMode = "tldr"
    language: LanguageCode = "tr"


class SummarizeAccepted(BaseModel):
    """202 Accepted — Celery task_id; client poll /api/summarize/{task_id}."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    status: Literal["pending", "running", "complete", "failed"] = "pending"


class SummaryDoc(BaseModel):
    """Final summary doc; faithfulness_gate level=SUMMARY ile validate edilir."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    mode: SummaryMode
    language: LanguageCode
    text: str = Field(min_length=1)
    citations: list[str] = Field(default_factory=list)
    faithfulness_meta: dict[str, float] = Field(default_factory=dict)
