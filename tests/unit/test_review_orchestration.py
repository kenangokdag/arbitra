"""F14-S4 — çekişmeli hakemlik orkestrasyon testleri.

Kanıt:
  - Pipeline sırası writer → critics (paralel) → editor.
  - Çıktı geçerli ReviewReport.
  - Çıpasız iddia (citation_critic grounded=false) editör tarafından düşürülür
    → nihai raporda yok (editör mock'u gerçek silme davranışını taklit eder;
    pipeline çıpasız hedefi editöre serialize ederek bu silmeyi MÜMKÜN kılar).
  - provenance.judgment_reproducible=False (HK-6).
  - LLM hatası yutulmaz: writer hatası → yükselir; tek eleştirmen düşerse
    rapora dürüst not düşer.

Gerçek LLM YOK: api.services.review_orchestration.call monkeypatch'lenir.
"""

from __future__ import annotations

from typing import Any

import pytest

import api.services.review_orchestration as orch
from api.models.review import (
    CitationIntegritySummary,
    Critique,
    CritiqueIssue,
    DimensionScore,
    EvidencePack,
    ExecutiveVerdict,
    Manuscript,
    ManuscriptMeta,
    ParsedReference,
)
from api.services.llm_service import LLMServiceError

pytestmark = pytest.mark.unit


# --- fixtures ---------------------------------------------------------------


def _manuscript() -> Manuscript:
    return Manuscript(
        meta=ManuscriptMeta(
            title="A Study of Things",
            abstract="We study things and find results.",
            language="en",
            word_count=3000,
            reference_count=2,
        ),
        full_text="Introduction. Methods. Results. Discussion.",
    )


def _evidence() -> EvidencePack:
    return EvidencePack(
        citation_integrity=CitationIntegritySummary(
            total=2, resolved=1, not_found_in_index=0, fabricated=1, retracted=0
        ),
        references=[
            ParsedReference(
                index=0, raw="Smith 2020", title="Real Work", status="resolved"
            ),
            ParsedReference(
                index=1,
                raw="Fake 2099",
                title="Ghost Paper",
                status="fabricated",
                evidence="DOI başka esere ait",
            ),
        ],
    )


def _draft_json(
    verdict: str = "major_revision",
    *,
    with_ungrounded: bool,
    editor_digest: bool = False,
) -> str:
    """Writer/editor structured çıktısı (DraftReport JSON).

    with_ungrounded=True → çıpasız bir övgü içerir (citation_critic flag'leyecek,
    editör mock'u silecek).
    editor_digest=True → editör adımının dolduracağı karar-desteği üst-özetini
    içerir (yalnız editör modu testlerinde editör mock'undan döndürülür).
    """
    weakness_point = "Bir uydurma atıf var (ref[1])."
    extra_strength = (
        '{"category": "novelty", "points": ["Çığır açan, eşsiz katkı (kanıtsız)."]}'
        if with_ungrounded
        else '{"category": "clarity", "points": ["Açık yazım."]}'
    )
    digest_field = (
        '"editor_digest": "Öneri: büyük revizyon (orta güven). Gerekçe: bir '
        'uydurma atıf (ref[1]) belirleyici; metodoloji yeterli ama atıf '
        'bütünlüğü zayıf.",'
        if editor_digest
        else ""
    )
    return (
        "{"
        '"summary": "Bir çalışma.",'
        f'"strengths": [{extra_strength}],'
        f'"weaknesses": [{{"category": "citations", "points": ["{weakness_point}"]}}],'
        '"detailed_comments": [{"area": "related_work", "comment": "ilgili iş", '
        '"evidence_ref": "ref[1] fabricated"}],'
        '"questions": ["Örneklem neden bu?"],'
        '"overall_assessment": "Genel değerlendirme.",'
        f'"verdict": "{verdict}",'
        f"{digest_field}"
        '"dimension_scores": ['
        '{"key": "originality", "score": 6.0, "rationale": "r"},'
        '{"key": "citation_integrity", "score": 3.0, "rationale": "uydurma var"}'
        "]"
        "}"
    )


class _FakeResp:
    def __init__(self, parsed: Any, model_used: str = "test-model-used") -> None:
        self.parsed_output = parsed
        self.model_used = model_used


# --- tests ------------------------------------------------------------------


