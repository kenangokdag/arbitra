"""F13-S6-P002+P003+P004 unit tests — manuscript_service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S6
RTF:  Page_Design/Sayfa_Plani_v2/6.1_yayin_icerigi_doldurma.rtf §Plan-Detayı

Strateji: progress_service test pattern — supabase_call_async monkeypatch,
LLM monkeypatch, pure helpers ayrı.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.models.llm import LLMResponse
from api.models.manuscript import (
    ManuscriptSection,
    QualityLLMOutput,
)
from api.services import manuscript_service

pytestmark = pytest.mark.unit


# ── Pure helpers ────────────────────────────────────────────────────────────


def test_word_count_simple() -> None:
    assert manuscript_service._word_count("bu bir test cümlesidir") == 4


def test_word_count_empty() -> None:
    assert manuscript_service._word_count("") == 0
    assert manuscript_service._word_count("   \n\t  ") == 0


def test_word_count_multiple_whitespace() -> None:
    assert manuscript_service._word_count("  iki\tkelime  ") == 2


def _section(
    stype: str = "intro",
    content: str = "",
    word_count: int = 0,
    flag: str | None = None,
) -> ManuscriptSection:
    return ManuscriptSection(
        section_type=stype,  # type: ignore[arg-type]
        content=content,
        word_count=word_count,
        ai_quality_flag=flag,  # type: ignore[arg-type]
        ai_quality_reason=None,
        updated_at=datetime.now(UTC),
    )


def test_gate_3_filled_50_words_open() -> None:
    sections = [
        _section("intro", "x " * 60, 60),
        _section("methods", "x " * 60, 60),
        _section("findings", "x " * 60, 60),
        _section("discussion", "", 0),
        _section("conclusion", "", 0),
    ]
    gate = manuscript_service._compute_gate(sections)
    assert gate.filled_count == 3
    assert gate.gate_open is True
    assert gate.quality_blocked is False


def test_gate_below_50_words_does_not_count() -> None:
    sections = [
        _section("intro", "x " * 60, 60),
        _section("methods", "x " * 60, 60),
        _section("findings", "x " * 30, 30),  # 30 kelime — sayılmaz
        _section("discussion", "", 0),
        _section("conclusion", "", 0),
    ]
    gate = manuscript_service._compute_gate(sections)
    assert gate.filled_count == 2
    assert gate.gate_open is False


def test_gate_quality_blocked_overrides_open() -> None:
    sections = [
        _section("intro", "x " * 60, 60, flag="sahte"),
        _section("methods", "x " * 60, 60),
        _section("findings", "x " * 60, 60),
        _section("discussion", "", 0),
        _section("conclusion", "", 0),
    ]
    gate = manuscript_service._compute_gate(sections)
    assert gate.filled_count == 3
    assert gate.quality_blocked is True
    assert gate.gate_open is False


def test_normalize_fills_missing_slots() -> None:
    rows = [
        {
            "section_type": "intro",
            "content": "abc",
            "word_count": 1,
            "ai_quality_flag": "ok",
            "ai_quality_reason": "akademik",
            "updated_at": "2026-05-11T00:00:00+00:00",
        }
    ]
    out = manuscript_service._normalize_sections(rows, "1970-01-01T00:00:00+00:00")
    assert len(out) == 5
    assert [s.section_type for s in out] == [
        "intro",
        "methods",
        "findings",
        "discussion",
        "conclusion",
    ]
    assert out[0].content == "abc"
    assert out[1].content == ""
    assert out[1].word_count == 0


# ── Supabase patch helper ───────────────────────────────────────────────────


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

    monkeypatch.setattr(manuscript_service, "supabase_call_async", _fake_call)
    monkeypatch.setattr(
        manuscript_service, "get_supabase_admin", lambda: SimpleNamespace()
    )
    return state


# ── ownership fail ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_sections_fails_when_not_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_queue(monkeypatch, [[]])  # ownership query returns empty
    with pytest.raises(LookupError):
        await manuscript_service.get_sections(uuid4(), uuid4())


# ── get_sections normalize + gate ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_sections_normalizes_and_computes_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    rows = [
        {
            "section_type": "intro",
            "content": "abc " * 60,
            "word_count": 60,
            "ai_quality_flag": "ok",
            "ai_quality_reason": "akademik",
            "updated_at": "2026-05-11T00:00:00+00:00",
        },
        {
            "section_type": "methods",
            "content": "xyz " * 60,
            "word_count": 60,
            "ai_quality_flag": None,
            "ai_quality_reason": None,
            "updated_at": "2026-05-11T00:00:00+00:00",
        },
    ]
    _patch_supabase_queue(
        monkeypatch,
        [[{"id": "x"}], rows],
    )
    resp = await manuscript_service.get_sections(uuid4(), pid)
    assert resp.project_id == pid
    assert len(resp.sections) == 5
    assert resp.gate_status.filled_count == 2
    assert resp.gate_status.gate_open is False


# ── upsert_section: word_count + flag reset ─────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_section_computes_word_count_and_resets_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid = uuid4()
    inserted = {
        "section_type": "intro",
        "content": "kelime " * 100,
        "word_count": 100,
        "ai_quality_flag": None,
        "ai_quality_reason": None,
        "updated_at": "2026-05-11T00:00:00+00:00",
    }
    _patch_supabase_queue(monkeypatch, [[{"id": "x"}], [inserted]])

    res = await manuscript_service.upsert_section(
        uuid4(), pid, "intro", "kelime " * 100
    )
    assert res.section_type == "intro"
    assert res.word_count == 100
    assert res.ai_quality_flag is None


@pytest.mark.asyncio
async def test_upsert_section_invalid_type_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="invalid_section_type"):
        await manuscript_service.upsert_section(
            uuid4(),
            uuid4(),
            "bogus",  # type: ignore[arg-type]
            "x",
        )


# ── evaluate_quality: empty → sahte, no LLM ─────────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_quality_empty_returns_sahte_no_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_queue(
        monkeypatch,
        [[{"id": "x"}], []],  # owner ok, no row → empty content branch
    )

    async def _spy_llm(*_a: Any, **_kw: Any) -> LLMResponse:
        raise AssertionError("LLM çağrılmamalıydı (boş içerik)")

    monkeypatch.setattr(manuscript_service, "llm_call", _spy_llm)
    resp = await manuscript_service.evaluate_quality(uuid4(), uuid4(), "intro")
    assert resp.flag == "sahte"
    assert resp.cache_hit is False


# ── evaluate_quality: cached flag → cache_hit True, no LLM ──────────────────


@pytest.mark.asyncio
async def test_evaluate_quality_cache_hit_skips_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached = {
        "section_type": "intro",
        "content": "akademik içerik buradadır.",
        "word_count": 3,
        "ai_quality_flag": "ok",
        "ai_quality_reason": "akademik prose",
    }
    _patch_supabase_queue(monkeypatch, [[{"id": "x"}], [cached]])

    async def _spy_llm(*_a: Any, **_kw: Any) -> LLMResponse:
        raise AssertionError("LLM çağrılmamalıydı (cache hit)")

    monkeypatch.setattr(manuscript_service, "llm_call", _spy_llm)
    resp = await manuscript_service.evaluate_quality(uuid4(), uuid4(), "intro")
    assert resp.flag == "ok"
    assert resp.cache_hit is True


# ── evaluate_quality: fresh content → LLM çağrılır + DB update ──────────────


@pytest.mark.asyncio
async def test_evaluate_quality_calls_llm_and_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fresh = {
        "section_type": "intro",
        "content": "Bu çalışma X alanını incelemektedir." * 5,
        "word_count": 40,
        "ai_quality_flag": None,
        "ai_quality_reason": None,
    }
    _patch_supabase_queue(monkeypatch, [[{"id": "x"}], [fresh], []])

    captured: dict[str, Any] = {}

    async def _fake_llm(prompt: str, **kwargs: Any) -> LLMResponse:
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return LLMResponse(
            text='{"flag":"ok","reason":"akademik anlatım."}',
            parsed_output=QualityLLMOutput(flag="ok", reason="akademik anlatım."),
            model_used="gemini-flash",
            tokens_in=100,
            tokens_out=20,
            latency_ms=400,
        )

    monkeypatch.setattr(manuscript_service, "llm_call", _fake_llm)
    resp = await manuscript_service.evaluate_quality(uuid4(), uuid4(), "intro")
    assert resp.flag == "ok"
    assert resp.cache_hit is False
    assert captured["kwargs"]["tier"] == "flash"
    assert captured["kwargs"]["mode"] == "manuscript_quality"


# ── auto_draft: no completed source → fallback message, no LLM ──────────────


@pytest.mark.asyncio
async def test_auto_draft_no_sources_returns_empty_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supabase_queue(monkeypatch, [[{"id": "x"}], []])

    async def _spy_llm(*_a: Any, **_kw: Any) -> LLMResponse:
        raise AssertionError("LLM çağrılmamalıydı (kaynak yok)")

    monkeypatch.setattr(manuscript_service, "llm_call", _spy_llm)
    resp = await manuscript_service.auto_draft(uuid4(), uuid4(), "intro")
    assert resp.source_steps == []
    assert "yeterli içerik bulunamadı" in resp.draft_content


# ── auto_draft: source meta present → LLM çağrılır ──────────────────────────


@pytest.mark.asyncio
async def test_auto_draft_with_sources_calls_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_rows = [
        {
            "step_id": "curation-4",
            "status": "completed",
            "meta": {"synthesis": "Adaptive learning literatürü..."},
        },
        {
            "step_id": "gapatlas-4",
            "status": "completed",
            "meta": {"decision": "Risk-low / Disruption-high"},
        },
    ]
    _patch_supabase_queue(monkeypatch, [[{"id": "x"}], progress_rows])

    captured: dict[str, Any] = {}

    async def _fake_llm(prompt: str, **kwargs: Any) -> LLMResponse:
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return LLMResponse(
            text="Bu çalışma uyarlanabilir öğrenme literatüründe ...",
            parsed_output=None,
            model_used="gemini-flash",
            tokens_in=500,
            tokens_out=120,
            latency_ms=800,
        )

    monkeypatch.setattr(manuscript_service, "llm_call", _fake_llm)
    resp = await manuscript_service.auto_draft(uuid4(), uuid4(), "intro")
    assert set(resp.source_steps) == {"curation-4", "gapatlas-4"}
    assert resp.draft_content.startswith("Bu çalışma uyarlanabilir")
    assert captured["kwargs"]["mode"] == "manuscript_auto_draft"
    assert "curation-4" in captured["prompt"]
    assert "gapatlas-4" in captured["prompt"]


# ── auto_draft: in_progress (not completed) source filtered out ─────────────


@pytest.mark.asyncio
async def test_auto_draft_filters_non_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_rows = [
        {
            "step_id": "curation-4",
            "status": "in_progress",
            "meta": {"synthesis": "yarım kalmış"},
        },
    ]
    _patch_supabase_queue(monkeypatch, [[{"id": "x"}], progress_rows])

    async def _spy_llm(*_a: Any, **_kw: Any) -> LLMResponse:
        raise AssertionError("LLM çağrılmamalıydı (completed adım yok)")

    monkeypatch.setattr(manuscript_service, "llm_call", _spy_llm)
    resp = await manuscript_service.auto_draft(uuid4(), uuid4(), "intro")
    assert resp.source_steps == []
