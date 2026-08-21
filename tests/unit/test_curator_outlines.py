"""P008 OutlinesCurator unit tests — Pydantic forbid + signals_13 sözleşmesi.

Coverage: 13-anahtar signals dict, decision_band thresholds, gate_warnings G3,
faithfulness gate integration (B-028 soft-fail: warnings gate_warnings'e), K1 yıl
placeholder year_verified=True default, multi-lang claim placeholder.
"""

from __future__ import annotations

import pytest

from api.services.curator import OutlinesCurator
from api.services.faithfulness_gate import (
    FaithfulnessGate,
    GateLevel,
    GateResult,
)

pytestmark = pytest.mark.unit


class _AlwaysFailGate(FaithfulnessGate):
    async def check(  # type: ignore[override]
        self,
        doc: object,
        level: GateLevel = GateLevel.SEARCH,
    ) -> GateResult:
        del doc, level
        return GateResult(
            passed=False,
            level=GateLevel.SEARCH,
            violations=["lvr<0.7:0.30"],
            metrics={"jsonschema_pct": 100.0, "lvr_min": 0.30},
        )


async def test_curator_returns_papers_with_13_signal_keys() -> None:
    curator = OutlinesCurator()
    result = await curator.curate(
        [("W123", 0.9), ("W456", 0.5)], "deep learning medicine", user_lang="en"
    )
    papers = result["papers"]
    assert len(papers) == 2
    for paper in papers:
        assert len(paper.signals_13) == 13
        # 5 kanıt + 8 placeholder anahtar set
        expected_keys = {
            "Q_weak",
            "MQ_Tier1",
            "CD5",
            "sleeping_beauty",
            "sentence_role_RES",
            "DI",
            "SB",
            "Ravg",
            "RS",
            "Ck",
            "EDk",
            "BC",
            "TSP",
        }
        assert set(paper.signals_13.keys()) == expected_keys


async def test_curator_decision_band_thresholds() -> None:
    curator = OutlinesCurator()
    result = await curator.curate(
        [("W1", 0.85), ("W2", 0.65), ("W3", 0.4), ("W4", 0.1)], "q"
    )
    papers = result["papers"]
    bands = [p.decision_band.value for p in papers]
    assert bands[0] == "canon"
    assert bands[1] == "strong_evidence"
    assert bands[2] == "frontier"
    assert bands[3] == "risk"


async def test_curator_low_score_emits_g3_warning() -> None:
    curator = OutlinesCurator()
    result = await curator.curate([("W1", 0.5)], "q")
    paper = result["papers"][0]
    assert any(w.gate_id.value == "G3" for w in paper.gate_warnings)


async def test_curator_high_score_no_warning() -> None:
    curator = OutlinesCurator()
    result = await curator.curate([("W1", 0.95)], "q")
    paper = result["papers"][0]
    # G4 INFO uyarıları test ortamında Supabase olmayınca beklenen; sadece WARN/ERROR kontrol
    from api.models.search import GateSeverity
    assert not any(w.severity == GateSeverity.WARN for w in paper.gate_warnings)


async def test_curator_faithfulness_meta_present() -> None:
    curator = OutlinesCurator()
    result = await curator.curate([("W1", 0.8)], "q")
    meta = result["faithfulness_meta"]
    assert meta.jsonschema_pct == 100.0


async def test_curator_gate_failure_soft_fails_with_warnings() -> None:
    """B-028: SEARCH level gate fail = soft-fail; violations gate_warnings'e gider, 200 doner."""
    curator = OutlinesCurator(gate=_AlwaysFailGate())
    result = await curator.curate([("W1", 0.8)], "q")
    assert result["papers"], "papers list bos olmamali"
    assert result["gate_warnings"], "gate fail oldugunda warnings dolu olmali"
    # F2 Day 4 LVR kalibrasyonu sonrasi hard-fail restore edilirse bu test revize."""


async def test_curator_empty_input_returns_empty_papers() -> None:
    curator = OutlinesCurator()
    result = await curator.curate([], "q")
    assert result["papers"] == []
    assert result["pmid_match_score"] == 0.0
    # decision_band fallback risk (papers empty)
    assert result["decision_band"].value == "risk"


async def test_curator_lang_routing_in_claim_text() -> None:
    curator = OutlinesCurator()
    result_tr = await curator.curate([("W1", 0.8)], "q", user_lang="tr")
    result_en = await curator.curate([("W1", 0.8)], "q", user_lang="en")
    result_id = await curator.curate([("W1", 0.8)], "q", user_lang="id")
    tr_claim = result_tr["papers"][0].citations_lvr[0].sentence
    en_claim = result_en["papers"][0].citations_lvr[0].sentence
    id_claim = result_id["papers"][0].citations_lvr[0].sentence
    assert "kanıt" in tr_claim.lower() or "sorgu" in tr_claim.lower()
    assert "evidence" in en_claim.lower() or "query" in en_claim.lower()
    assert "kueri" in id_claim.lower() or "bukti" in id_claim.lower()


async def test_curator_pmid_match_score_avg() -> None:
    curator = OutlinesCurator()
    result = await curator.curate([("W1", 0.9), ("W2", 0.5)], "q")
    assert result["pmid_match_score"] == pytest.approx(0.7, abs=0.001)