async def test_pipeline_order_and_valid_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """writer → critics → editor sırası + geçerli ReviewReport + provenance."""
    order: list[str] = []

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        mode = kw.get("mode")
        schema = kw["structured_output_schema"]
        order.append(mode)
        if mode == "review_writer":
            return _FakeResp(schema.model_validate_json(_draft_json(with_ungrounded=False)))
        if mode == "review_editor":
            return _FakeResp(schema.model_validate_json(_draft_json(with_ungrounded=False)))
        # critic
        return _FakeResp(Critique(critic="skeptik", issues=[]))

    monkeypatch.setattr(orch, "call", _fake_call)

    report = await orch.run_orchestration(
        _manuscript(), _evidence(), mode="author", language="en"
    )

    # writer ilk, editor son; aradakiler critics
    assert order[0] == "review_writer"
    assert order[-1] == "review_editor"
    assert order.count("review_writer") == 1
    assert order.count("review_editor") == 1
    # 5 eleştirmen writer ile editor arasında çağrıldı
    critic_modes = order[1:-1]
    assert len(critic_modes) == 5

    assert report.mode == "author"
    assert report.verdict == "major_revision"
    assert report.provenance.judgment_reproducible is False
    assert report.provenance.deterministic_engine is True
    assert report.provenance.engine_version == "f14-s4"
    assert report.final_score is not None
    # author modunda da HAFİF disclaimer var (R-4) ama editör digesti YOK
    assert report.ethics_notice is not None
    assert "insan hakemin yerine geçmez" in report.ethics_notice
    assert report.editor_digest is None
    # kanıt paketi rapora taşınmış
    assert report.evidence_pack.citation_integrity.fabricated == 1


