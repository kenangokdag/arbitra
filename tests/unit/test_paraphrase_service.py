"""F13-S3 5.3 Akademik Dil — paraphrase_service unit tests.

Strateji: dil tespit + cümle ayrıştırma + jaccard pure-fn; LLM mock.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.models.llm import LLMResponse
from api.services import paraphrase_service

pytestmark = pytest.mark.unit


def test_detect_lang_tr() -> None:
    assert paraphrase_service._detect_lang(
        "Bu çalışmada öğrenme süreçleri incelenmiştir."
    ) == "tr"


def test_detect_lang_en_fallback() -> None:
    assert paraphrase_service._detect_lang(
        "This study examines learning processes in higher education."
    ) == "en"


def test_detect_lang_id() -> None:
    assert paraphrase_service._detect_lang(
        "Penelitian ini bertujuan untuk menganalisis pengaruh teknologi dalam pendidikan dasar yang adalah."
    ) == "id"


def test_split_sentences_basic() -> None:
    out = paraphrase_service._split_sentences(
        "İlk cümle. İkinci cümle? Üçüncü cümle!"
    )
    assert len(out) == 3


def test_jaccard_high_for_synonyms() -> None:
    sim = paraphrase_service._jaccard_similarity(
        "Bu çalışma öğrenme süreçlerini inceler.",
        "Bu çalışma öğrenme süreçlerini incelemektedir.",
    )
    assert sim >= 0.5


def test_jaccard_low_for_meaning_drift() -> None:
    sim = paraphrase_service._jaccard_similarity(
        "Bu çalışma öğrenme süreçlerini inceler.",
        "Mars'taki yaşam koşulları büyük tartışma yarattı.",
    )
    assert sim < 0.2


def test_load_style_rules_tr() -> None:
    rules = paraphrase_service._load_style_rules("tr")
    assert "forbidden_definitive" in rules
    assert "kesinlikle" in rules["forbidden_definitive"]


def test_detect_change_type_definitive_removed() -> None:
    rules = paraphrase_service._load_style_rules("tr")
    ct = paraphrase_service._detect_change_type(
        "Bu yöntem kesinlikle her zaman doğru sonuç verir.",
        "Bu yöntem genellikle tutarlı sonuçlar üretebilmektedir.",
        rules,
    )
    assert ct == "definitive_removed"


@pytest.mark.asyncio
async def test_paraphrase_text_calls_llm_and_flags_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def _fake_llm(*_args: Any, **kwargs: Any) -> LLMResponse:
        captured["kwargs"] = kwargs
        # 2 cümle: birincisi yakın paraphrase, ikincisi büyük drift
        payload = {
            "sentences": [
                {
                    "index": 0,
                    "original": "İlk cümle test.",
                    "proposed": "İlk cümle test edilmektedir.",
                    "confidence": 0.92,
                },
                {
                    "index": 1,
                    "original": "İkinci cümle var.",
                    "proposed": "Tamamen alakasız uzay araştırması.",
                    "confidence": 0.5,
                },
            ]
        }
        return LLMResponse(
            text=json.dumps(payload),
            parsed_output=None,
            model_used="gemini-flash-tr",
            tokens_in=100,
            tokens_out=200,
            latency_ms=600,
        )

    # supabase profile lookup → None
    async def _fake_supa(_fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        return SimpleNamespace(data=[])

    monkeypatch.setattr(paraphrase_service, "llm_call", _fake_llm)
    monkeypatch.setattr(paraphrase_service, "supabase_call_async", _fake_supa)
    monkeypatch.setattr(
        paraphrase_service, "get_supabase_admin", lambda: SimpleNamespace()
    )

    resp = await paraphrase_service.paraphrase_text(
        uuid4(),
        uuid4(),
        "İlk cümle test. İkinci cümle var.",
        lang="tr",
    )
    assert resp.total_sentences == 2
    assert len(resp.sentences) == 2
    assert resp.meaning_drift_count >= 1
    assert captured["kwargs"]["tier"] == "flash"
    assert resp.lang == "tr"


@pytest.mark.asyncio
async def test_record_decision_inserts_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_uuid = uuid4()

    async def _fake_supa(_fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        return SimpleNamespace(data=[{"id": str(log_uuid)}])

    monkeypatch.setattr(paraphrase_service, "supabase_call_async", _fake_supa)
    monkeypatch.setattr(
        paraphrase_service, "get_supabase_admin", lambda: SimpleNamespace()
    )

    resp = await paraphrase_service.record_decision(
        user_id=uuid4(),
        session_id=uuid4(),
        sentence_index=0,
        sentence_original="orig",
        sentence_proposed="prop",
        decision="accept",
        edited_text=None,
        lang="tr",
        section_context="methods",
        meta={"x": 1},
    )
    assert resp.logged is True
    assert resp.log_id == log_uuid
