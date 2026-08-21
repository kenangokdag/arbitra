"""FAZ C2 — academic engine end-to-end wiring into run_pipeline (v2 report).

Proves the integration that makes FAZ A+B+C1 actually produce a populated v2
ReviewReport, plus the typed reviewer council, WITHOUT any network/LLM (every
heavy stage is monkeypatched in the established run_pipeline test style).

Covered:
  - Normal (consent-allowed) path → persisted report has non-empty findings,
    executive_verdict, risk_radar, action_plan, section_reviews, reviewer_council,
    document_classification, disclosure(external_ai_used=True), schema_version v2.
  - Consent-blocked path → ZERO external AI (classifier `call`, orchestration,
    assess-with-external-AI all proven not invoked); report still carries
    classification(unknown) + disclosure(degraded) + honest empty v2 fields + v2 schema.
  - Anchor verification integrated → a finding whose quote is NOT in the manuscript
    gets the C1 unverified-evidence limitation in the FINAL report.
  - Council → reviewer_council carries valid CouncilRole values with honest finding
    links (build_council unit + pipeline linking).
  - Degraded visibility → an engine degraded signal surfaces in evidence.degraded_features.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from api.models.review import (
    ActionItem,
    CitationIntegritySummary,
    Critique,
    CritiqueIssue,
    DimensionScore,
    Finding,
    Manuscript,
    ManuscriptAnchor,
    ManuscriptMeta,
    PrivacyConfig,
    ReviewProvenance,
    ReviewReport,
)
from engine.academic._engine_base import EngineResult
from engine.academic.anchoring import UNVERIFIED_ANCHORS_LIMITATION
from engine.academic.council import build_council, link_council_to_findings

pytestmark = pytest.mark.unit


# --- fixtures ---------------------------------------------------------------

_FULL_TEXT = (
    "We used a randomized controlled trial design to evaluate the intervention. "
    "The introduction motivates the study and its contribution to the field."
)


def _manuscript() -> Manuscript:
    return Manuscript(
        meta=ManuscriptMeta(
            title="A Worldclass Study",
            section_titles=["Methods", "Introduction"],
            word_count=2000,
            reference_count=10,
        ),
        full_text=_FULL_TEXT,
    )


def _engine_findings() -> EngineResult:
    """Two engine findings: one with a VERIFIED anchor (in text), one UNVERIFIED."""
    f_method = Finding(
        finding_id="method.f0",
        dimension="methodology_fit",
        severity="major",
        confidence=0.8,
        title="Methodology under-justified",
        manuscript_anchors=[
            ManuscriptAnchor(
                anchor_id="raw.q0",
                section="Methods",
                quote="randomized controlled trial design",  # verbatim in _FULL_TEXT
            )
        ],
        action_item_ids=["method.f0.a0"],
    )
    f_cite = Finding(
        finding_id="cite.f0",
        dimension="citation_integrity",
        severity="moderate",
        confidence=0.6,
        title="Citation cannot be verified",
        manuscript_anchors=[
            ManuscriptAnchor(
                anchor_id="raw.q1",
                section="References",
                quote="this exact fabricated quotation does not occur anywhere",
            )
        ],
    )
    actions = [
        ActionItem(
            action_id="method.f0.a0",
            priority="P0",
            instruction="Add a justification for the chosen design.",
            target_section="Methods",
            linked_finding_ids=["method.f0"],
        )
    ]
    return EngineResult(
        findings=[f_method, f_cite],
        action_items=actions,
        degraded=["qualitative_engine:llm_unavailable"],
    )


def _orch_report_with_council() -> ReviewReport:
    """Mimics real run_orchestration output: v1 fields + reviewer_council built from
    REAL critics (so the pipeline only needs to LINK findings)."""
    council = build_council(
        [
            Critique(
                critic="yontemci",
                issues=[
                    CritiqueIssue(
                        target="methods", problem="weak design", severity="major"
                    )
                ],
            ),
            Critique(
                critic="citation_critic",
                issues=[
                    CritiqueIssue(
                        target="refs", problem="unverifiable ref", severity="minor"
                    )
                ],
            ),
            Critique(critic="sempatik", issues=[]),
        ],
        editor_summary="Synthesis: revise methodology and citations.",
        editor_verdict="major_revision",
    )
    return ReviewReport(
        mode="author",
        language="en",
        manuscript_meta=_manuscript().meta,
        summary="Draft summary.",
        overall_assessment="Overall assessment.",
        verdict="major_revision",
        reviewer_council=council,
        provenance=ReviewProvenance(
            model_used="spy",
            persona_version="v",
            engine_version="f14-s4",
            generated_at=datetime.now(UTC),
        ),
    )


def _patch_io(monkeypatch, svc):
    """parse + citation services + stat → no-op (no network)."""
    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(svc, "_set_step", _noop)

    import engine.ingestion as ing

    monkeypatch.setattr(ing, "parse_document", lambda *a, **k: _manuscript())

    async def _resolve_all(refs):
        return ([], CitationIntegritySummary())

    async def _empty(*a, **k):
        return []

    monkeypatch.setattr(svc.review_citation_service, "resolve_all", _resolve_all)
    monkeypatch.setattr(svc.review_citation_service, "check_context", _empty)
    monkeypatch.setattr(svc.review_citation_service, "find_coverage_gaps", _empty)
    monkeypatch.setattr(svc, "_stat_findings", lambda t: [])


# ===========================================================================
# build_council / link unit (typed council from REAL critics)
# ===========================================================================


def test_build_council_maps_real_critics_to_roles():
    council = build_council(
        [
            Critique(critic="yontemci", issues=[CritiqueIssue(target="m", problem="p")]),
            Critique(critic="skeptik", issues=[]),
            Critique(
                critic="citation_critic",
                issues=[CritiqueIssue(target="r", problem="bad", severity="blocker")],
            ),
            Critique(critic="novelty_critic", issues=[]),
            Critique(critic="sempatik", issues=[]),
        ],
        editor_summary="editor synthesis",
        editor_verdict="reject",
    )
    roles = [c.role for c in council]
    assert roles == [
        "methodologist",
        "skeptical_reviewer",
        "citation_auditor",
        "field_expert",
        "constructive_reviewer",
        "editor_synthesizer",
    ]
    # blocker issue → reject-leaning stance + key_objection set
    cite = next(c for c in council if c.role == "citation_auditor")
    assert cite.stance == "reject-leaning"
    assert cite.key_objection == "bad"
    # supportive critic with no issues → no fabricated objection
    sympa = next(c for c in council if c.role == "constructive_reviewer")
    assert sympa.key_objection is None
    assert sympa.stance == "supportive"


def test_link_council_to_findings_honest_links():
    council = build_council(
        [
            Critique(critic="yontemci", issues=[]),
            Critique(critic="citation_critic", issues=[]),
            Critique(critic="sempatik", issues=[]),
        ],
        editor_summary="s",
        editor_verdict="minor_revision",
    )
    findings = _engine_findings().findings
    linked = link_council_to_findings(council, findings)
    by_role = {c.role: c for c in linked}
    # methodologist links the methodology finding; citation_auditor the citation one
    assert by_role["methodologist"].finding_ids == ["method.f0"]
    assert by_role["citation_auditor"].finding_ids == ["cite.f0"]
    # constructive_reviewer + editor have no clean dimension scope → empty (honest)
    assert by_role["constructive_reviewer"].finding_ids == []
    assert by_role["editor_synthesizer"].finding_ids == []


# ===========================================================================
# normal (consent-allowed) E2E
# ===========================================================================


@pytest.mark.asyncio
async def test_normal_path_populates_v2_report(monkeypatch):
    from api.services import review_service as svc

    _patch_io(monkeypatch, svc)

    from api.models.review import DocumentClassification

    async def _classify(*a, **k):
        return DocumentClassification(
            document_type="journal_article",
            document_type_confidence=0.9,
            study_design="quantitative",
            study_design_confidence=0.8,
        )

    monkeypatch.setattr(svc.academic_classifier, "classify_document", _classify)

    async def _assess(*a, **k):
        return _engine_findings()

    monkeypatch.setattr(svc, "assess_manuscript", _assess)

    async def _orch(*a, **k):
        return _orch_report_with_council()

    monkeypatch.setattr(svc.review_orchestration, "run_orchestration", _orch)

    captured: dict[str, object] = {}

    async def _capture_update(job_id, **fields):
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="author", language="en",
        privacy=PrivacyConfig(external_ai_consent="allowed"),
    )

    rep = ReviewReport.model_validate(captured["report"])
    assert rep.schema_version == "review_report.v2"
    assert len(rep.findings) == 2
    assert rep.executive_verdict is not None
    # 2026-08-08: karar agaci artik sayim degil, risk_radar readiness SKORU
    # kullaniyor (bkz. report_synthesis.py ACCEPT/REJECT_READINESS_THRESHOLD,
    # 61 makalelik goldset'e karsi kalibre edildi). Bu fixture'in 1 major + 1
    # moderate bulgusu, journal_article rubric'inin kapsadigi 10 boyuta
    # yayilinca readiness=96.3 -> accept (eskiden "sayim >=1 major -> her
    # zaman major_revision" kuraliyla "major_revision" cikiyordu). Bu test
    # override'i KANITLAMIYOR, sadece normal-yol kablolamayi dogruluyor -
    # override'in gercekten calistigini kanitlayan ayri test icin bkz.
    # test_verdict_is_overridden_by_deterministic_executive_verdict.
    assert rep.executive_verdict.recommended_decision == "accept"
    assert rep.verdict == "accept"
    assert len(rep.risk_radar) == 10  # spec 10 dimensions
    assert [a.action_id for a in rep.action_plan] == ["method.f0.a0"]
    assert rep.section_reviews  # non-empty
    assert rep.reviewer_council  # non-empty
    assert all(
        c.role
        in {
            "methodologist",
            "field_expert",
            "skeptical_reviewer",
            "constructive_reviewer",
            "citation_auditor",
            "ethics_reviewer",
            "statistics_reviewer",
            "editor_synthesizer",
        }
        for c in rep.reviewer_council
    )
    assert rep.document_classification is not None
    assert rep.document_classification.document_type == "journal_article"
    assert rep.disclosure is not None
    assert rep.disclosure.external_ai_used is True
    # provenance stamped with rubric_id + synthesis version (additive append)
    assert "rubric=" in rep.provenance.engine_version
    assert "report_synthesis.v1" in rep.provenance.engine_version
    # council finding links (best-effort) are present
    by_role = {c.role: c for c in rep.reviewer_council}
    assert by_role["methodologist"].finding_ids == ["method.f0"]
    assert by_role["citation_auditor"].finding_ids == ["cite.f0"]


@pytest.mark.asyncio
async def test_verdict_is_overridden_by_deterministic_executive_verdict(monkeypatch):
    """2026-08-07 ÇEKİRDEK KANIT: LLM (mocked orchestration) 'accept' diyor ama
    gerçek bir MAJOR bulgu var (deterministik executive_verdict 'major_revision'
    üretir) — nihai report.verdict LLM'in DEĞİL, deterministik kararın olmalı.
    Ayrıca: citation_integrity (net-eşleşen boyut, risk_radar'da gerçekten
    değerlendirildi) override edilir; importance (risk_radar karşılığı yok) LLM
    skorunda KALIR; final_score override-sonrası yeniden hesaplanır."""
    from api.services import review_service as svc

    _patch_io(monkeypatch, svc)

    from api.models.review import DocumentClassification

    async def _classify(*a, **k):
        return DocumentClassification(
            document_type="journal_article",
            document_type_confidence=0.9,
            study_design="quantitative",
            study_design_confidence=0.8,
        )

    monkeypatch.setattr(svc.academic_classifier, "classify_document", _classify)

    async def _assess(*a, **k):
        f_cite = Finding(
            finding_id="cite.f0",
            dimension="citation_integrity",
            severity="major",
            confidence=0.8,
            title="Uydurma atıf",
            global_issue=True,
            action_item_ids=["cite.f0.a0"],
        )
        # v2 karar ağacı sayım değil, risk_radar readiness SKORU kullanıyor
        # (2026-08-08, bkz. report_synthesis.py ACCEPT/REJECT_READINESS_THRESHOLD).
        # journal_article rubric'i 10 risk kategorisinin TAMAMINI kapsıyor, tek bir
        # major bulgu (citation) 10 boyuta yayılan ortalamayı 97.5'te bırakır — bu da
        # zaten "accept" demek, override'ı GÖRÜNÜR kılmaz. Deterministik kararın
        # gerçekten "accept"ten farklı bir yere (major_revision) düşmesini kanıtlamak
        # için diğer 5 boyuta da birer critical bulgu ekleniyor (readiness=75.0,
        # kalibre edilen [72.0, 78.5) bandına düşer).
        extra_dims = ["methodology", "evidence", "ethics", "reproducibility", "writing"]
        f_extra = [
            Finding(
                finding_id=f"extra.f{i}",
                dimension=dim,
                severity="critical",
                confidence=0.8,
                title=f"Kritik sorun ({dim})",
                global_issue=True,
                action_item_ids=[f"extra.f{i}.a0"],
            )
            for i, dim in enumerate(extra_dims)
        ]
        return EngineResult(
            findings=[f_cite, *f_extra],
            action_items=[
                ActionItem(
                    action_id="cite.f0.a0",
                    priority="P0",
                    instruction="Atfı düzelt.",
                    target_section="References",
                    linked_finding_ids=["cite.f0"],
                ),
                *[
                    ActionItem(
                        action_id=f"extra.f{i}.a0",
                        priority="P0",
                        instruction="Sorunu düzelt.",
                        target_section="General",
                        linked_finding_ids=[f"extra.f{i}"],
                    )
                    for i in range(len(extra_dims))
                ],
            ],
        )

    monkeypatch.setattr(svc, "assess_manuscript", _assess)

    async def _orch(*a, **k):
        # LLM kasten YANLIŞ/iyimser: "accept" + yüksek citation_integrity skoru.
        return ReviewReport(
            mode="author",
            language="en",
            manuscript_meta=_manuscript().meta,
            summary="s",
            overall_assessment="Makale sağlam görünüyor.",
            verdict="accept",
            dimension_scores=[
                DimensionScore(
                    key="citation_integrity", score=9.5, rationale="LLM: atıflar temiz"
                ),
                DimensionScore(key="importance", score=7.0, rationale="LLM: orta önemli"),
            ],
            provenance=ReviewProvenance(
                model_used="spy",
                persona_version="v",
                engine_version="f14-s4",
                generated_at=datetime.now(UTC),
            ),
        )

    monkeypatch.setattr(svc.review_orchestration, "run_orchestration", _orch)

    captured: dict[str, object] = {}

    async def _capture_update(job_id, **fields):
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="author", language="en",
        privacy=PrivacyConfig(external_ai_consent="allowed"),
    )

    rep = ReviewReport.model_validate(captured["report"])

    # ÇEKİRDEK İDDİA: LLM "accept" dedi ama deterministik karar kazandı.
    assert rep.executive_verdict is not None
    assert rep.executive_verdict.recommended_decision == "major_revision"
    assert rep.verdict == "major_revision"
    assert rep.verdict != "accept"  # LLM'in kendi (yanlış) tahmini KAYBETTİ

    by_key = {d.key: d for d in rep.dimension_scores}
    # citation_integrity: risk_radar'da gerçekten değerlendirildi (major bulgu var,
    # 100-25=75 -> 1+75/100*9=7.75) -> LLM'in 9.5'i DEĞİŞTİRİLDİ.
    assert by_key["citation_integrity"].score == pytest.approx(7.75)
    assert by_key["citation_integrity"].score != 9.5
    assert "Deterministik" in by_key["citation_integrity"].rationale
    # importance: risk_radar'ın 10 kategorisinde karşılığı yok -> LLM'in 7.0'ı KALDI.
    assert by_key["importance"].score == 7.0
    assert by_key["importance"].rationale == "LLM: orta önemli"

    # final_score override-sonrası (7.75+7.0)/2=7.375, compute_final_score 2 ondalığa
    # yuvarlıyor (round) -> 7.38. ESKİ (9.5+7.0)/2=8.25 DEĞİL.
    assert rep.final_score == pytest.approx(round((7.75 + 7.0) / 2, 2))
    assert rep.final_score != pytest.approx(round((9.5 + 7.0) / 2, 2))


@pytest.mark.asyncio
async def test_anchor_verification_applied_in_pipeline(monkeypatch):
    """A finding whose quote is NOT in the manuscript → C1 unverified limitation."""
    from api.services import review_service as svc

    _patch_io(monkeypatch, svc)

    from api.models.review import DocumentClassification

    async def _classify(*a, **k):
        return DocumentClassification(document_type="journal_article")

    monkeypatch.setattr(svc.academic_classifier, "classify_document", _classify)

    async def _assess(*a, **k):
        return _engine_findings()

    monkeypatch.setattr(svc, "assess_manuscript", _assess)

    async def _orch(*a, **k):
        return _orch_report_with_council()

    monkeypatch.setattr(svc.review_orchestration, "run_orchestration", _orch)

    captured: dict[str, object] = {}

    async def _capture_update(job_id, **fields):
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="author", language="en",
        privacy=PrivacyConfig(external_ai_consent="allowed"),
    )

    rep = ReviewReport.model_validate(captured["report"])
    cite = next(f for f in rep.findings if f.finding_id == "cite.f0")
    method = next(f for f in rep.findings if f.finding_id == "method.f0")
    assert UNVERIFIED_ANCHORS_LIMITATION in cite.limitations  # quote not in text
    assert UNVERIFIED_ANCHORS_LIMITATION not in method.limitations  # quote IS in text


@pytest.mark.asyncio
async def test_engine_degraded_signal_surfaces_in_evidence(monkeypatch):
    from api.services import review_service as svc

    _patch_io(monkeypatch, svc)

    from api.models.review import DocumentClassification

    async def _classify(*a, **k):
        return DocumentClassification(document_type="journal_article")

    monkeypatch.setattr(svc.academic_classifier, "classify_document", _classify)

    async def _assess(*a, **k):
        return _engine_findings()  # carries degraded=['qualitative_engine:llm_unavailable']

    monkeypatch.setattr(svc, "assess_manuscript", _assess)

    async def _orch(*a, **k):
        return _orch_report_with_council()

    monkeypatch.setattr(svc.review_orchestration, "run_orchestration", _orch)

    captured: dict[str, object] = {}

    async def _capture_update(job_id, **fields):
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="author", language="en",
        privacy=PrivacyConfig(external_ai_consent="allowed"),
    )

    degraded = captured["evidence_pack"]["degraded_features"]
    assert "qualitative_engine:llm_unavailable" in degraded


# ===========================================================================
# consent-blocked E2E — ZERO external AI
# ===========================================================================


@pytest.mark.asyncio
async def test_blocked_path_zero_external_ai_and_v2_degraded(monkeypatch):
    from api.services import review_service as svc

    _patch_io(monkeypatch, svc)

    # spy classifier external call: must NEVER fire when blocked.
    classifier_calls = {"n": 0}

    async def _spy_call(*a, **k):
        classifier_calls["n"] += 1
        raise AssertionError("classifier external AI called on blocked file!")

    monkeypatch.setattr(svc.academic_classifier, "call", _spy_call)

    # spy assess: must be invoked with allow_external_ai=False (no external AI).
    assess_seen = {"allow": None, "n": 0}

    async def _spy_assess(manuscript, rubric, evidence, *, allow_external_ai):
        assess_seen["n"] += 1
        assess_seen["allow"] = allow_external_ai
        return EngineResult(degraded=["qualitative_engine:external_ai_blocked"])

    monkeypatch.setattr(svc, "assess_manuscript", _spy_assess)

    # spy orchestration: must NEVER fire when blocked.
    orch_calls = {"n": 0}

    async def _spy_orch(*a, **k):
        orch_calls["n"] += 1
        return _orch_report_with_council()

    monkeypatch.setattr(svc.review_orchestration, "run_orchestration", _spy_orch)

    captured: dict[str, object] = {}

    async def _capture_update(job_id, **fields):
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf",
        mode="editor", language="tr",
        privacy=PrivacyConfig(
            confidentiality_mode="reviewer_confidential",
            external_ai_consent="blocked",
        ),
    )

    # zero external AI anywhere
    assert classifier_calls["n"] == 0
    assert orch_calls["n"] == 0, "GATE İHLALİ: orkestrasyon gizli dosyada çağrıldı!"
    assert assess_seen["n"] == 1
    assert assess_seen["allow"] is False, "assess external AI gizli dosyada açık!"

    rep = ReviewReport.model_validate(captured["report"])
    assert rep.schema_version == "review_report.v2"
    assert rep.document_classification is not None
    assert rep.document_classification.document_type == "unknown"
    assert rep.disclosure is not None
    assert rep.disclosure.degraded_due_to_consent is True
    assert rep.disclosure.external_ai_used is False
    # honest: no review performed → no rosy synthesis fabricated
    assert rep.findings == []
    assert rep.risk_radar == []
    assert rep.executive_verdict is None
    assert rep.reviewer_council == []
    # engine degraded signal still visible
    assert (
        "qualitative_engine:external_ai_blocked"
        in captured["evidence_pack"]["degraded_features"]
    )
