"""FAZ D — ScholarlyProvider abstraction katmanı (evidence_provider_spec.md).

NOT: yalnız SAF `base` sembolleri burada re-export edilir. `openalex` BURADA
import EDİLMEZ — o api.services.* import eder; paket __init__'te import edilirse
api.models.review → engine.providers (paket) → openalex → api.services →
api.models.review döngüsü oluşur. OpenAlexProvider açıkça
`from engine.providers.openalex import OpenAlexProvider` ile alınır.
"""

from __future__ import annotations

from engine.providers.base import (
    CitationEdge,
    ProviderError,
    ProviderSnapshot,
    ProviderStatus,
    RawReference,
    ResolutionStatus,
    ResolvedReference,
    ScholarlyProvider,
    ScholarlySearchQuery,
    Work,
    query_hash,
)

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
