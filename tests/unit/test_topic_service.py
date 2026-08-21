"""F13-S5 unit tests — topic_service (topic-proposals + draft-skeleton).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S5
RTF:  Page_Design/Sayfa_Plani_v2/5.2_yayin_taslagi.rtf §Plan-Detayı
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.models.llm import LLMResponse
from api.models.topic import (
    DraftSectionLLMOutput,
    TopicEvidenceChain,
    TopicProposal,
    TopicProposalsLLMOutput,
    TopicProposalsRequest,
    TopicSubQuestions,
)
from api.services import topic_service

pytestmark = pytest.mark.unit


def _patch_supabase_invoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Çalıştırılan lambda'yı doğrudan invoke ederek dönüşünü iletir."""

    async def _fake_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        return fn()

    monkeypatch.setattr(topic_service, "supabase_call_async", _fake_call)
    monkeypatch.setattr(
        topic_service, "get_supabase_admin", lambda: SimpleNamespace()
    )


def _patch_quota_and_cache(
    monkeypatch: pytest.MonkeyPatch,
    *,
    count: int = 0,
    cached: dict[str, Any] | None = None,
) -> dict[str, int]:
    calls = {"inc": 0}

    async def _state(_pid: Any) -> tuple[int, int]:
        return count, max(3 - count, 0)

    async def _incr(_pid: Any) -> None:
        calls["inc"] += 1

    monkeypatch.setattr(topic_service, "_quota_state", _state)
    monkeypatch.setattr(topic_service, "_quota_increment", _incr)
    monkeypatch.setattr(topic_service, "cache_get", lambda _ns, _k: cached)
    monkeypatch.setattr(
        topic_service, "cache_set", lambda _ns, _k, _v, ttl=None: None
    )
    return calls


def _make_proposal(title: str = "Yapay zekâ ile metin sınıflandırma") -> TopicProposal:
    return TopicProposal(
        title=title,
        sub_questions=TopicSubQuestions(
            cautious="X ile Y arasında bir ilişki var mı?",
            balanced="X, Y'yi nasıl etkiler?",
            bold="X, Y'yi anlamlı şekilde değiştirir.",
        ),
        top_3_refs=["W1", "W2"],
        method_suggestion="Karma yöntem (mixed-method) önerilir.",
        evidence_chain=TopicEvidenceChain(
            gap_summary="M1 hücresinde derinlik düşük.",
            method_summary="Profilde mixed-method baskın.",
            synthesis_summary="Sentez nicel ağırlık gösterdi.",
        ),
    )


# ── propose_topics: cache hit path ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_propose_topics_returns_cached_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    user_id = uuid4()
    proposals = [_make_proposal(f"Konu {i} başlığı için uzun isim") for i in range(3)]
    cached_payload = TopicProposalsLLMOutput(proposals=proposals).model_dump(
        mode="json"
    )
    _patch_supabase_invoke(monkeypatch)
    monkeypatch.setattr(
        topic_service,
        "_check_ownership",
        lambda _p, _u: {"id": str(pid), "user_id": str(user_id), "language": "tr"},
    )
    quota_calls = _patch_quota_and_cache(monkeypatch, count=1, cached=cached_payload)

    async def _spy_llm(*_a: Any, **_kw: Any) -> LLMResponse:
        raise AssertionError("Cache hit'te LLM çağrılmamalıydı")

    monkeypatch.setattr(topic_service, "llm_call", _spy_llm)

    req = TopicProposalsRequest(
        project_id=pid,
        gap_matrix_id="M1",
        gap_axis_x="theme_42",
        gap_axis_y="metod_7",
        method_profile=["randomized_controlled_trial"],
    )
    res = await topic_service.propose_topics(user_id, req)
    assert res.generation_count == 1
    assert res.daily_quota_remaining == 2
    assert len(res.proposals) == 3
    assert quota_calls["inc"] == 0


# ── propose_topics: quota exceeded path ─────────────────────────────────────


@pytest.mark.asyncio
async def test_propose_topics_quota_exceeded_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    user_id = uuid4()
    _patch_supabase_invoke(monkeypatch)
    monkeypatch.setattr(
        topic_service,
        "_check_ownership",
        lambda _p, _u: {"id": str(pid), "user_id": str(user_id), "language": "tr"},
    )
    _patch_quota_and_cache(monkeypatch, count=3, cached=None)

    req = TopicProposalsRequest(
        project_id=pid,
        gap_matrix_id="M1",
        gap_axis_x="theme_42",
        gap_axis_y="metod_7",
    )
    with pytest.raises(PermissionError, match="daily_quota_exceeded"):
        await topic_service.propose_topics(user_id, req)


