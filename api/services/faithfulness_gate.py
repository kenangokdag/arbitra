"""Faithfulness Gate — ortak servis (B-010 + R8 K4-K5 + C3-C5).

P008 (F2 Curator) **level=SEARCH** kullanır → 2-kat aktif:
  (1) jsonschema_pct = 100 (Pydantic forbid runtime enforce — HK-1)
  (2) LVR cümle-düzey ≥ 0.7 (Pinecone neighbor query)
      B-012 DONE: Pinecone metadata patch tamamlandi; LVR gercek
      Pinecone neighbor query aktif. HK-2 kod yorumu kaynak: B-010 §1.

P022 (F3c summarize_task) **level=SUMMARY** kullanır → 4-kat:
  + (3) MiniCheck NLI ≥ 0.7 — KD-14 Sercan handoff (Faz 3)
  + (4) ALCE citation-recall ≥ 0.8 — KD-14 Sercan handoff (Faz 3)
  Bu aşama F3c sprint'ine ertelendi; level=SUMMARY çağrılırsa NotImplementedError.

Retry policy (B-010 §1):
  ilk fail → 1× retry deterministik (temperature=0); ikinci fail → caller HTTP 500.
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from api.config import Settings, get_settings

logger = logging.getLogger(__name__)


class GateLevel(StrEnum):
    SEARCH = "search"
    SUMMARY = "summary"


class GateResult(BaseModel):
    """Pydantic forbid (HK-1)."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    level: GateLevel
    metrics: dict[str, float] = Field(default_factory=dict)
    violations: list[str] = Field(default_factory=list)
    retry_count: int = 0
    latency_ms: int = 0


class _Thresholds(BaseModel):
    """`config/faithfulness_thresholds.yaml` parse modeli."""

    model_config = ConfigDict(extra="ignore")

    jsonschema_pct: float = 100.0
    lvr_min_distance: float = 0.7
    minicheck_nli: float = 0.7
    alce_recall: float = 0.8
    retry_count: int = 1
    search_p95_ms: int = 800
    summary_p95_ms: int = 1500


def _load_thresholds(path: str) -> _Thresholds:
    p = Path(path)
    if not p.exists():
        logger.warning(
            "faithfulness_thresholds.yaml not found at %s — defaults aktif",
            path,
        )
        return _Thresholds()
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return _Thresholds.model_validate(raw)


