"""F13-S2-P003+P004 /api/workshop/* — atölye sayfaları arka uç.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S2-P003 + P004)
Sayfa: Page_Design/Sayfa_Plani_v2/5.1_yayin_formati.rtf §Plan-Detayı (2)+(3)

Endpoints:
- GET  /api/workshop/maturity?project_id=&publication_type=
- PUT  /api/workshop/progress           (step durumu yaz)
- POST /api/workshop/advisor-summary    (4-5 paragraf akademik özet, Gemini Flash)

Auth: AuthMiddleware request.state.user_id zorunlu.
Diary pattern: service-role + Python-level user_id JOIN sahiplik.
"""

from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.models.citation import (
    CitationBalanceRequest,
    CitationBalanceResponse,
    CitationSearchResponse,
    CitationStyle,
    CitationVerifyRequest,
    CitationVerifyResponse,
    FormatCitationResponse,
    Lang,
)
from api.models.defense import (
    DefenseSession,
    DefenseSessionUpsert,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    SuggestJuryResponse,
)
from api.models.individual import (
    ChecklistLang,
    ChecklistResponseModel,
    DocType,
    IndividualCheckResponse,
    IndividualCheckUpsert,
    JournalSuggestResponse,
    PersonalFeedbackRequest,
    PersonalFeedbackResponse,
)
from api.models.journal_sim import (
    JournalCalibrationResponse,
    Reviewer3PersonaRequest,
    Reviewer3PersonaResponse,
    StatcheckRequest,
    StatcheckResponse,
)
from api.models.jury_sim import (
    AnswerScoreRequest,
    AnswerScoreResponse,
    ConsistencyCheckRequest,
    ConsistencyCheckResponse,
    HydeFanoutRequest,
    HydeFanoutResponse,
    JuryDecisionBandRequest,
    JuryDecisionBandResponse,
    JuryQuestionRequest,
    JuryQuestionResponse,
)
from api.models.manuscript import (
    AutoDraftRequest,
    AutoDraftResponse,
    ManuscriptResponse,
    ManuscriptSection,
    ManuscriptUpsert,
    QualityCheckRequest,
    QualityCheckResponse,
    SectionType,
)
from api.models.paraphrase import (
    ParaphraseDecisionRequest,
    ParaphraseDecisionResponse,
    ParaphraseRequest,
    ParaphraseResponse,
)
from api.models.progress import (
    AdvisorSummaryRequest,
    AdvisorSummaryResponse,
    MaturityResponse,
    ProgressStep,
    ProgressUpsert,
    PublicationType,
)
from api.models.synthesis import SynthesizeRequest, SynthesizeResponse
from api.models.topic import (
    DraftSkeletonRequest,
    DraftSkeletonResponse,
    TopicProposalsRequest,
    TopicProposalsResponse,
)
from api.models.workshop_analytics import (
    CompareRequest,
    CompareResponse,
    GapProfileWorkshopResponse,
    ImpactCurveResponse,
    ImpactDimension,
    OriginalityResponse,
    OriginalityType,
)
from api.services import (
    citation_service,
    defense_service,
    gap_profile_workshop_service,
    impact_curve_service,
    individual_service,
    journal_sim_service,
    jury_sim_service,
    manuscript_service,
    originality_service,
    paraphrase_service,
    progress_service,
    study_compare_service,
    synthesis_service,
    topic_service,
)
from api.middleware.tier_gate import tier_gate
from api.services.llm_service import LLMServiceError

logger = logging.getLogger(__name__)

# M-14: router-level Depends(tier_gate) — anon kesin reddedilir (401), authed
# kullanıcılara WORKSHOP_PREFIX_QUOTA günlük tavanı uygulanır. V2'de
# Pro-only kilit için tek satır (`WORKSHOP_PREFIX_QUOTA[OGRENCI] = None`).
# Audit referansı: AUDIT_REPORT.md §11 M-14 / POL-COST-1.
router = APIRouter(
    prefix="/api/workshop",
    tags=["workshop"],
    dependencies=[Depends(tier_gate)],
)


def _user_id(request: Request) -> UUID:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="missing_user_id")
    try:
        return UUID(cast(str, uid))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="invalid_user_id") from exc


