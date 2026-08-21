"""F13-S9 unit tests — journal_sim_service (6.4 Dergi Simülasyonu).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S9
RTF:  Page_Design/Sayfa_Plani_v2/6.4_dergi_simulasyonu.rtf §Plan-Detayı
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.models.journal_sim import (
    JournalDistribution,
    Reviewer3PersonaRequest,
    ReviewerPersonaOutput,
    ReviewerQuestion,
    StatcheckRequest,
)
from api.models.llm import LLMResponse
from api.services import journal_sim_service

pytestmark = pytest.mark.unit


# ── helpers ─────────────────────────────────────────────────────────────────


def _patch_supabase_invoke(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        return fn()

    monkeypatch.setattr(journal_sim_service, "supabase_call_async", _fake_call)


# ── pure helpers ────────────────────────────────────────────────────────────


def test_compute_p_t_test_matches_scipy() -> None:
    p = journal_sim_service._compute_p("t", {"df": "50", "stat": "2.0"})
    assert 0.04 < p < 0.06


def test_compute_p_r_correlation() -> None:
    p = journal_sim_service._compute_p("r", {"stat": "0.3", "n": "50"})
    assert 0.0 < p < 0.05


def test_classify_diff_buckets() -> None:
    tol = {"green_max": 0.005, "yellow_max": 0.01}
    assert journal_sim_service._classify_diff(0.001, tol) == "green"
    assert journal_sim_service._classify_diff(0.008, tol) == "yellow"
    assert journal_sim_service._classify_diff(0.05, tol) == "red"


def test_parse_reported_p_handles_dot_leading() -> None:
    assert journal_sim_service._parse_reported_p(".05") == 0.05
    assert journal_sim_service._parse_reported_p("0.001") == 0.001


def test_trim_chain_depth_drops_third_level_followups() -> None:
    payload = ReviewerPersonaOutput(
        questions=[
            ReviewerQuestion(text="Soru bir uzun metin", depth=1, follow_up="alt"),
            ReviewerQuestion(text="Soru iki uzun metin", depth=2, follow_up="alt2"),
        ]
    )
    trimmed = journal_sim_service._trim_chain_depth(payload)
    assert trimmed.questions[0].follow_up == "alt"
    assert trimmed.questions[1].follow_up is None


def test_predict_verdict_band_shift_on_high_red() -> None:
    dist = JournalDistribution(
        window_size=50,
        accept_pct=0.5,
        major_pct=0.2,
        minor_pct=0.2,
        reject_pct=0.1,
        source="manual",
    )
    pred, conf = journal_sim_service._predict_verdict(dist, statcheck_red=0)
    assert pred == "accept"
    assert 0.49 <= conf <= 0.51

    pred2, _ = journal_sim_service._predict_verdict(dist, statcheck_red=3)
    assert pred2 == "minor"


# ── statcheck integration ───────────────────────────────────────────────────


def test_extract_statcheck_results_flags_inconsistent_t() -> None:
    cfg = journal_sim_service._load_statcheck_config()
    text = "We found t(48) = 2.50, p = .500 in our analysis."
    results = journal_sim_service._extract_statcheck_results(text, cfg)
    assert len(results) == 1
    r = results[0]
    assert r.test_type == "t"
    assert r.reported_p == 0.5
    assert r.status == "red"


def test_extract_statcheck_results_consistent_t_is_green() -> None:
    cfg = journal_sim_service._load_statcheck_config()
    # t(50)=2.0 → p ≈ .051; report .051 → green
    text = "Sonuçlar: t(50) = 2.00, p = .051 anlamlıdır."
    results = journal_sim_service._extract_statcheck_results(text, cfg)
    assert len(results) == 1
    assert results[0].status in ("green", "yellow")


# ── reviewer 3-persona (async, LLM mocked) ──────────────────────────────────


def _build_persona_output(persona_key: str) -> ReviewerPersonaOutput:
    return ReviewerPersonaOutput(
        questions=[
            ReviewerQuestion(
                text=f"{persona_key} hakem sorusu birinci madde uzun",
                depth=1,
                follow_up=None,
                anchor="satır 12",
            ),
            ReviewerQuestion(
                text=f"{persona_key} hakem sorusu ikinci madde",
                depth=2,
                follow_up="ikinci derinlik soru",
                anchor=None,
            ),
        ]
    )


@pytest.mark.asyncio
async def test_reviewer_3persona_runs_three_parallel_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    monkeypatch.setattr(
        journal_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(project_id),
            "scan_results": {},
        },
    )
    monkeypatch.setattr(
        journal_sim_service,
        "get_supabase_admin",
        lambda: SimpleNamespace(
            table=lambda _t: SimpleNamespace(
                update=lambda _v: SimpleNamespace(
                    eq=lambda _k, _val: SimpleNamespace(
                        execute=lambda: SimpleNamespace(data=None)
                    )
                )
            )
        ),
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
        persona_key = mode.replace("reviewer_", "")
        parsed = _build_persona_output(persona_key)
        return LLMResponse(
            text=parsed.model_dump_json(),
            model_used="gemini-flash",
            tokens_in=100,
            tokens_out=200,
            latency_ms=10,
            parsed_output=parsed,
        )

    monkeypatch.setattr(journal_sim_service, "llm_call", _fake_llm)

    req = Reviewer3PersonaRequest(
        project_id=project_id,
        session_id=session_id,
        manuscript_text=(
            "Bu çalışma 200 katılımcıyla gerçekleştirilmiştir. " * 10
        ),
        target_journal_id=None,
        lang="tr",
    )
    resp = await journal_sim_service.reviewer_3persona(user_id, req)
    assert resp.session_id == session_id
    assert sorted(calls) == [
        "reviewer_sempatik",
        "reviewer_skeptik",
        "reviewer_yontemci",
    ]
    # depth=2 + follow_up trim
    for persona in (resp.skeptik, resp.sempatik, resp.yontemci):
        for q in persona.questions:
            if q.depth == 2:
                assert q.follow_up is None


@pytest.mark.asyncio
async def test_reviewer_3persona_mismatched_project_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    monkeypatch.setattr(
        journal_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(uuid4()),
            "project_id": str(uuid4()),
            "scan_results": {},
        },
    )
    req = Reviewer3PersonaRequest(
        project_id=uuid4(),
        session_id=uuid4(),
        manuscript_text="x" * 200,
        target_journal_id=None,
        lang="tr",
    )
    with pytest.raises(PermissionError, match="session_project_mismatch"):
        await journal_sim_service.reviewer_3persona(uuid4(), req)


# ── statcheck endpoint ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_statcheck_run_returns_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    monkeypatch.setattr(
        journal_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(uuid4()),
            "scan_results": {},
        },
    )
    monkeypatch.setattr(
        journal_sim_service,
        "get_supabase_admin",
        lambda: SimpleNamespace(
            table=lambda _t: SimpleNamespace(
                update=lambda _v: SimpleNamespace(
                    eq=lambda _k, _val: SimpleNamespace(
                        execute=lambda: SimpleNamespace(data=None)
                    )
                )
            )
        ),
    )
    req = StatcheckRequest(
        session_id=session_id,
        manuscript_text=(
            "Birinci test: t(48) = 2.50, p = .500 olarak rapor edildi. "
            "İkinci test: t(50) = 2.00, p = .051 olarak rapor edildi."
        ),
    )
    resp = await journal_sim_service.statcheck_run(uuid4(), req)
    assert resp.summary.total == 2
    assert resp.summary.red >= 1


# ── journal-calibration ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_journal_calibration_fallback_when_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    monkeypatch.setattr(
        journal_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(uuid4()),
            "scan_results": {"statcheck": {"summary": {"red": 0}}},
        },
    )
    monkeypatch.setattr(
        journal_sim_service,
        "get_supabase_admin",
        lambda: SimpleNamespace(
            table=lambda _t: SimpleNamespace(
                update=lambda _v: SimpleNamespace(
                    eq=lambda _k, _val: SimpleNamespace(
                        execute=lambda: SimpleNamespace(data=None)
                    )
                )
            )
        ),
    )
    resp = await journal_sim_service.journal_calibration(
        uuid4(), session_id, "unknown-journal-9999"
    )
    assert resp.fallback_used is True
    assert resp.distribution.source == "field_average_placeholder"
    assert resp.prediction in {"accept", "minor", "major", "reject"}
    assert 0.0 <= resp.confidence <= 1.0


@pytest.mark.asyncio
async def test_journal_calibration_uses_manual_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    monkeypatch.setattr(
        journal_sim_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(uuid4()),
            "scan_results": {"statcheck": {"summary": {"red": 0}}},
        },
    )
    monkeypatch.setattr(
        journal_sim_service,
        "get_supabase_admin",
        lambda: SimpleNamespace(
            table=lambda _t: SimpleNamespace(
                update=lambda _v: SimpleNamespace(
                    eq=lambda _k, _val: SimpleNamespace(
                        execute=lambda: SimpleNamespace(data=None)
                    )
                )
            )
        ),
    )
    monkeypatch.setattr(
        journal_sim_service,
        "_load_review_distribution",
        lambda: {
            "window_size": 50,
            "journals": [
                {
                    "journal_id": "sleep-med",
                    "name": "Sleep Medicine",
                    "window_size": 50,
                    "accept_pct": 0.14,
                    "major_pct": 0.62,
                    "minor_pct": 0.18,
                    "reject_pct": 0.06,
                    "source": "manual",
                }
            ],
            "field_average_fallback": {
                "accept_pct": 0.12,
                "major_pct": 0.42,
                "minor_pct": 0.30,
                "reject_pct": 0.16,
            },
        },
    )
    resp = await journal_sim_service.journal_calibration(
        uuid4(), session_id, "sleep-med"
    )
    assert resp.fallback_used is False
    assert resp.journal_name == "Sleep Medicine"
    assert resp.prediction == "major"
