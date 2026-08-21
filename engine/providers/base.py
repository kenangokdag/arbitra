"""FAZ D — ScholarlyProvider abstraction (literatür/atıf/kanıt katmanı).

Sözleşme: docs/worldclass/SPECS/evidence_provider_spec.md.
Amaç: Arbitra'nın atıf/kanıt katmanı TEK bir providera bağlı kalmasın; OpenAlex,
Crossref, Semantic Scholar, PubMed veya gelecekteki kaynaklar adapter olarak
eklenebilsin (evidence_provider_spec.md §Amaç).

Bu modül SAF'tır (yalnız pydantic + stdlib). api/* veya engine/academic/* import
ETMEZ → katman tersine bağımlılık yok; api.models.review bunu güvenle import eder
(ProviderSnapshot evidence provenance'ında taşınır). Gerçek HTTP/çözüm DELEGE edilir:
OpenAlexProvider (engine/providers/openalex.py) → api/services/openalex_polite.py +
api/services/review_citation_service.py (kron-mücevher çözüm/dürüstlük mantığı
YENİDEN YAZILMAZ, sarılır).
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

# --- provider çağrı durumu (spec §ProviderSnapshot status değerleri) ---------

ProviderStatus = Literal["ok", "degraded", "failed", "rate_limited", "auth_missing"]
"""evidence_provider_spec.md §ProviderSnapshot — 5 değer.
  ok            : çağrı başarılı, sonuç döndü.
  degraded      : kısmî/azaltılmış sonuç (retry sonrası kalıcı bozulma).
  failed        : malformed response / beklenmeyen sağlayıcı hatası.
  rate_limited  : 429 / hız limiti.
  auth_missing  : kimlik/yapılandırma eksik (örn OPENALEX_EMAIL yok) — fake result YOK.
"""

# ResolvedReference.status — api.models.review.CitationStatus ile BİREBİR aynı
# değerler (HK-3 'yok ≠ uydurma'). base SAF kalsın diye literal burada YENİDEN
# yazılır (api'yi import etmez); anlam tek kaynak: api/models/review.py:42-47.
ResolutionStatus = Literal[
    "resolved",
    "not_found_in_index",
    "fabricated",
    "retracted",
]


class ProviderError(Exception):
    """Sağlayıcı çağrısı sessiz boş-listeye düşürülemez (spec §Başarı kapısı:
    'Provider failure sessiz boş liste değildir'). Adapter'in bare Protocol
    metotları arıza durumunda bunu fırlatır; *_with_snapshot varyantları ise
    arızayı GÖRÜNÜR (status=failed/...) snapshot olarak döndürür."""


# --- snapshot (spec §ProviderSnapshot) --------------------------------------


class ProviderSnapshot(BaseModel):
    """Tek provider çağrısının rapor-provenance kaydı (spec §ProviderSnapshot).

    Her evidence sonucu provider + status taşır (spec §Başarı kapısı). Arıza
    sessiz boş-liste DEĞİL, status alanında görünür."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    provider_version: str
    query_hash: str
    request_time: datetime
    status: ProviderStatus
    result_count: int = 0
    cache_hit: bool = False
    limitations: list[str] = Field(default_factory=list)


# --- caching key / query_hash (spec §Caching) -------------------------------


def query_hash(*, provider: str, endpoint: str, query: str, provider_version: str) -> str:
    """Deterministik cache/provenance anahtarı.

    spec §Caching cache key = provider + endpoint + normalized query + provider
    version. datetime/random YOK → aynı sorgu aynı hash (test edilebilir).
    'normalized query' = küçük harf + tek-boşluk (whitespace çöker)."""
    normalized = " ".join(query.lower().split())
    payload = "\x1f".join((provider, endpoint, normalized, provider_version))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --- tipli veri şekilleri (Protocol'ün referansladığı) ----------------------
# Yalnız openalex_polite'in GERÇEKTEN sağladığı alanlar (anti-halüsinasyon):
# openalex_polite._to_preview (api/services/openalex_polite.py:80-102) +
# _resolve_via_work (review_citation_service.py:179-205) çıktısına sadık.


class ScholarlySearchQuery(BaseModel):
    """search_works girdisi → openalex_polite.search_works_raw parametreleri
    (api/services/openalex_polite.py:307-334)."""

    model_config = ConfigDict(extra="forbid")

    query: str
    limit: int = Field(5, ge=1, le=25)
    filters: list[str] = Field(default_factory=list)  # OpenAlex filter ifadeleri
    sort: str = "relevance_score:desc"


class Work(BaseModel):
    """Bir bilimsel eser — OpenAlex Work payload'ından İNDİRGENMİŞ.

    Alanlar openalex_polite._to_preview (api/services/openalex_polite.py:80-102)
    ile aynı kaynaktan; ek olarak is_retracted (review_citation_service.py:183) +
    referenced_work_ids (OpenAlex 'referenced_works'; bkz api/routes/search.py:72
    'referenced_works_count' select alanı — referenced_works ailesi mevcut).
    OpenAlex tam-metin SAĞLAMAZ → abstract en üst doğrulama (limitation: abstract only)."""

    model_config = ConfigDict(extra="forbid")

    openalex_id: str | None = None
    doi: str | None = None
    title: str | None = None
    abstract: str | None = None
    year: int | None = None
    venue: str | None = None
    authors: list[str] = Field(default_factory=list)
    cited_by_count: int = 0
    is_retracted: bool = False
    referenced_work_ids: list[str] = Field(default_factory=list)


class RawReference(BaseModel):
    """resolve_reference girdisi — çözümlemeden ÖNCEKi referans (ParsedReference'in
    parse-alanları, api/models/review.py:91-104)."""

    model_config = ConfigDict(extra="forbid")

    index: int = 0
    raw: str = ""
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    venue: str | None = None


class ResolvedReference(BaseModel):
    """resolve_reference çıktısı — kron-mücevher çözüm sonucunun Protocol şekli.
    api/services/review_citation_service.resolve_reference ParsedReference döner;
    adapter onu buna eşler (status/openalex_id/is_retracted/evidence + Work)."""

    model_config = ConfigDict(extra="forbid")

    raw_index: int
    status: ResolutionStatus
    openalex_id: str | None = None
    is_retracted: bool = False
    evidence: str | None = None
    work: Work | None = None


class CitationEdge(BaseModel):
    """Atıf grafı kenarı. get_references: source=work_id, target=atıf yapılan eser.
    get_citations: source=atıf yapan eser, target=work_id."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    target_id: str


# --- Protocol (spec §Provider Protocol) -------------------------------------


@runtime_checkable
class ScholarlyProvider(Protocol):
    """Literatür/atıf sağlayıcı sözleşmesi (spec §Provider Protocol).

    Business logic raw provider URL bilmez (spec §Başarı kapısı): tüketici bu
    Protocol'e konuşur, HTTP/endpoint adapter'in içinde kalır."""

    name: str
    version: str

    async def search_works(self, query: ScholarlySearchQuery) -> list[Work]: ...

    async def resolve_reference(self, reference: RawReference) -> ResolvedReference: ...

    async def get_work(self, work_id: str) -> Work | None: ...

    async def get_references(self, work_id: str) -> list[CitationEdge]: ...

    async def get_citations(self, work_id: str) -> list[CitationEdge]: ...


__all__ = [
    "CitationEdge",
    "ProviderError",
    "ProviderSnapshot",
    "ProviderStatus",
    "RawReference",
    "ResolutionStatus",
    "ResolvedReference",
    "ScholarlyProvider",
    "ScholarlySearchQuery",
    "Work",
    "query_hash",
]
