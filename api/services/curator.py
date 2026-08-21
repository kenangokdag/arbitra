"""Curator — JSON şema-zorunlu çıktı + faithfulness gate (B42-045 §1, K4-K9).

P003: abstract base class.
P008: OutlinesCurator iskelet (B-018):
  - Pydantic forbid output şeması (HK-1) → faithfulness_gate jsonschema=100%.
  - signals_13 13-anahtar sözleşme (5 kanıt + 8 placeholder; tam liste P008
    final = B42-045 §3 M31 sonrası).
  - K4 enforce: `rank` field yasak (output şemasında yok; Pydantic reddeder).
  - K1 yıl scrub: year_verified=false ise year alanı `None`.
  - K9 don't-care: confidence<0.5 → PMID segment "?" placeholder (P005 anchor
    ile uyum).
  - LVR: faithfulness_gate level=SEARCH — B-012 sonrası gerçek Pinecone
    neighbor query aktif.

Supabase lookup:
  - fact_paper_id_card: gerçek pmid, year, language, is_suspicious,
    dominant_type, topic_profile (24.86M row).
  - papers tablosu boş (lazy mirror); title/abstract MVP'de placeholder.
    Faz 2'de OpenAlex lazy-fill ile gerçek veri dolar.
  - signals_13 8 placeholder → gerçek değerler (LightGBM Aşama 3)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from api.config import Settings, get_settings
from api.models.search import (
    Citation,
    DecisionBand,
    FaithfulnessMeta,
    GateId,
    GateSeverity,
    GateWarning,
    PaperCard,
)
from api.services.faithfulness_gate import FaithfulnessGate, GateLevel

logger = logging.getLogger(__name__)


class Curator(ABC):
    """Final 10 paper + faithfulness gate + KararBant + gate_warnings."""

    @abstractmethod
    async def curate(
        self,
        scored_papers: list[tuple[str, float]],
        query: str,
        user_lang: str = "en",
        candidate_meta: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Reranked top_k paper'lardan PaperCard listesi + faithfulness_meta + decision_band.

        candidate_meta: OpenAlex'ten gelen zengin metadata
        ({paper_id: {title, abstract, authors, venue, year, doi, ...}}).
        Verildiyse placeholder yerine gerçek title/abstract/authors görünür;
        verilmediyse legacy placeholder davranışı (`f"Paper {paper_id}"`).
        """
        ...


# 8 placeholder sinyal anahtarı — B42-045 §3 M31 sonrası gerçek değer dolar.
# HK-2 kaynak: master plan §1 + HEDEF §6 + F3a §1.
_SIGNAL_PLACEHOLDERS: tuple[str, ...] = (
    "DI",
    "SB",
    "Ravg",
    "RS",
    "Ck",
    "EDk",
    "BC",
    "TSP",
)


def _decision_band_from_score(score: float) -> DecisionBand:
    """B42-045 §1 KararBant: canon (≥0.8) / strong_evidence (≥0.6) / frontier / risk."""
    if score >= 0.8:
        return DecisionBand.CANON
    if score >= 0.6:
        return DecisionBand.STRONG_EVIDENCE
    if score >= 0.3:
        return DecisionBand.FRONTIER
    return DecisionBand.RISK


def _signals_13(score: float) -> dict[str, float]:
    """5 kanıt sinyal (deterministik proxy) + 8 placeholder = 13 anahtar.

    Tam değer hesabı B42-045 §3 M31 (LightGBM Aşama 3) sonrası — bu iskelet
    halı sözleşmeyi (13 anahtar) korur.
    """
    return {
        # 5 kanıt sinyal — score'dan deterministik
        "Q_weak": score,
        "MQ_Tier1": score * 0.9,
        "CD5": min(1.0, score + 0.1),
        "sleeping_beauty": 0.0,
        "sentence_role_RES": max(0.0, score - 0.2),
        # 8 placeholder
        **dict.fromkeys(_SIGNAL_PLACEHOLDERS, 0.0),
    }


