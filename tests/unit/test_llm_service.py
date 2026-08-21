"""F8 LLMService unit tests (DM-LLM-3/4/7).

Coverage: tier routing (flash/pro) + ProjectContext/page_state injection +
structured_output parse + LLMServiceError mapping. Router chokepoint mock'lanır.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, Field

from api.models.llm import ProjectContext
from api.models.review import (
    CitationIntegritySummary,
    DimensionScore,
    EvidencePack,
    ExecutiveVerdict,
    Finding,
    ManuscriptMeta,
    ParsedReference,
    ReviewProvenance,
    ReviewReport,
    RiskRadarItem,
)

pytestmark = pytest.mark.unit


def _make_review_report() -> ReviewReport:
    """Plan: docs/plans/DANISMAN_REPORT_GROUNDING_PERSONA_2026-08-16.md §4.3 test'i.

    Kasıtlı 1 critical, 1 minor finding + 1 (moat-doğrulanmış görünen) referans
    içerir — özetleyicinin critical'i taşıyıp minor'ı VE referans listesini
    ATLADIĞINI kanıtlamak için (token-bütçe disiplini regresyon guard'ı)."""
    return ReviewReport(
        mode="author",
        language="tr",
        manuscript_meta=ManuscriptMeta(title="Test Manuscript"),
        summary="özet",
        overall_assessment="genel değerlendirme",
        verdict="major_revision",
        dimension_scores=[
            DimensionScore(key="soundness", score=6.5, rationale="orta"),
        ],
        provenance=ReviewProvenance(
            model_used="gemini-flash-tr",
            persona_version="v1",
            engine_version="v1",
            generated_at=datetime.now(timezone.utc),
        ),
        executive_verdict=ExecutiveVerdict(
            overall_readiness_score=42.0,
            recommended_decision="major_revision",
            one_sentence_diagnosis="Yöntem bölümü zayıf.",
            top_fatal_risks=["Örneklem büyüklüğü raporlanmamış"],
        ),
        risk_radar=[
            RiskRadarItem(
                dimension="soundness",
                score=40.0,
                severity="major",
                why_it_matters="Yöntem tekrarlanabilir değil.",
            ),
        ],
        findings=[
            Finding(
                finding_id="F-CRIT-1",
                dimension="soundness",
                severity="critical",
                title="Örneklem büyüklüğü hesabı eksik",
                summary="Power analizi raporlanmamış.",
                global_issue=True,
                action_item_ids=["A-1"],
            ),
            Finding(
                finding_id="F-MINOR-1",
                dimension="clarity",
                severity="minor",
                title="Şekil 3 başlığı belirsiz",
                summary="Eksen etiketleri eksik.",
                global_issue=True,
            ),
        ],
        evidence_pack=EvidencePack(
            citation_integrity=CitationIntegritySummary(
                total=10, resolved=8, fabricated=1, retracted=0, not_found_in_index=1
            ),
            references=[
                ParsedReference(
                    index=1,
                    raw="Smith 2020",
                    title="EVIDENCE_PACK_REFERENCE_TITLE_MARKER",
                ),
            ],
        ),
    )


def _fake_response(
    content: str,
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    model: str | None = None,
) -> Any:
    """model=None → gerçek litellm ModelResponse'un bazı yollarda .model
    boş bırakabildiği durumu simüle eder (Optional alan, bkz. llm_service.py
    call()'daki getattr fallback yorumu)."""

    class _Msg:
        def __init__(self, c: str) -> None:
            self.content = c

    class _Choice:
        def __init__(self, c: str) -> None:
            self.message = _Msg(c)

    class _Usage:
        def __init__(self, p: int, co: int) -> None:
            self.prompt_tokens = p
            self.completion_tokens = co

    class _Resp:
        def __init__(self, c: str, m: str | None) -> None:
            self.choices = [_Choice(c)]
            self.usage = _Usage(prompt_tokens, completion_tokens)
            self.model = m

    return _Resp(content, model)


class _SubQueries(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sub_queries: list[str] = Field(min_length=1)


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Router chokepoint mock; çağrı argümanlarını yakalar."""
    seen: dict[str, Any] = {}

    async def fake(**kwargs: Any) -> Any:
        seen.update(kwargs)
        return _fake_response("ok-text")

    monkeypatch.setattr("api.services.llm_service.acompletion", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    return seen


async def test_llm_service_call_flash_basic(captured: dict[str, Any]) -> None:
    from api.services.llm_service import call

    resp = await call(prompt="hello", tier="flash")
    assert resp.text == "ok-text"
    assert resp.model_used == "gemini-flash-tr"
    assert captured["model"] == "gemini-flash-tr"
    assert captured["temperature"] == 0.2
    assert captured["max_tokens"] == 600


async def test_llm_service_call_pro_tiebreak(captured: dict[str, Any]) -> None:
    from api.services.llm_service import call

    resp = await call(prompt="tough", tier="pro")
    assert resp.model_used == "gemini-pro-tiebreak"
    assert captured["model"] == "gemini-pro-tiebreak"
    assert captured["temperature"] == 0.1
    assert captured["max_tokens"] == 800


@pytest.mark.parametrize(
    "mode",
    [
        "review_writer",
        "review_editor",
        "critic_skeptik",
        "critic_yontemci",
        "critic_sempatik",
        "citation_critic",
        "novelty_critic",
    ],
)
async def test_llm_service_review_pipeline_modes_use_temperature_zero(
    captured: dict[str, Any], mode: str
) -> None:
    """2026-08-20 kullanıcı bulgusu: review pipeline'ın 7 aşaması da (tier'dan
    bağımsız) temperature=0 ile çağrılmalı — aksi halde aynı makale art arda
    analiz edilince farklı bulgu sayısı/verdict/skor çıkıyordu (kanıtlanmış
    gerçek regresyon, temperature>0 + seed yok)."""
    from api.services.llm_service import call

    tier = "pro" if mode in {"review_writer", "review_editor"} else "flash"
    await call(prompt="x", tier=tier, mode=mode)
    assert captured["temperature"] == 0.0
    assert captured["seed"] == 42
    # 2026-08-20 canlı testte bulunan gerçek regresyon: Vertex 403 (billing)
    # → Claude fallback denendiğinde Anthropic seed'i desteklemediği için
    # fallback da patlıyordu. drop_params=True bunu düzeltiyor.
    assert captured["drop_params"] is True


@pytest.mark.parametrize(
    "mode",
    [
        "manuscript_classifier",
        "academic_dimension",
        "qualitative_rigor",
        "quantitative_validity",
    ],
)
async def test_llm_service_academic_assessment_modes_use_temperature_zero(
    captured: dict[str, Any], mode: str
) -> None:
    """2026-08-21 kullanıcı talebi ("moat 3-boyutu çöz"): assess_manuscript()'in
    KENDİ İÇİNDEKİ 4 motoru (classifier/dimension_engine/qualitative/
    quantitative — hepsi tier="flash") review_orchestration'ın 7 aşaması gibi
    hâlâ örnekleme yapıyordu; risk_radar'ın deterministik override'ı
    (report_synthesis.apply_deterministic_dimension_scores) bunların ürettiği
    `findings`'e dayanıyor, yani asıl varyans kaynağı buradaydı — özellikle
    quantitative_validity, statistical_consistency'yi doğrudan besliyor."""
    from api.services.llm_service import call

    await call(prompt="x", tier="flash", mode=mode)
    assert captured["temperature"] == 0.0
    assert captured["seed"] == 42
    assert captured["drop_params"] is True


async def test_llm_service_non_pipeline_modes_keep_tier_based_temperature(
    captured: dict[str, Any],
) -> None:
    """Chat/Danışman modları (default, review_advisor, ...) bu düzeltmenin
    DIŞINDA kalmalı — konuşma hâlâ tier-bazlı temperature kullanıyor, seed
    hiç gönderilmiyor."""
    from api.services.llm_service import call

    await call(prompt="merhaba", tier="flash", mode="review_advisor")
    assert captured["temperature"] == 0.2
    assert "seed" not in captured
    assert "drop_params" not in captured


async def test_llm_service_model_used_reflects_actual_response_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2026-08-13: Router bir Claude fallback'ine düşerse (litellm ModelResponse.
    model gerçek çalışan modeli taşır), LLMResponse.model_used İSTENEN alias'ı
    (örn. 'gemini-pro-tiebreak') DEĞİL, GERÇEKTE yanıt veren modeli yansıtmalı —
    eski hardcoded-provenance bug'ının kök nedeni tam burasıydı."""
    from api.services.llm_service import call

    async def fake(**kwargs: Any) -> Any:
        return _fake_response("ok-text", model="claude-pro-fallback")

    monkeypatch.setattr("api.services.llm_service.acompletion", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    resp = await call(prompt="tough", tier="pro")
    assert resp.model_used == "claude-pro-fallback"


async def test_llm_service_model_used_falls_back_to_alias_when_response_model_empty(
    captured: dict[str, Any],
) -> None:
    """response.model boşsa (bazı yollarda litellm bunu boş bırakabilir,
    Optional alan) istenen alias'a dürüstçe düş — None/boş string yazma."""
    from api.services.llm_service import call

    resp = await call(prompt="hello", tier="flash")
    assert resp.model_used == "gemini-flash-tr"


async def test_llm_service_project_context_injection(captured: dict[str, Any]) -> None:
    from api.services.llm_service import call

    ctx = ProjectContext(
        project_id="p1",
        user_id="u1",
        topic="social media anxiety",
        hypothesis="screen time correlates with GAD",
    )
    await call(prompt="advise", tier="flash", project_ctx=ctx)
    system = captured["messages"][0]["content"]
    assert "p1" in system
    assert "social media anxiety" in system
    assert "screen time correlates with GAD" in system


async def test_llm_service_page_state_injection(captured: dict[str, Any]) -> None:
    from api.services.llm_service import call

    page = {"selected_topic": "burnout", "candidates": 3}
    await call(prompt="advise", tier="flash", page_state=page)
    system = captured["messages"][0]["content"]
    assert "burnout" in system
    assert "Sayfada şu an görünen veri" in system


async def test_llm_service_report_context_injection(captured: dict[str, Any]) -> None:
    """Plan §4.3: verdict/executive_verdict/risk_radar/critical finding sisteme
    giriyor; minor finding VE evidence_pack.references (tam liste) GİRMİYOR —
    token-bütçe disiplini regresyon guard'ı."""
    from api.services.llm_service import call

    report = _make_review_report()
    await call(prompt="bu rapor hakkında ne dersin?", tier="flash", report_context=report)
    system = captured["messages"][0]["content"]

    assert "major_revision" in system
    assert "Yöntem bölümü zayıf" in system
    assert "Örneklem büyüklüğü raporlanmamış" in system
    assert "soundness" in system
    assert "F-CRIT-1" in system
    assert "Örneklem büyüklüğü hesabı eksik" in system
    assert "uydurma=1" in system

    # Token-bütçesi guard'ı: minor finding VE ham referans listesi TAŞINMAMALI.
    assert "F-MINOR-1" not in system
    assert "Şekil 3 başlığı belirsiz" not in system
    assert "EVIDENCE_PACK_REFERENCE_TITLE_MARKER" not in system


async def test_llm_service_no_report_context_skips_injection(captured: dict[str, Any]) -> None:
    from api.services.llm_service import call

    await call(prompt="advise", tier="flash")
    system = captured["messages"][0]["content"]
    assert "Verdict:" not in system


async def test_llm_service_structured_output_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(**_: Any) -> Any:
        return _fake_response('{"sub_queries":["a","b","c"]}')

    monkeypatch.setattr("api.services.llm_service.acompletion", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from api.services.llm_service import call

    resp = await call(prompt="x", tier="flash", structured_output_schema=_SubQueries)
    assert resp.parsed_output is not None
    assert isinstance(resp.parsed_output, _SubQueries)
    assert resp.parsed_output.sub_queries == ["a", "b", "c"]


async def test_llm_service_provider_error_raises_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(**_: Any) -> Any:
        raise RuntimeError("provider down")

    monkeypatch.setattr("api.services.llm_service.acompletion", boom)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from api.services.llm_service import LLMServiceError, call

    with pytest.raises(LLMServiceError, match="provider down"):
        await call(prompt="x", tier="flash")


async def test_llm_service_structured_parse_truncated_raises_service_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1 fix: Gemini truncate → ValidationError → LLMServiceError (not raw)."""
    truncated = '{"sub_queries": ["alpha", "beta", "Multi-'

    async def fake(**_: Any) -> Any:
        return _fake_response(truncated)

    monkeypatch.setattr("api.services.llm_service.acompletion", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from api.services.llm_service import LLMServiceError, call

    with pytest.raises(LLMServiceError, match="structured_output parse failed"):
        await call(prompt="x", tier="flash", structured_output_schema=_SubQueries)


async def test_llm_service_strips_markdown_code_fence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gemini Flash bazen ```json\\n…\\n``` ile sarıyor; parse öncesi soyulmalı."""
    fenced = '```json\n{"sub_queries":["x","y","z"]}\n```'

    async def fake(**_: Any) -> Any:
        return _fake_response(fenced)

    monkeypatch.setattr("api.services.llm_service.acompletion", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from api.services.llm_service import call

    resp = await call(prompt="x", tier="flash", structured_output_schema=_SubQueries)
    assert isinstance(resp.parsed_output, _SubQueries)
    assert resp.parsed_output.sub_queries == ["x", "y", "z"]


def test_strip_code_fence_handles_unterminated_fence() -> None:
    """max_tokens kapağı yanıtı kesince kapanış fence'i eksik olabilir; opening yine soyulur."""
    from api.services.llm_service import _strip_code_fence

    truncated = '```json\n{"sub_queries":["a","b'
    out = _strip_code_fence(truncated)
    assert not out.startswith("```")
    assert out.startswith('{"sub_queries"')
