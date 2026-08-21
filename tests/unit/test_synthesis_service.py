"""F13-S11-P001 unit tests — synthesis_service (atölye 3.4 literatür sentezi)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from api.services import synthesis_service

pytestmark = pytest.mark.unit


def test_jaccard_overlap_high() -> None:
    a = "Adaptive learning systems improve student outcomes."
    b = "Adaptive learning systems improve student outcomes in higher education."
    assert synthesis_service._jaccard(a, b) > 0.6


def test_jaccard_overlap_low() -> None:
    assert synthesis_service._jaccard("foo bar baz", "qux quux") == 0.0


def test_flag_for_thresholds() -> None:
    assert synthesis_service._flag_for(0.8) == "green"
    assert synthesis_service._flag_for(0.5) == "yellow"
    assert synthesis_service._flag_for(0.2) == "red"


def test_format_citation_apa_style() -> None:
    row = {
        "authors": [{"name": "Smith J"}, {"name": "Doe A"}],
        "year": 2024,
        "title": "Adaptive learning",
        "venue": "JEdu",
    }
    out = synthesis_service._format_citation(row)
    assert "Smith J" in out
    assert "(2024)" in out
    assert "JEdu" in out


def test_format_citation_no_authors() -> None:
    row = {"year": None, "title": "Anon"}
    out = synthesis_service._format_citation(row)
    assert "Anonymous" in out
    assert "n.d." in out


def test_theme_warning_dominant() -> None:
    profiles = [
        {"topic_profile": {"theme_ids": ["T1"], "theme_scores": [0.9]}},
        {"topic_profile": {"theme_ids": ["T1"], "theme_scores": [0.95]}},
    ]
    msg = synthesis_service._theme_warning(profiles, "tr")
    assert msg is not None and "T1" in msg


def test_theme_warning_diverse_returns_none() -> None:
    profiles = [
        {"topic_profile": {"theme_ids": ["T1", "T2"], "theme_scores": [0.5, 0.5]}},
        {"topic_profile": {"theme_ids": ["T2", "T3"], "theme_scores": [0.4, 0.6]}},
    ]
    assert synthesis_service._theme_warning(profiles, "tr") is None


def test_theme_warning_empty_profiles() -> None:
    assert synthesis_service._theme_warning([], "tr") is None


def test_resolve_lang_explicit_arg() -> None:
    assert synthesis_service._resolve_lang("en", {}) == "en"


def test_resolve_lang_falls_back_to_project() -> None:
    assert synthesis_service._resolve_lang(None, {"language": "id"}) == "id"


def test_resolve_lang_default_tr() -> None:
    assert synthesis_service._resolve_lang(None, {}) == "tr"


def test_build_sentences_red_flag_for_no_citations() -> None:
    from api.models.synthesis import SynthesisLLMOutput, SynthesisLLMSentence

    llm = SynthesisLLMOutput(
        sentences=[
            SynthesisLLMSentence(text="Unsupported claim.", citation_indices=[99]),
        ]
    )
    sentences, avg = synthesis_service._build_sentences(llm, {1: "W1"}, {"W1": "abs"})
    assert sentences[0].flag == "red"
    assert sentences[0].citations == []
    assert avg == 0.0


def test_build_sentences_jaccard_on_cited_abstracts() -> None:
    from api.models.synthesis import SynthesisLLMOutput, SynthesisLLMSentence

    llm = SynthesisLLMOutput(
        sentences=[
            SynthesisLLMSentence(
                text="adaptive learning improves outcomes",
                citation_indices=[1],
            ),
        ]
    )
    paper_id_by_index = {1: "W1"}
    abstracts = {"W1": "adaptive learning improves outcomes in higher education"}
    sentences, avg = synthesis_service._build_sentences(
        llm, paper_id_by_index, abstracts
    )
    assert sentences[0].flag in ("green", "yellow")
    assert "W1" in sentences[0].citations
    assert avg > 0.4


def test_compose_text_inline_tags() -> None:
    from api.models.synthesis import SynthesisSentence

    sentences = [
        SynthesisSentence(
            text="X improves Y.", citations=["W1"], faithfulness_score=0.7, flag="green"
        ),
        SynthesisSentence(
            text="Z is debated.",
            citations=["W2", "W1"],
            faithfulness_score=0.5,
            flag="yellow",
        ),
    ]
    text = synthesis_service._compose_text(sentences, {"W1": 1, "W2": 2})
    assert "[01]" in text
    assert "[02][01]" in text


@pytest.mark.asyncio
async def test_synthesize_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid4()
    user_id = uuid4()

    queue: list[Any] = [
        {"id": str(project_id), "user_id": str(user_id), "language": "tr"},
        [
            {
                "paper_id": "W1",
                "title": "Adaptive learning",
                "abstract": "adaptive learning improves student outcomes",
                "authors": [{"name": "Smith J"}],
                "year": 2024,
                "venue": "JEdu",
            },
            {
                "paper_id": "W2",
                "title": "Online platforms",
                "abstract": "online platforms support diverse learners",
                "authors": [{"name": "Doe A"}],
                "year": 2023,
                "venue": "JOLT",
            },
        ],
        [
            {
                "paper_id": "W1",
                "topic_profile": {"theme_ids": ["T1"], "theme_scores": [0.4]},
            },
            {
                "paper_id": "W2",
                "topic_profile": {"theme_ids": ["T2"], "theme_scores": [0.6]},
            },
        ],
    ]

    async def _fake_supa(_fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        del timeout
        return queue.pop(0)

    class _FakeLLMResp:
        def __init__(self) -> None:
            from api.models.synthesis import (
                SynthesisLLMOutput,
                SynthesisLLMSentence,
            )

            self.parsed_output = SynthesisLLMOutput(
                sentences=[
                    SynthesisLLMSentence(
                        text="adaptive learning improves student outcomes",
                        citation_indices=[1],
                    ),
                    SynthesisLLMSentence(
                        text="online platforms support diverse learners",
                        citation_indices=[2],
                    ),
                ]
            )

    async def _fake_llm(*_args: Any, **_kwargs: Any) -> Any:
        return _FakeLLMResp()

    monkeypatch.setattr(synthesis_service, "supabase_call_async", _fake_supa)
    monkeypatch.setattr(synthesis_service, "llm_call", _fake_llm)

    out = await synthesis_service.synthesize(
        user_id, project_id, ["W1", "W2"], "neutral", None
    )
    assert len(out.sentences) == 2
    assert len(out.references) == 2
    assert out.lang == "tr"
    assert out.mode == "neutral"
    assert out.theme_warning is None
    assert out.total_faithfulness > 0
    assert "[01]" in out.synthesis_text


@pytest.mark.asyncio
async def test_synthesize_rejects_other_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    other = uuid4()

    async def _fake_supa(fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        del timeout
        return fn()

    from types import SimpleNamespace

    class _FakeTable:
        def select(self, _cols: str) -> _FakeTable:
            return self

        def eq(self, _col: str, _val: Any) -> _FakeTable:
            return self

        def limit(self, _n: int) -> _FakeTable:
            return self

        def execute(self) -> Any:
            return SimpleNamespace(
                data=[{"id": str(project_id), "user_id": str(other), "language": "tr"}]
            )

    monkeypatch.setattr(synthesis_service, "supabase_call_async", _fake_supa)
    monkeypatch.setattr(
        synthesis_service,
        "get_supabase_admin",
        lambda: SimpleNamespace(table=lambda _n: _FakeTable()),
    )

    with pytest.raises(PermissionError):
        await synthesis_service.synthesize(
            uuid4(), project_id, ["W1"], "neutral", None
        )