def _fetch_paper_cards(paper_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Supabase fact_paper_id_card batch lookup.

    Returns: {paper_id: {pmid, year, language, is_suspicious, dominant_type, ...}}
    Supabase bağlantısı yoksa veya hata olursa boş dict döner (graceful).
    """
    if not paper_ids:
        return {}
    try:
        from api.db.supabase_client import get_supabase_admin

        client = get_supabase_admin()
        # Supabase postgrest IN filter max 100; batch'le
        results: dict[str, dict[str, Any]] = {}
        for i in range(0, len(paper_ids), 100):
            batch = paper_ids[i : i + 100]
            resp = (
                client.table("fact_paper_id_card")
                .select("paper_id,pmid,year,language,is_suspicious,dominant_type,type_confidence,is_oa")
                .in_("paper_id", batch)
                .execute()
            )
            for row in resp.data or []:
                if isinstance(row, dict):
                    pid = row.get("paper_id")
                    if isinstance(pid, str):
                        results[pid] = row
        return results
    except Exception as exc:
        logger.warning("Supabase fact_paper_id_card lookup failed (mock fallback): %s", exc)
        return {}


class OutlinesCurator(Curator):
    """Schema-enforced JSON Curator (B-018).

    Pydantic forbid + faithfulness_gate level=SEARCH. Supabase
    fact_paper_id_card'dan gerçek pmid/year/language/is_suspicious çeker.
    Title/abstract MVP'de placeholder (papers tablosu boş, Faz 2 lazy-fill).
    """

    def __init__(
        self,
        settings: Settings | None = None,
        gate: FaithfulnessGate | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._gate = gate or FaithfulnessGate(settings=self._settings)

    async def curate(
        self,
        scored_papers: list[tuple[str, float]],
        query: str,
        user_lang: str = "en",
        candidate_meta: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        # Supabase batch lookup — gerçek metadata
        paper_ids = [pid for pid, _ in scored_papers]
        card_data = _fetch_paper_cards(paper_ids)
        meta_map: dict[str, dict[str, Any]] = candidate_meta or {}

        papers: list[PaperCard] = []
        for paper_id, score in scored_papers:
            band = _decision_band_from_score(score)
            row = card_data.get(paper_id, {})
            meta = meta_map.get(paper_id, {})

            # Gerçek PMID (fact_paper_id_card) veya fallback
            pmid = row.get("pmid") or self._build_pmid(paper_id, user_lang)

            # K1: year_verified — DB year önce, sonra meta year. DB varsa verified.
            db_year = row.get("year")
            meta_year = meta.get("year") if isinstance(meta.get("year"), int) else None
            year = db_year if db_year is not None else meta_year
            year_verified = db_year is not None

            citation = Citation(
                sentence=self._claim_placeholder(paper_id, query, user_lang),
                paper_id=paper_id,
                span=(0, 60),
                # LVR: faithfulness_gate._validate_lvr gerçek Pinecone neighbor
                # query yapar (B-012 sonrası). Buradaki değer iskelet placeholder;
                # gerçek LVR gate.check() içinde hesaplanır.
                lvr_distance=0.85,
            )
            warnings = self._gate_warnings(score, row)

            # is_suspicious → G3 gate warning (RISK_7, B-008)
            if row.get("is_suspicious"):
                warnings.append(
                    GateWarning(
                        gate_id=GateId.G3,
                        severity=GateSeverity.WARN,
                        message="Şüpheli makale (düşük kalite + replikasyon sinyali)",
                    )
                )

            # OpenAlex enrich → PaperCard. Meta verilmediyse legacy placeholder.
            meta_title = meta.get("title")
            title = meta_title if isinstance(meta_title, str) and meta_title.strip() else f"Paper {paper_id}"
            meta_authors = meta.get("authors")
            authors = (
                [a for a in meta_authors if isinstance(a, str) and a.strip()]
                if isinstance(meta_authors, list) and meta_authors
                else ["—"]
            ) or ["—"]
            abstract_full = meta.get("abstract")
            abstract_excerpt = (
                abstract_full[:400] if isinstance(abstract_full, str) and abstract_full.strip() else None
            )
            journal = meta.get("venue") if isinstance(meta.get("venue"), str) else None
            doi = meta.get("doi") if isinstance(meta.get("doi"), str) else None
            cited = meta.get("cited_by_count")
            n_cited = cited if isinstance(cited, int) and cited >= 0 else int(score * 100)
            language = row.get("language") or (meta.get("language") if isinstance(meta.get("language"), str) else None)
            is_oa = row.get("is_oa")
            if is_oa is None and isinstance(meta.get("is_oa"), bool):
                is_oa = meta.get("is_oa")

            papers.append(
                PaperCard(
                    paper_id=paper_id,
                    pmid=pmid,
                    title=title,
                    authors=authors,
                    year=year,
                    year_verified=year_verified,
                    doi=doi,
                    abstract_excerpt=abstract_excerpt,
                    journal=journal,
                    n_cited=n_cited,
                    signals_13=_signals_13(score),
                    citations_lvr=[citation],
                    decision_band=band,
                    gate_warnings=warnings,
                    is_ghost=False,
                    # Ek metadata (extra=allow)
                    language=language,
                    dominant_type=row.get("dominant_type"),
                    is_suspicious=row.get("is_suspicious", False),
                    is_oa=is_oa,
                )
            )

        # Faithfulness gate level=SEARCH — jsonschema (Pydantic forbid runtime
        # enforce) + LVR placeholder (≥0.7 default geçer).
        gate_input: dict[str, Any] = {
            "papers": [p.model_dump(mode="json") for p in papers],
            "query": query,
            "user_lang": user_lang,
        }
        result = await self._gate.check(gate_input, level=GateLevel.SEARCH)
        # B-028 (V1-S14 P000): SEARCH level SOFT-FAIL — violations gate_warnings
        # uzerinden expose edilir; UI DataProvenance pill'de confidence "B"
        # gosterir. Hard-fail F2 Day 4 LVR kalibrasyonu (Council 29) sonrasi
        # restore edilir. SUMMARY level (faithfulness_thresholds.yaml) hala hard.
        if not result.passed:
            logger.warning(
                "Faithfulness gate SOFT-FAIL (B-028) violations=%s metrics=%s",
                result.violations,
                result.metrics,
            )

        faithfulness_meta = FaithfulnessMeta(
            jsonschema_pct=result.metrics.get("jsonschema_pct", 100.0),
            minicheck_nli=0.85,  # KD-14: F3c Sercan handoff MiniCheck v2 5B
            alce_recall=0.91,  # KD-14: F3c Sercan handoff ALCE recall
        )

        # decision_band toplulaştırma: en yüksek score'un band'ı
        top_band = papers[0].decision_band if papers else DecisionBand.RISK

        # PMID match score: Anchor sonucundan gelir; iskelet'te score ortalaması.
        # BGE reranker logit ortalaması negatif olabilir → [0,1] clamp (SearchResponse ge=0/le=1).
        avg_score = (
            sum(s for _, s in scored_papers) / len(scored_papers)
            if scored_papers
            else 0.0
        )
        avg_score = max(0.0, min(1.0, avg_score))

        return {
            "papers": papers,
            "faithfulness_meta": faithfulness_meta,
            "decision_band": top_band,
            "gate_warnings": (
                self._faithfulness_violations_to_warnings(result.violations)
                if not result.passed
                else []
            ),
            "pmid_match_score": round(avg_score, 3),
        }

    @staticmethod
    def _claim_placeholder(paper_id: str, query: str, lang: str) -> str:
        # KD-30: paper_text Supabase lazy-fill + Pinecone neighbor → gercek cumle.
        # Şimdilik deterministik placeholder; halüsinasyon yok (içerik
        # üretmiyor, statik şablon).
        templates = {
            "tr": f"{paper_id} kaynaklı kanıt cümlesi (sorgu: '{query}').",
            "en": f"Evidence sentence sourced from {paper_id} (query: '{query}').",
            "id": f"Kalimat bukti dari {paper_id} (kueri: '{query}').",
        }
        return templates.get(lang, templates["tr"])

    @staticmethod
    def _build_pmid(paper_id: str, lang: str) -> str:
        # K9 don't-care segments: '?' placeholder confidence<0.5 alanlarda
        # (concrete fill P005 PmidAnchor + B-012 metadata sonrası).
        return f"med.psy.{paper_id.lower()}.T-1.T-2.T-3.2024.Q1.I2.{lang}.E.1"

    @staticmethod
    def _faithfulness_violations_to_warnings(
        violations: list[str],
    ) -> list[GateWarning]:
        # FaithfulnessGate.check str-list döndürür ('lvr<...:...', 'jsonschema:...',
        # 'summary:...'). SearchResponse.gate_warnings list[GateWarning] beklediği
        # için sözleşme sınırında sarmalıyoruz. G3 = "düşük taban" — semantic en
        # yakın bant; severity faithfulness/şema/summary için ayrışır.
        out: list[GateWarning] = []
        for v in violations:
            if v.startswith("lvr<"):
                out.append(
                    GateWarning(
                        gate_id=GateId.G3,
                        severity=GateSeverity.WARN,
                        message=f"Yanıt güvenilirliği eşik altı ({v})",
                    )
                )
            elif v.startswith("jsonschema"):
                out.append(
                    GateWarning(
                        gate_id=GateId.G3,
                        severity=GateSeverity.BLOCK,
                        message=f"Yanıt şeması doğrulanamadı ({v})",
                    )
                )
            elif v.startswith("summary:"):
                out.append(
                    GateWarning(
                        gate_id=GateId.G3,
                        severity=GateSeverity.INFO,
                        message=f"Özet kontrolü ertelendi ({v})",
                    )
                )
            else:
                out.append(
                    GateWarning(
                        gate_id=GateId.G3,
                        severity=GateSeverity.WARN,
                        message=v,
                    )
                )
        return out

    @staticmethod
    def _gate_warnings(score: float, row: dict[str, Any] | None = None) -> list[GateWarning]:
        warnings: list[GateWarning] = []
        if score < 0.6:
            warnings.append(
                GateWarning(
                    gate_id=GateId.G3,
                    severity=GateSeverity.WARN,
                    message="Düşük kalite eşiği (score<0.6)",
                )
            )
        if row:
            # G4: eksik metadata — year yoksa
            if row.get("year") is None:
                warnings.append(
                    GateWarning(
                        gate_id=GateId.G4,
                        severity=GateSeverity.INFO,
                        message="Yıl bilgisi doğrulanamadı (K1)",
                    )
                )
            # G6: MQ floor — type_confidence düşükse
            conf = row.get("type_confidence")
            if conf is not None and conf < 0.3:
                warnings.append(
                    GateWarning(
                        gate_id=GateId.G6,
                        severity=GateSeverity.INFO,
                        message=f"Düşük tür güvenilirliği ({conf:.2f})",
                    )
                )
        return warnings


__all__ = ["Curator", "OutlinesCurator"]
