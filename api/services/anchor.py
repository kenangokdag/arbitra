"""Anchor — PMID 12-segment partial match + OpenAlex semantic anchor (B42-045 K6).

PMID format: `D.F.S.T1.T2.T3.Y.Q.I.L.R.V` (12 sabit segment, dot-separated).
Wildcard `*` her segment için izinli; `?` K9 confidence<0.5 placeholder.
OpenAlexAnchor: natural-language query → top-cited W-IDs as anchor seeds.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import ClassVar

import httpx

logger = logging.getLogger(__name__)

PMID_SEGMENT_COUNT = 12
SEGMENT_NAMES: tuple[str, ...] = (
    "D",
    "F",
    "S",
    "T1",
    "T2",
    "T3",
    "Y",
    "Q",
    "I",
    "L",
    "R",
    "V",
)
WILDCARD = "*"
PLACEHOLDER = "?"  # K9: confidence<0.5
_PMID_TOKEN_PATTERN = re.compile(
    r"[A-Za-z0-9*?_-]+(?:\.[A-Za-z0-9*?_-]+){" + str(PMID_SEGMENT_COUNT - 1) + r"}"
)


class Anchor(ABC):
    """Anchor seed resolver → top 3-10 paper_ids for pool router boost."""

    @abstractmethod
    async def match(self, query: str, top_k: int = 10) -> list[str]:
        """Query → anchor paper_id list. Natural-language queries supported."""
        ...


@dataclass(frozen=True)
class PartialPMID:
    """PMID 12-segment representation; None = absent (don't-care), str = exact/wildcard/placeholder."""

    D: str | None = None
    F: str | None = None
    S: str | None = None
    T1: str | None = None
    T2: str | None = None
    T3: str | None = None
    Y: str | None = None
    Q: str | None = None
    I: str | None = None  # noqa: E741 — single-letter spec'ten gelen segment adı
    L: str | None = None
    R: str | None = None
    V: str | None = None

    # Field order (Python dataclass guarantees insertion order)
    SEGMENTS: ClassVar[tuple[str, ...]] = SEGMENT_NAMES

    def to_string(self) -> str:
        """Render `D.F.S.T1.T2.T3.Y.Q.I.L.R.V`; None segment'lere `?` yerleşir (K9)."""
        return ".".join(getattr(self, seg) or PLACEHOLDER for seg in self.SEGMENTS)

    def non_null_count(self) -> int:
        """Set olan (None olmayan) segment sayısı."""
        return sum(1 for seg in self.SEGMENTS if getattr(self, seg) is not None)


def parse_pmid(raw: str) -> PartialPMID | None:
    """Dot-separated 12-segment PMID stringini parse et.

    Returns None if segment count != 12.
    Empty string segment → None (don't-care).
    `?` placeholder ve `*` wildcard segment olarak korunur.
    """
    if not raw or not isinstance(raw, str):
        return None
    parts = raw.split(".")
    if len(parts) != PMID_SEGMENT_COUNT:
        return None
    kwargs: dict[str, str | None] = {}
    for seg_name, value in zip(SEGMENT_NAMES, parts, strict=True):
        kwargs[seg_name] = value if value else None
    return PartialPMID(**kwargs)


def extract_partial_from_query(query: str) -> PartialPMID | None:
    """Query metninden PMID-like substring çıkar; yoksa None."""
    if not query:
        return None
    match = _PMID_TOKEN_PATTERN.search(query)
    if not match:
        return None
    return parse_pmid(match.group(0))


def score_match(query_pmid: PartialPMID, corpus_pmid: PartialPMID) -> float:
    """Segment-by-segment match score ∈ [0, 1].

    Scoring kuralı:
      - query None → don't-care (denominator'a sayılmaz).
      - query `*` wildcard → don't-care (denominator'a sayılmaz; "buradan herhangi değer").
      - query `?` placeholder (K9) → don't-care (denominator'a sayılmaz).
      - query exact eşleşme → +1.
      - query mismatch → 0.

    Eğer denominator 0 ise (query tamamen don't-care) → 0.0 döner.
    """
    matches = 0
    denominator = 0
    for seg_name in SEGMENT_NAMES:
        q_val = getattr(query_pmid, seg_name)
        c_val = getattr(corpus_pmid, seg_name)
        if q_val is None or q_val in (PLACEHOLDER, WILDCARD):
            continue
        denominator += 1
        if q_val == c_val:
            matches += 1
    if denominator == 0:
        return 0.0
    return matches / denominator


class PmidAnchor(Anchor):
    """In-memory PMID corpus üzerinde 12-segment partial match.

    P005: in-memory corpus (test/dev). P005-followup: Supabase fact_paper_id_card.pmid join.
    """

    DEFAULT_THRESHOLD = 0.6

    def __init__(self, corpus: list[str] | None = None, threshold: float | None = None) -> None:
        self._corpus: list[PartialPMID] = []
        if corpus:
            for raw in corpus:
                parsed = parse_pmid(raw)
                if parsed is not None:
                    self._corpus.append(parsed)
        self._threshold = threshold if threshold is not None else self.DEFAULT_THRESHOLD

    async def match(self, query: str, top_k: int = 10) -> list[str]:
        partial = extract_partial_from_query(query)
        if partial is None or partial.non_null_count() == 0:
            return []
        scored: list[tuple[PartialPMID, float]] = []
        for corpus_pmid in self._corpus:
            score = score_match(partial, corpus_pmid)
            if score >= self._threshold:
                scored.append((corpus_pmid, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return [pmid.to_string() for pmid, _ in scored[:top_k]]


_OPENALEX_BASE = "https://api.openalex.org"


class OpenAlexAnchor(Anchor):
    """OpenAlex search-based anchor — natural-language query → top-cited W-IDs.

    Falls back to PMID extraction first; if no PMID found, calls OpenAlex search.
    """

    def __init__(self, email: str | None = None, timeout: float = 8.0) -> None:
        self._email = email
        self._timeout = timeout
        self._pmid_anchor = PmidAnchor()

    async def match(self, query: str, top_k: int = 10) -> list[str]:
        # Try PMID extraction first
        pmid_results = await self._pmid_anchor.match(query, top_k=top_k)
        if pmid_results:
            return pmid_results

        # Natural-language: call OpenAlex search
        params: dict = {
            "search": query,
            "per-page": str(min(top_k, 10)),
            "sort": "cited_by_count:desc",
            "select": "id",
        }
        if self._email:
            params["mailto"] = self._email

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{_OPENALEX_BASE}/works", params=params)
                resp.raise_for_status()
                data = resp.json()
            ids: list[str] = []
            for work in data.get("results", []):
                raw_id = work.get("id", "")
                # id comes as "https://openalex.org/W123456"
                wid = raw_id.split("/")[-1]
                if wid.startswith("W"):
                    ids.append(wid)
            logger.debug("OpenAlexAnchor query=%r → %d anchors", query[:60], len(ids))
            return ids[:top_k]
        except Exception as exc:
            logger.warning("OpenAlexAnchor failed query=%r: %s", query[:60], exc)
            return []


__all__ = [
    "PLACEHOLDER",
    "PMID_SEGMENT_COUNT",
    "SEGMENT_NAMES",
    "WILDCARD",
    "Anchor",
    "OpenAlexAnchor",
    "PartialPMID",
    "PmidAnchor",
    "extract_partial_from_query",
    "parse_pmid",
    "score_match",
]


_ = fields  # mypy-friendly: dataclass fields() iter helper future use
