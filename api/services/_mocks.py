"""Geçici mock implementations P004-P008 concrete impl gelene kadar.

Her concrete impl commit'i (P004 Listener Gemini, P006 PoolRouter RRF, P007 Reranker BGE,
P008 Curator Outlines+LVR) bu dosyadaki MockX sınıfını kaldırır + factory'i swap eder.

P010 mock backend ile /api/search end-to-end 200 dönmeli (mock papers + faithfulness).
"""

from typing import Any

from api.models.search import (
    Citation,
    DecisionBand,
    FaithfulnessMeta,
    GateId,
    GateSeverity,
    GateWarning,
    PaperCard,
)
from api.services.anchor import Anchor
from api.services.curator import Curator
from api.services.listener import Listener
from api.services.pool_router import PoolRouter
from api.services.reranker import Reranker


class MockListener(Listener):
    """P004 fallback: deterministic alt-query üreteci.

    Async ABC'ye uyumlu — gerçek GeminiListener swap'i GEMINI_API_KEY dolu olmadığı
    test/dev'de aynı imza ile yer tutar.
    """

    async def listen(
        self, query: str, k: int = 5, lang: str = "auto"
    ) -> list[str]:
        del lang
        rewrites = [query]
        for i in range(min(k, 3)):
            rewrites.append(f"{query} alt-{i + 1}")
        return rewrites


class MockAnchor(Anchor):
    """P005 PmidAnchor mevcut; bu mock fallback boş corpus için."""

    async def match(self, query: str, top_k: int = 10) -> list[str]:
        del query, top_k
        return []


class MockPoolRouter(PoolRouter):
    """P006 öncesi: deterministic candidate id generator."""

    async def fan_out(
        self,
        sub_queries: list[str],
        anchor_ids: list[str],
        top_k: int = 200,
        filter: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        del sub_queries, filter
        candidates: list[tuple[str, float]] = [(aid, 1.0) for aid in anchor_ids]
        i = 0
        while len(candidates) < min(top_k, 50):
            score = max(0.0, 1.0 - i * 0.02)
            candidates.append((f"W{1000 + i}", score))
            i += 1
        return candidates[:top_k]


class MockReranker(Reranker):
    """P007 fallback: deterministic linear-decay skor (test/dev)."""

    async def rerank(
        self,
        candidates: list[str],
        query: str,
        top_k: int = 10,
        candidate_texts: dict[str, str] | None = None,
    ) -> list[tuple[str, float]]:
        del query, candidate_texts
        return [(c, max(0.0, 1.0 - i * 0.05)) for i, c in enumerate(candidates[:top_k])]


class MockCurator(Curator):
    """P008 fallback (test/dev): deterministic PaperCard list + faithfulness=100/0.85/0.91.

    signals_13 placeholder: 5 kanıtlı sinyal (master plan §1 + HEDEF.md §6 + F3a §1 dokümante).
    Tam 13 sinyal listesi B42-045 §3 M31'den doğrulanacak — Known Debt: OutlinesCurator concrete
    (LightGBM Aşama 3 type_vector girdi + B42-040 12 chip + sentence-role 5-class).
    """

    async def curate(
        self,
        scored_papers: list[tuple[str, float]],
        query: str,
        user_lang: str = "en",
    ) -> dict[str, Any]:
        papers: list[PaperCard] = []
        for paper_id, score in scored_papers:
            band = DecisionBand.CANON if score >= 0.8 else DecisionBand.FRONTIER
            citations = [
                Citation(
                    sentence=f"Mock claim about {paper_id} relating to {query}.",
                    paper_id=paper_id,
                    span=(0, 60),
                    lvr_distance=0.85,
                )
            ]
            warnings: list[GateWarning] = []
            if score < 0.6:
                warnings.append(
                    GateWarning(
                        gate_id=GateId.G3,
                        severity=GateSeverity.WARN,
                        message="Low quality floor",
                    )
                )
            # 5 kanıt sinyal (master §1 + HEDEF §6) + 8 placeholder = 13 sinyal yapısı korunur
            signals: dict[str, float] = {
                "Q_weak": score,
                "MQ_Tier1": score * 0.9,
                "CD5": 0.5,
                "sleeping_beauty": 0.0,
                "sentence_role_RES": 0.4,
                # 8 placeholder — P008'de gerçek değerler (B42-045 §3 M31)
                "DI": 0.0,
                "SB": 0.0,
                "Ravg": 0.0,
                "RS": 0.0,
                "Ck": 0.0,
                "EDk": 0.0,
                "BC": 0.0,
                "TSP": 0.0,
            }
            papers.append(
                PaperCard(
                    paper_id=paper_id,
                    pmid=f"med.psy.{paper_id.lower()}.T-1.T-2.T-3.2024.Q1.I2.{user_lang}.E.1",
                    title=f"Mock paper {paper_id}",
                    authors=["Doe, J.", "Smith, A."],
                    year=2024,
                    year_verified=True,
                    doi=f"10.1000/{paper_id}",
                    abstract_excerpt=f"Mock abstract for {paper_id} (query='{query}').",
                    journal="Mock Journal",
                    n_cited=int(score * 100),
                    signals_13=signals,
                    citations_lvr=citations,
                    decision_band=band,
                    gate_warnings=warnings,
                )
            )
        return {
            "papers": papers,
            "faithfulness_meta": FaithfulnessMeta(
                jsonschema_pct=100.0,
                minicheck_nli=0.85,
                alce_recall=0.91,
            ),
            "decision_band": DecisionBand.CANON,
            "gate_warnings": [],
            "pmid_match_score": 0.78,
        }


__all__ = [
    "MockAnchor",
    "MockCurator",
    "MockListener",
    "MockPoolRouter",
    "MockReranker",
]
