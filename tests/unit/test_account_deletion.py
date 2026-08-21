"""KVKK hard-delete — account_deletion_service + route güvenlik kanıtı.

İki geri-DÖNÜLMEZ vaadi backend kanıtı:
  1. delete_account: 14 doğrudan tablo user_id ile silinir, projects silinir,
     review_job AYRI (review) client'ta silinir, enrichment_log NÖTRLENİR (set null,
     silinmez), auth.admin.delete_user TAM 1 kez ve EN SON çağrılır.
  2. NEGATİF (en kritik): servis hiçbir GLOBAL/paylaşılan tabloya (papers/fact_*/
     dim_*/app_theme_settings/waitlist/schema_migrations) DOKUNMAZ — dokunulan
     tablo kümesi ⊆ izinli küme ve yasaklı kümeyle kesişimi BOŞ.
  3. route: 401 (auth yok) · 400 (onay yanlış/eksik) · 200 + makbuz (happy).
  4. review tekil silme: 204 (sahip) · 404 (başkasının işi = BOLA).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from api.services.account_deletion_service import _DIRECT_USER_TABLES

pytestmark = pytest.mark.unit

_UID = "user-kvkk-1"
_EMAIL = "deleted-user@example.com"

# HARDCODED beklenen kapsam — KASITLI olarak _DIRECT_USER_TABLES'tan TÜRETİLMEZ.
# Bu literal, sabit listeye tablo EKLENMESİNİ ya da SİLİNMESİNİ yakalar (türetseydik
# mutasyon testi vacuous olurdu: liste değişince beklenti de değişir, test yeşil kalır).
EXPECTED_DIRECT = {
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
    "projects",
}
# Servisin DOKUNMASINA izin verilen TAM küme (exhaustive). waitlist = kullanıcı PII
# (KVKK kapsamında kasıtlı silinir; email ile). review_job ayrı Supabase'te,
# enrichment_log nötrlenir. Bu kümeye eşitlik (subset değil) → beklenmeyen HER tablo
# (global olsun olmasın) testi kırar.
EXPECTED_ALLOWED = EXPECTED_DIRECT | {"review_job", "enrichment_log", "waitlist"}

# Asla DOKUNULMAMASI gereken global/paylaşılan tablolar (waitlist ARTIK değil — o PII).
_GLOBAL_FORBIDDEN = {
    "papers",
    "summary_cache",
    "app_theme_settings",
    "schema_migrations",
    "fact_gap_matrix",
    "fact_paper_quality_v3",
    "dim_field",
    "dim_theme",
    "dim_ghost_paper",
}


# --- fake supabase recorder (delete/update + auth admin) ---------------------


class _Builder:
    def __init__(self, fake: _Fake, table: str) -> None:
        self._fake = fake
        self._table = table
        self._op: str | None = None
        self._update: dict[str, Any] | None = None
        self._filters: list[tuple[str, Any]] = []

    def delete(self) -> _Builder:
        self._op = "delete"
        return self

    def update(self, payload: dict[str, Any]) -> _Builder:
        self._op = "update"
        self._update = payload
        return self

    def eq(self, col: str, val: Any) -> _Builder:
        self._filters.append((col, val))
        return self

    def execute(self) -> SimpleNamespace:
        self._fake.events.append(
            {
                "client": self._fake.tag,
                "table": self._table,
                "op": self._op,
                "filters": list(self._filters),
                "update": self._update,
            }
        )
        rows = self._fake.rows_for(self._table)
        return SimpleNamespace(data=rows)


class _Admin:
    def __init__(self, fake: _Fake) -> None:
        self._fake = fake

    def get_user_by_id(self, user_id: str) -> SimpleNamespace:
        # Gerçek admin API imzası: get_user_by_id(uid)->UserResponse(.user.email)
        # (doğrulandı: .venv introspection). Email yoksa user=None (silinmiş kullanıcı).
        self._fake.events.append(
            {"client": self._fake.tag, "table": "__auth_get__", "op": "get_user",
             "filters": [("user_id", user_id)], "update": None}
        )
        if self._fake.email is None:
            return SimpleNamespace(user=None)
        return SimpleNamespace(user=SimpleNamespace(email=self._fake.email))

    def delete_user(self, user_id: str) -> SimpleNamespace:
        self._fake.events.append(
            {"client": self._fake.tag, "table": "__auth__", "op": "delete_user",
             "filters": [("user_id", user_id)], "update": None}
        )
        self._fake.auth_deleted.append(user_id)
        return SimpleNamespace(user=None)


class _Fake:
    def __init__(
        self,
        events: list[dict[str, Any]],
        tag: str,
        *,
        rows: int = 1,
        email: str | None = _EMAIL,
    ) -> None:
        self.events = events
        self.tag = tag
        self._rows = rows
        self.email = email
        self.auth_deleted: list[str] = []
        self.auth = SimpleNamespace(admin=_Admin(self))

    def table(self, name: str) -> _Builder:
        return _Builder(self, name)

    def rows_for(self, table: str) -> list[dict[str, Any]]:
        # Her silme/güncelleme eşleşen satır döndürsün (PostgREST returning=repr).
        return [{"user_id": _UID}] * self._rows


@pytest.fixture
def _patch_clients(monkeypatch: pytest.MonkeyPatch):
    """MAIN + REVIEW client'larını fake'e bağla, supabase_call_async'i direct yap."""
    events: list[dict[str, Any]] = []
    main = _Fake(events, "main")
    review = _Fake(events, "review")

    monkeypatch.setattr(
        "api.services.account_deletion_service.get_supabase_admin", lambda: main
    )
    monkeypatch.setattr(
        "api.services.account_deletion_service.get_review_supabase_admin",
        lambda: review,
    )

    async def _direct(fn: Any) -> Any:
        return fn()

    monkeypatch.setattr(
        "api.services.account_deletion_service.supabase_call_async", _direct
    )
    return SimpleNamespace(events=events, main=main, review=review)