def _ensure_supabase() -> None:
    from api.config import get_settings

    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SECRET_KEY:
        raise HTTPException(
            status_code=503, detail="supabase_unavailable_workshop_disabled"
        )


@router.get("/maturity", response_model=MaturityResponse)
async def get_maturity(
    request: Request,
    project_id: UUID = Query(...),
    publication_type: PublicationType = Query(...),
) -> MaturityResponse:
    """Yayın türüne göre olgunluk + UI checklist + Danışmana butonu aktif flag."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await progress_service.calculate_maturity(
            user_id, project_id, publication_type
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="project_not_found") from exc


@router.put(
    "/progress",
    response_model=ProgressStep,
    status_code=status.HTTP_200_OK,
)
async def upsert_progress(req: ProgressUpsert, request: Request) -> ProgressStep:
    """Step durumu yaz/güncelle. completed → completed_at otomatik now()."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await progress_service.upsert_step(user_id, req)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="project_not_found") from exc


@router.post(
    "/advisor-summary",
    response_model=AdvisorSummaryResponse,
)
async def advisor_summary(
    req: AdvisorSummaryRequest, request: Request
) -> AdvisorSummaryResponse:
    """5.1 RTF §Plan-Detayı (3) — "Danışmana Gitmeden Evvel" akademik özet.

    Gemini Flash + prompt mühendisliği (Omer 2026-05-10 kararı: Pro değil).
    LLM hatası → 503.
    """
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await progress_service.summarize_advisor(
            user_id, req.project_id, req.publication_type
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="project_not_found") from exc
    except LLMServiceError as exc:
        logger.exception("workshop advisor-summary LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.post("/paraphrase", response_model=ParaphraseResponse)
async def paraphrase(
    req: ParaphraseRequest, request: Request
) -> ParaphraseResponse:
    """5.3 Akademik Dil — Gemini Flash batch paraphrase + meaning-drift kontrol."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await paraphrase_service.paraphrase_text(
            user_id,
            req.project_id,
            req.document_text,
            req.lang,
            req.section_context,
        )
    except LLMServiceError as exc:
        logger.exception("workshop paraphrase LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.post(
    "/paraphrase-decision", response_model=ParaphraseDecisionResponse
)
async def paraphrase_decision(
    req: ParaphraseDecisionRequest, request: Request
) -> ParaphraseDecisionResponse:
    """5.3 Akademik Dil — sessiz öğrenme log (accept/reject/edit)."""
    user_id = _user_id(request)
    _ensure_supabase()
    return await paraphrase_service.record_decision(
        user_id,
        req.session_id,
        req.sentence_index,
        req.sentence_original,
        req.sentence_proposed,
        req.decision,
        req.edited_text,
        req.lang,
        req.section_context,
        req.meta,
    )


# ── F13-S4 5.4 Atıf Stil — 4 endpoint ──────────────────────────────────────


@router.get("/citation-search", response_model=CitationSearchResponse)
async def citation_search(
    request: Request,
    project_id: UUID = Query(...),
    query: str = Query(..., min_length=1, max_length=200),
    lang: Lang = Query("tr"),
) -> CitationSearchResponse:
    """5.4 — kelime/iddia → havuzdan top-20 paper (synonym fallback)."""
    _user_id(request)
    _ensure_supabase()
    return await citation_service.search_citations(project_id, query, lang)


@router.post("/citation-verify", response_model=CitationVerifyResponse)
async def citation_verify(
    req: CitationVerifyRequest, request: Request
) -> CitationVerifyResponse:
    """5.4 — cümle-başı 4-sınıf doğrulama (ok/hallucinated/topic_mismatch/needs_citation)."""
    _user_id(request)
    _ensure_supabase()
    return await citation_service.verify_citations(req.project_id, req.document_text)


@router.get("/format-citation", response_model=FormatCitationResponse)
async def format_one(
    request: Request,
    paper_id: str = Query(..., min_length=1),
    style: CitationStyle = Query("apa"),
) -> FormatCitationResponse:
    """5.4 — tek paper'ı 5 stilden birinde formatla (LLM yok, deterministic)."""
    _user_id(request)
    _ensure_supabase()
    try:
        return await citation_service.format_one_citation(paper_id, style)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="paper_not_found") from exc


