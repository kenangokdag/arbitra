"""F8 LLM context + response models (DM-LLM-4 + DM-LLM-7).

ProjectContext = cross-step coherence için Supabase'den çekilen state.
PageContext = "Danışmana Sor" butonunun gönderdiği sayfa-spesifik state.
LLMResponse = LLMService dönüş tipi; structured_output_schema verilirse parsed_output set.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    user_id: str
    topic: str | None = Field(default=None, max_length=500)
    hypothesis: str | None = Field(default=None, max_length=1000)
    selected_method: str | None = Field(default=None, max_length=200)
    corpus_filter: dict[str, Any] | None = None
    last_decisions: list[str] = Field(default_factory=list, max_length=5)


class PageContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: str = Field(min_length=1, max_length=80)
    page_state: dict[str, Any] | None = None


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    parsed_output: BaseModel | None = None
    model_used: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
