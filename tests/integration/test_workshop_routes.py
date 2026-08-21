"""F13-S2-P003 — /api/workshop/* integration tests.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (4 integration)
Strateji: TestClient + JWT(HS256) + progress_service monkeypatch.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

_USER_ID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = jwt.encode({"sub": _USER_ID}, "x", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patched_progress(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """SUPABASE guard pass + supabase_call_async sıralı mock.

    state["queue"] her çağrıda bir item pop'lar; default empty → [].
    """
    monkeypatch.setenv("SUPABASE_URL", "http://test.local")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test-key")
    from api.config import get_settings

    get_settings.cache_clear()

    state: dict[str, Any] = {"queue": []}

    async def _fake_call(_fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        if state["queue"]:
            return SimpleNamespace(data=state["queue"].pop(0))
        return SimpleNamespace(data=[])

    from api.services import progress_service

    monkeypatch.setattr(progress_service, "supabase_call_async", _fake_call)
    monkeypatch.setattr(
        progress_service, "get_supabase_admin", lambda: SimpleNamespace()
    )
    return state


def _step_row(step_id: str, status: str = "completed", **overrides: Any) -> dict[str, Any]:
    base = {
        "project_id": str(uuid4()),
        "step_id": step_id,
        "status": status,
        "completed_at": datetime.now(UTC).isoformat() if status == "completed" else None,
        "meta": {},
        "updated_at": datetime.now(UTC).isoformat(),
    }
    base.update(overrides)
    return base


# ── M-14: workshop router-level tier_gate — anon kesin reddedilir ──────────
def test_workshop_anon_request_rejected(
    client: TestClient,
) -> None:
    """Audit M-14 / POL-COST-1: Authorization header'sız atölye çağrısı 401 olmalı.

    İki savunma katmanı: (a) AuthMiddleware Authorization yoksa 401 atar,
    (b) düşse bile router-level Depends(tier_gate) WORKSHOP_PREFIX_QUOTA[ANON]=None
    ile auth_required_for_tier fırlatır. Bu test (a) katmanını doğrular; (b)
    katmanı kodda mevcudiyetiyle defense-in-depth.
    """
    resp = client.get(
        f"/api/workshop/maturity?project_id={uuid4()}&publication_type=tez",
    )
    assert resp.status_code == 401
    body = resp.json()
    # Auth middleware ya da tier_gate katmanından biri yakalamalı.
    error = body.get("error") or (body.get("detail") or {}).get("error", "")
    assert error in {"missing_or_invalid_authorization_header", "auth_required_for_tier"}


# ── Test 1: GET /maturity tez project bulunamadı → 404 ──────────────────────
def test_get_maturity_project_not_found(
    client: TestClient,
    auth_headers: dict[str, str],
    patched_progress: dict[str, Any],
) -> None:
    project_id = uuid4()
    # 1. çağrı = assert_owner → empty
    patched_progress["queue"].extend([[]])

    resp = client.get(
        f"/api/workshop/maturity?project_id={project_id}&publication_type=tez",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "project_not_found"


# ── Test 2: GET /maturity bildiri tüm zorunlu → button_active True ──────────
def test_get_maturity_bildiri_all_required(
    client: TestClient,
    auth_headers: dict[str, str],
    patched_progress: dict[str, Any],
) -> None:
    project_id = uuid4()
    # 1. assert_owner → 1 row
    # 2. list_steps → 3 zorunlu (discovery-1, gapatlas-1, curation-4) hepsi tamam
    patched_progress["queue"].extend(
        [
            [{"id": str(project_id)}],
            [
                _step_row("discovery-1", project_id=str(project_id)),
                _step_row("gapatlas-1", project_id=str(project_id)),
                _step_row("curation-4", project_id=str(project_id)),
            ],
        ]
    )

    resp = client.get(
        f"/api/workshop/maturity?project_id={project_id}&publication_type=bildiri",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["button_active"] is True
    assert body["required_total"] == 3
    assert body["required_completed"] == 3
    assert body["publication_type"] == "bildiri"


# ── Test 3: PUT /progress upsert → 200 ──────────────────────────────────────
def test_put_progress_happy(
    client: TestClient,
    auth_headers: dict[str, str],
    patched_progress: dict[str, Any],
) -> None:
    project_id = uuid4()
    inserted = _step_row("discovery-1", project_id=str(project_id))
    patched_progress["queue"].extend(
        [
            [{"id": str(project_id)}],  # assert_owner
            [inserted],  # upsert response
        ]
    )

    resp = client.put(
        "/api/workshop/progress",
        headers=auth_headers,
        json={
            "project_id": str(project_id),
            "step_id": "discovery-1",
            "status": "completed",
            "meta": {"anchor": "X"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["step_id"] == "discovery-1"
    assert body["status"] == "completed"


# ── Test 4: PUT /progress geçersiz status → 422 (Pydantic) ──────────────────
def test_put_progress_invalid_status(
    client: TestClient,
    auth_headers: dict[str, str],
    patched_progress: dict[str, Any],
) -> None:
    resp = client.put(
        "/api/workshop/progress",
        headers=auth_headers,
        json={
            "project_id": str(uuid4()),
            "step_id": "discovery-1",
            "status": "BOGUS",
            "meta": {},
        },
    )
    assert resp.status_code == 422


# ── Test 6: POST /paraphrase happy path (LLM mock) ──────────────────────────
def test_post_paraphrase_happy(
    client: TestClient,
    auth_headers: dict[str, str],
    patched_progress: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    # 1. supabase profile lookup → empty
    patched_progress["queue"].extend([[]])

    from api.models.llm import LLMResponse
    from api.services import paraphrase_service

    # paraphrase_service kendi supabase_call_async'ını kullanıyor — bunu da mock'la
    async def _fake_supa(_fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ASYNC109
        return SimpleNamespace(data=[])

    monkeypatch.setattr(paraphrase_service, "supabase_call_async", _fake_supa)
    monkeypatch.setattr(
        paraphrase_service, "get_supabase_admin", lambda: SimpleNamespace()
    )

    async def _fake_llm(*_a: Any, **_kw: Any) -> LLMResponse:
        return LLMResponse(
            text='{"sentences":[{"index":0,"original":"x","proposed":"x mektedir","confidence":0.9}]}',
            parsed_output=None,
            model_used="gemini-flash-tr",
            tokens_in=50,
            tokens_out=60,
            latency_ms=400,
        )

    monkeypatch.setattr(paraphrase_service, "llm_call", _fake_llm)

    resp = client.post(
        "/api/workshop/paraphrase",
        headers=auth_headers,
        json={
            "project_id": str(project_id),
            "document_text": "Bu çalışma örnektir.",
            "lang": "tr",
            "section_context": "intro",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_sentences"] >= 1
    assert body["lang"] == "tr"
    assert len(body["sentences"]) >= 1


# ── Test 5: POST /advisor-summary happy path (LLM mock) ─────────────────────
def test_post_advisor_summary_happy(
    client: TestClient,
    auth_headers: dict[str, str],
    patched_progress: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    # 1. assert_owner; 2. list_steps → 1 completed step
    patched_progress["queue"].extend(
        [
            [{"id": str(project_id)}],
            [_step_row("discovery-1", project_id=str(project_id))],
        ]
    )

    from api.models.llm import LLMResponse
    from api.services import progress_service

    async def _fake_llm(*_args: Any, **_kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text="Bu çalışma X alanında konumlanmaktadır...",
            parsed_output=None,
            model_used="gemini-flash-tr",
            tokens_in=200,
            tokens_out=160,
            latency_ms=900,
        )

    monkeypatch.setattr(progress_service, "llm_call", _fake_llm)

    resp = client.post(
        "/api/workshop/advisor-summary",
        headers=auth_headers,
        json={"project_id": str(project_id), "publication_type": "makale"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["step_count_used"] == 1
    assert body["publication_type"] == "makale"
    assert "X alanında" in body["summary"]