# --- service: delete_account ------------------------------------------------


def test_direct_table_constant_pinned_to_hardcoded_literal() -> None:
    """Mutasyon kalkanı: sabit liste HARDCODED beklentiye birebir eşit + tam 14.

    Bu, _DIRECT_USER_TABLES'a tablo EKLENMESİNİ (kişisel olmayan veriyi yanlışlıkla
    silmek) VE listeden tablo SİLİNMESİNİ (kişisel veriyi geride bırakmak — KVKK
    ihlali) yakalar. Beklenti listeden TÜRETİLMEDİĞİ için test gerçekten kırılır."""
    assert set(_DIRECT_USER_TABLES) == EXPECTED_DIRECT
    assert len(_DIRECT_USER_TABLES) == 14


@pytest.mark.asyncio
async def test_delete_account_touches_all_14_direct_tables(_patch_clients) -> None:
    from api.services import account_deletion_service as svc

    receipt = await svc.delete_account(_UID)

    deletes = {
        e["table"]: e
        for e in _patch_clients.events
        if e["op"] == "delete" and e["client"] == "main"
    }
    # HARDCODED 14 tablonun HEPSİ user_id ile silindi (beklenti türetilmedi).
    for table in EXPECTED_DIRECT:
        assert table in deletes, f"{table} silinmedi"
        assert ("user_id", _UID) in deletes[table]["filters"], f"{table} user_id'siz"
        assert receipt[table] == 1

    # projects açıkça silindi (→ 7 alt tablo cascade).
    assert "projects" in deletes


@pytest.mark.asyncio
async def test_delete_account_review_job_on_review_client(_patch_clients) -> None:
    from api.services import account_deletion_service as svc

    await svc.delete_account(_UID)

    review_deletes = [
        e
        for e in _patch_clients.events
        if e["table"] == "review_job" and e["op"] == "delete"
    ]
    assert len(review_deletes) == 1
    # review_job AYRI (review) Supabase'te silinmeli, main'de DEĞİL.
    assert review_deletes[0]["client"] == "review"
    assert ("user_id", _UID) in review_deletes[0]["filters"]


@pytest.mark.asyncio
async def test_delete_account_enrichment_log_neutralized_not_deleted(
    _patch_clients,
) -> None:
    from api.services import account_deletion_service as svc

    await svc.delete_account(_UID)

    enrich = [e for e in _patch_clients.events if e["table"] == "enrichment_log"]
    assert len(enrich) == 1
    # Silme DEĞİL — update set user_id=NULL (system log korunur).
    assert enrich[0]["op"] == "update"
    assert enrich[0]["update"] == {"user_id": None}
    assert ("user_id", _UID) in enrich[0]["filters"]


