"""KVKK "unutulma hakkı" — ANINDA kalıcı (hard) silme. TEK doğruluk kaynağı.

Omer'in açık kararı: soft-delete YOK, grace-period YOK, yeni şema YOK. Veri
silinince geri DÖNMEZ. Bu yüzden silme kapsamı (`_DIRECT_USER_TABLES`) tek yerde,
denetlenebilir bir sabit listede tutulur — yanlış tablo = ya kişisel veri kalır
(hukuki ihlal) ya da GLOBAL/paylaşılan veri silinir (felaket).

Sıra (KESİN):
  1. Tüm VERİ silmeleri (MAIN direct tablolar → projects cascade → REVIEW review_job)
  2. enrichment_log NÖTRLEME (silme DEĞİL; system log satırı korunur, kişi NULL'lanır)
  3. EN SON auth.users (Supabase admin) — veri gittikten sonra; bir hata olursa
     auth hâlâ durur → yeniden çalıştırılabilir, asla "auth silindi ama veri orphan"
     durumu oluşmaz.

Veri silmeleri WHERE user_id ile yapılır → DOĞAL idempotent (yeniden çalışmak güvenli).
Hatalar YUTULMAZ (CANON/observability) — propagate eder; çağıran 500 görür ve retry eder.
"""

from __future__ import annotations

import logging
from typing import Any

from api.db.supabase_client import (
    get_review_supabase_admin,
    get_supabase_admin,
    supabase_call_async,
)

logger = logging.getLogger(__name__)

# --- SİLME KAPSAMI (denetlenebilir tek liste) -------------------------------
# MAIN Supabase'te `WHERE user_id = <id>` ile DOĞRUDAN silinen 14 tablo.
# `projects` silindiğinde 7 alt tablo ON DELETE CASCADE ile OTOMATİK gider
# (project_chat_messages, project_anchor, project_cluster, project_seed_papers,
#  project_progress, manuscript_section, defense_session) — onları AÇIKÇA silmeyiz.
# enrichment_log burada YOK (silinmez, nötrlenir). review_job burada YOK (ayrı
# REVIEW Supabase'te, ayrı çağrı). Doğrulandı: db/migrations (0001/0012/0014/0015/
# 0026/0029/0030/0035) + projects cascade (0016/0019/0025/0027/0028/0029/0030).
_DIRECT_USER_TABLES: tuple[str, ...] = (
    "user_profiles",
    "user_quota",
    "chat_sessions",
    "chat_messages",
    "topic_locks",
    "user_reading_list",
    "user_notes",
    "user_silent_learning_log",
    "user_style_profile",
    "user_profile_fields",
    "user_profile_subfields",
    "project_event",
    "project_completion",
    "projects",  # cascade → 7 alt tablo
)

_REVIEW_TABLE = "review_job"
_ENRICHMENT_LOG = "enrichment_log"


async def _delete_where_user(db: Any, table: str, user_id: str) -> int:
    """`DELETE FROM table WHERE user_id = <id>` → silinen satır sayısı.

    PostgREST delete varsayılan olarak silinen satırları döndürür (bkz
    reading_list_service.delete_item) → len(data) = silinen sayı. Idempotent:
    ikinci çağrıda 0 döner (satır kalmadı), hata değil."""

    def _q() -> Any:
        return db.table(table).delete().eq("user_id", user_id).execute()

    resp = await supabase_call_async(_q)
    return len(resp.data or [])


async def delete_account(user_id: str) -> dict[str, Any]:
    """Bir kullanıcının TÜM kişisel verisini kalıcı sil + auth kaydını kapat.

    Döndürür: makbuz sözlüğü {tablo: silinen_satır, ..., "auth_deleted": bool}.
    Sıra: önce TÜM veri, en SON auth (orphan-auth yerine retry-edilebilir hata).
    Hata yutulmaz — propagate eder.
    """
    main = get_supabase_admin()
    review = get_review_supabase_admin()
    receipt: dict[str, Any] = {}

    # 1) MAIN doğrudan tablolar (projects → cascade 7 alt tablo).
    for table in _DIRECT_USER_TABLES:
        receipt[table] = await _delete_where_user(main, table, user_id)

    # 2) REVIEW Supabase: review_job (user_id TEXT = Supabase sub).
    receipt[_REVIEW_TABLE] = await _delete_where_user(review, _REVIEW_TABLE, user_id)

    # 3) enrichment_log NÖTRLE (silme değil — ON DELETE SET NULL semantiği; system
    #    log satırı korunur, kişi bağı koparılır). Idempotent: ikinci kez 0 satır.
    def _neutralize() -> Any:
        return (
            main.table(_ENRICHMENT_LOG)
            .update({"user_id": None})
            .eq("user_id", user_id)
            .execute()
        )

    neut = await supabase_call_async(_neutralize)
    receipt[f"{_ENRICHMENT_LOG}_neutralized"] = len(neut.data or [])

    # 4) waitlist PII (email/name/ip/user_agent — KVKK kapsamında kişisel veri).
    #    DİKKAT: waitlist'te user_id YOK → EMAIL ile silinir. Email'i auth silmeden
    #    ÖNCE al (kullanıcı hâlâ varken). user_profiles'ta email kolonu YOK
    #    (doğrulandı: migration 0001) → Supabase admin API get_user_by_id ile alınır
    #    (yöntem .venv introspection ile doğrulandı: get_user_by_id(uid)->UserResponse,
    #    .user.email taşır). Email bulunamazsa (silinmiş/eksik) → atla + logla;
    #    erasure'ı ÇÖKERTME. (Gerçek API hatası YUTULMAZ — try/except yok, propagate.)
    def _get_user() -> Any:
        return main.auth.admin.get_user_by_id(user_id)

    user_resp = await supabase_call_async(_get_user)
    user_obj = getattr(user_resp, "user", None)
    email = getattr(user_obj, "email", None) if user_obj is not None else None
    if email:

        def _del_waitlist() -> Any:
            # EMAIL ile sil (user_id DEĞİL) — waitlist'te user_id kolonu yok.
            return main.table("waitlist").delete().eq("email", email).execute()

        wl = await supabase_call_async(_del_waitlist)
        receipt["waitlist"] = len(wl.data or [])
    else:
        receipt["waitlist"] = 0
        logger.info(
            "account delete user=%s: no email → waitlist purge skipped", user_id
        )

    # 5) EN SON: auth.users (Supabase admin). Veri zaten gitti → bu adım patlarsa
    #    fonksiyon yeniden çalıştırılabilir (veri silmeleri no-op olur, auth retry).
    def _delete_auth() -> Any:
        return main.auth.admin.delete_user(user_id)

    await supabase_call_async(_delete_auth)
    receipt["auth_deleted"] = True

    logger.info("account hard-deleted user=%s receipt=%s", user_id, receipt)
    return receipt


async def delete_review_job(user_id: str, job_id: str) -> bool:
    """Tek hakemlik işini sahip-kapsamlı sil (REVIEW Supabase).

    `WHERE job_id AND user_id` → BOLA-güvenli: başka kullanıcının işi eşleşmez.
    Döndürür: silindi mi (eşleşen satır var mıydı). False = sahip değil / yok → 404.
    """
    review = get_review_supabase_admin()

    def _q() -> Any:
        return (
            review.table(_REVIEW_TABLE)
            .delete()
            .eq("job_id", job_id)
            .eq("user_id", user_id)
            .execute()
        )

    resp = await supabase_call_async(_q)
    return bool(resp.data)
