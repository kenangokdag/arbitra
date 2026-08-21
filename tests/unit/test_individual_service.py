"""F13-S8 unit tests — individual_service (6.3 Bireysel Kontrol).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S8
RTF:  Page_Design/Sayfa_Plani_v2/6.3_bireysel_kontrol.rtf §Plan-Detayı
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.models.individual import (
    ChecklistCategory,
    ChecklistItem,
    ChecklistResponseModel,
    PersonalFeedbackLLMOutput,
)
from api.models.llm import LLMResponse
from api.services import individual_service

pytestmark = pytest.mark.unit


# ── helpers ─────────────────────────────────────────────────────────────────


def _patch_supabase_invoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """supabase_call_async → lambda'yı doğrudan invoke et."""

    async def _fake_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        return fn()

    monkeypatch.setattr(individual_service, "supabase_call_async", _fake_call)


def _checklist_fixture() -> ChecklistResponseModel:
    return ChecklistResponseModel(
        version="v0_test",
        language="tr",
        doc_type="makale",
        note=None,
        categories=[
            ChecklistCategory(
                id="etik",
                label="Etik Kurul",
                items=[
                    ChecklistItem(
                        id="etik_1",
                        soru="Etik kurul onayınız var mı?",
                        aciklama="...",
                        evet_metin="evet",
                        hayir_metin="hayır",
                        yapamadim_metin="yapamadım",
                        kritik=True,
                    ),
                    ChecklistItem(
                        id="etik_2",
                        soru="Aydınlatılmış onam toplandı mı?",
                        aciklama="...",
                        evet_metin="evet",
                        hayir_metin="hayır",
                        yapamadim_metin="yapamadım",
                        kritik=False,
                    ),
                ],
            )
        ],
    )


# ── 1) saf yardımcılar ──────────────────────────────────────────────────────


def test_merge_checklist_entry_replaces_existing() -> None:
    existing: list[dict[str, Any]] = [
        {
            "checklist_id": "makale_tr",
            "item_id": "etik_1",
            "response": "hayir",
            "noted_at": "2026-05-10T00:00:00+00:00",
        },
        {
            "checklist_id": "makale_tr",
            "item_id": "etik_2",
            "response": "evet",
            "noted_at": "2026-05-10T00:00:00+00:00",
        },
    ]
    merged = individual_service._merge_checklist_entry(
        existing, "makale_tr", "etik_1", "evet"
    )
    assert len(merged) == 2
    e1 = next(e for e in merged if e["item_id"] == "etik_1")
    assert e1["response"] == "evet"
    e2 = next(e for e in merged if e["item_id"] == "etik_2")
    assert e2["response"] == "evet"


def test_count_responses_handles_all_categories() -> None:
    entries = [
        {"response": "evet"},
        {"response": "evet"},
        {"response": "hayir"},
        {"response": "yapamadim"},
    ]
    assert individual_service._count_responses(entries) == (2, 1, 1)


def test_critical_blocked_true_when_critical_negative() -> None:
    checklist = _checklist_fixture()
    entries = [{"item_id": "etik_1", "response": "hayir"}]
    assert individual_service._critical_blocked(entries, checklist) is True


def test_critical_blocked_false_when_only_noncritical_negative() -> None:
    checklist = _checklist_fixture()
    entries = [
        {"item_id": "etik_1", "response": "evet"},
        {"item_id": "etik_2", "response": "hayir"},
    ]
    assert individual_service._critical_blocked(entries, checklist) is False


# ── 2) load_checklist ───────────────────────────────────────────────────────


def test_load_checklist_returns_model_for_makale_tr() -> None:
    result = individual_service.load_checklist("makale", "tr")
    assert result.doc_type == "makale"
    assert result.language == "tr"
    assert len(result.categories) >= 1


def test_load_checklist_unknown_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.setattr(individual_service, "_CHECKLIST_DIR", tmp_path / "missing")
    with pytest.raises(LookupError, match="checklist_not_found"):
        individual_service.load_checklist("makale", "tr")


# ── 3) upsert_individual_check ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_individual_check_merges_and_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    user_id = uuid4()

    monkeypatch.setattr(
        individual_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(uuid4()),
            "individual_check": [
                {
                    "checklist_id": "makale_tr",
                    "item_id": "etik_2",
                    "response": "evet",
                    "noted_at": "2026-05-10T00:00:00+00:00",
                }
            ],
        },
    )
    monkeypatch.setattr(
        individual_service,
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
        individual_service, "load_checklist", lambda *_a: _checklist_fixture()
    )

    resp = await individual_service.upsert_individual_check(
        user_id,
        session_id,
        "makale_tr",
        "etik_1",
        "hayir",
        "makale",
        "tr",
    )
    assert resp.total_items_answered == 2
    assert resp.evet_count == 1
    assert resp.hayir_count == 1
    assert resp.critical_blocked is True


