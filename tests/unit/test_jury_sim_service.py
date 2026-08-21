"""F13-S10 unit tests — jury_sim_service (6.5 Jüri Simülasyonu).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S10
RTF:  Page_Design/Sayfa_Plani_v2/6.5_juri_simulasyonu.rtf §Plan-Detayı
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.models.jury_sim import (
    AnswerScoreRequest,
    ConsistencyCheckRequest,
    ConsistencyConflict,
    ConsistencyOutput,
    HydeChunk,
    HydeFanoutRequest,
    HydeHypotheticalsOutput,
    JuryDecisionBandRequest,
    JuryPersonaOutput,
    JuryQuestion,
    JuryQuestionRequest,
)
from api.models.llm import LLMResponse
from api.services import jury_sim_service

pytestmark = pytest.mark.unit


# ── helpers ─────────────────────────────────────────────────────────────────


def _patch_supabase_invoke(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        return fn()

    monkeypatch.setattr(jury_sim_service, "supabase_call_async", _fake_call)


def _fake_admin_client() -> SimpleNamespace:
    return SimpleNamespace(
        table=lambda _t: SimpleNamespace(
            update=lambda _v: SimpleNamespace(
                eq=lambda _k, _val: SimpleNamespace(
                    execute=lambda: SimpleNamespace(data=None)
                )
            ),
            select=lambda _c: SimpleNamespace(
                eq=lambda _k, _v: SimpleNamespace(
                    eq=lambda _k2, _v2: SimpleNamespace(
                        limit=lambda _n: SimpleNamespace(
                            execute=lambda: SimpleNamespace(data=[{"id": "x"}])
                        )
                    ),
                    limit=lambda _n: SimpleNamespace(
                        execute=lambda: SimpleNamespace(data=[{"id": "x"}])
                    ),
                )
            ),
        )
    )


# ── pure helpers ────────────────────────────────────────────────────────────


def test_tokenize_lowercases_words_min_3_chars() -> None:
    toks = jury_sim_service._tokenize("Bu CALISMA 200 katılımcı")
    assert "calisma" in toks
    assert "200" in toks
    assert "bu" not in toks  # <3 char


def test_clarity_score_full_answer() -> None:
    text = (
        "Bu çalışma 200 katılımcı ile yürütülmüş ve sonuçlar anlamlı "
        "olarak bulunmuştur. İstatistiksel analizler kapsamlı şekilde "
        "yapılmıştır. Yöntem geçerli olarak kabul edilmiş ayrıca alanın "
        "literatürü ile uyumlu çıkmıştır. Pearson korelasyonu hesaplanmış "
        "regresyon modelleri uygulanmış varyans analizi gerçekleşmiştir. "
        "Smith, 2021 referans olarak gösterilmiştir."
    )
    assert jury_sim_service._clarity_score(text) >= 0.9


def test_clarity_score_empty_zero() -> None:
    assert jury_sim_service._clarity_score("   ") == 0.0


def test_depth_score_from_hypotheticals_token_overlap() -> None:
    answer = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
    hyps = ["alpha beta gamma delta epsilon", "zzz yyy xxx"]
    score = jury_sim_service._depth_score_from_hypotheticals(answer, hyps)
    assert 0.4 <= score <= 0.6  # 1/2 hypotheticals matched


def test_evidence_coverage_picks_top_3() -> None:
    answer = "alpha beta gamma delta"
    top = [
        HydeChunk(paper_id="p1", chunk_idx=0, sentence="alpha beta", score=0.9),
        HydeChunk(paper_id="p2", chunk_idx=0, sentence="zzz yyy", score=0.5),
    ]
    score = jury_sim_service._evidence_coverage(answer, top)
    assert score > 0.0


def test_classify_reaction_thresholds() -> None:
    thr = {"weighted_sum_thresholds": {"satisfied_min": 0.65, "dissatisfied_max": 0.35}}
    assert jury_sim_service._classify_reaction(0.7, thr) == "satisfied"
    assert jury_sim_service._classify_reaction(0.5, thr) == "probing"
    assert jury_sim_service._classify_reaction(0.2, thr) == "dissatisfied"


def test_predict_band_buckets() -> None:
    pred, conf, _advice = jury_sim_service._predict_band(0.8, 0)
    assert pred == "accept"
    assert conf >= 0.75
    pred2, _c2, _ = jury_sim_service._predict_band(0.65, 0)
    assert pred2 == "minor"
    pred3, _c3, _ = jury_sim_service._predict_band(0.5, 0)
    assert pred3 == "major"
    pred4, _c4, _ = jury_sim_service._predict_band(0.2, 0)
    assert pred4 == "reject"


def test_predict_band_conflict_penalty_drops_band() -> None:
    # 0.8 - 0.05*5 = 0.55 → major
    pred, _conf, _ = jury_sim_service._predict_band(0.8, 5)
    assert pred == "major"


def test_trim_jury_depth_filters_invalid_depth() -> None:
    output = JuryPersonaOutput(
        questions=[
            JuryQuestion(
                persona="canli", idx=0, text="Birinci soru uzun metin", depth=1
            ),
            JuryQuestion(
                persona="canli", idx=1, text="İkinci soru uzun", depth=2, parent_idx=0
            ),
        ]
    )
    trimmed = jury_sim_service._trim_jury_depth(output)
    assert len(trimmed.questions) == 2


def test_detect_missing_concepts() -> None:
    missing = jury_sim_service._detect_missing_concepts(
        ["alpha", "beta", "gamma"], "manuscript alpha and beta"
    )
    assert missing == ["gamma"]


def test_detect_missing_concepts_none_when_no_manuscript() -> None:
    assert (
        jury_sim_service._detect_missing_concepts(["alpha"], None) == []
    )


# ── jury_question (5 persona parallel) ─────────────────────────────────────


def _build_jury_persona_output(persona_key: str) -> JuryPersonaOutput:
    return JuryPersonaOutput(
        questions=[
            JuryQuestion(
                persona=persona_key,  # type: ignore[arg-type]
                idx=0,
                text=f"{persona_key} birinci soru uzun metni vardır",
                depth=1,
            ),
            JuryQuestion(
                persona=persona_key,  # type: ignore[arg-type]
                idx=1,
                text=f"{persona_key} ikinci soru uzun metin",
                depth=2,
                parent_idx=0,
            ),
        ]
    )


@pytest.mark.asyncio
async def test_jury_question_runs_5_personas_parallel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    project_id = uuid4()

    monkeypatch.setattr(
        jury_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(project_id),
            "scan_results": {},
        },
    )
    monkeypatch.setattr(
        jury_sim_service, "get_supabase_admin", _fake_admin_client
    )

    calls: list[str] = []

    async def _fake_llm(
        prompt: str,
        *,
        tier: str,
        mode: str,
        structured_output_schema: Any = None,
        max_tokens: int = 600,
    ) -> LLMResponse:
        calls.append(mode)
        persona_key = mode.replace("jury_", "")
        parsed = _build_jury_persona_output(persona_key)
        return LLMResponse(
            text=parsed.model_dump_json(),
            model_used="gemini-flash",
            tokens_in=100,
            tokens_out=200,
            latency_ms=10,
            parsed_output=parsed,
        )

    monkeypatch.setattr(jury_sim_service, "llm_call", _fake_llm)

    req = JuryQuestionRequest(
        project_id=project_id,
        session_id=session_id,
        manuscript_text="Manuscript uzun metin ve içerik. " * 20,
        lang="tr",
    )
    resp = await jury_sim_service.jury_question(uuid4(), req)
    assert resp.session_id == session_id
    assert sorted(calls) == [
        "jury_anti_tez",
        "jury_canli",
        "jury_dis_disiplin",
        "jury_pratisyen",
        "jury_yontemci",
    ]
    # 5 personas × 2 questions = 10 total
    assert len(resp.questions) == 10
    # idx_offset reindexing: anti_tez ⊕ canli ⊕ etc — distinct idx range
    indices = sorted(q.idx for q in resp.questions)
    assert len(set(indices)) == 10


@pytest.mark.asyncio
async def test_jury_question_mismatched_project_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    monkeypatch.setattr(
        jury_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(uuid4()),
            "project_id": str(uuid4()),
            "scan_results": {},
        },
    )
    req = JuryQuestionRequest(
        project_id=uuid4(),
        session_id=uuid4(),
        manuscript_text="x" * 200,
        lang="tr",
    )
    with pytest.raises(PermissionError, match="session_project_mismatch"):
        await jury_sim_service.jury_question(uuid4(), req)


# ── hyde_fanout_rerank ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hyde_fanout_rerank_returns_graceful_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)

    monkeypatch.setattr(
        jury_sim_service, "get_supabase_admin", _fake_admin_client
    )

    async def _fake_llm(
        prompt: str,
        *,
        tier: str,
        mode: str,
        structured_output_schema: Any = None,
        max_tokens: int = 600,
    ) -> LLMResponse:
        parsed = HydeHypotheticalsOutput(
            hypotheticals=[
                "Hipotetik cevap bir uzun metin",
                "Hipotetik cevap iki uzun metin",
                "Hipotetik cevap üç uzun metin",
                "Hipotetik cevap dört uzun metin",
                "Hipotetik cevap beş uzun metin",
            ],
            key_concepts=["alpha", "beta", "gamma"],
        )
        return LLMResponse(
            text=parsed.model_dump_json(),
            model_used="gemini-flash",
            tokens_in=100,
            tokens_out=200,
            latency_ms=10,
            parsed_output=parsed,
        )

    monkeypatch.setattr(jury_sim_service, "llm_call", _fake_llm)

    req = HydeFanoutRequest(
        project_id=uuid4(),
        question_text="Yönteminizin geçerliliği nedir?",
        manuscript_text="Manuscript alpha ve beta içerir.",
        lang="tr",
    )
    resp = await jury_sim_service.hyde_fanout_rerank(uuid4(), req)
    assert len(resp.hyde_hypotheticals) == 5
    assert resp.fanout_used is False  # V1 graceful — Pinecone canlı değil
    assert resp.rerank_used is False
    assert "gamma" in resp.missing_concepts  # alpha+beta manuscript'te


@pytest.mark.asyncio
async def test_hyde_fanout_rerank_project_not_found_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    monkeypatch.setattr(
        jury_sim_service,
        "get_supabase_admin",
        lambda: SimpleNamespace(
            table=lambda _t: SimpleNamespace(
                select=lambda _c: SimpleNamespace(
                    eq=lambda _k, _v: SimpleNamespace(
                        eq=lambda _k2, _v2: SimpleNamespace(
                            limit=lambda _n: SimpleNamespace(
                                execute=lambda: SimpleNamespace(data=[])
                            )
                        )
                    )
                )
            )
        ),
    )
    req = HydeFanoutRequest(
        project_id=uuid4(),
        question_text="Yönteminizin geçerliliği nedir?",
        lang="tr",
    )
    with pytest.raises(LookupError, match="project_not_found"):
        await jury_sim_service.hyde_fanout_rerank(uuid4(), req)


# ── answer_score ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_answer_score_high_quality_satisfied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    monkeypatch.setattr(
        jury_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(uuid4()),
            "scan_results": {
                "jury_session": {
                    "questions": [
                        {"idx": 0, "text": "Soru bir", "depth": 1, "persona": "canli"}
                    ]
                }
            },
        },
    )
    monkeypatch.setattr(
        jury_sim_service, "get_supabase_admin", _fake_admin_client
    )

    req = AnswerScoreRequest(
        session_id=session_id,
        question_idx=0,
        user_answer=(
            "Yöntem alpha beta gamma delta epsilon zeta eta theta iota kappa "
            "lambda mu nu xi omikron pi rho sigma. Smith, 2021 atıfı gösterdi."
        ),
        answer_seconds=45,
        hyde_top=[
            HydeChunk(
                paper_id="p1",
                chunk_idx=0,
                sentence="alpha beta gamma delta epsilon",
                score=0.9,
            )
        ],
        hyde_hypotheticals=["alpha beta gamma delta epsilon"],
        key_concepts=["alpha", "beta"],
    )
    resp = await jury_sim_service.answer_score(uuid4(), req)
    assert resp.question_idx == 0
    assert resp.weighted_score > 0.5
    assert resp.jury_reaction in {"satisfied", "probing", "dissatisfied"}


@pytest.mark.asyncio
async def test_answer_score_missing_concepts_trigger_follow_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    monkeypatch.setattr(
        jury_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(uuid4()),
            "scan_results": {"jury_session": {"questions": []}},
        },
    )
    monkeypatch.setattr(
        jury_sim_service, "get_supabase_admin", _fake_admin_client
    )

    req = AnswerScoreRequest(
        session_id=session_id,
        question_idx=0,
        user_answer="Kısa cevap.",
        answer_seconds=10,
        hyde_top=[],
        hyde_hypotheticals=[],
        key_concepts=["alpha", "beta"],
    )
    resp = await jury_sim_service.answer_score(uuid4(), req)
    assert "alpha" in resp.missing_concepts
    # Düşük weighted_score → probing/dissatisfied
    assert resp.weighted_score < 0.5


# ── consistency_check ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_consistency_check_skips_when_no_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    monkeypatch.setattr(
        jury_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(uuid4()),
            "scan_results": {"jury_session": {"questions": []}},
        },
    )

    req = ConsistencyCheckRequest(session_id=session_id)
    resp = await jury_sim_service.consistency_check(uuid4(), req)
    assert resp.conflicts == []
    assert "yeterli" in resp.summary.lower()


@pytest.mark.asyncio
async def test_consistency_check_calls_flash_with_qa_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    monkeypatch.setattr(
        jury_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(uuid4()),
            "scan_results": {
                "jury_session": {
                    "questions": [
                        {
                            "idx": 0,
                            "text": "A nedir?",
                            "user_answer": "A pozitiftir.",
                        },
                        {
                            "idx": 5,
                            "text": "A etkisi?",
                            "user_answer": "A etkisizdir.",
                        },
                    ]
                }
            },
        },
    )
    monkeypatch.setattr(
        jury_sim_service, "get_supabase_admin", _fake_admin_client
    )

    captured: list[str] = []

    async def _fake_llm(
        prompt: str,
        *,
        tier: str,
        mode: str,
        structured_output_schema: Any = None,
        max_tokens: int = 600,
    ) -> LLMResponse:
        captured.append(prompt)
        parsed = ConsistencyOutput(
            conflicts=[
                ConsistencyConflict(
                    q_idx_a=0, q_idx_b=5, conflict_text="A pozitif vs etkisiz çelişki"
                )
            ],
            summary="Bir çelişki bulundu.",
        )
        return LLMResponse(
            text=parsed.model_dump_json(),
            model_used="gemini-flash",
            tokens_in=100,
            tokens_out=200,
            latency_ms=10,
            parsed_output=parsed,
        )

    monkeypatch.setattr(jury_sim_service, "llm_call", _fake_llm)

    req = ConsistencyCheckRequest(session_id=session_id)
    resp = await jury_sim_service.consistency_check(uuid4(), req)
    assert len(resp.conflicts) == 1
    assert resp.conflicts[0].q_idx_a == 0
    assert "[0]" in captured[0]  # qa_block formatı
    assert "[5]" in captured[0]


# ── jury_decision_band ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_jury_decision_band_high_avg_predicts_accept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    monkeypatch.setattr(
        jury_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(uuid4()),
            "scan_results": {
                "jury_session": {
                    "questions": [
                        {"idx": 0, "weighted_score": 0.85},
                        {"idx": 1, "weighted_score": 0.78},
                    ]
                }
            },
        },
    )
    monkeypatch.setattr(
        jury_sim_service, "get_supabase_admin", _fake_admin_client
    )

    req = JuryDecisionBandRequest(session_id=session_id)
    resp = await jury_sim_service.jury_decision_band(uuid4(), req)
    assert resp.prediction == "accept"
    assert resp.score_summary["answered_count"] == 2.0
    assert resp.score_summary["conflict_count"] == 0.0


@pytest.mark.asyncio
async def test_jury_decision_band_conflict_penalty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    monkeypatch.setattr(
        jury_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(uuid4()),
            "scan_results": {
                "jury_session": {
                    "questions": [
                        {"idx": 0, "weighted_score": 0.8},
                        {"idx": 1, "weighted_score": 0.8},
                    ],
                    "consistency_check": {
                        "conflicts": [
                            {"q_idx_a": 0, "q_idx_b": 1, "conflict_text": "x"},
                            {"q_idx_a": 0, "q_idx_b": 1, "conflict_text": "y"},
                            {"q_idx_a": 0, "q_idx_b": 1, "conflict_text": "z"},
                            {"q_idx_a": 0, "q_idx_b": 1, "conflict_text": "w"},
                        ]
                    },
                }
            },
        },
    )
    monkeypatch.setattr(
        jury_sim_service, "get_supabase_admin", _fake_admin_client
    )

    req = JuryDecisionBandRequest(session_id=session_id)
    resp = await jury_sim_service.jury_decision_band(uuid4(), req)
    # 0.8 - 0.05*4 = 0.6 → minor
    assert resp.prediction == "minor"
    assert resp.score_summary["conflict_count"] == 4.0