async def test_provenance_model_used_reflects_actual_editor_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2026-08-13: provenance.model_used ARTIK hardcoded 'gemini-pro-tiebreak'
    DEĞİL — editörün SON turdaki gerçek LLMResponse.model_used'ını taşır.
    Router Claude fallback'ine düşerse (örn. 'claude-pro-fallback') rapor
    bunu DOĞRU yansıtmalı, sabit Gemini adı YAZMAMALI."""

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        mode = kw.get("mode")
        schema = kw["structured_output_schema"]
        if mode == "review_writer":
            return _FakeResp(
                schema.model_validate_json(_draft_json(with_ungrounded=False)),
                model_used="gemini-pro-tiebreak",
            )
        if mode == "review_editor":
            # Router bu turda Claude fallback'ine düşmüş varsayımı.
            return _FakeResp(
                schema.model_validate_json(_draft_json(with_ungrounded=False)),
                model_used="claude-pro-fallback",
            )
        return _FakeResp(Critique(critic="skeptik", issues=[]), model_used="gemini-flash-tr")

    monkeypatch.setattr(orch, "call", _fake_call)

    report = await orch.run_orchestration(
        _manuscript(), _evidence(), mode="author", language="en"
    )

    assert report.provenance.model_used == "claude-pro-fallback"


async def test_ungrounded_claim_dropped_by_editor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """citation_critic grounded=false → editör çıpasız övgüyü siler (final'de yok)."""
    ungrounded_phrase = "eşsiz katkı (kanıtsız)"

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        mode = kw.get("mode")
        schema = kw["structured_output_schema"]
        if mode == "review_writer":
            # writer çıpasız övgü içeren taslak üretir
            return _FakeResp(schema.model_validate_json(_draft_json(with_ungrounded=True)))
        if mode == "citation_critic":
            return _FakeResp(
                Critique(
                    critic="citation_critic",
                    issues=[
                        CritiqueIssue(
                            target="strengths.novelty",
                            problem="Çıpasız övgü; kanıt paketinde dayanağı yok.",
                            severity="major",
                            grounded=False,
                        )
                    ],
                )
            )
        if mode == "review_editor":
            # editör çıpasız övgüyü silmiş nihai rapor döner (with_ungrounded=False)
            return _FakeResp(
                schema.model_validate_json(_draft_json(with_ungrounded=False))
            )
        # diğer critics boş
        return _FakeResp(Critique(critic="skeptik", issues=[]))

    monkeypatch.setattr(orch, "call", _fake_call)

    report = await orch.run_orchestration(
        _manuscript(), _evidence(), mode="author", language="en"
    )

    # nihai raporda çıpasız ifade GEÇMEZ
    all_strength_text = " ".join(
        p for g in report.strengths for p in g.points
    )
    assert ungrounded_phrase not in all_strength_text


async def test_editor_mode_ethics_notice_is_strong_and_prominent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mode='editor' → ethics_notice GÜÇLÜ + zorunlu (R-4).

    Editör notu yazar notundan anlamlı şekilde FARKLI olmalı: gizlilik
    sorumluluğu + dergi LLM-politikası + yayımlanmamış makale dili içermeli.
    """

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        mode = kw.get("mode")
        schema = kw["structured_output_schema"]
        if mode in ("review_writer", "review_editor"):
            return _FakeResp(
                schema.model_validate_json(
                    _draft_json(with_ungrounded=False, editor_digest=True)
                )
            )
        return _FakeResp(Critique(critic="skeptik", issues=[]))

    monkeypatch.setattr(orch, "call", _fake_call)

    report = await orch.run_orchestration(
        _manuscript(), _evidence(), mode="editor", language="tr"
    )
    assert report.ethics_notice is not None
    notice = report.ethics_notice
    # güçlü dil: insan-karar + gizlilik + dergi-politikası + yayımlanmamış makale
    assert "insan hakemin" in notice
    assert "Gizlilik sorumluluğu" in notice
    assert "yayımlanmamış makale" in notice
    assert "LLM-hakemlik politika" in notice
    # editör notu, yazar (hafif) notundan UZUN ve daha güçlü
    assert len(report.ethics_notice) > len(orch._ETHICS_NOTICE_AUTHOR)


async def test_editor_mode_carries_decision_support_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mode='editor' → editör digesti (karar desteği) rapora taşınır;
    editör-yönelimli çerçeve writer + editor prompt'una enjekte edilir."""
    seen_writer_prompt: list[str] = []
    seen_editor_prompt: list[str] = []

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        mode = kw.get("mode")
        schema = kw["structured_output_schema"]
        if mode == "review_writer":
            seen_writer_prompt.append(prompt)
            return _FakeResp(
                schema.model_validate_json(_draft_json(with_ungrounded=False))
            )
        if mode == "review_editor":
            seen_editor_prompt.append(prompt)
            return _FakeResp(
                schema.model_validate_json(
                    _draft_json(with_ungrounded=False, editor_digest=True)
                )
            )
        return _FakeResp(Critique(critic="skeptik", issues=[]))

    monkeypatch.setattr(orch, "call", _fake_call)

    report = await orch.run_orchestration(
        _manuscript(), _evidence(), mode="editor", language="tr"
    )

    # KARAR DESTEĞİ: editör digesti dolu + karar-odaklı
    assert report.editor_digest is not None
    assert "Öneri:" in report.editor_digest
    # editör-yönelimli çerçeve writer + editor prompt'unda görünür
    assert "EDİTÖR MODU" in seen_writer_prompt[0]
    assert "KARAR DESTEĞİ" in seen_writer_prompt[0]
    assert "editor_digest" in seen_editor_prompt[0]


async def test_author_mode_has_no_editor_digest_or_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REGRESYON: author modunda digest YOK + editör çerçevesi prompt'a girmez."""
    seen_writer_prompt: list[str] = []

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        mode = kw.get("mode")
        schema = kw["structured_output_schema"]
        if mode == "review_writer":
            seen_writer_prompt.append(prompt)
        if mode in ("review_writer", "review_editor"):
            # author modunda bile model digest üretirse rapora GEÇMEMELİ
            return _FakeResp(
                schema.model_validate_json(
                    _draft_json(with_ungrounded=False, editor_digest=True)
                )
            )
        return _FakeResp(Critique(critic="skeptik", issues=[]))

    monkeypatch.setattr(orch, "call", _fake_call)

    report = await orch.run_orchestration(
        _manuscript(), _evidence(), mode="author", language="tr"
    )
    assert report.editor_digest is None
    assert "EDİTÖR MODU" not in seen_writer_prompt[0]


async def test_writer_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """writer LLM hatası YUTULMAZ → LLMServiceError yükselir."""

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        if kw.get("mode") == "review_writer":
            raise LLMServiceError("writer down")
        return _FakeResp(Critique(critic="skeptik", issues=[]))

    monkeypatch.setattr(orch, "call", _fake_call)

    with pytest.raises(LLMServiceError):
        await orch.run_orchestration(
            _manuscript(), _evidence(), mode="author", language="en"
        )


async def test_writer_truncation_recovers_on_single_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2026-08-14 (docs/plans/LLM_THINKING_TRUNCATION_RETRY_2026-08-14.md):
    writer'ın _DraftReport çağrısı 'structured_output parse failed' ile
    (Gemini Pro thinking-truncation'ını taklit ederek) İLK denemede
    başarısız olursa, 1x otomatik retry ile İKİNCİ denemede kurtarılır —
    pipeline devam eder, rapor üretilir, dürüst bir not düşülür."""
    writer_call_count = 0

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        nonlocal writer_call_count
        mode = kw.get("mode")
        schema = kw["structured_output_schema"]
        if mode == "review_writer":
            writer_call_count += 1
            if writer_call_count == 1:
                raise LLMServiceError("structured_output parse failed (_DraftReport)")
            return _FakeResp(
                schema.model_validate_json(_draft_json(with_ungrounded=False))
            )
        if mode == "review_editor":
            return _FakeResp(
                schema.model_validate_json(_draft_json(with_ungrounded=False))
            )
        return _FakeResp(Critique(critic="skeptik", issues=[]))

    monkeypatch.setattr(orch, "call", _fake_call)

    report = await orch.run_orchestration(
        _manuscript(), _evidence(), mode="author", language="en"
    )
    assert writer_call_count == 2
    assert "tekrar üretildi" in report.overall_assessment


async def test_editor_truncation_recovers_on_single_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Aynı senaryo editor adımında — retry editor'ı kurtarır, rapor üretilir."""
    editor_call_count = 0

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        nonlocal editor_call_count
        mode = kw.get("mode")
        schema = kw["structured_output_schema"]
        if mode == "review_writer":
            return _FakeResp(
                schema.model_validate_json(_draft_json(with_ungrounded=False))
            )
        if mode == "review_editor":
            editor_call_count += 1
            if editor_call_count == 1:
                raise LLMServiceError("structured_output parse failed (_DraftReport)")
            return _FakeResp(
                schema.model_validate_json(_draft_json(with_ungrounded=False))
            )
        return _FakeResp(Critique(critic="skeptik", issues=[]))

    monkeypatch.setattr(orch, "call", _fake_call)

    report = await orch.run_orchestration(
        _manuscript(), _evidence(), mode="author", language="en"
    )
    assert editor_call_count == 2
    assert "tekrar üretildi" in report.overall_assessment


async def test_writer_truncation_retry_exhausted_still_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry de aynı hatayla başarısız olursa mevcut davranış (yükselt)
    KORUNUR — regresyon yok, sonsuz retry yok (tam olarak 1 deneme daha)."""
    call_count = 0

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        nonlocal call_count
        if kw.get("mode") == "review_writer":
            call_count += 1
            raise LLMServiceError("structured_output parse failed (_DraftReport)")
        return _FakeResp(Critique(critic="skeptik", issues=[]))

    monkeypatch.setattr(orch, "call", _fake_call)

    with pytest.raises(LLMServiceError):
        await orch.run_orchestration(
            _manuscript(), _evidence(), mode="author", language="en"
        )
    assert call_count == 2  # ilk deneme + tam 1 retry, fazlası değil


async def test_non_truncation_llm_error_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Başka türden bir LLMServiceError (örn. ağ hatası) retry-DEĞİL,
    doğrudan yükseltilir — retry sadece truncation sınıfına özel."""
    call_count = 0

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        nonlocal call_count
        if kw.get("mode") == "review_writer":
            call_count += 1
            raise LLMServiceError("LLM çağrısı başarısız: connection reset")
        return _FakeResp(Critique(critic="skeptik", issues=[]))

    monkeypatch.setattr(orch, "call", _fake_call)

    with pytest.raises(LLMServiceError):
        await orch.run_orchestration(
            _manuscript(), _evidence(), mode="author", language="en"
        )
    assert call_count == 1  # retry TETİKLENMEDİ


async def test_single_critic_failure_is_honest_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bir eleştirmen düşerse pipeline devam eder + rapora dürüst not düşer."""

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        mode = kw.get("mode")
        schema = kw["structured_output_schema"]
        if mode in ("review_writer", "review_editor"):
            return _FakeResp(
                schema.model_validate_json(_draft_json(with_ungrounded=False))
            )
        if mode == "novelty_critic":
            raise LLMServiceError("novelty critic down")
        return _FakeResp(Critique(critic="skeptik", issues=[]))

    monkeypatch.setattr(orch, "call", _fake_call)

    report = await orch.run_orchestration(
        _manuscript(), _evidence(), mode="author", language="en"
    )
    assert "yanıt veremedi" in report.overall_assessment
    assert "novelty_critic" in report.overall_assessment


# --- 2026-08-07: dimension_scores/verdict entegrasyonu yardımcı fonksiyonları -


def test_compute_final_score_is_mean_of_dimension_scores() -> None:
    scores = [
        DimensionScore(key="soundness", score=8.0, rationale="r"),
        DimensionScore(key="clarity", score=6.0, rationale="r"),
    ]
    assert orch.compute_final_score(scores) == 7.0


def test_compute_final_score_empty_is_none() -> None:
    """Boş liste -> None (uydurma yok, HK-7)."""
    assert orch.compute_final_score([]) is None


def test_serialize_executive_verdict_contains_decision_and_override_notice() -> None:
    """2026-08-07: editor'a geçilen deterministik özet, kendi verdict alanının
    override edileceğini AÇIKÇA söylemeli (guardian'ın prose-tutarlılık
    endişesine karşı tek güvence — bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md)."""
    v = ExecutiveVerdict(
        overall_readiness_score=62.5,
        recommended_decision="major_revision",
        confidence=0.7,
        top_fatal_risks=["Uydurma atıf tespit edildi"],
        one_sentence_diagnosis="Ciddi bulgular var.",
    )
    block = orch.serialize_executive_verdict(v)
    assert "major_revision" in block
    assert "62" in block  # readiness skoru
    assert "Uydurma atıf tespit edildi" in block
    assert "override edilecek" in block or "değiştirilecek" in block  # açık uyarı
    assert "TUTARLI" in block