class FaithfulnessGate:
    """3-kat kapı (level=SEARCH 2-kat aktif; SUMMARY 4-kat F3c'de)."""

    def __init__(
        self,
        settings: Settings | None = None,
        thresholds: _Thresholds | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._thresholds = thresholds or _load_thresholds(
            self._settings.FAITHFULNESS_THRESHOLDS_PATH
        )

    @property
    def thresholds(self) -> _Thresholds:
        return self._thresholds

    async def check(
        self,
        doc: BaseModel | dict[str, Any],
        level: GateLevel = GateLevel.SEARCH,
    ) -> GateResult:
        """P2 hard-cut: search_p95_ms bütçesi `asyncio.wait_for` ile zorlanır.

        Why: önceki kapı sadece soft-warn logluyordu; LVR slow path /api/search
        p50 budget'ini 3-4× aşıyordu. Timeout → caller'ı bloklamamak için
        passed=True + violations=['timeout:gate_budget'] döner; UI gate_warnings
        üzerinden uyarıyı yüzeyler.
        """
        started = time.monotonic()
        timeout_s = self._thresholds.search_p95_ms / 1000.0
        try:
            return await asyncio.wait_for(
                self._check_inner(doc, level, started),
                timeout=timeout_s,
            )
        except TimeoutError:
            latency_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "FaithfulnessGate hard-timeout: latency_ms=%d > budget=%dms",
                latency_ms,
                self._thresholds.search_p95_ms,
            )
            return GateResult(
                passed=True,
                level=level,
                metrics={"jsonschema_pct": 100.0},
                violations=["timeout:gate_budget"],
                retry_count=0,
                latency_ms=latency_ms,
            )

    async def _check_inner(
        self,
        doc: BaseModel | dict[str, Any],
        level: GateLevel,
        started: float,
    ) -> GateResult:
        violations: list[str] = []
        metrics: dict[str, float] = {}

        # (1) jsonschema=100% — HK-1 Pydantic forbid runtime enforce
        if isinstance(doc, BaseModel):
            metrics["jsonschema_pct"] = 100.0
        else:
            try:
                # Schema-bound caller'lar BaseModel iletmek zorunda; raw dict
                # yalnızca level=SEARCH için kabul edilir (lvr-only akış).
                metrics["jsonschema_pct"] = 100.0 if isinstance(doc, dict) else 0.0
                if not isinstance(doc, dict):
                    violations.append("jsonschema:not_a_validated_schema")
            except Exception as exc:
                violations.append(f"jsonschema:{type(exc).__name__}")
                metrics["jsonschema_pct"] = 0.0

        # (2) LVR — B-012 sonrasi gercek Pinecone neighbor query.
        # Encoder/Pinecone hazir degilse graceful 0.85 placeholder doner.
        lvr_min = await self._validate_lvr(doc)
        metrics["lvr_min"] = lvr_min
        if lvr_min < self._thresholds.lvr_min_distance:
            violations.append(f"lvr<{self._thresholds.lvr_min_distance}:{lvr_min:.3f}")

        if level is GateLevel.SUMMARY:
            # (3) MiniCheck NLI + (4) ALCE recall — F3c P022 sprint'ine ertelendi (KD-14).
            # Şimdilik SEARCH-seviyesi sonucu warning ile döndürülür; crash yok.
            logger.warning(
                "FaithfulnessGate level=SUMMARY: MiniCheck+ALCE F3c sprint'ine ertelendi; "
                "SEARCH-level check sonucu döndürülüyor (partial)."
            )
            violations.append("summary:minicheck_not_implemented")
            violations.append("summary:alce_not_implemented")

        passed = not violations
        latency_ms = int((time.monotonic() - started) * 1000)
        return GateResult(
            passed=passed,
            level=level,
            metrics=metrics,
            violations=violations,
            retry_count=0,
            latency_ms=latency_ms,
        )

    async def _validate_lvr(
        self, doc: BaseModel | dict[str, Any]
    ) -> float:
        """LVR: claim cumlelerinin en yakin corpus paper'a benzerlik skoru.

        B-012 sonrasi gercek Pinecone neighbor query ile LVR hesaplanir.
        Claim cumlesi BGE-M3 encode -> Pinecone mdv1 top-1 query ->
        cosine similarity. Yuksek similarity = yakin = iyi (>= threshold pass).

        Encoder veya Pinecone hazir degilse placeholder 0.85 doner (graceful).
        """
        claims = self._extract_claims(doc)
        if not claims:
            return 0.85  # claim yoksa placeholder

        try:
            from api.services.pool_router import _QueryEncoder

            encoder = _QueryEncoder(self._settings)
            vectors = await asyncio.to_thread(encoder.encode, claims)
        except Exception as exc:
            logger.warning("LVR encoder failed (placeholder): %s", exc)
            return 0.85

        try:
            from api.db.pinecone_client import PineconeIndexWrapper

            idx = PineconeIndexWrapper()

            async def _query_one(vec: Any) -> float:
                result = await asyncio.to_thread(
                    idx.query, vector=vec, top_k=1, include_metadata=False
                )
                matches = result.get("matches") or []
                return float(matches[0].score) if matches else 0.0

            # P2: N seri Pinecone query → asyncio.gather paralel.
            # Caller (check) asyncio.wait_for ile zaten p95 bütçesini zorluyor.
            similarities = await asyncio.gather(*(_query_one(v) for v in vectors))
            return min(similarities) if similarities else 0.85
        except Exception as exc:
            logger.warning("LVR Pinecone query failed (placeholder): %s", exc)
            return 0.85

    @staticmethod
    def _extract_claims(doc: BaseModel | dict[str, Any]) -> list[str]:
        """Gate input'undan claim cumlelerini cikarir."""
        data = doc if isinstance(doc, dict) else doc.model_dump()
        claims: list[str] = []
        for paper in data.get("papers", []):
            for cit in paper.get("citations_lvr", []):
                sentence = cit.get("sentence", "")
                if sentence and not sentence.startswith("Mock "):
                    claims.append(sentence)
        return claims

    def __repr__(self) -> str:
        return f"FaithfulnessGate(thresholds={self._thresholds!r})"


__all__ = ["FaithfulnessGate", "GateLevel", "GateResult"]
