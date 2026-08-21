"""F14-S5 Hakemlik async iş runner — uçtan uca boru hattı + kalıcılık.

Akış (her adımda review_job.status + progress güncellenir → FE çarkı, R-2):
  parsing → checking_citations → checking_context → coverage
          → orchestrating → assembling → done   (hata → failed + error)

Sözleşme: api/models/review.py. Motorlar:
  - engine.ingestion.parse_document                 (S1)
  - review_citation_service.resolve_all/check_context/find_coverage_gaps (S2/S3)
  - journal_sim_service._extract_statcheck_results  (statcheck köprüsü, reuse)
  - review_orchestration.run_orchestration          (S4)

Observability (CANON): hata-yutma yok. Boru hattı bilinçli boundary'de
(arka-plan görev) try/except ile sarılır → hata LOGLANIR + review_job.error'a
DÜRÜSTÇE yazılır + status=failed; sessiz pass YOK.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from api.db.supabase_client import get_review_supabase_admin, supabase_call_async
from api.models.journal_sim import StatcheckResult
from api.models.review import (
    EvidencePack,
    Manuscript,
    PrivacyConfig,
    ReviewLang,
    ReviewMode,
    ReviewReport,
    ReviewStage,
    ReviewStageState,
    ReviewStatusResponse,
    StatFinding,
)
from api.services import consent_gate, review_citation_service, review_orchestration
from api.services.journal_sim_service import (
    _extract_statcheck_results,
    _load_statcheck_config,
)
from api.services.openalex_polite import OpenAlexError
from engine.academic import assessment as academic_assessment
from engine.academic import classifier as academic_classifier
from engine.academic import council as academic_council
from engine.academic import report_synthesis
from engine.academic.anchoring import verify_finding_anchors
from engine.academic.assessment import assess_manuscript
from engine.academic.rubric_registry import select_rubric
from engine.academic.security_findings import security_finding_from_warnings
from engine.providers.openalex import OpenAlexProvider, _map_error_status

logger = logging.getLogger(__name__)

_TABLE = "review_job"

# status → (progress, insan-dili etiket) — son-kullanıcı dili (ham kod değil).
_STEP: dict[str, tuple[float, str]] = {
    "queued": (0.0, "Sıraya alındı"),
    "parsing": (0.1, "Belge okunuyor"),
    "checking_citations": (0.35, "Atıflar doğrulanıyor"),
    "checking_context": (0.55, "Atıf bağlamı denetleniyor"),
    "coverage": (0.7, "Alan kapsaması taranıyor"),
    "orchestrating": (0.8, "Hakem paneli çalışıyor"),
    "assembling": (0.95, "Rapor derleniyor"),
    "done": (1.0, "Tamamlandı"),
    "failed": (1.0, "Hata oluştu"),
}


# --- G4: per-stage durum izleyici (FE StageTimeline görünürlüğü) ------------
# run_pipeline'ın GERÇEKTEN koştuğu fazları durable ReviewStage sözlüğüne eşler.
# Sözlük (api/models/review.py:496) aspirasyonel 12 stage taşır; biz YALNIZ
# gerçekten icra edilen 7 fazı emit ederiz (uydurma stage YOK). Eşleme:
#   parsing              → parse_document
#   classify             → classify
#   checking_citations   → resolve_references
#   checking_context + coverage → retrieve_evidence (ikisi de kanıt toplama; tek stage)
#   orchestrating(assess)→ run_academic_engines
#   orchestrating(council)→ run_reviewer_council (gizli/rıza-yok dosyada SKIPPED)
#   assembling           → build_report
# Not: file_security_scan/extract_references/select_guidelines/editor_synthesis/
# prepare_exports henüz AYRI faz değil → emit edilmez (boş/sahte stage göstermeyiz).
_PIPELINE_STAGES: tuple[ReviewStage, ...] = (
    "parse_document",
    "classify",
    "resolve_references",
    "retrieve_evidence",
    "run_academic_engines",
    "run_reviewer_council",
    "build_report",
)


class _StageTracker:
    """Pipeline fazlarını ReviewStageState[] olarak tutar (FE timeline kaynağı).

    Tüm stage'ler 'queued' başlar; pipeline ilerledikçe running→completed/degraded/
    skipped/failed olur. dump() → review_job.stages jsonb'a yazılacak deterministik
    liste (her zaman _PIPELINE_STAGES sırasında)."""

    def __init__(self) -> None:
        self._stages: dict[str, ReviewStageState] = {
            s: ReviewStageState(stage=s, status="queued") for s in _PIPELINE_STAGES
        }

    def start(self, stage: ReviewStage) -> None:
        st = self._stages[stage]
        st.status = "running"
        st.started_at = datetime.now(UTC)

    def complete(self, stage: ReviewStage, summary: str | None = None) -> None:
        st = self._stages[stage]
        st.status = "completed"
        st.progress = 1.0
        st.completed_at = datetime.now(UTC)
        if summary is not None:
            st.summary = summary

    def degrade(
        self, stage: ReviewStage, reason: str, summary: str | None = None
    ) -> None:
        st = self._stages[stage]
        st.status = "degraded"
        st.completed_at = datetime.now(UTC)
        st.degraded_reason = reason
        if summary is not None:
            st.summary = summary

    def skip(self, stage: ReviewStage, reason: str) -> None:
        st = self._stages[stage]
        st.status = "skipped"
        st.degraded_reason = reason

    def fail_running(self, error_code: str) -> None:
        """Hata anında: henüz 'running' olan stage'i failed işaretle (dürüst)."""
        for s in _PIPELINE_STAGES:
            st = self._stages[s]
            if st.status == "running":
                st.status = "failed"
                st.error_code = error_code
                st.completed_at = datetime.now(UTC)

    def dump(self) -> list[dict[str, Any]]:
        return [self._stages[s].model_dump(mode="json") for s in _PIPELINE_STAGES]