# ── propose_topics: full LLM path ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_propose_topics_calls_pro_with_candidates_in_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    user_id = uuid4()
    candidate_papers = [
        {
            "paper_id": "W1",
            "title": "Deep learning for NLP",
            "abstract": "We propose a deep learning architecture.",
            "year": 2024,
            "citations_count": 500,
            "authors": [{"name": "Smith J"}],
        }
    ]
    _patch_supabase_invoke(monkeypatch)
    monkeypatch.setattr(
        topic_service,
        "_check_ownership",
        lambda _p, _u: {"id": str(pid), "user_id": str(user_id), "language": "tr"},
    )
    monkeypatch.setattr(
        topic_service,
        "_fetch_seed_papers_meta",
        lambda _p, _l: candidate_papers,
    )
    quota_calls = _patch_quota_and_cache(monkeypatch, count=0, cached=None)

    proposals = [_make_proposal(f"Yeni konu {i} başlığı") for i in range(3)]
    parsed = TopicProposalsLLMOutput(proposals=proposals)

    captured: dict[str, Any] = {}

    async def _fake_llm(prompt: str, **kwargs: Any) -> LLMResponse:
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return LLMResponse(
            text=parsed.model_dump_json(),
            parsed_output=parsed,
            model_used="gemini-pro",
            tokens_in=1500,
            tokens_out=500,
            latency_ms=3000,
        )

    monkeypatch.setattr(topic_service, "llm_call", _fake_llm)

    req = TopicProposalsRequest(
        project_id=pid,
        gap_matrix_id="M1",
        gap_axis_x="theme_42",
        gap_axis_y="metod_7",
        method_profile=["rct"],
        synthesis_text="Sentez metni burada.",
    )
    res = await topic_service.propose_topics(user_id, req)
    assert len(res.proposals) == 3
    assert res.generation_count == 1
    assert res.daily_quota_remaining == 2
    assert captured["kwargs"]["tier"] == "pro"
    assert captured["kwargs"]["mode"] == "topic_proposals"
    assert "W1" in captured["prompt"]
    assert "Deep learning for NLP" in captured["prompt"]
    assert "Sentez metni burada." in captured["prompt"]
    assert quota_calls["inc"] == 1


# ── propose_topics: ownership fail ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_propose_topics_ownership_fail_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    _patch_supabase_invoke(monkeypatch)

    def _raise(_p: Any, _u: Any) -> dict[str, Any]:
        raise PermissionError("project_not_owned")

    monkeypatch.setattr(topic_service, "_check_ownership", _raise)

    async def _spy_llm(*_a: Any, **_kw: Any) -> LLMResponse:
        raise AssertionError("Ownership fail'de LLM çağrılmamalıydı")

    monkeypatch.setattr(topic_service, "llm_call", _spy_llm)

    req = TopicProposalsRequest(
        project_id=pid,
        gap_matrix_id="M1",
        gap_axis_x="t",
        gap_axis_y="m",
    )
    with pytest.raises(PermissionError, match="project_not_owned"):
        await topic_service.propose_topics(uuid4(), req)


# ── draft_skeleton: 4 paralel section paths ─────────────────────────────────


@pytest.mark.asyncio
async def test_draft_skeleton_runs_one_flash_per_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    user_id = uuid4()
    monkeypatch.setattr(
        topic_service,
        "_check_ownership",
        lambda _p, _u: {"id": str(pid), "user_id": str(user_id), "language": "tr"},
    )

    section_paper_map = {
        "intro": [
            {
                "paper_id": "W10",
                "title": "Intro paper",
                "year": 2020,
                "authors": [{"name": "A"}],
                "citations_count": 100,
            }
        ],
        "methods": [
            {
                "paper_id": "W20",
                "title": "Methods paper",
                "year": 2019,
                "authors": [{"name": "B"}],
                "citations_count": 50,
            }
        ],
        "findings": [
            {
                "paper_id": "W30",
                "title": "Findings paper",
                "year": 2021,
                "authors": [{"name": "C"}],
                "citations_count": 75,
            }
        ],
        "discussion": [
            {
                "paper_id": "W40",
                "title": "Discussion paper",
                "year": 2018,
                "authors": [{"name": "D"}],
                "citations_count": 250,
            }
        ],
    }
    _patch_supabase_invoke(monkeypatch)
    monkeypatch.setattr(
        topic_service,
        "_fetch_section_papers",
        lambda _p, section, _m: section_paper_map[section],
    )

    llm_calls = {"n": 0}

    async def _fake_llm(prompt: str, **kwargs: Any) -> LLMResponse:
        llm_calls["n"] += 1
        parsed = DraftSectionLLMOutput(
            draft_paragraph=(
                "Bu paragraf çalışmanın ana noktasını anlatır ve "
                "section'a uygun şekilde literatür ile bağlanır."
            ),
            why_explanation="Bu bölüm okuyucuya bağlamı verir.",
        )
        return LLMResponse(
            text=parsed.model_dump_json(),
            parsed_output=parsed,
            model_used="gemini-flash",
            tokens_in=500,
            tokens_out=120,
            latency_ms=900,
        )

    monkeypatch.setattr(topic_service, "llm_call", _fake_llm)

    topic = _make_proposal()
    res = await topic_service.draft_skeleton(
        user_id,
        pid,
        topic,
        method_metod_ids=["m1"],
        sections=["intro", "methods", "findings", "discussion"],
        lang=None,
    )
    assert len(res.sections) == 4
    assert {s.name for s in res.sections} == {
        "intro",
        "methods",
        "findings",
        "discussion",
    }
    assert llm_calls["n"] == 4
    assert res.lang == "tr"
    for sec in res.sections:
        assert len(sec.top_5_papers) == 1


# ── _resolve_lang: explicit beats project language ──────────────────────────


def test_resolve_lang_explicit_wins() -> None:
    assert (
        topic_service._resolve_lang("en", {"language": "tr"}) == "en"
    )
    assert topic_service._resolve_lang(None, {"language": "id"}) == "id"
    assert topic_service._resolve_lang(None, {"language": "ja"}) == "tr"


# ── _short_authors edge cases ───────────────────────────────────────────────


def test_short_authors_handles_missing_and_extras() -> None:
    assert topic_service._short_authors(None) == "(bilinmiyor)"
    assert topic_service._short_authors([]) == "(bilinmiyor)"
    assert (
        topic_service._short_authors(
            [{"name": "A"}, {"name": "B"}, {"name": "C"}, {"name": "D"}]
        )
        == "A, B, et al."
    )
