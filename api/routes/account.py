"""KVKK hesap silme /api/account — ANINDA kalıcı (hard) hesap silme.

  DELETE /api/account — auth ZORUNLU; gövdede bilinçli onay cümlesi şart
    ({"confirm_phrase": "HESABIMI SİL"}). Eşleşmezse 400. Başarıda 200 + makbuz.

Auth: request.state.user_id (AuthMiddleware) — review._user_id helper'ı REUSE eder
(ikinci yetki yolu açılmaz). Geri DÖNÜLMEZ işlem → onay cümlesi zorunlu, sessiz
silme yok. Mantık account_deletion_service'te (tek doğruluk kaynağı).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from api.routes.review import _user_id
from api.services import account_deletion_service

router = APIRouter(prefix="/api/account", tags=["account"])

# Türkçe onay cümlesi — kullanıcı bilinçli olarak yazmalı (yanlışlıkla silme yok).
_CONFIRM_PHRASE = "HESABIMI SİL"


class DeleteAccountRequest(BaseModel):
    """Hesap silme gövdesi. extra='forbid' → beklenmedik alan 422."""

    model_config = ConfigDict(extra="forbid")

    # Default "" → eksik alan da mismatch yoluna düşer (eksik/yanlış → tek tip 400,
    # pydantic 422 değil). Bilinmeyen alan yine extra='forbid' ile 422.
    confirm_phrase: str = ""


@router.delete("")
async def delete_account(request: Request, body: DeleteAccountRequest) -> dict[str, Any]:
    """Hesabı ve tüm kişisel veriyi kalıcı sil. Onay cümlesi şart; başarıda makbuz."""
    user_id = _user_id(request)
    if body.confirm_phrase != _CONFIRM_PHRASE:
        raise HTTPException(status_code=400, detail="confirm_phrase_mismatch")

    receipt = await account_deletion_service.delete_account(user_id)
    # bool int alt-sınıfı → auth_deleted=True'yu sayma; yalnız gerçek satır sayıları.
    deleted_total = sum(
        v for v in receipt.values() if isinstance(v, int) and not isinstance(v, bool)
    )
    return {
        "status": "deleted",
        "rows_deleted": deleted_total,
        "auth_deleted": receipt.get("auth_deleted", False),
        "receipt": receipt,
    }