# --- kalıcılık yardımcıları -------------------------------------------------


async def _insert_job(
    user_id: str,
    mode: ReviewMode,
    language: ReviewLang,
    source_name: str,
    source_kind: str,
    privacy: PrivacyConfig | None = None,
    idempotency_key: str | None = None,
    parent_job_id: UUID | None = None,
) -> UUID:
    db = get_review_supabase_admin()
    progress, label = _STEP["queued"]
    row: dict[str, Any] = {
        "user_id": user_id,
        "mode": mode,
        "language": language,
        "status": "queued",
        "progress": progress,
        "step_label": label,
        "source_name": source_name,
        "source_kind": source_kind,
    }
    if privacy is not None:
        row["privacy"] = privacy.model_dump(mode="json")
    if idempotency_key is not None:
        row["idempotency_key"] = idempotency_key
    if parent_job_id is not None:
        row["parent_job_id"] = str(parent_job_id)

    # KVKK retention eşiği (migration 0044 + UI sözü: review/page.tsx "bu süre
    # sonunda yüklenen dosya silinir"). Cron review_retention_delete_expired
    # delete_after < now() satırlarını siler. Default 30g (PrivacyConfig.retention_days).
    retention_days = privacy.retention_days if privacy is not None else 30
    row["delete_after"] = (
        datetime.now(UTC) + timedelta(days=retention_days)
    ).isoformat()

    def _q() -> Any:
        return db.table(_TABLE).insert(row).execute()

    resp = await supabase_call_async(_q)
    data = cast(list[dict[str, Any]], resp.data or [])
    if not data:
        raise RuntimeError("review_job insert returned no row")
    return UUID(str(data[0]["job_id"]))


async def _find_by_idempotency_key(user_id: str, key: str) -> UUID | None:
    """Aynı (user_id, key) ile var olan job — duplicate enqueue koruması (BE-1).

    DB tarafında idx_review_job_idempotency UNIQUE (migration 0042) bütünlüğü
    GARANTİ eder; bu ön-kontrol yaygın retry/çift-tık halini pürüzsüzleştirir."""
    db = get_review_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_TABLE)
            .select("job_id")
            .eq("user_id", user_id)
            .eq("idempotency_key", key)
            .limit(1)
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = cast(list[dict[str, Any]], resp.data or [])
    return UUID(str(rows[0]["job_id"])) if rows else None


async def _update(job_id: UUID, **fields: Any) -> None:
    db = get_review_supabase_admin()
    fields["updated_at"] = datetime.now(UTC).isoformat()

    def _q() -> Any:
        return db.table(_TABLE).update(fields).eq("job_id", str(job_id)).execute()

    await supabase_call_async(_q)