@pytest.mark.asyncio
async def test_delete_account_auth_deleted_once_and_last(_patch_clients) -> None:
    from api.services import account_deletion_service as svc

    receipt = await svc.delete_account(_UID)

    auth_events = [e for e in _patch_clients.events if e["table"] == "__auth__"]
    assert len(auth_events) == 1, "auth.admin.delete_user TAM 1 kez çağrılmalı"
    # EN SON adım: tüm veri silmelerinden sonra.
    assert _patch_clients.events[-1]["table"] == "__auth__"
    assert _patch_clients.main.auth_deleted == [_UID]
    assert receipt["auth_deleted"] is True


_PSEUDO = {"__auth__", "__auth_get__"}  # tablo değil; auth admin çağrı işaretleri


@pytest.mark.asyncio
async def test_delete_account_never_touches_global_tables(_patch_clients) -> None:
    """EN KRİTİK negatif test: dokunulan tablo kümesi BEKLENEN'e BİREBİR eşit.

    Eşitlik (subset değil) → kapsama EKLENEN beklenmedik HER tablo (global olsun ya
    da olmasın) testi kırar; _GLOBAL_FORBIDDEN örneğinde olmasa bile yakalanır."""
    from api.services import account_deletion_service as svc

    await svc.delete_account(_UID)

    touched = {
        e["table"] for e in _patch_clients.events if e["table"] not in _PSEUDO
    }
    # Birebir eşitlik: ne eksik ne fazla.
    assert touched == EXPECTED_ALLOWED, (
        f"beklenmeyen={touched - EXPECTED_ALLOWED} eksik={EXPECTED_ALLOWED - touched}"
    )
    # Ek kalkan: yasaklı global tablolardan hiçbiri dokunulan kümede değil.
    assert touched.isdisjoint(_GLOBAL_FORBIDDEN), (
        f"GLOBAL tabloya dokunuldu: {touched & _GLOBAL_FORBIDDEN}"
    )


@pytest.mark.asyncio
async def test_delete_account_waitlist_purged_by_email(_patch_clients) -> None:
    """KVKK: kullanıcının waitlist PII'si EMAIL ile (user_id değil) silinir."""
    from api.services import account_deletion_service as svc

    receipt = await svc.delete_account(_UID)

    wl = [
        e
        for e in _patch_clients.events
        if e["table"] == "waitlist" and e["op"] == "delete"
    ]
    assert len(wl) == 1
    assert wl[0]["client"] == "main"
    # EMAIL ile silinmeli — user_id ile DEĞİL.
    assert ("email", _EMAIL) in wl[0]["filters"]
    assert all(col != "user_id" for col, _ in wl[0]["filters"])
    assert receipt["waitlist"] == 1
    # waitlist silme auth silmeden ÖNCE (kullanıcı hâlâ varken email alınabildi).
    tables_in_order = [e["table"] for e in _patch_clients.events]
    assert tables_in_order.index("waitlist") < tables_in_order.index("__auth__")


@pytest.mark.asyncio
async def test_delete_account_succeeds_without_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Email yoksa (kullanıcı/satır eksik) → waitlist atlanır, erasure ÇÖKMEZ."""
    from api.services import account_deletion_service as svc

    events: list[dict[str, Any]] = []
    main = _Fake(events, "main", email=None)  # get_user_by_id → user=None
    review = _Fake(events, "review")
    monkeypatch.setattr(svc, "get_supabase_admin", lambda: main)
    monkeypatch.setattr(svc, "get_review_supabase_admin", lambda: review)

    async def _direct(fn: Any) -> Any:
        return fn()

    monkeypatch.setattr(svc, "supabase_call_async", _direct)

    receipt = await svc.delete_account(_UID)

    # waitlist'e HİÇ delete çağrısı yapılmadı (email yok → atlandı, çökme yok).
    assert not [e for e in events if e["table"] == "waitlist"]
    assert receipt["waitlist"] == 0
    # Erasure yine de tamamlandı: tüm direct tablolar + auth silindi.
    assert receipt["auth_deleted"] is True
    assert events[-1]["table"] == "__auth__"


@pytest.mark.asyncio
async def test_delete_account_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hata yutulmaz — DB hatası propagate eder (sahte başarı yok)."""
    from api.services import account_deletion_service as svc

    monkeypatch.setattr(svc, "get_review_supabase_admin", lambda: object())

    class _BoomMain:
        def table(self, _name: str) -> Any:
            raise RuntimeError("db down")

    monkeypatch.setattr(svc, "get_supabase_admin", lambda: _BoomMain())

    async def _direct(fn: Any) -> Any:
        return fn()

    monkeypatch.setattr(svc, "supabase_call_async", _direct)

    with pytest.raises(RuntimeError, match="db down"):
        await svc.delete_account(_UID)


