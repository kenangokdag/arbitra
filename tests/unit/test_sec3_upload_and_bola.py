"""SEC-3 / P01-T02 — dosya içerik doğrulaması + BOLA sahiplik kapısı.

İki güvenlik vaadi backend kanıtı:
  1. magic-byte: uzantısı değiştirilmiş (disguise) dosya gate'te reddedilir.
  2. BOLA: kullanıcı B, kullanıcı A'nın işini status/report ile OKUYAMAZ
     (sahiplik service sınırında zorlanır → LookupError → route 404).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.routes.review import _validate_magic

# --- magic-byte doğrulaması -------------------------------------------------

# Gerçek imza önekleri (icat değil — dosya format spesifikasyonu).
_PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
_ZIP = b"PK\x03\x04\x14\x00\x00\x00"  # docx/zip ortak (OOXML bir zip)
_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 8  # eski .doc
_ELF = b"\x7fELF\x02\x01\x01\x00"  # linux yürütülebilir — hiçbir türe uymamalı
_HTML = b"<!DOCTYPE html><html><body>phish</body></html>"


def test_pdf_magic_accepts_real_pdf():
    _validate_magic("pdf", _PDF)  # raise etmemeli


@pytest.mark.parametrize("disguised", [_ELF, _HTML, _ZIP, _OLE])
def test_pdf_magic_rejects_non_pdf(disguised):
    with pytest.raises(HTTPException) as ei:
        _validate_magic("pdf", disguised)
    assert ei.value.status_code == 400
    assert "mismatch" in ei.value.detail


def test_docx_accepts_zip_and_ole():
    _validate_magic("docx", _ZIP)
    _validate_magic("docx", _OLE)


def test_docx_rejects_executable():
    with pytest.raises(HTTPException):
        _validate_magic("docx", _ELF)


def test_zip_accepts_zip_rejects_pdf():
    _validate_magic("zip", _ZIP)
    with pytest.raises(HTTPException):
        _validate_magic("zip", _PDF)


def test_latex_accepts_text_rejects_binary():
    _validate_magic("latex", b"\\documentclass{article}\\begin{document}hi")
    with pytest.raises(HTTPException):
        _validate_magic("latex", _ELF)  # NUL içerir → ikili → reddedilir


# --- BOLA: başka kullanıcının işine erişim engellenir -----------------------


@pytest.mark.asyncio
async def test_bola_status_other_user_cannot_read(monkeypatch):
    """A'nın işini B isteyince → LookupError (route bunu 404'e çevirir)."""
    from api.services import review_service as svc

    job_id = uuid4()

    async def _row_owned_by_a(jid):
        return {"job_id": str(job_id), "user_id": "user-A", "status": "done",
                "progress": 1.0, "step_label": "ok"}

    monkeypatch.setattr(svc, "_fetch_job", _row_owned_by_a)

    # Sahibi (A) okuyabilir
    res = await svc.get_status("user-A", job_id)
    assert res.status == "done"

    # Yabancı (B) okuyamaz
    with pytest.raises(LookupError):
        await svc.get_status("user-B", job_id)


@pytest.mark.asyncio
async def test_bola_report_other_user_cannot_read(monkeypatch):
    from api.services import review_service as svc

    job_id = uuid4()
    report_blob = {
        "mode": "author", "language": "tr",
        "manuscript_meta": {}, "summary": "s", "overall_assessment": "o",
        "verdict": "minor_revision",
        "provenance": {
            "model_used": "m", "persona_version": "v", "engine_version": "v",
            "generated_at": "2026-01-01T00:00:00Z",
        },
    }

    async def _row(jid):
        return {"job_id": str(job_id), "user_id": "owner", "report": report_blob}

    monkeypatch.setattr(svc, "_fetch_job", _row)

    rep = await svc.get_report("owner", job_id)
    assert rep.verdict == "minor_revision"

    with pytest.raises(LookupError):
        await svc.get_report("attacker", job_id)


@pytest.mark.asyncio
async def test_bola_missing_job_is_lookup_error(monkeypatch):
    from api.services import review_service as svc

    async def _none(jid):
        return None

    monkeypatch.setattr(svc, "_fetch_job", _none)

    with pytest.raises(LookupError):
        await svc.get_status("anyone", uuid4())