async def _set_step(job_id: UUID, status: str, **extra: Any) -> None:
    progress, label = _STEP[status]
    await _update(job_id, status=status, progress=progress, step_label=label, **extra)


async def _save_stages(job_id: UUID, tracker: _StageTracker) -> None:
    """G4: per-stage durumu review_job.stages jsonb'a yaz (FE timeline kaynağı)."""
    await _update(job_id, stages=tracker.dump())


async def _fetch_job(job_id: UUID) -> dict[str, Any] | None:
    db = get_review_supabase_admin()

    def _q() -> Any:
        return db.table(_TABLE).select("*").eq("job_id", str(job_id)).limit(1).execute()

    resp = await supabase_call_async(_q)
    rows = cast(list[dict[str, Any]], resp.data or [])
    return rows[0] if rows else None


# --- statcheck köprüsü ------------------------------------------------------


def _stat_findings(full_text: str) -> list[StatFinding]:
    """Mevcut Nuijten statcheck motorunu StatFinding'e köprüle (reuse)."""
    cfg = _load_statcheck_config()
    raw: list[StatcheckResult] = _extract_statcheck_results(full_text, cfg)
    return [
        StatFinding(
            test_type=str(r.test_type),
            reported_p=r.reported_p,
            computed_p=r.computed_p,
            status=cast(Any, r.status),
            match_text=r.match_text,
        )
        for r in raw
    ]


# --- public: iş oluştur + çalıştır ------------------------------------------


async def create_and_dispatch(
    *,
    user_id: str,
    mode: ReviewMode,
    language: ReviewLang,
    data: bytes,
    kind: str,
    filename: str,
    privacy: PrivacyConfig | None = None,
    idempotency_key: str | None = None,
    parent_job_id: UUID | None = None,
) -> tuple[UUID, bool]:
    """İşi oluştur (queued) → (job_id, is_new) döndür.

    BE-1 idempotency: `idempotency_key` verilmişse aynı (user_id, key) ile var
    olan iş varsa O job_id + is_new=False döner (yeni iş AÇILMAZ, boru hattı
    yeniden DISPATCH EDİLMEZ → çift quota/LLM maliyeti yok). Çağıran is_new=False
    ise background.add_task ÇAĞIRMAMALI.

    parent_job_id (VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17): kullanıcının BİLİNÇLİ
    seçtiği önceki versiyon. BOLA-safe — insert'ten ÖNCE sahiplik doğrulanır,
    aksi halde LookupError (route 404'e çevirir, /report ile TUTARLI desen)."""
    if parent_job_id is not None:
        parent_row = await _fetch_job(parent_job_id)
        if not parent_row or parent_row.get("user_id") != user_id:
            raise LookupError("parent job not found")
    if idempotency_key is not None:
        existing = await _find_by_idempotency_key(user_id, idempotency_key)
        if existing is not None:
            logger.info(
                "idempotent hit: user=%s key=%s → existing job %s (no re-dispatch)",
                user_id, idempotency_key, existing,
            )
            return existing, False
    try:
        job_id = await _insert_job(
            user_id, mode, language, filename, kind, privacy, idempotency_key,
            parent_job_id,
        )
    except Exception:
        # TOCTOU yarışı: ön-kontrol ile insert arasında eşzamanlı ikinci submit
        # aynı satırı yazmış olabilir → DB unique index (idx_review_job_idempotency,
        # 0042) insert'i reddeder. Bu durumda 500 fırlatmak yerine var olan işi
        # dürüstçe döndür. Yarış DEĞİLSE (gerçek hata) → yeniden fırlat (yutma yok).
        if idempotency_key is not None:
            existing = await _find_by_idempotency_key(user_id, idempotency_key)
            if existing is not None:
                logger.info(
                    "idempotent race resolved: user=%s key=%s → existing job %s",
                    user_id, idempotency_key, existing,
                )
                return existing, False
        raise
    return job_id, True


