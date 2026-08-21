"""F13-S13 unit tests — completion_service (S2 Proje Tamamlama).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S13
RTF:  Page_Design/Sayfa_Plani_v2/S2_proje_tamamlama.rtf
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.models.completion import (
    CompletionFeedback,
    StepReviewLLMItem,
    StepReviewLLMOutput,
)
from api.models.llm import LLMResponse
from api.services import completion_service

pytestmark = pytest.mark.unit


# ── helpers ─────────────────────────────────────────────────────────────────


def _patch_supabase_invoke(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        return fn()

    monkeypatch.setattr(completion_service, "supabase_call_async", _fake_call)


# ── pure helpers ────────────────────────────────────────────────────────────


def test_score_event_step_three_events_full_score() -> None:
    events = {"2.1_arastirma_alani": {"total": 3, "resolved": 0}}
    s = completion_service._score_event_step(events, "2.1_arastirma_alani")
    assert s == 1.0


def test_score_event_step_one_event_partial() -> None:
    events = {"2.1_arastirma_alani": {"total": 1, "resolved": 1}}
    # base = 1/3 ≈ 0.33; resolved_ratio = 1.0 → +0.2 → 0.53
    s = completion_service._score_event_step(events, "2.1_arastirma_alani")
    assert 0.5 < s < 0.6


def test_score_event_step_empty_zero() -> None:
    assert completion_service._score_event_step({}, "x") == 0.0


def test_score_manuscript_step_three_filled() -> None:
    sections = [
        {"section_type": "intro", "word_count": 100, "ai_quality_flag": "ok"},
        {"section_type": "methods", "word_count": 80, "ai_quality_flag": None},
        {"section_type": "findings", "word_count": 60, "ai_quality_flag": "ok"},
    ]
    s = completion_service._score_manuscript_step(sections, 3, 50)
    assert s == 1.0


def test_score_manuscript_step_sahte_excluded() -> None:
    sections = [
        {"section_type": "intro", "word_count": 200, "ai_quality_flag": "sahte"},
        {"section_type": "methods", "word_count": 100, "ai_quality_flag": "ok"},
    ]
    s = completion_service._score_manuscript_step(sections, 3, 50)
    # Yalnız 1 geçerli / 3 hedef = 0.33
    assert 0.3 < s < 0.4


def test_score_defense_step_full_score() -> None:
    session = {"jury_members": [{"name": "x"}], "question_pool": [{"q": "y"}]}
    assert completion_service._score_defense_step(session) == 1.0


def test_score_defense_step_partial() -> None:
    session = {"jury_members": [{"name": "x"}], "question_pool": []}
    assert completion_service._score_defense_step(session) == 0.5


def test_score_defense_step_none() -> None:
    assert completion_service._score_defense_step(None) == 0.0


def test_score_scan_step_filled() -> None:
    session = {
        "scan_results": {
            "individual_check": {"checklist_id": "x", "items": {"a": "evet"}}
        }
    }
    s = completion_service._score_scan_step(session, ["individual_check"])
    assert s == 1.0


def test_score_scan_step_missing_path() -> None:
    session = {"scan_results": {}}
    s = completion_service._score_scan_step(session, ["individual_check"])
    assert s == 0.0


def test_score_jury_decision_uses_confidence() -> None:
    session = {
        "scan_results": {
            "jury_session": {"decision_band": {"confidence": 0.82, "prediction": "accept"}}
        }
    }
    s = completion_service._score_jury_decision(session)
    assert abs(s - 0.82) < 1e-9


def test_score_jury_decision_no_band_zero() -> None:
    session = {"scan_results": {"jury_session": {}}}
    s = completion_service._score_jury_decision(session)
    assert s == 0.0


def test_status_from_score_above_threshold() -> None:
    assert completion_service._status_from_score(0.7, 0.6) == "basarili"
    assert completion_service._status_from_score(0.5, 0.6) == "gelistirilmeli"


def test_evaluate_advice_rules_picks_matching_status() -> None:
    rules_cfg = {
        "rules": [
            {
                "trigger_step": "6.5_juri_simulasyonu",
                "trigger_status": "gelistirilmeli",
                "advice": "Jüri açığı var — sentez paragrafına dön.",
            },
            {
                "trigger_step": "__any__",
                "trigger_status": "basarili",
                "advice": "Sonraki proje önerisi.",
            },
        ],
        "max_advice_in_snapshot": 3,
    }
    step_statuses = {
        "6.5_juri_simulasyonu": "gelistirilmeli",
        "2.1_arastirma_alani": "basarili",
    }
    advice = completion_service._evaluate_advice_rules(rules_cfg, step_statuses)
    assert len(advice) == 2
    assert "Jüri" in advice[0]


def test_evaluate_advice_rules_max_cap() -> None:
    rules_cfg = {
        "rules": [
            {"trigger_step": "__any__", "trigger_status": "basarili", "advice": f"a{i}"}
            for i in range(10)
        ],
        "max_advice_in_snapshot": 3,
    }
    advice = completion_service._evaluate_advice_rules(
        rules_cfg, {"x": "basarili"}
    )
    assert len(advice) == 3


def test_build_step_reviews_uses_signal_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    badge_cfg = {
        "steps": [
            {
                "step_id": "2.1",
                "label": "Alan",
                "basarili_min": 0.6,
                "signal_source": "project_event",
                "page_slug": "2.1_arastirma_alani",
            },
            {
                "step_id": "6.1",
                "label": "İçerik",
                "basarili_min": 0.6,
                "signal_source": "manuscript_section",
                "min_filled_sections": 3,
                "min_word_count_per_section": 50,
            },
        ]
    }
    events_by_page = {"2.1_arastirma_alani": {"total": 3, "resolved": 0}}
    sections = [
        {"section_type": "intro", "word_count": 100, "ai_quality_flag": "ok"},
        {"section_type": "methods", "word_count": 100, "ai_quality_flag": "ok"},
        {"section_type": "findings", "word_count": 100, "ai_quality_flag": "ok"},
    ]
    reviews = completion_service._build_step_reviews(
        badge_cfg, events_by_page, sections, None
    )
    assert len(reviews) == 2
    assert reviews[0]["status"] == "basarili"
    assert reviews[1]["status"] == "basarili"


# ── create_snapshot ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_snapshot_persists_and_returns_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    user_id = uuid4()
    project_id = uuid4()
    completion_id = uuid4()
    now_iso = datetime.now(UTC).isoformat()

    monkeypatch.setattr(
        completion_service,
        "_verify_project_ownership",
        lambda pid, uid: None,
    )
    monkeypatch.setattr(
        completion_service,
        "_count_events_by_page",
        lambda uid, pid: {"2.1_arastirma_alani": {"total": 3, "resolved": 2}},
    )
    monkeypatch.setattr(
        completion_service,
        "_fetch_manuscript_sections",
        lambda pid: [
            {"section_type": "intro", "word_count": 80, "ai_quality_flag": "ok"},
            {"section_type": "methods", "word_count": 100, "ai_quality_flag": "ok"},
            {"section_type": "findings", "word_count": 70, "ai_quality_flag": "ok"},
        ],
    )
    monkeypatch.setattr(
        completion_service,
        "_fetch_defense_session",
        lambda pid: {
            "id": "d1",
            "jury_members": [{"name": "X"}],
            "question_pool": [{"q": "Y"}],
            "scan_results": {
                "individual_check": {"checklist_id": "x", "items": {"a": "evet"}},
                "journal_calibration": {"prediction": "minor", "confidence": 0.6},
                "jury_session": {
                    "decision_band": {"prediction": "accept", "confidence": 0.8}
                },
            },
        },
    )

    upsert_rows = [
        {
            "id": str(completion_id),
            "project_id": str(project_id),
            "completed_at": now_iso,
            "delete_after": now_iso,
            "snapshot": {},
        }
    ]
    monkeypatch.setattr(
        completion_service,
        "get_supabase_admin",
        lambda: SimpleNamespace(
            table=lambda _t: SimpleNamespace(
                upsert=lambda _v, on_conflict=None: SimpleNamespace(
                    execute=lambda: SimpleNamespace(data=upsert_rows)
                )
            )
        ),
    )

    async def _fake_llm(
        prompt: str,
        *,
        tier: str,
        mode: str,
        structured_output_schema: Any = None,
        max_tokens: int = 600,
    ) -> LLMResponse:
        # Verilen step listesinden step_id'leri çıkarıp her birine yorum üret
        ids = []
        for line in prompt.splitlines():
            if line.startswith("- ") and " (" in line:
                ids.append(line.split(" ", 1)[1].split(" (", 1)[0])
        parsed = StepReviewLLMOutput(
            reviews=[
                StepReviewLLMItem(step_id=sid, comment=f"{sid} için yorum.")
                for sid in ids
            ],
            summary_paragraph="Proje genel olarak dengeli ilerlemiş; sentez "
            "ayağı güçlü, savunma simülasyonu da kabul bandında. Bir sonraki "
            "tur için boşluk haritasını derinleştir.",
        )
        return LLMResponse(
            text=parsed.model_dump_json(),
            model_used="gemini-flash",
            tokens_in=100,
            tokens_out=200,
            latency_ms=10,
            parsed_output=parsed,
        )

    monkeypatch.setattr(completion_service, "llm_call", _fake_llm)

    resp = await completion_service.create_snapshot(user_id, project_id)
    assert resp.completion_id == completion_id
    assert resp.project_id == project_id
    assert len(resp.snapshot.step_reviews) == 10  # badge_thresholds: 10 steps
    assert (
        resp.snapshot.badges.basarili + resp.snapshot.badges.gelistirilmeli == 10
    )
    assert resp.snapshot.summary_paragraph.startswith("Proje")
    # graduate_advice: Mezun (basarili sahip → __any__ rule) eklenir
    assert len(resp.snapshot.graduate_advice) > 0


@pytest.mark.asyncio
async def test_create_snapshot_raises_when_project_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)

    def _raise(_pid: Any, _uid: Any) -> None:
        raise LookupError("project_not_found")

    monkeypatch.setattr(completion_service, "_verify_project_ownership", _raise)

    with pytest.raises(LookupError, match="project_not_found"):
        await completion_service.create_snapshot(uuid4(), uuid4())


# ── record_feedback ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_feedback_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    user_id = uuid4()
    project_id = uuid4()
    completion_id = uuid4()
    now_iso = datetime.now(UTC).isoformat()

    monkeypatch.setattr(
        completion_service,
        "_verify_project_ownership",
        lambda pid, uid: None,
    )
    updated_rows = [
        {
            "id": str(completion_id),
            "project_id": str(project_id),
            "updated_at": now_iso,
        }
    ]
    monkeypatch.setattr(
        completion_service,
        "get_supabase_admin",
        lambda: SimpleNamespace(
            table=lambda _t: SimpleNamespace(
                update=lambda _v: SimpleNamespace(
                    eq=lambda _k, _v2: SimpleNamespace(
                        eq=lambda _k2, _v3: SimpleNamespace(
                            execute=lambda: SimpleNamespace(data=updated_rows)
                        )
                    )
                )
            )
        ),
    )

    feedback = CompletionFeedback(
        topic_suggestion_rating=4,
        process_rating=5,
        missing_features="PDF export henüz yok.",
        overall_satisfaction=4,
        nps=9,
    )
    resp = await completion_service.record_feedback(user_id, project_id, feedback)
    assert resp.completion_id == completion_id
    assert resp.feedback.nps == 9


@pytest.mark.asyncio
async def test_record_feedback_404_when_snapshot_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)

    monkeypatch.setattr(
        completion_service,
        "_verify_project_ownership",
        lambda pid, uid: None,
    )
    monkeypatch.setattr(
        completion_service,
        "get_supabase_admin",
        lambda: SimpleNamespace(
            table=lambda _t: SimpleNamespace(
                update=lambda _v: SimpleNamespace(
                    eq=lambda _k, _v2: SimpleNamespace(
                        eq=lambda _k2, _v3: SimpleNamespace(
                            execute=lambda: SimpleNamespace(data=[])
                        )
                    )
                )
            )
        ),
    )

    feedback = CompletionFeedback(
        topic_suggestion_rating=3,
        process_rating=3,
        missing_features="",
        overall_satisfaction=3,
        nps=5,
    )
    with pytest.raises(
        LookupError, match="completion_not_found_run_snapshot_first"
    ):
        await completion_service.record_feedback(uuid4(), uuid4(), feedback)
