"""F13-S7-P002+P003 unit tests — defense_service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S7
RTF:  Page_Design/Sayfa_Plani_v2/6.2_savunma_formati.rtf §Plan-Detayı
Migration: db/migrations/0028_defense_session.sql
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.models.defense import (
    DefenseQuestion,
    DefenseQuestionsLLMOutput,
    DefenseSessionUpsert,
    FoundPaper,
    JuryMember,
)
from api.models.llm import LLMResponse
from api.services import defense_service

pytestmark = pytest.mark.unit


def _patch_supabase_queue(
    monkeypatch: pytest.MonkeyPatch, responses: list[list[dict[str, Any]]]
) -> dict[str, int]:
    """Sıralı yanıt kuyruğu — her supabase_call_async çağrısında bir liste döner."""
    state = {"i": 0}

    async def _fake_call(
        _fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        i = state["i"]
        state["i"] += 1
        data = responses[i] if i < len(responses) else []
        return SimpleNamespace(data=data)

    monkeypatch.setattr(defense_service, "supabase_call_async", _fake_call)
    monkeypatch.setattr(
        defense_service, "get_supabase_admin", lambda: SimpleNamespace()
    )
    return state


# ── Pure helper: _aggregate_authors ─────────────────────────────────────────


def test_aggregate_authors_groups_by_name_and_ranks() -> None:
    papers = [
        {
            "paper_id": "W1",
            "authors": [
                {"name": "Smith J", "affiliation": "MIT"},
                {"name": "Doe A"},
            ],
            "citations_count": 100,
        },
        {
            "paper_id": "W2",
            "authors": [{"name": "Smith J"}],
            "citations_count": 50,
        },
        {
            "paper_id": "W3",
            "authors": [{"name": "Smith J"}],
            "citations_count": 25,
        },
        {
            "paper_id": "W4",
            "authors": [{"name": "Doe A"}],
            "citations_count": 1000,
        },
    ]
    suggestions = defense_service._aggregate_authors(papers)
    # Smith J = 3 papers; Doe A = 2 papers → Smith first
    assert suggestions[0].name == "Smith J"
    assert suggestions[0].paper_count == 3
    assert suggestions[0].total_citations == 100 + 50 + 25
    assert suggestions[0].affiliation == "MIT"
    assert suggestions[1].name == "Doe A"
    assert suggestions[1].paper_count == 2


def test_aggregate_authors_empty_returns_empty() -> None:
    assert defense_service._aggregate_authors([]) == []


def test_aggregate_authors_ignores_invalid_rows() -> None:
    papers = [
        {"paper_id": "W1", "authors": None, "citations_count": 5},
        {"paper_id": "W2", "authors": [{}, {"name": ""}], "citations_count": 5},
        {"paper_id": "W3", "authors": [{"name": "Real Author"}], "citations_count": 7},
    ]
    suggestions = defense_service._aggregate_authors(papers)
    assert len(suggestions) == 1
    assert suggestions[0].name == "Real Author"


def test_aggregate_authors_caps_top_paper_ids_at_three() -> None:
    papers = [
        {
            "paper_id": f"W{i}",
            "authors": [{"name": "Prolific"}],
            "citations_count": 1,
        }
        for i in range(6)
    ]
    suggestions = defense_service._aggregate_authors(papers)
    assert suggestions[0].paper_count == 6
    assert len(suggestions[0].top_paper_ids) == 3


# ── Pure helper: _merge_pool ────────────────────────────────────────────────


def test_merge_pool_replaces_same_index_keeps_others() -> None:
    existing = [
        {
            "jury_member_index": 0,
            "category": "method",
            "question": "Eski soru 0 metni",
            "depth": 1,
        },
        {
            "jury_member_index": 1,
            "category": "method",
            "question": "Eski soru 1 metni",
            "depth": 1,
        },
    ]
    new_qs = [
        DefenseQuestion(
            jury_member_index=1,
            category="contribution",
            question="Yeni soru metni 1",
            depth=1,
        )
    ]
    merged = defense_service._merge_pool(existing, new_qs, jury_index=1)
    # index 0 kept; index 1 replaced
    assert any(q.get("question") == "Eski soru 0 metni" for q in merged)
    assert not any(q.get("question") == "Eski soru 1 metni" for q in merged)
    assert any(q.get("question") == "Yeni soru metni 1" for q in merged)


# ── upsert_session: insert path ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_session_insert_returns_full_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    inserted_row = {
        "id": str(uuid4()),
        "project_id": str(pid),
        "session_type": "tez",
        "scheduled_date": None,
        "jury_size": 3,
        "title": "Test Tezi",
        "field": "T-EDU",
        "preferred_lang": "tr",
        "jury_members": [],
        "question_pool": [],
        "created_at": "2026-05-11T00:00:00+00:00",
        "updated_at": "2026-05-11T00:00:00+00:00",
    }
    _patch_supabase_queue(monkeypatch, [[{"id": "x"}], [inserted_row]])

    res = await defense_service.upsert_session(
        uuid4(),
        DefenseSessionUpsert(
            project_id=pid,
            session_type="tez",
            jury_size=3,
            title="Test Tezi",
            field="T-EDU",
            jury_members=[],
        ),
    )
    assert res.session_type == "tez"
    assert res.jury_size == 3
    assert res.field == "T-EDU"
    assert res.preferred_lang == "tr"


# ── upsert_session: update path (session_id provided) ───────────────────────


@pytest.mark.asyncio
async def test_upsert_session_update_path_validates_project_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    sid = uuid4()
    existing = {
        "id": str(sid),
        "project_id": str(pid),
        "session_type": "tez",
        "scheduled_date": None,
        "jury_size": 3,
        "title": "old",
        "field": "T-EDU",
        "preferred_lang": "tr",
        "jury_members": [],
        "question_pool": [],
        "created_at": "2026-05-11T00:00:00+00:00",
        "updated_at": "2026-05-11T00:00:00+00:00",
    }
    updated = {**existing, "title": "new", "jury_size": 5}
    _patch_supabase_queue(
        monkeypatch,
        [
            [{"id": "x"}],  # 1st owner check (upsert_session)
            [existing],  # _fetch_session_owned select
            [{"id": "x"}],  # 2nd owner check inside _fetch_session_owned
            [updated],  # update
        ],
    )
    res = await defense_service.upsert_session(
        uuid4(),
        DefenseSessionUpsert(
            session_id=sid,
            project_id=pid,
            session_type="tez",
            jury_size=5,
            title="new",
            field="T-EDU",
            jury_members=[],
        ),
    )
    assert res.title == "new"
    assert res.jury_size == 5


# ── upsert_session: mismatch session.project_id → PermissionError ───────────


@pytest.mark.asyncio
async def test_upsert_session_project_mismatch_raises_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid_a = uuid4()
    pid_b = uuid4()
    sid = uuid4()
    existing = {
        "id": str(sid),
        "project_id": str(pid_b),  # session belongs to a different project
        "session_type": "tez",
        "scheduled_date": None,
        "jury_size": 3,
        "title": "old",
        "field": "T-EDU",
        "preferred_lang": "tr",
        "jury_members": [],
        "question_pool": [],
        "created_at": "2026-05-11T00:00:00+00:00",
        "updated_at": "2026-05-11T00:00:00+00:00",
    }
    _patch_supabase_queue(
        monkeypatch,
        [[{"id": "x"}], [existing], [{"id": "x"}]],
    )
    with pytest.raises(PermissionError):
        await defense_service.upsert_session(
            uuid4(),
            DefenseSessionUpsert(
                session_id=sid,
                project_id=pid_a,  # mismatched
                session_type="tez",
                jury_size=3,
                title="x",
                field="T-EDU",
                jury_members=[],
            ),
        )


# ── generate_questions: full path with LLM mock ─────────────────────────────


@pytest.mark.asyncio
async def test_generate_questions_calls_llm_and_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sid = uuid4()
    pid = uuid4()
    session_row = {
        "id": str(sid),
        "project_id": str(pid),
        "session_type": "tez",
        "scheduled_date": None,
        "jury_size": 3,
        "title": "Test",
        "field": "T-EDU",
        "preferred_lang": "tr",
        "jury_members": [
            JuryMember(
                name="Prof Smith",
                field="ML",
                found_papers=[
                    FoundPaper(paper_id="W1", title="DL survey", year=2024)
                ],
            ).model_dump(mode="json")
        ],
        "question_pool": [],
        "created_at": "2026-05-11T00:00:00+00:00",
        "updated_at": "2026-05-11T00:00:00+00:00",
    }
    manuscript_rows = [
        {"section_type": "intro", "content": "Bu çalışma X'i inceler."},
        {"section_type": "methods", "content": "Yöntem olarak Y kullanıldı."},
    ]
    _patch_supabase_queue(
        monkeypatch,
        [
            [session_row],  # _fetch_session_owned select
            [{"id": "x"}],  # owner check
            manuscript_rows,  # manuscript fetch
            [],  # update question_pool
        ],
    )

    llm_questions = [
        DefenseQuestion(
            jury_member_index=0,
            category="method",
            question=f"Yöntem sorusu numara {i} detay",
            depth=1,
        )
        for i in range(8)
    ]
    parsed = DefenseQuestionsLLMOutput(questions=llm_questions)

    captured: dict[str, Any] = {}

    async def _fake_llm(prompt: str, **kwargs: Any) -> LLMResponse:
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return LLMResponse(
            text=parsed.model_dump_json(),
            parsed_output=parsed,
            model_used="gemini-pro",
            tokens_in=2000,
            tokens_out=600,
            latency_ms=4000,
        )

    monkeypatch.setattr(defense_service, "llm_call", _fake_llm)

    res = await defense_service.generate_questions(uuid4(), sid, 0)
    assert res.session_id == sid
    assert res.jury_member_index == 0
    assert len(res.questions) == 8
    assert all(q.jury_member_index == 0 for q in res.questions)
    assert res.total_pool_size == 8
    assert captured["kwargs"]["tier"] == "pro"
    assert captured["kwargs"]["mode"] == "defense_questions"
    assert "Prof Smith" in captured["prompt"]
    assert "DL survey" in captured["prompt"]


# ── generate_questions: jury_member_index out of range → IndexError ─────────


@pytest.mark.asyncio
async def test_generate_questions_index_oor_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sid = uuid4()
    pid = uuid4()
    session_row = {
        "id": str(sid),
        "project_id": str(pid),
        "session_type": "tez",
        "scheduled_date": None,
        "jury_size": 1,
        "title": "Test",
        "field": "T-EDU",
        "preferred_lang": "tr",
        "jury_members": [],
        "question_pool": [],
        "created_at": "2026-05-11T00:00:00+00:00",
        "updated_at": "2026-05-11T00:00:00+00:00",
    }
    _patch_supabase_queue(
        monkeypatch,
        [[session_row], [{"id": "x"}], []],
    )

    async def _spy_llm(*_a: Any, **_kw: Any) -> LLMResponse:
        raise AssertionError("LLM çağrılmamalıydı (index OOR)")

    monkeypatch.setattr(defense_service, "llm_call", _spy_llm)

    with pytest.raises(IndexError):
        await defense_service.generate_questions(uuid4(), sid, 0)


# ── suggest_jury: full SQL path ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_suggest_jury_returns_top_authors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    topic_rows = [{"paper_id": "W1"}, {"paper_id": "W2"}]
    paper_rows = [
        {
            "paper_id": "W1",
            "authors": [{"name": "A"}],
            "citations_count": 10,
        },
        {
            "paper_id": "W2",
            "authors": [{"name": "A"}, {"name": "B"}],
            "citations_count": 20,
        },
    ]
    _patch_supabase_queue(
        monkeypatch,
        [[{"id": "x"}], topic_rows, paper_rows],
    )

    res = await defense_service.suggest_jury(uuid4(), pid, "T-EDU")
    assert res.field == "T-EDU"
    # A: 2 papers, B: 1 paper
    assert res.suggestions[0].name == "A"
    assert res.suggestions[0].paper_count == 2
    assert res.suggestions[1].name == "B"
    assert res.suggestions[1].paper_count == 1