async def run_pipeline(
    job_id: UUID,
    *,
    data: bytes,
    kind: str,
    filename: str,
    mode: ReviewMode,
    language: ReviewLang,
    privacy: PrivacyConfig | None = None,
) -> None:
    """Uçtan uca boru hattı. Hata → failed + error (yutma yok).

    SEC-2: privacy external AI'yi engelliyorsa (gizli dosya, rıza yok) LLM
    orkestrasyonu ATLANIR → deterministik-only degraded rapor (consent_gate)."""
    # Lazy import: ingestion ağır/opsiyonel bağımlılıklar (pymupdf/docx) içerir;
    # modül yükleme servisi düşürmesin.
    from engine.ingestion import parse_document

    tracker = _StageTracker()
    try:
        await _set_step(job_id, "parsing")
        tracker.start("parse_document")
        await _save_stages(job_id, tracker)
        manuscript: Manuscript = parse_document(data, cast(Any, kind), filename)
        await _update(job_id, manuscript=manuscript.model_dump(mode="json"))
        tracker.complete("parse_document")
        await _save_stages(job_id, tracker)

        # P03-T01/T02: belge + çalışma türü sınıflandırma (parse SONRASI, atıf ÖNCESİ).
        # SEC-2: external AI engelliyse classifier içerik göndermez → dürüst unknown.
        # NOT: ayrı bir flat JobStatus EKLENMEZ — review_job.status CHECK constraint'i
        # (migration 0041) bunu reddeder. Durable per-stage 'classify' takibi 'stages'
        # jsonb'da (BE-1) yapılır. Burada sonuç 'classification' kolonuna + rapora yazılır.
        tracker.start("classify")
        await _save_stages(job_id, tracker)
        classify_allowed = consent_gate.external_ai_allowed(privacy)
        classification = await academic_classifier.classify_document(
            manuscript, allow_external_ai=classify_allowed
        )
        await _update(
            job_id,
            classification=classification.model_dump(mode="json"),
            step_label="Belge ve çalışma türü belirlendi",
        )
        tracker.complete(
            "classify",
            summary=f"{classification.effective_document_type} / "
            f"{classification.effective_study_design}",
        )
        await _save_stages(job_id, tracker)

        # FAZ D (BE-2): OpenAlex kullanımı ProviderSnapshot olarak provenance'a
        # GÖRÜNÜR kaydedilir (evidence_provider_spec.md §ProviderSnapshot). Çözüm
        # mantığı (kron-mücevher) DEĞİŞMEZ — snapshot'lar mevcut çağrıların ETRAFINA
        # eklenir; tam Protocol-routing 2. provider eklenince yapılacak (ertelendi).
        provider = OpenAlexProvider()
        provider_snapshots = []

        await _set_step(job_id, "checking_citations")
        tracker.start("resolve_references")
        await _save_stages(job_id, tracker)
        degraded_features: list[str] = []
        resolved_refs, integrity = await review_citation_service.resolve_all(
            manuscript.references
        )
        # §41 (2026-08-12): resolver ağ hatasını dürüstçe not_found_in_index'e
        # düşürür (hiç raise etmez) AMA artık SESSİZ değil — provider_errors>0
        # ise stage GÖRÜNÜR 'degraded' (find_coverage_gaps ile aynı disiplin);
        # per-referans çözüm sonucu CitationIntegritySummary + ParsedReference.
        # status/resolution_degraded taşır.
        if integrity.provider_errors:
            degraded_features.append(
                f"citations:openalex_resolution_failed:{integrity.provider_errors}"
            )
        provider_snapshots.append(
            provider.build_snapshot(
                endpoint="resolve_references",
                query="|".join(
                    sorted((r.doi or r.title or r.raw) for r in resolved_refs)
                ),
                status="degraded" if integrity.provider_errors else "ok",
                result_count=integrity.resolved + integrity.retracted,
                limitations=[
                    "abstract only",
                    "stage-level snapshot; per-reference provider errors are honestly "
                    "downgraded to not_found_in_index inside the resolver",
                ]
                + (
                    [f"{integrity.provider_errors}/{integrity.total} references: "
                     "provider error, not genuine non-match"]
                    if integrity.provider_errors
                    else []
                ),
            )
        )

        if integrity.provider_errors:
            tracker.degrade(
                "resolve_references",
                reason=f"citations:openalex_resolution_failed:{integrity.provider_errors}",
                summary=f"{integrity.resolved}/{integrity.total} çözüldü",
            )
        else:
            tracker.complete(
                "resolve_references",
                summary=f"{integrity.resolved}/{integrity.total} çözüldü",
            )
        await _save_stages(job_id, tracker)

        await _set_step(job_id, "checking_context")
        tracker.start("retrieve_evidence")
        await _save_stages(job_id, tracker)
        context_findings = await review_citation_service.check_context(
            manuscript.in_text_citations, resolved_refs
        )
        provider_snapshots.append(
            provider.build_snapshot(
                endpoint="check_context",
                query="|".join(sorted(c.claim for c in context_findings)) or "(none)",
                status="ok",
                result_count=len(context_findings),
                limitations=["abstract only"],  # bağlam yalnız özetten denetlenir
            )
        )

        await _set_step(job_id, "coverage")
        # §41: bu stage'in KENDİ nedenleri ayrı tutulur — degraded_features
        # (report-wide) resolve_references stage'inin nedenini de taşıyor,
        # onu retrieve_evidence'a yanlış-atfetmemek için (stage sınırı netliği).
        retrieve_evidence_degraded_reasons: list[str] = []
        coverage_query = (manuscript.meta.title or manuscript.meta.abstract or "")[:200]
        try:
            coverage_gaps = await review_citation_service.find_coverage_gaps(
                manuscript.meta, resolved_refs
            )
        except OpenAlexError as exc:
            # BE-2 / P02-T05: sağlayıcı arızası SESSİZ boş-liste değil; GÖRÜNÜR
            # degraded_feature + ProviderSnapshot(status=failed/...) olarak işaretlenir
            # (CANON/observability: hata kaybolmaz). Boru hattı düşmez — kapsama eksik
            # ama rapor üretilir, eksiklik raporda yazar.
            logger.warning(
                "coverage degraded job=%s: OpenAlex unavailable: %s", job_id, exc
            )
            coverage_gaps = []
            degraded_features.append("coverage:openalex_unavailable")
            retrieve_evidence_degraded_reasons.append("coverage:openalex_unavailable")
            _status, _lims = _map_error_status(exc)
            provider_snapshots.append(
                provider.build_snapshot(
                    endpoint="find_coverage_gaps",
                    query=coverage_query,
                    status=_status,
                    limitations=_lims,
                )
            )
        else:
            provider_snapshots.append(
                provider.build_snapshot(
                    endpoint="find_coverage_gaps",
                    query=coverage_query,
                    status="ok",
                    result_count=len(coverage_gaps),
                )
            )

        evidence = EvidencePack(
            citation_integrity=integrity,
            references=resolved_refs,
            context_findings=context_findings,
            coverage_gaps=coverage_gaps,
            stat_findings=_stat_findings(manuscript.full_text),
            degraded_features=degraded_features,
            provider_snapshots=provider_snapshots,
        )
        await _update(job_id, evidence_pack=evidence.model_dump(mode="json"))
        if retrieve_evidence_degraded_reasons:
            # Kanıt toplama KISMİ tamamlandı (örn coverage OpenAlex arızası) →
            # stage 'degraded' + neden GÖRÜNÜR (sessiz 'completed' değil).
            tracker.degrade(
                "retrieve_evidence", reason="; ".join(retrieve_evidence_degraded_reasons)
            )
        else:
            tracker.complete(
                "retrieve_evidence",
                summary=f"{len(context_findings)} bağlam, {len(coverage_gaps)} kapsam boşluğu",
            )
        await _save_stages(job_id, tracker)

        await _set_step(job_id, "orchestrating")
        tracker.start("run_academic_engines")
        await _save_stages(job_id, tracker)
        consent_ok = consent_gate.external_ai_allowed(privacy)

        # FAZ C2: akademik motor (rubrik → assess → anchor doğrulama). Status
        # 'orchestrating' altında kalır (DB 0041 status CHECK yeni durum kabul
        # etmez; step_label ile insan-dili ilerleme verilir, flat status değişmez).
        await _update(job_id, step_label="Akademik motor değerlendiriyor")
        rubric = select_rubric(
            document_type=classification.effective_document_type,
            study_design=classification.effective_study_design,
            # 2026-08-13 (§46): kullanıcı override'ıysa kesin değer (1.0) — confidence
            # kavramı model tahmini için geçerli, insan seçimi için değil.
            study_design_confidence=(
                1.0
                if classification.user_study_design_override
                else classification.study_design_confidence
            ),
            review_mode=mode,
            strictness="standard",
        )
        engine_result = await assess_manuscript(
            manuscript, rubric, evidence, allow_external_ai=consent_ok
        )
        # Motor degradasyonu GÖRÜNÜR: aynı desen (coverage gibi) evidence'a yazılır
        # (CANON/observability: hata/eksik kaybolmaz). Boş = sorun yok.
        if engine_result.degraded:
            evidence.degraded_features.extend(engine_result.degraded)
            await _update(job_id, evidence_pack=evidence.model_dump(mode="json"))

        # FAZ C1: makale-çıpa doğrulaması (deterministik; doğrulanamayan alıntıya
        # dürüst limitation eklenir, bulgu SİLİNMEZ, alıntı UYDURULMAZ).
        anchor_result = verify_finding_anchors(engine_result.findings, manuscript)
        findings = anchor_result.findings

        # ARBITRA_RESEARCH_BRIEF.md Görev A: PDF injection tespiti varsa GARANTİLİ
        # (LLM'e bağımlı olmayan) bir Finding + ActionItem ekle — güvenlik sinyali
        # LLM'in prompt'taki uyarıyı fark edip rapora yazmasına bırakılmaz.
        security_pair = security_finding_from_warnings(manuscript.meta.parse_warnings)
        if security_pair is not None:
            security_finding, security_action = security_pair
            findings = [*findings, security_finding]
            engine_result.action_items = [*engine_result.action_items, security_action]

        if engine_result.degraded:
            tracker.degrade(
                "run_academic_engines", reason="; ".join(engine_result.degraded)
            )
        else:
            tracker.complete(
                "run_academic_engines", summary=f"{len(findings)} bulgu"
            )
        await _save_stages(job_id, tracker)

        if not consent_ok:
            # SEC-2 GATE: gizli dosya + rıza yok → external LLM ÇAĞRILMAZ.
            # assess da allow_external_ai=False ile koştu → bulgu yok + degraded
            # sinyali (yukarıda evidence'a yazıldı). DÜRÜST degraded rapor: v2 sentez
            # alanları BOŞ bırakılır (inceleme yapılmadı → sahte "her şey yolunda"
            # radar/verdict üretilmez; v1 deterministik bütünlük verdict'i taşır).
            logger.info(
                "review job %s: external AI blocked (confidential) → deterministic-only",
                job_id,
            )
            report = consent_gate.degraded_report(
                manuscript, evidence, mode, language, privacy
            )
            report.findings = findings  # dürüst (boş)
            # Hakem paneli external LLM gerektirir → gizli/rıza-yok dosyada KOŞMADI.
            tracker.skip(
                "run_reviewer_council", reason="external_ai_blocked (confidential)"
            )
            await _save_stages(job_id, tracker)
        else:
            tracker.start("run_reviewer_council")
            await _save_stages(job_id, tracker)

            # FAZ C1 deterministik sentez (saf fonksiyonlar — LLM yok, bit-kararlı).
            # 2026-08-07: run_orchestration'dan ÖNCE hesaplanıyor (eskiden sonra
            # hesaplanıyordu) — hem editor'a geçilebilsin (rapor kendiyle
            # çelişmesin) hem de report.verdict/dimension_scores'u override
            # edebilelim (bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md bölüm 26-27,
            # guardian ile 2 tur danışma: goldset'e karşı test edilen skorlar
            # eskiden tamamen çapasız serbest LLM yargısıydı).
            risk_radar = report_synthesis.build_risk_radar(findings, rubric)
            executive_verdict = report_synthesis.build_executive_verdict(
                findings, risk_radar, evidence
            )
            deterministic_summary_block = review_orchestration.serialize_executive_verdict(
                executive_verdict
            )

            report = await review_orchestration.run_orchestration(
                manuscript,
                evidence,
                mode,
                language,
                deterministic_summary_block=deterministic_summary_block,
            )
            report.disclosure = consent_gate.build_disclosure(
                privacy, external_ai_used=True, providers=["llm"]
            )
            report.findings = findings
            report.risk_radar = risk_radar
            report.executive_verdict = executive_verdict

            # DETERMİNİSTİK OVERRIDE: writer/editor'ın kendi serbest verdict/
            # dimension_scores'u yerini, kanıta-dayalı (Finding severity-sayımı)
            # executive_verdict/risk_radar'a bırakır — net-eşleşmeyen 3 boyut
            # (importance/community_value/contextualization) ve risk_radar'ın
            # "değerlendirilmedi" (None) dediği durumlar LLM'in kendi skorunda
            # KALIR (düşürülmez). LLM'in orijinal tahmini denetim izi için loglanır.
            logger.info(
                "review job %s: verdict override llm=%s -> deterministic=%s",
                job_id,
                report.verdict,
                executive_verdict.recommended_decision,
            )
            report.verdict = executive_verdict.recommended_decision
            report.dimension_scores = report_synthesis.apply_deterministic_dimension_scores(
                report.dimension_scores, risk_radar
            )
            # final_score dimension_scores'un ortalaması — override SONRASI
            # yeniden hesaplanmazsa, override ÖNCESİ (tamamen LLM) skorlara göre
            # hesaplanmış kalır, yeni dimension_scores ile TUTARSIZ olurdu.
            report.final_score = review_orchestration.compute_final_score(
                report.dimension_scores
            )

            report.action_plan = report_synthesis.build_action_plan(
                findings, engine_result.action_items
            )
            # G3: rubric beklenen-bölümleri verir → manuscript'te eksik beklenen
            # bölümler status="missing" SectionReview olarak üretilir.
            report.section_reviews = report_synthesis.build_section_reviews(
                findings, manuscript, rubric
            )
            # GERÇEK critic/editör konseyi orchestration'da kuruldu; burada motor
            # bulgularına en-iyi-çaba (dimension overlap) bağlanır.
            report.reviewer_council = academic_council.link_council_to_findings(
                report.reviewer_council, findings
            )
            tracker.complete(
                "run_reviewer_council",
                summary=f"{len(report.reviewer_council)} hakem görüşü",
            )
            await _save_stages(job_id, tracker)

        # P03: sınıflandırmayı HER İKİ yolda da rapora çıpala (rubrik routing kaynağı).
        report.document_classification = classification
        # v2 şema damgası + provenance künyesi (rubric_id + motor/sentez sürümleri).
        report.schema_version = "review_report.v2"
        report.provenance = report.provenance.model_copy(
            update={
                "engine_version": (
                    f"{report.provenance.engine_version}; "
                    f"{academic_assessment.ENGINE_VERSION}; "
                    f"rubric={rubric.rubric_id}; "
                    f"{report_synthesis.SYNTHESIS_VERSION}"
                )
            }
        )

        await _set_step(job_id, "assembling")
        tracker.start("build_report")
        await _save_stages(job_id, tracker)
        await _update(job_id, report=report.model_dump(mode="json"))
        tracker.complete("build_report", summary=f"verdict={report.verdict}")
        await _save_stages(job_id, tracker)

        await _set_step(job_id, "done")
        logger.info("review job %s done (verdict=%s)", job_id, report.verdict)
    except Exception as exc:  # bilinçli boundary — hata saklanır, yutulmaz
        logger.exception("review pipeline failed job=%s", job_id)
        # G4: o an 'running' olan stage'i failed işaretle (FE timeline'da hata GÖRÜNÜR;
        # sessiz çark değil). stages persist DB hatası asıl hatayı maskeLEMESİN.
        tracker.fail_running(f"{type(exc).__name__}")
        try:
            await _save_stages(job_id, tracker)
        except Exception:
            logger.exception("failed to persist failed-stage marker job=%s", job_id)
        await _set_step(job_id, "failed", error=f"{type(exc).__name__}: {exc}")