@router.post("/citation-balance", response_model=CitationBalanceResponse)
async def citation_balance(
    req: CitationBalanceRequest, request: Request
) -> CitationBalanceResponse:
    """5.4 — atıf listesi yıl histogramı + eski/yeni denge önerisi."""
    _user_id(request)
    _ensure_supabase()
    payload = await citation_service.compute_balance(
        req.project_id, req.citation_paper_ids
    )
    return CitationBalanceResponse(**payload)


# ── F13-S11 3.4 Literatür Sentezi ──────────────────────────────────────────


@router.post("/synthesize", response_model=SynthesizeResponse)
async def workshop_synthesize(
    req: SynthesizeRequest, request: Request
) -> SynthesizeResponse:
    """3.4 — 1..25 paper'dan akademik sentez (Gemini Pro + faithfulness)."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await synthesis_service.synthesize(
            user_id, req.project_id, req.paper_ids, req.mode, req.lang
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="project_not_owned") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop synthesize LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


# ── F13-S11 4.2–4.5 Atölye Analitik (gap/originality/compare/impact) ───────


@router.get("/originality", response_model=OriginalityResponse)
async def workshop_originality(
    request: Request,
    project_id: UUID = Query(...),
    type: OriginalityType = Query(...),
    year_from: int | None = Query(default=None, ge=1900, le=2100),
    year_to: int | None = Query(default=None, ge=1900, le=2100),
    theme_id: str | None = Query(default=None, max_length=200),
) -> OriginalityResponse:
    """4.3 — proje havuzundan yıkıcı (cd_5) veya sleeping beauty (b) paper listesi."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await originality_service.fetch_originality(
            user_id, project_id, type, year_from, year_to, theme_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/gap/{matrix_id}/{axis_x}/{axis_y}",
    response_model=GapProfileWorkshopResponse,
)
async def workshop_gap_profile(
    request: Request,
    matrix_id: str,
    axis_x: str,
    axis_y: str,
    project_id: UUID = Query(...),
) -> GapProfileWorkshopResponse:
    """4.2 — gap hücresi profili: 7-dim radar + sparkline + komşu + dergi + top paper."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await gap_profile_workshop_service.fetch_gap_profile(
            user_id, project_id, matrix_id, axis_x, axis_y
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop gap-profile LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.post("/compare", response_model=CompareResponse)
async def workshop_compare(
    req: CompareRequest, request: Request
) -> CompareResponse:
    """4.4 — 2-5 gap hücresi karşılaştırma (Risk/Disruption/Virgin/SB/Pub) + öneri."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await study_compare_service.compare_gaps(user_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop compare LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.get("/impact-curve", response_model=ImpactCurveResponse)
async def workshop_impact_curve(
    request: Request,
    project_id: UUID = Query(...),
    dimension: ImpactDimension = Query(...),
    value: str = Query(..., min_length=1, max_length=200),
    years: int = Query(10, ge=2, le=30),
) -> ImpactCurveResponse:
    """4.5 — boyut (topic/method) için yayın eğrisi + ★ yıkıcı + ♦ SB + momentum."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await impact_curve_service.fetch_impact_curve(
            user_id, project_id, dimension, value, years
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop impact-curve LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


# ── F13-S5 5.2 Yayın Taslağı — topic-proposals + draft-skeleton ────────────


@router.post("/topic-proposals", response_model=TopicProposalsResponse)
async def workshop_topic_proposals(
    req: TopicProposalsRequest, request: Request
) -> TopicProposalsResponse:
    """5.2 — Gemini Pro: gap+metod+sentez → 3 konu kartı (3 mod RQ + kanıt zinciri)."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await topic_service.propose_topics(user_id, req)
    except PermissionError as exc:
        detail = str(exc)
        code = 429 if detail == "daily_quota_exceeded" else 403
        raise HTTPException(status_code=code, detail=detail) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop topic-proposals LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.post("/draft-skeleton", response_model=DraftSkeletonResponse)
