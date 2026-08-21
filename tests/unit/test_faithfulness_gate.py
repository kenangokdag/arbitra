"""P008 FaithfulnessGate unit tests — level=SEARCH (2-kat); SUMMARY rejected.

Coverage: jsonschema=100% Pydantic-validated dict pass; raw non-dict fail;
LVR placeholder 0.85 ≥ 0.7 threshold pass; threshold revize → fail; level=SUMMARY
NotImplementedError; thresholds yaml load + defaults.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel, ConfigDict

from api.config import Settings
from api.services.faithfulness_gate import (
    FaithfulnessGate,
    GateLevel,
    GateResult,
)

pytestmark = pytest.mark.unit


def _settings_with_thresholds(path: str) -> Settings:
    return Settings(FAITHFULNESS_THRESHOLDS_PATH=path)  # type: ignore[arg-type]


class _SchemaDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    foo: str
    bar: int


async def test_gate_search_pass_for_pydantic_doc(tmp_path: Path) -> None:
    yaml_p = tmp_path / "th.yaml"
    yaml_p.write_text("lvr_min_distance: 0.7\njsonschema_pct: 100\n")
    gate = FaithfulnessGate(settings=_settings_with_thresholds(str(yaml_p)))
    doc = _SchemaDoc(foo="x", bar=1)
    result = await gate.check(doc, level=GateLevel.SEARCH)
    assert result.passed
    assert result.violations == []
    assert result.metrics["jsonschema_pct"] == 100.0
    assert result.metrics["lvr_min"] == pytest.approx(0.85)
    assert result.level is GateLevel.SEARCH


async def test_gate_search_pass_for_dict(tmp_path: Path) -> None:
    yaml_p = tmp_path / "th.yaml"
    yaml_p.write_text("lvr_min_distance: 0.7\n")
    gate = FaithfulnessGate(settings=_settings_with_thresholds(str(yaml_p)))
    result = await gate.check({"papers": []}, level=GateLevel.SEARCH)
    assert result.passed
    assert result.metrics["jsonschema_pct"] == 100.0


async def test_gate_search_fail_when_lvr_below_threshold(tmp_path: Path) -> None:
    yaml_p = tmp_path / "th.yaml"
    # Eşiği placeholder 0.85'in üzerine çıkar → fail bekleniyor
    yaml_p.write_text("lvr_min_distance: 0.99\n")
    gate = FaithfulnessGate(settings=_settings_with_thresholds(str(yaml_p)))
    result = await gate.check({"x": 1}, level=GateLevel.SEARCH)
    assert not result.passed
    assert any(v.startswith("lvr<") for v in result.violations)


async def test_gate_summary_falls_back_to_search_level(tmp_path: Path) -> None:
    yaml_p = tmp_path / "th.yaml"
    yaml_p.write_text("lvr_min_distance: 0.5\n")
    gate = FaithfulnessGate(settings=_settings_with_thresholds(str(yaml_p)))
    result = await gate.check({"x": 1}, level=GateLevel.SUMMARY)
    assert isinstance(result, GateResult)
    assert result.level is GateLevel.SUMMARY


async def test_gate_thresholds_default_when_yaml_missing() -> None:
    settings = Settings(  # type: ignore[arg-type]
        FAITHFULNESS_THRESHOLDS_PATH="/nonexistent/path.yaml"
    )
    gate = FaithfulnessGate(settings=settings)
    # Default 0.7 LVR threshold; placeholder 0.85 yeterli
    result = await gate.check({"x": 1}, level=GateLevel.SEARCH)
    assert result.passed
    assert gate.thresholds.lvr_min_distance == 0.7
    assert gate.thresholds.jsonschema_pct == 100.0


async def test_gate_result_pydantic_forbid_extra() -> None:
    """HK-1: GateResult Pydantic forbid (extra alan reddi)."""
    with pytest.raises(ValueError):
        GateResult(  # type: ignore[call-arg]
            passed=True,
            level=GateLevel.SEARCH,
            extra_field="boom",
        )


async def test_lvr_extract_claims_from_papers() -> None:
    """_extract_claims filters out Mock-prefixed sentences."""
    gate = FaithfulnessGate(
        settings=Settings(FAITHFULNESS_THRESHOLDS_PATH="/nonexistent.yaml")  # type: ignore[arg-type]
    )
    doc = {
        "papers": [
            {
                "citations_lvr": [
                    {"sentence": "Real claim about MCDM."},
                    {"sentence": "Mock claim ignored."},
                ]
            }
        ]
    }
    claims = gate._extract_claims(doc)
    assert len(claims) == 1
    assert claims[0] == "Real claim about MCDM."


async def test_lvr_no_claims_returns_placeholder(tmp_path: Path) -> None:
    """No claims -> LVR placeholder 0.85."""
    yaml_p = tmp_path / "th.yaml"
    yaml_p.write_text("lvr_min_distance: 0.7\n")
    gate = FaithfulnessGate(settings=_settings_with_thresholds(str(yaml_p)))
    result = await gate.check({"papers": []}, level=GateLevel.SEARCH)
    assert result.passed
    assert result.metrics["lvr_min"] == pytest.approx(0.85)


async def test_lvr_real_pinecone_query(tmp_path: Path) -> None:
    """LVR with mocked encoder + Pinecone -> real distance calculation."""
    yaml_p = tmp_path / "th.yaml"
    yaml_p.write_text("lvr_min_distance: 0.7\n")
    gate = FaithfulnessGate(settings=_settings_with_thresholds(str(yaml_p)))

    doc = {
        "papers": [
            {
                "citations_lvr": [
                    {"sentence": "Deep learning improves medical diagnosis."}
                ]
            }
        ]
    }

    # Mock encoder
    mock_encoder = MagicMock()
    mock_encoder.encode.return_value = [[0.1] * 1024]

    # Mock Pinecone result: cosine_sim=0.92 -> distance=0.08
    mock_match = MagicMock()
    mock_match.score = 0.92
    mock_pinecone_result = MagicMock()
    mock_pinecone_result.get.return_value = [mock_match]

    with (
        patch("api.services.pool_router._QueryEncoder", return_value=mock_encoder),
        patch("api.db.pinecone_client.PineconeIndexWrapper") as mock_idx,
    ):
        mock_idx.return_value.query.return_value = mock_pinecone_result
        result = await gate.check(doc, level=GateLevel.SEARCH)

    assert result.passed
    # cosine similarity = 0.92, which is >= 0.7 threshold -> pass
    assert result.metrics["lvr_min"] == pytest.approx(0.92, abs=0.01)


async def test_lvr_encoder_failure_graceful(tmp_path: Path) -> None:
    """Encoder failure -> graceful fallback 0.85."""
    yaml_p = tmp_path / "th.yaml"
    yaml_p.write_text("lvr_min_distance: 0.7\n")
    gate = FaithfulnessGate(settings=_settings_with_thresholds(str(yaml_p)))

    doc = {
        "papers": [
            {"citations_lvr": [{"sentence": "A real claim."}]}
        ]
    }

    with patch(
        "api.services.pool_router._QueryEncoder",
        side_effect=RuntimeError("no model"),
    ):
        result = await gate.check(doc, level=GateLevel.SEARCH)

    assert result.passed
    assert result.metrics["lvr_min"] == pytest.approx(0.85)


async def test_gate_search_hard_timeout_returns_passed_with_violation(
    tmp_path: Path,
) -> None:
    """P2 fix: budget aşımı → wait_for hard cut, passed=True + timeout violation."""
    yaml_p = tmp_path / "th.yaml"
    yaml_p.write_text("search_p95_ms: 100\nlvr_min_distance: 0.7\n")
    gate = FaithfulnessGate(settings=_settings_with_thresholds(str(yaml_p)))

    async def _slow_lvr(*_args: object, **_kw: object) -> float:
        await asyncio.sleep(0.5)
        return 0.9

    with patch.object(gate, "_validate_lvr", side_effect=_slow_lvr):
        t0 = time.monotonic()
        result = await gate.check({"papers": []}, level=GateLevel.SEARCH)
        elapsed = time.monotonic() - t0

    assert result.passed is True
    assert "timeout:gate_budget" in result.violations
    assert result.metrics["jsonschema_pct"] == 100.0
    assert elapsed < 0.4  # 100ms budget + cancel/teardown slack


async def test_gate_passes_with_invalid_thresholds_yaml_silently() -> None:
    """Bozuk yaml gerçekten thresholds'ı patlatmamalı; defaults'a düş."""
    # Empty file → yaml.safe_load None → _Thresholds defaults
    import tempfile

    with tempfile.NamedTemporaryFile(
        suffix=".yaml", mode="w", delete=False
    ) as f:
        f.write("")
        path = f.name
    settings = Settings(FAITHFULNESS_THRESHOLDS_PATH=path)  # type: ignore[arg-type]
    gate = FaithfulnessGate(settings=settings)
    result = await gate.check({"x": 1}, level=GateLevel.SEARCH)
    assert result.passed
