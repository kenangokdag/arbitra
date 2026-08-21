"""FAZ D — OpenAlexProvider: ScholarlyProvider Protocol'ünün OpenAlex adapter'i.

DELEGE eder, YENİDEN YAZMAZ:
  - search_works / get_work / get_references → api/services/openalex_polite.py
    (HTTP + polite-pool rate-limit + resilience + 4xx-no-retry; sıfırdan istemci YOK).
  - resolve_reference → api/services/review_citation_service.resolve_reference
    (kron-mücevher: DOI öncelik → fabricated tespiti → fuzzy → dürüst not_found;
     R-1/HK-3/HK-4 mantığı DOKUNULMAZ — burada yalnız Protocol şekline eşlenir).

Her çağrı bir ProviderSnapshot üretebilir (spec §ProviderSnapshot). Arıza SESSİZ
boş-liste DEĞİL (spec §Başarı kapısı): bare Protocol metotları ProviderError
fırlatır; *_with_snapshot varyantları arızayı GÖRÜNÜR (status=failed/...) snapshot
döndürür (review_service görünürlük enstrümantasyonu bunları kullanır).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from api.config import Settings
from api.services.openalex_polite import (
    OpenAlexError,
    _abstract_from_inverted,
    fetch_work_by_id,
    search_works_raw,
)
from engine.providers.base import (
    CitationEdge,
    ProviderError,
    ProviderSnapshot,
    ProviderStatus,
    RawReference,
    ResolvedReference,
    ScholarlySearchQuery,
    Work,
    query_hash,
)

# spec §ProviderSnapshot örneği "provider_version": "2026-06". openalex_polite'te
# ayrı bir sürüm sabiti yok → adapter sözleşme sürümü burada tanımlanır.
# VARSAYIM (Omer-audit): polite-pool istemci sözleşmesinin ay-damgası; yeni
# provider/şema değişiminde elle bump edilir.
OPENALEX_PROVIDER_NAME = "openalex"
OPENALEX_PROVIDER_VERSION = "2026-06"

# OpenAlex tam-metin SAĞLAMAZ — en üst doğrulama abstract (spec §Support levels:
# abstract_only). Bu limitation içerik-taşıyan çağrılara sabit-doğru eklenir.
_ABSTRACT_ONLY = "abstract only"


def _short_id(wid: str | None) -> str | None:
    return wid.rsplit("/", 1)[-1] if isinstance(wid, str) and wid else None


def _work_from_raw(raw: dict[str, Any]) -> Work:
    """Ham OpenAlex Work payload → tipli Work. Yalnız openalex_polite'in gerçekten
    ürettiği alanlar (api/services/openalex_polite.py:80-102) + is_retracted +
    referenced_works. abstract = _abstract_from_inverted (openalex_polite:68)."""
    authors_raw = raw.get("authorships") or []
    authors = [
        a.get("author", {}).get("display_name", "")
        for a in authors_raw
        if a.get("author", {}).get("display_name")
    ]
    venue = (
        (raw.get("primary_location") or {}).get("source", {}) or {}
    ).get("display_name")
    return Work(
        openalex_id=_short_id(raw.get("id")),
        doi=raw.get("doi"),
        title=raw.get("title") or raw.get("display_name"),
        abstract=_abstract_from_inverted(raw.get("abstract_inverted_index")),
        year=(int(raw["publication_year"]) if isinstance(raw.get("publication_year"), int) else None),
        venue=venue,
        authors=authors[:10],
        cited_by_count=int(raw.get("cited_by_count") or 0),
        is_retracted=bool(raw.get("is_retracted", False)),
        referenced_work_ids=[
            s for s in (_short_id(r) for r in (raw.get("referenced_works") or [])) if s
        ],
    )


def _map_error_status(exc: OpenAlexError) -> tuple[ProviderStatus, list[str]]:
    """OpenAlexError → spec §Provider error mapping.

    Tespit, openalex_polite'in GERÇEKTEN ürettiği mesajlara dayanır:
      - 'not configured' → auth_missing (openalex_polite.py:120/185/287/301/321).
      - '429' / 'rate'   → rate_limited (best-effort; 429 call_resilient'te retry
        edilir, kalıcı olursa mesajda kod görünebilir).
      - aksi              → failed (client error / malformed / network).
    """
    msg = str(exc).lower()
    if "not configured" in msg:
        return "auth_missing", ["OPENALEX_EMAIL not configured (polite-pool)"]
    if "429" in msg or "rate limit" in msg or "rate-limit" in msg:
        return "rate_limited", [str(exc)[:200]]
    return "failed", [str(exc)[:200]]


class OpenAlexProvider:
    """ScholarlyProvider Protocol'ünün OpenAlex implementasyonu (delege eder)."""

    name: str = OPENALEX_PROVIDER_NAME
    version: str = OPENALEX_PROVIDER_VERSION

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings

    # --- snapshot fabrikası (review_service görünürlük enstrümantasyonu kullanır) ---

    def build_snapshot(
        self,
        *,
        endpoint: str,
        query: str,
        status: ProviderStatus,
        result_count: int = 0,
        cache_hit: bool = False,
        limitations: list[str] | None = None,
    ) -> ProviderSnapshot:
        """Tek doğruluk kaynağı: name/version + deterministik query_hash + zaman
        damgası. query_hash zamandan/random'dan bağımsız (spec §Caching)."""
        return ProviderSnapshot(
            provider=self.name,
            provider_version=self.version,
            query_hash=query_hash(
                provider=self.name,
                endpoint=endpoint,
                query=query,
                provider_version=self.version,
            ),
            request_time=datetime.now(UTC),
            status=status,
            result_count=result_count,
            cache_hit=cache_hit,
            limitations=limitations or [],
        )

    # --- search_works -----------------------------------------------------

    async def search_works_with_snapshot(
        self, query: ScholarlySearchQuery
    ) -> tuple[list[Work], ProviderSnapshot]:
        """Arızayı YUTMAZ ama yükseltmez — (boş liste, failed-snapshot) döndürür."""
        try:
            raw = await search_works_raw(
                query.query,
                limit=query.limit,
                filters=query.filters or None,
                sort=query.sort,
                settings=self._settings,
            )
        except OpenAlexError as exc:
            status, lims = _map_error_status(exc)
            return [], self.build_snapshot(
                endpoint="search_works",
                query=query.query,
                status=status,
                limitations=lims,
            )
        works = [_work_from_raw(w) for w in raw]
        return works, self.build_snapshot(
            endpoint="search_works",
            query=query.query,
            status="ok",
            result_count=len(works),
            limitations=[_ABSTRACT_ONLY],
        )

    async def search_works(self, query: ScholarlySearchQuery) -> list[Work]:
        works, snap = await self.search_works_with_snapshot(query)
        if snap.status in ("failed", "rate_limited", "auth_missing"):
            raise ProviderError(
                f"openalex search_works {snap.status}: {snap.limitations}"
            )
        return works

    # --- get_work ---------------------------------------------------------

    async def get_work_with_snapshot(
        self, work_id: str
    ) -> tuple[Work | None, ProviderSnapshot]:
        try:
            raw = await fetch_work_by_id(work_id, settings=self._settings)
        except OpenAlexError as exc:
            status, lims = _map_error_status(exc)
            return None, self.build_snapshot(
                endpoint="get_work", query=work_id, status=status, limitations=lims
            )
        if raw is None:  # 404 — yok (hata değil); not found → ok + 0 sonuç.
            return None, self.build_snapshot(
                endpoint="get_work", query=work_id, status="ok", result_count=0
            )
        work = _work_from_raw(raw)
        return work, self.build_snapshot(
            endpoint="get_work",
            query=work_id,
            status="ok",
            result_count=1,
            limitations=[_ABSTRACT_ONLY],
        )

    async def get_work(self, work_id: str) -> Work | None:
        work, snap = await self.get_work_with_snapshot(work_id)
        if snap.status in ("failed", "rate_limited", "auth_missing"):
            raise ProviderError(
                f"openalex get_work {snap.status}: {snap.limitations}"
            )
        return work

    # --- resolve_reference (kron-mücevher delege) -------------------------

    async def resolve_reference_with_snapshot(
        self, reference: RawReference
    ) -> tuple[ResolvedReference, ProviderSnapshot]:
        """Çözümü kron-mücevhere (review_citation_service) delege eder; mantık
        DEĞİŞTİRİLMEZ, yalnız Protocol şekline eşlenir. Resolver ağ hatasını
        zaten dürüstçe not_found_in_index'e düşürür (hiç raise etmez) → snapshot
        stage-seviyesinde 'ok'; sonuç status'ü ResolvedReference.status taşır."""
        from api.models.review import ParsedReference  # local — katman/cycle önleme
        from api.services.review_citation_service import (
            resolve_reference as _resolve,
        )

        parsed_in = ParsedReference(
            index=reference.index,
            raw=reference.raw,
            title=reference.title,
            authors=list(reference.authors),
            year=reference.year,
            doi=reference.doi,
            venue=reference.venue,
        )
        parsed_out = await _resolve(parsed_in, settings=self._settings)
        resolved = ResolvedReference(
            raw_index=parsed_out.index,
            status=parsed_out.status,
            openalex_id=parsed_out.openalex_id,
            is_retracted=parsed_out.is_retracted,
            evidence=parsed_out.evidence,
        )
        query = reference.doi or reference.title or reference.raw or str(reference.index)
        count = 1 if resolved.status in ("resolved", "retracted") else 0
        return resolved, self.build_snapshot(
            endpoint="resolve_reference",
            query=query,
            status="ok",
            result_count=count,
            limitations=[_ABSTRACT_ONLY],
        )

    async def resolve_reference(self, reference: RawReference) -> ResolvedReference:
        resolved, _snap = await self.resolve_reference_with_snapshot(reference)
        return resolved

    # --- get_references (referenced_works alanından) ----------------------
    # PROTOCOL-TAMLIĞI (dormant): get_references / get_references_with_snapshot
    # ScholarlyProvider Protocol'ünde TANIMLI (evidence_provider_spec.md) ve
    # tam çalışır (referenced_works → CitationEdge); ancak şu an PRODUCTION
    # ÇAĞRANI YOK. Aktif atıf-çözüm akışı resolve_reference üzerinden gider;
    # bir eserin kaynakçasını grafa açmak GELECEK "citation-graph" işine ait.
    # get_citations gibi sessizce bırakılmaz — burada DÜRÜSTÇE ertelenmiş olarak
    # işaretlenir (Protocol şeklini korur, sahte çağıran uydurulmaz). Bağlanınca
    # (atıf-grafı feature) bu metotlar olduğu gibi kullanılacaktır.

    async def get_references_with_snapshot(
        self, work_id: str
    ) -> tuple[list[CitationEdge], ProviderSnapshot]:
        """Bir eserin referanslarını (referenced_works) CitationEdge listesine eşle
        + ProviderSnapshot döndür. DORMANT: Protocol-tamlığı için var, production
        çağıranı yok (yukarıdaki nota bak); atıf-grafı işinde devreye girer."""
        try:
            raw = await fetch_work_by_id(work_id, settings=self._settings)
        except OpenAlexError as exc:
            status, lims = _map_error_status(exc)
            return [], self.build_snapshot(
                endpoint="get_references", query=work_id, status=status, limitations=lims
            )
        if raw is None:
            return [], self.build_snapshot(
                endpoint="get_references", query=work_id, status="ok", result_count=0
            )
        src = _short_id(raw.get("id")) or _short_id(work_id) or work_id
        edges = [
            CitationEdge(source_id=src, target_id=s)
            for s in (_short_id(r) for r in (raw.get("referenced_works") or []))
            if s
        ]
        return edges, self.build_snapshot(
            endpoint="get_references",
            query=work_id,
            status="ok",
            result_count=len(edges),
        )

    async def get_references(self, work_id: str) -> list[CitationEdge]:
        """ScholarlyProvider.get_references — snapshot'sız sade kenar listesi;
        snapshot status arızalıysa ProviderError yükseltir (sessiz boş-liste yok).
        DORMANT: Protocol-tamlığı, henüz production çağıranı yok (sınıf-içi nota bak)."""
        edges, snap = await self.get_references_with_snapshot(work_id)
        if snap.status in ("failed", "rate_limited", "auth_missing"):
            raise ProviderError(
                f"openalex get_references {snap.status}: {snap.limitations}"
            )
        return edges

    # --- get_citations (DÜRÜST ertelendi) ---------------------------------

    async def get_citations(self, work_id: str) -> list[CitationEdge]:
        """ERTELENDİ: bir eseri ATIF YAPAN eserleri bulmak 'cites:<id>' sorgusu
        gerektirir; openalex_polite bunu açmıyor ve sıfırdan HTTP yazmak yasak.
        Sessiz boş-liste YERİNE dürüst NotImplementedError (spec §Başarı kapısı:
        arıza/eksiklik sessiz boş-liste değildir). İkinci provider/atıf-grafı
        işinde openalex_polite'e 'cites' fonksiyonu eklenince bağlanır."""
        raise NotImplementedError(
            "get_citations deferred: needs a 'cites:<id>' query not yet exposed by "
            "openalex_polite (no silent empty list per evidence_provider_spec.md)"
        )


__all__ = [
    "OPENALEX_PROVIDER_NAME",
    "OPENALEX_PROVIDER_VERSION",
    "OpenAlexProvider",
]
