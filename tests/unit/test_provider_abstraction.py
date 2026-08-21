"""FAZ D — ScholarlyProvider abstraction + ProviderSnapshot görünürlük testleri.

Kanıt (evidence_provider_spec.md §Başarı kapısı):
  - Adapter openalex_polite'e DELEGE eder (gerçek import sitesinde monkeypatch).
  - Her çağrı doğru ProviderSnapshot üretir: ok / failed / rate_limited / auth_missing.
  - Sağlayıcı arızası SESSİZ boş-liste DEĞİL (bare metot raise; *_with_snapshot
    failed-status snapshot döndürür).
  - query_hash deterministik (aynı sorgu → aynı hash; farklı → farklı).
  - Citation flow evidence_pack'inde ProviderSnapshot[] görünür (provider+status).

Ağ YOK: openalex_polite fonksiyonları engine.providers.openalex namespace'inde
monkeypatch edilir; review_citation_service.resolve_reference de gerçek sitesinde.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from api.services.openalex_polite import OpenAlexError
from engine.providers import base as pbase
from engine.providers.base import (
    ProviderError,
    ProviderSnapshot,
    RawReference,
    ScholarlyProvider,
    ScholarlySearchQuery,
    query_hash,
)
from engine.providers.openalex import (
    OPENALEX_PROVIDER_VERSION,
    OpenAlexProvider,
    _map_error_status,
)

pytestmark = pytest.mark.unit


def _raw_work(
    *, wid: str = "W123", title: str = "A Title", year: int = 2020,
    cited_by: int = 10, is_retracted: bool = False,
    abstract_inverted: dict[str, list[int]] | None = None,
    referenced: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"https://openalex.org/{wid}",
        "title": title,
        "display_name": title,
        "publication_year": year,
        "is_retracted": is_retracted,
        "cited_by_count": cited_by,
        "abstract_inverted_index": abstract_inverted,
        "referenced_works": referenced or [],
    }


# --- query_hash determinizmi -------------------------------------------------


def test_query_hash_deterministic_and_normalized() -> None:
    a = query_hash(provider="openalex", endpoint="search_works",
                   query="Deep   Learning", provider_version="2026-06")
    b = query_hash(provider="openalex", endpoint="search_works",
                   query="deep learning", provider_version="2026-06")
    c = query_hash(provider="openalex", endpoint="search_works",
                   query="something else", provider_version="2026-06")
    assert a == b, "aynı normalize sorgu → aynı hash"
    assert a != c, "farklı sorgu → farklı hash"
    # endpoint + version anahtarın parçası (spec §Caching).
    d = query_hash(provider="openalex", endpoint="get_work",
                   query="deep learning", provider_version="2026-06")
    e = query_hash(provider="openalex", endpoint="search_works",
                   query="deep learning", provider_version="2027-01")
    assert a != d and a != e


def test_openalex_provider_satisfies_protocol() -> None:
    assert isinstance(OpenAlexProvider(), ScholarlyProvider)


# --- error mapping (spec §Provider error mapping) ---------------------------


def test_error_status_mapping() -> None:
    st, _ = _map_error_status(OpenAlexError("OPENALEX_EMAIL not configured (polite-pool gerekli)"))
    assert st == "auth_missing"
    st, _ = _map_error_status(OpenAlexError("openalex client error 429: rate limit"))
    assert st == "rate_limited"
    st, _ = _map_error_status(OpenAlexError("openalex search failed: boom"))
    assert st == "failed"


# --- search_works ------------------------------------------------------------


async def test_search_works_ok_produces_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake(query: str, **kw: Any) -> list[dict[str, Any]]:
        return [_raw_work(wid="W1", title="Attention"), _raw_work(wid="W2", title="BERT")]

    monkeypatch.setattr("engine.providers.openalex.search_works_raw", _fake)

    works, snap = await OpenAlexProvider().search_works_with_snapshot(
        ScholarlySearchQuery(query="transformers", limit=5)
    )
    assert [w.openalex_id for w in works] == ["W1", "W2"]
    assert snap.provider == "openalex"
    assert snap.provider_version == OPENALEX_PROVIDER_VERSION
    assert snap.status == "ok"
    assert snap.result_count == 2
    assert snap.cache_hit is False
    assert "abstract only" in snap.limitations
    assert isinstance(snap, ProviderSnapshot)


async def test_search_works_failure_not_silent_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _boom(query: str, **kw: Any) -> list[dict[str, Any]]:
        raise OpenAlexError("openalex search failed: 503")

    monkeypatch.setattr("engine.providers.openalex.search_works_raw", _boom)

    works, snap = await OpenAlexProvider().search_works_with_snapshot(
        ScholarlySearchQuery(query="x")
    )
    # GÖRÜNÜR arıza, sessiz ok-with-empty DEĞİL.
    assert works == []
    assert snap.status == "failed"
    assert snap.result_count == 0
    assert snap.limitations  # hata mesajı taşınır

    # bare Protocol metodu arızayı YUTMAZ → raise.
    with pytest.raises(ProviderError):
        await OpenAlexProvider().search_works(ScholarlySearchQuery(query="x"))


async def test_search_works_auth_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noauth(query: str, **kw: Any) -> list[dict[str, Any]]:
        raise OpenAlexError("OPENALEX_EMAIL not configured (polite-pool gerekli)")

    monkeypatch.setattr("engine.providers.openalex.search_works_raw", _noauth)
    _works, snap = await OpenAlexProvider().search_works_with_snapshot(
        ScholarlySearchQuery(query="x")
    )
    assert snap.status == "auth_missing"


# --- get_work / get_references ----------------------------------------------


async def test_get_work_ok_and_404(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ok(work_id: str, **kw: Any) -> dict[str, Any] | None:
        return _raw_work(wid="W42", title="Found")

    monkeypatch.setattr("engine.providers.openalex.fetch_work_by_id", _ok)
    work, snap = await OpenAlexProvider().get_work_with_snapshot("W42")
    assert work is not None and work.openalex_id == "W42"
    assert snap.status == "ok" and snap.result_count == 1

    async def _none(work_id: str, **kw: Any) -> dict[str, Any] | None:
        return None

    monkeypatch.setattr("engine.providers.openalex.fetch_work_by_id", _none)
    work, snap = await OpenAlexProvider().get_work_with_snapshot("W999")
    assert work is None
    assert snap.status == "ok" and snap.result_count == 0  # 404 = yok, hata değil


async def test_get_references_from_referenced_works(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ok(work_id: str, **kw: Any) -> dict[str, Any] | None:
        return _raw_work(
            wid="W1",
            referenced=["https://openalex.org/W10", "https://openalex.org/W11"],
        )

    monkeypatch.setattr("engine.providers.openalex.fetch_work_by_id", _ok)
    edges, snap = await OpenAlexProvider().get_references_with_snapshot("W1")
    assert {e.target_id for e in edges} == {"W10", "W11"}
    assert all(e.source_id == "W1" for e in edges)
    assert snap.status == "ok" and snap.result_count == 2


async def test_get_citations_deferred_not_silent() -> None:
    # Dürüst: sessiz boş-liste DEĞİL, açık NotImplementedError.
    with pytest.raises(NotImplementedError):
        await OpenAlexProvider().get_citations("W1")


# --- resolve_reference (kron-mücevhere delege) ------------------------------


async def test_resolve_reference_delegates_to_crown_jewel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.models.review import ParsedReference

    captured: dict[str, Any] = {}

    async def _fake_resolve(ref: ParsedReference, *, settings: Any = None) -> ParsedReference:
        captured["title"] = ref.title
        return ref.model_copy(
            update={"status": "resolved", "openalex_id": "W42", "evidence": "ok"}
        )

    monkeypatch.setattr(
        "api.services.review_citation_service.resolve_reference", _fake_resolve
    )

    resolved, snap = await OpenAlexProvider().resolve_reference_with_snapshot(
        RawReference(index=3, raw="x", title="Attention Is All You Need", doi="10.1/x")
    )
    assert captured["title"] == "Attention Is All You Need"  # delege edildi
    assert resolved.status == "resolved"
    assert resolved.openalex_id == "W42"
    assert resolved.raw_index == 3
    assert snap.status == "ok" and snap.result_count == 1


async def test_resolve_reference_not_found_is_visible_not_fabricated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.models.review import ParsedReference

    async def _fake_resolve(ref: ParsedReference, *, settings: Any = None) -> ParsedReference:
        return ref.model_copy(update={"status": "not_found_in_index", "evidence": "yok"})

    monkeypatch.setattr(
        "api.services.review_citation_service.resolve_reference", _fake_resolve
    )
    resolved, snap = await OpenAlexProvider().resolve_reference_with_snapshot(
        RawReference(index=0, raw="x", title="Niche")
    )
    assert resolved.status == "not_found_in_index"
    assert snap.status == "ok"  # stage tamam; çözüm sonucu status alanında
    assert snap.result_count == 0


# --- citation flow görünürlüğü (evidence_pack provider_snapshots) ------------


async def test_flow_records_provider_snapshots(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_pipeline evidence_pack'inde ProviderSnapshot[] görünür (provider+status)."""
    from api.services import review_service as svc
    from tests.unit.test_review_degraded import _patch_pipeline_common

    _patch_pipeline_common(monkeypatch, svc)

    async def _ok(meta: Any, refs: Any) -> list[Any]:
        return []

    monkeypatch.setattr(svc.review_citation_service, "find_coverage_gaps", _ok)

    captured: dict[str, Any] = {}

    async def _capture_update(job_id: Any, **fields: Any) -> None:
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf", mode="editor", language="tr"
    )

    snaps = captured["evidence_pack"]["provider_snapshots"]
    assert snaps, "evidence_pack provider_snapshots boş olmamalı"
    assert all(s["provider"] == "openalex" for s in snaps)
    assert all("status" in s for s in snaps)
    endpoints = {s["query_hash"] for s in snaps}  # her çağrı ayrı hash
    assert len(endpoints) == len(snaps)
    # resolve + context + coverage = 3 stage snapshot
    assert len(snaps) == 3
    assert all(s["status"] == "ok" for s in snaps)