# --- public: okuma ----------------------------------------------------------


async def get_status(user_id: str, job_id: UUID) -> ReviewStatusResponse:
    row = await _fetch_job(job_id)
    if not row or row.get("user_id") != user_id:
        raise LookupError("review job not found")
    # G4: per-stage durum listesi (FE StageTimeline). Boş/eski satırda [] döner
    # (additive — v1 satırları stages kolonu '[]' default'uyla kırılmaz).
    raw_stages = row.get("stages") or []
    stages = [ReviewStageState.model_validate(s) for s in raw_stages]
    return ReviewStatusResponse(
        job_id=job_id,
        status=cast(Any, row["status"]),
        progress=float(row.get("progress") or 0.0),
        step_label=row.get("step_label") or "",
        error=row.get("error"),
        stages=stages,
    )


async def delete_job(user_id: str, job_id: UUID) -> bool:
    """Tek hakemlik işini sahip-kapsamlı sil (KVKK tekil silme).

    İnce sarmalayıcı: kalıcı silme mantığı account_deletion_service'te (tek kaynak);
    burası yalnız UUID→text köprülemesi yapar. False = sahip değil / yok → route 404.
    """
    from api.services import account_deletion_service

    return await account_deletion_service.delete_review_job(user_id, str(job_id))


async def get_report(user_id: str, job_id: UUID) -> ReviewReport:
    row = await _fetch_job(job_id)
    if not row or row.get("user_id") != user_id:
        raise LookupError("review job not found")
    report = row.get("report")
    if not report:
        raise LookupError("report not ready")
    return ReviewReport.model_validate(report)