# ── 4) suggest_journals — V1 fallback ───────────────────────────────────────


@pytest.mark.asyncio
async def test_suggest_journals_empty_seed_marks_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    monkeypatch.setattr(
        individual_service,
        "get_supabase_admin",
        lambda: SimpleNamespace(
            table=lambda _t: SimpleNamespace(
                select=lambda _c: SimpleNamespace(
                    eq=lambda _k1, _v1: SimpleNamespace(
                        eq=lambda _k2, _v2: SimpleNamespace(
                            limit=lambda _n: SimpleNamespace(
                                execute=lambda: SimpleNamespace(
                                    data=[{"id": "00000000-0000-0000-0000-000000000000"}]
                                )
                            )
                        )
                    )
                )
            )
        ),
    )
    monkeypatch.setattr(individual_service, "_load_seed_journals", lambda: [])

    resp = await individual_service.suggest_journals(
        uuid4(), uuid4(), "machine learning"
    )
    assert resp.journals == []
    assert resp.fallback_used is True


@pytest.mark.asyncio
async def test_suggest_journals_filters_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    monkeypatch.setattr(
        individual_service,
        "get_supabase_admin",
        lambda: SimpleNamespace(
            table=lambda _t: SimpleNamespace(
                select=lambda _c: SimpleNamespace(
                    eq=lambda _k1, _v1: SimpleNamespace(
                        eq=lambda _k2, _v2: SimpleNamespace(
                            limit=lambda _n: SimpleNamespace(
                                execute=lambda: SimpleNamespace(
                                    data=[{"id": "11111111-1111-1111-1111-111111111111"}]
                                )
                            )
                        )
                    )
                )
            )
        ),
    )
    monkeypatch.setattr(
        individual_service,
        "_load_seed_journals",
        lambda: [
            {
                "issn": "1234-5678",
                "name": "Test Journal",
                "indices": ["SCIE"],
                "sjr_quartile": "Q1",
                "scope_label": "Machine Learning and AI",
                "scope_match": 0.8,
            },
            {
                "issn": "9999-0000",
                "name": "Off Topic",
                "indices": ["ESCI"],
                "scope_label": "Botany",
            },
        ],
    )

    resp = await individual_service.suggest_journals(
        uuid4(), uuid4(), "machine learning"
    )
    assert len(resp.journals) == 1
    assert resp.journals[0].name == "Test Journal"
    assert resp.fallback_used is False


# ── 5) generate_personal_feedback ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_personal_feedback_calls_flash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    monkeypatch.setattr(
        individual_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(project_id),
            "individual_check": [
                {"item_id": "etik_1", "response": "hayir"},
                {"item_id": "etik_2", "response": "yapamadim"},
            ],
        },
    )
    monkeypatch.setattr(
        individual_service, "load_checklist", lambda *_a: _checklist_fixture()
    )

    parsed = PersonalFeedbackLLMOutput(
        feedback_paragraph=(
            "Etik kurul onayınız henüz tamamlanmadığı için kritik bir risk söz "
            "konusudur. Aydınlatılmış onam belgelerini de oluşturmadığınızı "
            "belirttiniz. Bu iki konuya öncelik vererek ilerlemenizi öneririm."
        ),
        weak_areas=["etik kurul", "aydınlatılmış onam"],
    )

    async def _fake_llm(
        prompt: str,
        *,
        tier: str,
        mode: str,
        structured_output_schema: Any = None,
        max_tokens: int = 600,
    ) -> LLMResponse:
        return LLMResponse(
            text=parsed.model_dump_json(),
            model_used="gemini-flash",
            tokens_in=10,
            tokens_out=10,
            latency_ms=1,
            parsed_output=parsed,
        )

    monkeypatch.setattr(individual_service, "llm_call", _fake_llm)

    resp = await individual_service.generate_personal_feedback(
        user_id, project_id, session_id, "makale", "tr", "Manuscript özeti"
    )
    assert resp.session_id == session_id
    assert "etik" in resp.feedback_paragraph.lower()
    assert resp.weak_areas == ["etik kurul", "aydınlatılmış onam"]


@pytest.mark.asyncio
async def test_generate_personal_feedback_mismatched_project_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_invoke(monkeypatch)
    session_id = uuid4()
    monkeypatch.setattr(
        individual_service,
        "_fetch_session",
        lambda sid, uid: {
            "id": str(session_id),
            "project_id": str(uuid4()),
            "individual_check": [],
        },
    )
    with pytest.raises(PermissionError, match="session_project_mismatch"):
        await individual_service.generate_personal_feedback(
            uuid4(), uuid4(), session_id, "makale", "tr", None
        )