async def test_flow_provider_failure_snapshot_is_honest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coverage sağlayıcı arızası → snapshot status failed; SESSİZ ok-with-empty DEĞİL."""
    from api.services import review_service as svc
    from tests.unit.test_review_degraded import _patch_pipeline_common

    _patch_pipeline_common(monkeypatch, svc)

    async def _boom(meta: Any, refs: Any) -> list[Any]:
        raise OpenAlexError("OpenAlex 503")

    monkeypatch.setattr(svc.review_citation_service, "find_coverage_gaps", _boom)

    captured: dict[str, Any] = {}

    async def _capture_update(job_id: Any, **fields: Any) -> None:
        captured.update(fields)

    monkeypatch.setattr(svc, "_update", _capture_update)

    await svc.run_pipeline(
        uuid4(), data=b"x", kind="pdf", filename="f.pdf", mode="editor", language="tr"
    )

    snaps = captured["evidence_pack"]["provider_snapshots"]
    failed = [s for s in snaps if s["status"] in
              ("failed", "degraded", "rate_limited", "auth_missing")]
    assert failed, "sağlayıcı arızası ProviderSnapshot'ta GÖRÜNMELİ (sessiz değil)"
    assert any(s["result_count"] == 0 for s in failed)
    # mevcut degraded_features sinyali de korunur (çoğaltma değil, entegrasyon).
    assert "coverage:openalex_unavailable" in captured["evidence_pack"]["degraded_features"]


# pbase import edildiğini kullan (ruff F401 önleme) — Protocol modülü sağlık kontrolü.
def test_base_module_exports() -> None:
    assert hasattr(pbase, "ScholarlyProvider")
    assert hasattr(pbase, "ProviderSnapshot")