async def get_parent_job_id(user_id: str, job_id: UUID) -> UUID | None:
    """VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17 §2.4 — sahip-kapsamlı okuma.

    get_report()'un imzasına BİLİNÇLİ olarak dokunulmadı (chat.py'nin
    _build_report_context'i ona bağımlı, DANISMAN_REPORT_GROUNDING_PERSONA
    planının blast-radius'unu genişletmemek için AYRI, küçük fonksiyon)."""
    row = await _fetch_job(job_id)
    if not row or row.get("user_id") != user_id:
        raise LookupError("review job not found")
    raw = row.get("parent_job_id")
    return UUID(str(raw)) if raw else None


async def list_user_jobs(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Kullanıcının KENDİ job'ları — admin_list_jobs'un (aşağıda) BİREBİR aynı
    deseni, user_id filtresiyle. Upload sayfasındaki 'önceki versiyon' seçici
    için (VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17 §3.3)."""
    db = get_review_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_TABLE)
            .select("job_id, mode, language, status, source_name, source_kind, "
                    "created_at, updated_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    resp = await supabase_call_async(_q)
    return cast(list[dict[str, Any]], resp.data or [])


# --- admin ------------------------------------------------------------------


async def admin_list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    db = get_review_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_TABLE)
            .select("job_id, user_id, mode, language, status, progress, "
                    "source_name, source_kind, created_at, updated_at, error")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    resp = await supabase_call_async(_q)
    return cast(list[dict[str, Any]], resp.data or [])


async def mark_stale_jobs_failed(older_than_minutes: int = 30) -> list[str]:
    """Yarıda kalmış (orphan) işleri DÜRÜST terminal duruma çek (BE-1).

    BackgroundTasks süreç-içi: deploy/restart sırasında çalışan işin görevi ölür
    ama satır non-terminal kalır → kullanıcı SONSUZ dönen çark görür. Bu süpürme
    eşikten eski non-terminal işleri failed("interrupted") yapar → sahte "çalışıyor"
    yerine dürüst hata. (Gerçek RESUME ayrı: upload baytları durable storage'da
    olmalı — object storage kararı park, OPEN_WORK.log.)

    Döndürür: failed'a çekilen job_id listesi. idx_review_job_resume kullanır.
    """
    db = get_review_supabase_admin()
    cutoff = datetime.now(UTC) - timedelta(minutes=older_than_minutes)
    cutoff_iso = cutoff.isoformat()

    def _q_find() -> Any:
        return (
            db.table(_TABLE)
            .select("job_id")
            .not_.in_("status", ["done", "failed"])
            .lt("updated_at", cutoff_iso)
            .execute()
        )

    resp = await supabase_call_async(_q_find)
    rows = cast(list[dict[str, Any]], resp.data or [])
    swept: list[str] = []
    for r in rows:
        jid = UUID(str(r["job_id"]))
        await _set_step(
            jid,
            "failed",
            error="interrupted: process restart or timeout (no durable resume)",
        )
        swept.append(str(jid))
    if swept:
        logger.warning("swept %d stale review jobs → failed: %s", len(swept), swept)
    return swept


async def admin_stats() -> dict[str, Any]:
    """Özet sayılar (durum dağılımı + toplam)."""
    rows = await admin_list_jobs(limit=1000)
    by_status: dict[str, int] = {}
    for r in rows:
        s = str(r.get("status") or "unknown")
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "total": len(rows),
        "by_status": by_status,
        "done": by_status.get("done", 0),
        "failed": by_status.get("failed", 0),
    }