async def workshop_draft_skeleton(
    req: DraftSkeletonRequest, request: Request
) -> DraftSkeletonResponse:
    """5.2 — IMRaD 4 paralel Flash + bölüm-bazlı top-5 paper SQL."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await topic_service.draft_skeleton(
            user_id,
            req.project_id,
            req.selected_topic,
            req.method_metod_ids,
            req.sections,
            req.lang,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop draft-skeleton LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


# ── F13-S6 6.1 Yayın İçeriği — manuscript_section 4 endpoint ───────────────


@router.get("/manuscript", response_model=ManuscriptResponse)
async def manuscript_list(
    request: Request,
    project_id: UUID = Query(...),
) -> ManuscriptResponse:
    """6.1 — 5 bölümün içerik + word_count + quality_flag + gate_status."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await manuscript_service.get_sections(user_id, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="project_not_found") from exc


@router.put(
    "/manuscript/{section_type}",
    response_model=ManuscriptSection,
)
async def manuscript_upsert(
    section_type: SectionType,
    req: ManuscriptUpsert,
    request: Request,
) -> ManuscriptSection:
    """6.1 — bölüm içeriği yaz; word_count auto-compute, quality_flag NULL."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await manuscript_service.upsert_section(
            user_id, req.project_id, section_type, req.content
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="project_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/manuscript/quality-check", response_model=QualityCheckResponse)
async def manuscript_quality_check(
    req: QualityCheckRequest, request: Request
) -> QualityCheckResponse:
    """6.1 — Gemini Flash: ok | sahte (lorem ipsum/test metni) + 1 cümle."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await manuscript_service.evaluate_quality(
            user_id, req.project_id, req.section_type
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="project_not_found") from exc
    except LLMServiceError as exc:
        logger.exception("workshop manuscript quality-check LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.post("/manuscript/auto-draft", response_model=AutoDraftResponse)
async def manuscript_auto_draft(
    req: AutoDraftRequest, request: Request
) -> AutoDraftResponse:
    """6.1 — önceki adım çıktıları → Gemini Flash 1 paragraf taslak."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await manuscript_service.auto_draft(
            user_id, req.project_id, req.section_type
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="project_not_found") from exc
    except LLMServiceError as exc:
        logger.exception("workshop manuscript auto-draft LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


# ── F13-S7 6.2 Savunma Formatı — defense_session 3 endpoint ────────────────


@router.post("/defense/session", response_model=DefenseSession)
async def defense_session_upsert(
    req: DefenseSessionUpsert, request: Request
) -> DefenseSession:
    """6.2 — oturum yarat veya güncelle (jury_size, jury_members, vb)."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await defense_service.upsert_session(user_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/defense/generate-questions", response_model=GenerateQuestionsResponse
)
async def defense_generate_questions(
    req: GenerateQuestionsRequest, request: Request
) -> GenerateQuestionsResponse:
    """6.2 — Gemini Pro: jüri üyesi başına 8-12 soru (Stanford-style)."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await defense_service.generate_questions(
            user_id, req.session_id, req.jury_member_index
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IndexError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop defense generate-questions LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.get("/defense/suggest-jury", response_model=SuggestJuryResponse)
async def defense_suggest_jury(
    request: Request,
    project_id: UUID = Query(...),
    field: str = Query(..., min_length=1, max_length=200),
) -> SuggestJuryResponse:
    """6.2 — havuzdan field (theme_id) ile en aktif 5 yazar önerisi."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await defense_service.suggest_jury(user_id, project_id, field)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── F13-S8 6.3 Bireysel Kontrol — checklist + journal + feedback 4 endpoint ──


@router.get("/checklist", response_model=ChecklistResponseModel)
async def workshop_checklist(
    request: Request,
    doc_type: DocType = Query(...),
    lang: ChecklistLang = Query("tr"),
) -> ChecklistResponseModel:
    """6.3 — engine/checklist/{doc_type}_{lang}.json statik yükle."""
    _user_id(request)
    try:
        return individual_service.load_checklist(doc_type, lang)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/individual-check", response_model=IndividualCheckResponse)
async def workshop_individual_check(
    req: IndividualCheckUpsert,
    request: Request,
    doc_type: DocType = Query(...),
    lang: ChecklistLang = Query("tr"),
) -> IndividualCheckResponse:
    """6.3 — tek cevabı defense_session.individual_check'e merge et + kritik kapı."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await individual_service.upsert_individual_check(
            user_id,
            req.session_id,
            req.checklist_id,
            req.item_id,
            req.response,
            doc_type,
            lang,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/journal-suggest", response_model=JournalSuggestResponse)
async def workshop_journal_suggest(
    request: Request,
    project_id: UUID = Query(...),
    field: str = Query("", max_length=200),
) -> JournalSuggestResponse:
    """6.3 — V1 fallback: dim_journal yok → engine/journals/seed.json."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await individual_service.suggest_journals(user_id, project_id, field)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/personal-feedback", response_model=PersonalFeedbackResponse)
