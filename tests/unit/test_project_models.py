"""F9 P093 — api/models/project.py Pydantic kontrat testleri.

Plan: docs/plans/F9_kesif_workbench.md §7 (endpoint sözleşmesi) + §12 (test stratejisi)
- HK-1 (extra=forbid): bilinmeyen alan reddedilir
- name 1-200 char (DB CHECK 0015:22 ile aynı sınırlar)
- current_stage model layer'da regex zorlamaz (DB CHECK iş yapar)
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from api.models.project import (
    ProjectCreate,
    ProjectFromQRequest,
    ProjectFromQResponse,
    ProjectListItem,
    ProjectRead,
)

pytestmark = pytest.mark.unit


# ── 1. ProjectCreate name boş → ValidationError ──────────────────────────────


@pytest.mark.parametrize("bad", ["", "   "])
def test_project_create_empty_or_whitespace_name_raises(bad: str) -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(name=bad)


# ── 2. ProjectCreate name 201 char → ValidationError ─────────────────────────


def test_project_create_name_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(name="x" * 201)


# ── 3. ProjectCreate extra alan (HK-1) → ValidationError ─────────────────────


def test_project_create_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate.model_validate({"name": "ok", "foo": 1})


# ── 4. ProjectRead current_stage model layer'da regex zorlamaz ───────────────


def test_project_read_current_stage_no_regex_at_model_layer() -> None:
    """Plan §7: regex CHECK DB'de tutulur, model layer geçirgen."""
    now = datetime.now(UTC)
    payload = {
        "id": "p-1",
        "name": "X",
        "status": "active",
        "current_stage": "1.1",
        "created_at": now,
        "updated_at": now,
    }
    valid = ProjectRead(**payload)
    assert valid.current_stage == "1.1"

    # '9.9' DB CHECK ihlal eder ama model layer kabul eder (regex yok)
    bypass = ProjectRead(**{**payload, "current_stage": "9.9"})
    assert bypass.current_stage == "9.9"


# ── 5. ProjectListItem minimal happy ─────────────────────────────────────────


def test_project_list_item_minimal_payload() -> None:
    now = datetime.now(UTC)
    item = ProjectListItem(
        id="p-1",
        name="A",
        status="active",
        current_stage="1.1",
        updated_at=now,
    )
    assert item.id == "p-1"
    assert item.status == "active"
    # extra=forbid — bilinmeyen alan reddedilir
    with pytest.raises(ValidationError):
        ProjectListItem.model_validate(
            {**item.model_dump(), "ghost": "boom"}
        )


# ── 6. F11 Phase A — ProjectFromQRequest ─────────────────────────────────────


def test_from_q_request_happy() -> None:
    req = ProjectFromQRequest(
        q_query="bahasa indonesia mcdm",
        q_lang="tr",
        selected_paper_ids=["W123", "W456"],
    )
    assert req.q_query == "bahasa indonesia mcdm"
    assert req.q_lang == "tr"
    assert req.selected_paper_ids == ["W123", "W456"]


@pytest.mark.parametrize("bad", ["", "   ", "\n\t  "])
def test_from_q_request_empty_query_raises(bad: str) -> None:
    with pytest.raises(ValidationError):
        ProjectFromQRequest(
            q_query=bad, q_lang="tr", selected_paper_ids=["W1"]
        )


def test_from_q_request_invalid_lang_raises() -> None:
    with pytest.raises(ValidationError):
        ProjectFromQRequest.model_validate(
            {"q_query": "x", "q_lang": "fr", "selected_paper_ids": ["W1"]}
        )


def test_from_q_request_empty_paper_ids_raises() -> None:
    with pytest.raises(ValidationError):
        ProjectFromQRequest(
            q_query="x", q_lang="tr", selected_paper_ids=[]
        )


def test_from_q_request_too_many_paper_ids_raises() -> None:
    with pytest.raises(ValidationError):
        ProjectFromQRequest(
            q_query="x",
            q_lang="tr",
            selected_paper_ids=[f"W{i}" for i in range(26)],
        )


def test_from_q_request_dup_paper_ids_raises() -> None:
    with pytest.raises(ValidationError):
        ProjectFromQRequest(
            q_query="x",
            q_lang="tr",
            selected_paper_ids=["W1", "W2", "W1"],
        )


def test_from_q_response_minimal() -> None:
    resp = ProjectFromQResponse(
        project_id="prj-1", seed_query="bahasa", seed_paper_count=3
    )
    assert resp.project_id == "prj-1"
    assert resp.seed_paper_count == 3
    with pytest.raises(ValidationError):
        ProjectFromQResponse.model_validate(
            {**resp.model_dump(), "extra": "x"}
        )