# --- service: delete_review_job (BOLA) --------------------------------------


@pytest.mark.asyncio
async def test_delete_review_job_owner_true(_patch_clients) -> None:
    from api.services import account_deletion_service as svc

    ok = await svc.delete_review_job(_UID, "job-1")
    assert ok is True
    ev = next(e for e in _patch_clients.events if e["table"] == "review_job")
    assert ev["client"] == "review"
    assert ("job_id", "job-1") in ev["filters"]
    assert ("user_id", _UID) in ev["filters"]


@pytest.mark.asyncio
async def test_delete_review_job_not_owner_false(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.services import account_deletion_service as svc

    events: list[dict[str, Any]] = []
    review = _Fake(events, "review", rows=0)  # eşleşen satır YOK
    monkeypatch.setattr(svc, "get_review_supabase_admin", lambda: review)

    async def _direct(fn: Any) -> Any:
        return fn()

    monkeypatch.setattr(svc, "supabase_call_async", _direct)

    ok = await svc.delete_review_job("attacker", "job-of-someone-else")
    assert ok is False


# --- route: DELETE /api/account ---------------------------------------------


def _token(sub: str) -> str:
    return jwt.encode({"sub": sub}, "x", algorithm="HS256")


def test_account_delete_requires_auth(client: TestClient) -> None:
    resp = client.request(
        "DELETE", "/api/account", json={"confirm_phrase": "HESABIMI SİL"}
    )
    assert resp.status_code == 401, resp.text


def test_account_delete_wrong_confirm_400(client: TestClient) -> None:
    client.headers["Authorization"] = f"Bearer {_token(_UID)}"
    resp = client.request("DELETE", "/api/account", json={"confirm_phrase": "nope"})
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "confirm_phrase_mismatch"


def test_account_delete_missing_confirm_400(client: TestClient) -> None:
    client.headers["Authorization"] = f"Bearer {_token(_UID)}"
    resp = client.request("DELETE", "/api/account", json={})
    assert resp.status_code == 400, resp.text


def test_account_delete_happy_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from api.routes import account as account_route

    async def _fake_delete(user_id: str) -> dict[str, Any]:
        assert user_id == _UID
        return {"user_profiles": 1, "projects": 2, "auth_deleted": True}

    monkeypatch.setattr(
        account_route.account_deletion_service, "delete_account", _fake_delete
    )
    client.headers["Authorization"] = f"Bearer {_token(_UID)}"
    resp = client.request(
        "DELETE", "/api/account", json={"confirm_phrase": "HESABIMI SİL"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "deleted"
    assert body["auth_deleted"] is True
    assert body["rows_deleted"] == 3  # 1 + 2 (int değerlerin toplamı)


# --- route: DELETE /api/review/jobs/{job_id} (BOLA) -------------------------


def test_review_delete_owner_204(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from api.services import review_service

    async def _del(user_id: str, job_id: Any) -> bool:
        return True

    monkeypatch.setattr(review_service, "delete_job", _del)
    client.headers["Authorization"] = f"Bearer {_token(_UID)}"
    resp = client.request("DELETE", f"/api/review/jobs/{uuid4()}")
    assert resp.status_code == 204, resp.text


def test_review_delete_other_user_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Başkasının işi → 404 (BOLA: varlığı ifşa etme)."""
    from api.services import review_service

    async def _del(user_id: str, job_id: Any) -> bool:
        return False  # eşleşme yok = sahip değil / yok

    monkeypatch.setattr(review_service, "delete_job", _del)
    client.headers["Authorization"] = f"Bearer {_token(_UID)}"
    resp = client.request("DELETE", f"/api/review/jobs/{uuid4()}")
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"] == "job_not_found"