async def workshop_personal_feedback(
    req: PersonalFeedbackRequest, request: Request
) -> PersonalFeedbackResponse:
    """6.3 — Flash 1 paragraf kişisel geri-bildirim (hayır/yapamadım maddelerden)."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await individual_service.generate_personal_feedback(
            user_id,
            req.project_id,
            req.session_id,
            req.doc_type,
            req.lang,
            req.manuscript_summary,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop personal-feedback LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


# ── F13-S9 6.4 Dergi Simülasyonu — 3-persona + statcheck + kalibrasyon ─────


@router.post("/defense/reviewer-3persona", response_model=Reviewer3PersonaResponse)
async def workshop_reviewer_3persona(
    req: Reviewer3PersonaRequest, request: Request
) -> Reviewer3PersonaResponse:
    """6.4 — Şüpheci/Sempatik/Yöntemci paralel Flash hakem (chain depth max 2)."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await journal_sim_service.reviewer_3persona(user_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop reviewer-3persona LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.post("/defense/statcheck", response_model=StatcheckResponse)
async def workshop_statcheck(
    req: StatcheckRequest, request: Request
) -> StatcheckResponse:
    """6.4 — Nuijten regex + scipy ile p-değer tutarlılık (green/yellow/red)."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await journal_sim_service.statcheck_run(user_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/defense/journal-calibration", response_model=JournalCalibrationResponse)
async def workshop_journal_calibration(
    request: Request,
    session_id: UUID = Query(...),
    journal_id: str | None = Query(default=None, max_length=200),
) -> JournalCalibrationResponse:
    """6.4 — review_distribution.json + verdict tahmini (statcheck red ile band düşür)."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await journal_sim_service.journal_calibration(
            user_id, session_id, journal_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── F13-S10 6.5 Jüri Simülasyonu — 5 endpoint ──────────────────────────────


@router.post("/defense/jury-question", response_model=JuryQuestionResponse)
async def workshop_jury_question(
    req: JuryQuestionRequest, request: Request
) -> JuryQuestionResponse:
    """6.5 — 5 persona (canli/anti_tez/yontemci/dis_disiplin/pratisyen) paralel Flash."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await jury_sim_service.jury_question(user_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop jury-question LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.post("/defense/hyde-fanout-rerank", response_model=HydeFanoutResponse)
async def workshop_hyde_fanout_rerank(
    req: HydeFanoutRequest, request: Request
) -> HydeFanoutResponse:
    """6.5 — HyDE 5 hipotetik + Pinecone fanout (V1 graceful) + missing concept."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await jury_sim_service.hyde_fanout_rerank(user_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop hyde-fanout-rerank LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.post("/defense/answer-score", response_model=AnswerScoreResponse)
async def workshop_answer_score(
    req: AnswerScoreRequest, request: Request
) -> AnswerScoreResponse:
    """6.5 — evidence + depth + clarity rubric → jüri tepkisi (V1 token-overlap)."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await jury_sim_service.answer_score(user_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/defense/consistency-check", response_model=ConsistencyCheckResponse)
async def workshop_consistency_check(
    req: ConsistencyCheckRequest, request: Request
) -> ConsistencyCheckResponse:
    """6.5 — Flash second-pass tüm cevapları semantik çelişki tarar."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await jury_sim_service.consistency_check(user_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("workshop consistency-check LLM call failed")
        raise HTTPException(status_code=503, detail="llm_unavailable") from exc


@router.post("/defense/jury-decision-band", response_model=JuryDecisionBandResponse)
async def workshop_jury_decision_band(
    req: JuryDecisionBandRequest, request: Request
) -> JuryDecisionBandResponse:
    """6.5 — avg weighted_score - 0.05·conflict_count → accept/minor/major/reject."""
    user_id = _user_id(request)
    _ensure_supabase()
    try:
        return await jury_sim_service.jury_decision_band(user_id, req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
