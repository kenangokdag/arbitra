"""F14 Hakemlik /api/review/* — async peer-review uçları.

Akış: POST /upload (belge) → iş oluşur (queued) + arka-planda boru hattı dispatch
→ FE GET /{job_id}/status'u poll eder (dönen çark) → done olunca GET /{job_id}/report.

Auth: AuthMiddleware request.state.user_id zorunlu (router-level tier_gate).
Admin uçları: settings.ADMIN_USER_IDS allowlist (prod'da zorunlu, dev'de bypass).
Hakemlik ≠ jüri → ayrı namespace (R-6); defense/workshop'a bağlanmaz.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)

from api.config import get_settings
from api.middleware.tier_gate import tier_gate
from api.models.review import (
    ReviewReportResponse,
    ReviewStatusResponse,
    ReviewUploadResponse,
    VersionComparisonResponse,
)
from api.services import (
    consent_gate,
    report_export_service,
    review_service,
    version_comparison_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/review",
    tags=["review"],
    dependencies=[Depends(tier_gate)],
)

_MAX_UPLOAD_BYTES = 30 * 1024 * 1024  # 30 MB — güvenlik (R-4)
_EXT_KIND: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".tex": "latex",
    ".zip": "zip",
}


def _user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="missing_user_id")
    return str(uid)


def _require_admin(request: Request) -> str:
    uid = _user_id(request)
    settings = get_settings()
    allow = {x.strip() for x in settings.ADMIN_USER_IDS.split(",") if x.strip()}
    if allow:
        if uid not in allow:
            raise HTTPException(status_code=403, detail="admin_only")
    elif settings.APP_ENV == "production":
        # Prod'da allowlist boşsa kapı KAPALI (fail-closed, R-4).
        raise HTTPException(status_code=403, detail="admin_allowlist_unset")
    return uid


def _content_key(data: bytes, *parts: str) -> str:
    """İçerik + config'ten deterministik idempotency anahtarı (BE-1).

    Aynı dosya + aynı ayarlarla tekrar yükleme → aynı anahtar → aynı iş.
    Farklı config (mod/dil/gizlilik) → farklı anahtar (haklı olarak yeni iş)."""
    h = hashlib.sha256()
    h.update(data)
    for p in parts:
        h.update(b"\x00")
        h.update(p.encode("utf-8"))
    return h.hexdigest()


def _detect_kind(filename: str) -> str:
    lower = filename.lower()
    for ext, kind in _EXT_KIND.items():
        if lower.endswith(ext):
            return kind
    raise HTTPException(
        status_code=400,
        detail="unsupported_file_type (Word/PDF/LaTeX/ZIP bekleniyor)",
    )


# SEC-3 / P01-T02: içerik-tipi (magic-byte) doğrulaması. Uzantı YALANCI olabilir
# (yürütülebilir/HTML uzantısı .pdf'e değiştirilmiş) → ham baytlar imzayla
# karşılaştırılır. Savunma derinliği: parser'a güvenip "fail later" beklemeyiz.
_PDF_MAGIC = (b"%PDF",)
_ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")  # zip local/empty/spanned
_OLE_MAGIC = (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",)  # legacy .doc (OLE2)


def _validate_magic(kind: str, data: bytes) -> None:
    """Baytların türle tutarlılığını doğrula; uyuşmazlıkta 400 (sessiz kabul YOK).

    - pdf  → %PDF imzası
    - docx → ZIP imzası (OOXML bir zip) veya OLE2 (eski .doc, parser sonra dürüstçe
             reddeder ama gate'te de geçer)
    - zip  → ZIP imzası
    - latex→ metin: ilk blokta NUL bayt yok + utf-8/latin-1 çözülebilir (ikili değil)
    """
    head = data[:512]
    if kind == "pdf":
        ok = any(head.startswith(m) for m in _PDF_MAGIC)
    elif kind == "docx":
        ok = any(head.startswith(m) for m in (*_ZIP_MAGIC, *_OLE_MAGIC))
    elif kind == "zip":
        ok = any(head.startswith(m) for m in _ZIP_MAGIC)
    elif kind == "latex":
        # Metin dosyası: ikili içerik (NUL) reddedilir; çözülemiyorsa ikilidir.
        if b"\x00" in head:
            ok = False
        else:
            try:
                head.decode("utf-8")
                ok = True
            except UnicodeDecodeError:
                try:
                    head.decode("latin-1")
                    ok = True
                except UnicodeDecodeError:
                    ok = False
    else:  # ulaşılmaz — _detect_kind yalnız bilinen türleri döndürür
        ok = False
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="file_content_mismatch (dosya içeriği uzantıyla uyuşmuyor)",
        )


@router.post("/upload", response_model=ReviewUploadResponse)
async def upload_review(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    mode: Literal["author", "editor"] = Form("author"),
    language: Literal["tr", "en"] = Form("en"),
    # SEC-2 / P01-T03 gizlilik alanları (opsiyonel; güvenli default consent_gate'te).
    is_author: bool = Form(True),
    confidentiality_mode: Literal["author_owned", "reviewer_confidential"] | None = Form(None),
    external_ai_consent: Literal["allowed", "blocked", "requires_private_mode"] | None = Form(None),
    retention_days: int = Form(30),
    # VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17: kullanıcının BİLİNÇLİ seçtiği
    # önceki versiyon (otomatik/sessiz eşleştirme YOK).
    parent_job_id: UUID | None = Form(None),
) -> ReviewUploadResponse:
    user_id = _user_id(request)
    filename = file.filename or "manuscript"
    kind = _detect_kind(filename)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty_file")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file_too_large (max 30MB)")
    # SEC-3: uzantı imzasıyla içerik tutarlı mı (disguise edilmiş dosya reddedilir).
    _validate_magic(kind, data)

    # Gizlilik + external-AI consent çözümü (editor/confidential → default blocked).
    privacy = consent_gate.resolve_privacy(
        mode=mode,
        is_author=is_author,
        confidentiality_mode=confidentiality_mode,
        external_ai_consent=external_ai_consent,
        retention_days=retention_days,
    )

    # BE-1 idempotency: aynı içerik+config → aynı iş. Çift-tık / FE retry / ağ
    # tekrarı yeni iş AÇMAZ, boru hattını yeniden ÇALIŞTIRMAZ (çift LLM/quota yok).
    # İstemci Idempotency-Key verirse onu kullan; yoksa içerik hash'inden türet.
    client_key = request.headers.get("Idempotency-Key")
    idempotency_key = client_key or _content_key(
        data, mode, language, privacy.confidentiality_mode, privacy.external_ai_consent
    )

    try:
        job_id, is_new = await review_service.create_and_dispatch(
            user_id=user_id,
            mode=mode,
            language=language,
            data=data,
            kind=kind,
            filename=filename,
            privacy=privacy,
            idempotency_key=idempotency_key,
            parent_job_id=parent_job_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="parent_job_not_found") from exc
    # Yalnız YENİ iş için boru hattını başlat — idempotent tekrarda re-dispatch YOK.
    if is_new:
        background.add_task(
            review_service.run_pipeline,
            job_id,
            data=data,
            kind=kind,
            filename=filename,
            mode=mode,
            language=language,
            privacy=privacy,
        )
    return ReviewUploadResponse(job_id=job_id, status="queued")


@router.get("/jobs")
async def my_jobs(request: Request, limit: int = 20) -> dict[str, Any]:
    """Kullanıcının KENDİ job'ları — VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17 §3.3,
    upload sayfasındaki 'önceki versiyon' seçici için. /admin/jobs (aşağıda,
    admin-only) ile AYNI response şekli, farklı segment derinliği — path
    çakışması yok, doğrulandı (plan §2.5)."""
    user_id = _user_id(request)
    return {"jobs": await review_service.list_user_jobs(user_id, limit=limit)}


@router.get("/admin/jobs")
async def admin_jobs(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return {"jobs": await review_service.admin_list_jobs()}


@router.get("/admin/stats")
async def admin_stats(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return await review_service.admin_stats()


@router.post("/admin/sweep-stale")
async def admin_sweep_stale(
    request: Request, older_than_minutes: int = 30
) -> dict[str, Any]:
    """BE-1: yarıda kalmış (deploy/restart kurbanı) işleri DÜRÜST failed yap.

    Ops/cron tetikler → kullanıcı sonsuz dönen çark yerine dürüst hata görür.
    Gerçek resume (object storage) ayrı; bu, orphan'ı görünür kılan emniyet kapağıdır."""
    _require_admin(request)
    swept = await review_service.mark_stale_jobs_failed(older_than_minutes)
    return {"swept": len(swept), "job_ids": swept}


@router.get("/{job_id}/status", response_model=ReviewStatusResponse)
async def review_status(request: Request, job_id: UUID) -> ReviewStatusResponse:
    user_id = _user_id(request)
    try:
        return await review_service.get_status(user_id, job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="job_not_found") from exc


@router.get("/{job_id}/report", response_model=ReviewReportResponse)
async def review_report(request: Request, job_id: UUID) -> ReviewReportResponse:
    user_id = _user_id(request)
    try:
        report = await review_service.get_report(user_id, job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="report_not_ready") from exc
    return ReviewReportResponse(job_id=job_id, report=report)


@router.get("/{job_id}/comparison", response_model=VersionComparisonResponse)
async def review_comparison(request: Request, job_id: UUID) -> VersionComparisonResponse:
    """VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17 §2.5 — deterministik versiyon özeti.

    parent_job_id set edilmemişse (ilk yükleme) comparison=None döner — bu bir
    HATA DEĞİL, normal durum (404 fırlatılmaz). get_report() İKİ KEZ çağrılır
    (mevcut, chat.py'nin de kullandığı fonksiyon REUSE edilir — imzasına
    dokunulmadı, plan §2.4)."""
    user_id = _user_id(request)
    try:
        parent_job_id = await review_service.get_parent_job_id(user_id, job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="job_not_found") from exc

    if parent_job_id is None:
        return VersionComparisonResponse(job_id=job_id, comparison=None)

    try:
        current_report = await review_service.get_report(user_id, job_id)
        previous_report = await review_service.get_report(user_id, parent_job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="report_not_ready") from exc

    comparison = version_comparison_service.build_version_comparison(
        parent_job_id, previous_report, current_report
    )
    return VersionComparisonResponse(job_id=job_id, comparison=comparison)


@router.get("/{job_id}/export.docx")
async def review_export_docx(request: Request, job_id: UUID) -> Response:
    """RAPOR_DOCX_EXPORT_2026-08-16: hakem raporunu .docx olarak indir.

    Sahip-kapsamlı (BOLA-güvenli) — /report ile BİREBİR aynı desen
    (review_service.get_report, review.py:248-255). tier_gate router seviyesinde
    zaten uygulanıyor (satır 40-44), burada ekstra kod gerekmiyor.
    """
    user_id = _user_id(request)
    try:
        report = await review_service.get_report(user_id, job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="report_not_ready") from exc

    docx_bytes = report_export_service.build_docx(report, job_id)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="arbitra-rapor-{job_id}.docx"'
        },
    )


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_review_job(request: Request, job_id: UUID) -> None:
    """KVKK tekil silme: kullanıcının kendi hakemlik işini kalıcı sil.

    Sahip-kapsamlı (BOLA-güvenli): eşleşmezse 404 (başkasının işi ifşa edilmez).
    Başarıda 204. Mantık review_service.delete_job → account_deletion_service."""
    user_id = _user_id(request)
    deleted = await review_service.delete_job(user_id, job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="job_not_found")
