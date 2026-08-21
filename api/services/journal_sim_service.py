"""F13-S9 6.4 Dergi Simülasyonu — journal_sim_service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S9
RTF:  Page_Design/Sayfa_Plani_v2/6.4_dergi_simulasyonu.rtf §Plan-Detayı

3 fonksiyon:
  1. reviewer_3persona(...)   → 3 paralel Flash, scan_results.reviewer_3persona
  2. statcheck_run(...)       → Nuijten regex + scipy compute → scan_results.statcheck
  3. journal_calibration(...) → review_distribution.json + verdict tahmini

V1 notu: coherence-check (sentence-transformers cosine < 0.55) RTF (8) henüz
yok — calibration-bound olarak sabaha bırakıldı (overnight raporu).
kmkarakaya HF dergitarama runtime API V2'ye ertelendi; V1 sadece manuel JSON +
field_average fallback.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from scipy.stats import chi2 as _chi2_dist  # type: ignore[import-untyped]
from scipy.stats import f as _f_dist
from scipy.stats import t as _t_dist

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.journal_sim import (
    JournalCalibrationResponse,
    JournalDistribution,
    Reviewer3PersonaRequest,
    Reviewer3PersonaResponse,
    ReviewerPersonaOutput,
    StatcheckRequest,
    StatcheckResponse,
    StatcheckResult,
    StatcheckSummary,
    Verdict,
)
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_ENGINE_ROOT = Path(__file__).resolve().parents[2] / "engine"
_PERSONAS_DIR = _ENGINE_ROOT / "personas" / "journal"
_STATCHECK_PATH = _ENGINE_ROOT / "statcheck" / "multilingual.json"
_REVIEW_DIST_PATH = _ENGINE_ROOT / "journals" / "review_distribution.json"

_PERSONAS: tuple[str, str, str] = ("skeptik", "sempatik", "yontemci")


# ── ownership ───────────────────────────────────────────────────────────────


def _fetch_session(session_id: UUID, user_id: UUID) -> dict[str, Any]:
    """defense_session + sahiplik (projects.user_id JOIN)."""
    client = get_supabase_admin()
    resp = (
        client.table("defense_session")
        .select("id,project_id,scan_results")
        .eq("id", str(session_id))
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        raise LookupError("session_not_found")
    row = rows[0]
    proj_resp = (
        client.table("projects")
        .select("id")
        .eq("id", str(row["project_id"]))
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not (proj_resp.data or []):
        raise PermissionError("session_not_owned")
    return row


def _merge_scan_results(
    existing: dict[str, Any], patch: dict[str, Any]
) -> dict[str, Any]:
    """scan_results JSONB shallow merge — patch anahtarları override eder."""
    merged = dict(existing or {})
    merged.update(patch)
    return merged


async def _persist_scan_results(session_id: UUID, scan_results: dict[str, Any]) -> None:
    def _update() -> Any:
        return (
            get_supabase_admin()
            .table("defense_session")
            .update({"scan_results": scan_results})
            .eq("id", str(session_id))
            .execute()
        )

    await supabase_call_async(_update, timeout=8.0)


# ── 1) reviewer_3persona ────────────────────────────────────────────────────


def _load_persona_config(key: str) -> dict[str, Any]:
    path = _PERSONAS_DIR / f"{key}.json"
    if not path.exists():
        raise LookupError(f"persona_config_not_found:{key}")
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _build_reviewer_prompt(
    persona_cfg: dict[str, Any],
    manuscript_text: str,
    target_journal_id: str | None,
    lang: str,
) -> str:
    focus = ", ".join(persona_cfg.get("question_focus", []))
    lang_directive = "Türkçe yaz." if lang == "tr" else "Write in English."
    journal_line = (
        f"target_journal_id: {target_journal_id}\n"
        if target_journal_id
        else "target_journal_id: (yok — generic akademik standart)\n"
    )
    return (
        f"{lang_directive}\n\n"
        f"Persona seed: {persona_cfg.get('prompt_seed', '')}\n"
        f"Question focus: {focus}\n"
        f"Chain depth max: {persona_cfg.get('chain_max_depth', 2)}\n\n"
        f"{journal_line}"
        f"Manuscript:\n```\n{manuscript_text}\n```\n\n"
        "Çıktı SADECE JSON, schema: "
        '{"questions": [{"text": str, "depth": 1|2, '
        '"follow_up": str|null, "anchor": str|null}]}'
    )


def _trim_chain_depth(payload: ReviewerPersonaOutput) -> ReviewerPersonaOutput:
    """Hard-cap 2: depth >2 olmamalı; depth=2 + follow_up varsa follow_up = None."""
    safe = []
    for q in payload.questions:
        if q.depth > 2:
            continue
        if q.depth == 2 and q.follow_up:
            safe.append(q.model_copy(update={"follow_up": None}))
        else:
            safe.append(q)
    return payload.model_copy(update={"questions": safe})


async def _call_one_persona(
    persona_key: str,
    manuscript_text: str,
    target_journal_id: str | None,
    lang: str,
) -> ReviewerPersonaOutput:
    cfg = _load_persona_config(persona_key)
    prompt = _build_reviewer_prompt(cfg, manuscript_text, target_journal_id, lang)
    response = await llm_call(
        prompt,
        tier="flash",
        mode=f"reviewer_{persona_key}",
        structured_output_schema=ReviewerPersonaOutput,
        max_tokens=800,
    )
    parsed = response.parsed_output
    if not isinstance(parsed, ReviewerPersonaOutput):
        raise ValueError(f"reviewer_{persona_key}_llm_output_invalid")
    return _trim_chain_depth(parsed)


async def reviewer_3persona(
    user_id: UUID, req: Reviewer3PersonaRequest
) -> Reviewer3PersonaResponse:
    """3 persona paralel Flash; defense_session.scan_results.reviewer_3persona merge."""
    row = await supabase_call_async(
        lambda: _fetch_session(req.session_id, user_id), timeout=8.0
    )
    if str(row.get("project_id")) != str(req.project_id):
        raise PermissionError("session_project_mismatch")

    skeptik, sempatik, yontemci = await asyncio.gather(
        _call_one_persona(
            "skeptik", req.manuscript_text, req.target_journal_id, req.lang
        ),
        _call_one_persona(
            "sempatik", req.manuscript_text, req.target_journal_id, req.lang
        ),
        _call_one_persona(
            "yontemci", req.manuscript_text, req.target_journal_id, req.lang
        ),
    )

    existing = cast(dict[str, Any], row.get("scan_results") or {})
    patch = {
        "reviewer_3persona": {
            "skeptik": skeptik.model_dump(),
            "sempatik": sempatik.model_dump(),
            "yontemci": yontemci.model_dump(),
            "generated_at": datetime.now(UTC).isoformat(),
        }
    }
    await _persist_scan_results(req.session_id, _merge_scan_results(existing, patch))

    return Reviewer3PersonaResponse(
        session_id=req.session_id,
        skeptik=skeptik,
        sempatik=sempatik,
        yontemci=yontemci,
    )


# ── 2) statcheck_run ────────────────────────────────────────────────────────


def _load_statcheck_config() -> dict[str, Any]:
    if not _STATCHECK_PATH.exists():
        raise LookupError("statcheck_config_not_found")
    return cast(dict[str, Any], json.loads(_STATCHECK_PATH.read_text(encoding="utf-8")))


def _parse_reported_p(p_raw: str) -> float:
    """'.05' → 0.05; '<.001' op zaten ayrı yakalanıyor."""
    txt = p_raw.strip()
    if txt.startswith("."):
        txt = "0" + txt
    return float(txt)


def _compute_p(test_type: str, groups: dict[str, str]) -> float:
    """test_type'a göre scipy ile p-değer yeniden hesaplaması."""
    if test_type == "t":
        df = float(groups["df"])
        stat = abs(float(groups["stat"]))
        return cast(float, 2.0 * (1.0 - _t_dist.cdf(stat, df)))
    if test_type == "F":
        df1 = float(groups["df1"])
        df2 = float(groups["df2"])
        stat = float(groups["stat"])
        return cast(float, 1.0 - _f_dist.cdf(stat, df1, df2))
    if test_type == "chi2":
        df = float(groups["df"])
        stat = float(groups["stat"])
        return cast(float, 1.0 - _chi2_dist.cdf(stat, df))
    if test_type == "r":
        r = float(groups["stat"])
        n = float(groups["n"])
        if n <= 2 or abs(r) >= 1.0:
            return 1.0
        denom = (1.0 - r * r) or 1e-12
        t_stat = abs(r) * ((n - 2) / denom) ** 0.5
        return cast(float, 2.0 * (1.0 - _t_dist.cdf(t_stat, n - 2)))
    raise ValueError(f"unknown_test_type:{test_type}")


def _classify_diff(
    diff: float, tolerance: dict[str, float]
) -> str:
    if diff <= tolerance.get("green_max", 0.005):
        return "green"
    if diff <= tolerance.get("yellow_max", 0.01):
        return "yellow"
    return "red"


def _extract_statcheck_results(
    manuscript_text: str, cfg: dict[str, Any]
) -> list[StatcheckResult]:
    tolerance = cast(dict[str, float], cfg.get("tolerance", {}))
    patterns = cast(list[dict[str, Any]], cfg.get("patterns", []))
    results: list[StatcheckResult] = []
    for pat in patterns:
        test_type = str(pat["test_type"])
        regex = re.compile(str(pat["regex"]), flags=re.IGNORECASE | re.DOTALL)
        for m in regex.finditer(manuscript_text):
            groups = {k: v for k, v in m.groupdict().items() if v is not None}
            try:
                reported_p = _parse_reported_p(groups["p"])
                computed_p = _compute_p(test_type, groups)
            except (KeyError, ValueError) as exc:
                logger.debug("statcheck skip match: %s", exc)
                continue
            diff = abs(reported_p - computed_p)
            status = _classify_diff(diff, tolerance)
            reported_dict: dict[str, float | str] = {
                k: v for k, v in groups.items() if k not in {"p", "op"}
            }
            reported_dict["op"] = groups.get("op", "=")
            results.append(
                StatcheckResult(
                    test_type=cast(Any, test_type),
                    reported=reported_dict,
                    reported_p=min(reported_p, 1.0),
                    computed_p=min(max(computed_p, 0.0), 1.0),
                    diff=min(diff, 1.0),
                    status=cast(Any, status),
                    match_text=m.group(0)[:400],
                )
            )
    return results


async def statcheck_run(
    user_id: UUID, req: StatcheckRequest
) -> StatcheckResponse:
    """Regex + scipy ile p-değer tutarlılık; sonuçları scan_results.statcheck'e yaz."""
    row = await supabase_call_async(
        lambda: _fetch_session(req.session_id, user_id), timeout=8.0
    )
    cfg = _load_statcheck_config()
    results = _extract_statcheck_results(req.manuscript_text, cfg)
    summary = StatcheckSummary(
        total=len(results),
        green=sum(1 for r in results if r.status == "green"),
        yellow=sum(1 for r in results if r.status == "yellow"),
        red=sum(1 for r in results if r.status == "red"),
    )
    existing = cast(dict[str, Any], row.get("scan_results") or {})
    patch = {
        "statcheck": {
            "results": [r.model_dump() for r in results],
            "summary": summary.model_dump(),
            "generated_at": datetime.now(UTC).isoformat(),
        }
    }
    await _persist_scan_results(req.session_id, _merge_scan_results(existing, patch))

    return StatcheckResponse(
        session_id=req.session_id, results=results, summary=summary
    )


# ── 3) journal_calibration ──────────────────────────────────────────────────


def _load_review_distribution() -> dict[str, Any]:
    if not _REVIEW_DIST_PATH.exists():
        raise LookupError("review_distribution_not_found")
    return cast(
        dict[str, Any], json.loads(_REVIEW_DIST_PATH.read_text(encoding="utf-8"))
    )


def _find_journal_entry(
    journal_id: str | None, raw: dict[str, Any]
) -> dict[str, Any] | None:
    if not journal_id:
        return None
    journals = cast(list[dict[str, Any]], raw.get("journals") or [])
    for j in journals:
        if (
            j.get("journal_id") == journal_id
            or j.get("issn") == journal_id
            or j.get("id") == journal_id
        ):
            return j
    return None


def _predict_verdict(
    dist: JournalDistribution, statcheck_red: int
) -> tuple[Verdict, float]:
    """Basit V1: dağılımdaki en yüksek bandı seç; red sayısı yüksekse +1 band düşür.

    confidence = max bandın oranı * (1 - 0.1*statcheck_red), [0,1] kıskaç.
    """
    bands: list[tuple[Verdict, float]] = [
        ("accept", dist.accept_pct),
        ("minor", dist.minor_pct),
        ("major", dist.major_pct),
        ("reject", dist.reject_pct),
    ]
    bands.sort(key=lambda b: b[1], reverse=True)
    top, top_pct = bands[0]
    order = ["accept", "minor", "major", "reject"]
    if statcheck_red >= 3 and top != "reject":
        idx = min(order.index(top) + 1, len(order) - 1)
        top = cast(Verdict, order[idx])
    confidence = max(0.0, min(1.0, top_pct * (1.0 - 0.1 * statcheck_red)))
    return top, confidence


async def journal_calibration(
    user_id: UUID,
    session_id: UUID,
    journal_id: str | None,
) -> JournalCalibrationResponse:
    """review_distribution.json + verdict tahmini + statcheck red ile band kayması."""
    row = await supabase_call_async(
        lambda: _fetch_session(session_id, user_id), timeout=8.0
    )
    raw = _load_review_distribution()
    entry = _find_journal_entry(journal_id, raw)

    if entry is not None:
        dist = JournalDistribution(
            window_size=int(entry.get("window_size") or raw.get("window_size") or 50),
            accept_pct=float(entry["accept_pct"]),
            major_pct=float(entry["major_pct"]),
            minor_pct=float(entry["minor_pct"]),
            reject_pct=float(entry["reject_pct"]),
            source=cast(Any, entry.get("source") or "manual"),
        )
        journal_name = cast(str | None, entry.get("name"))
        fallback_used = False
    else:
        fb = cast(dict[str, Any], raw.get("field_average_fallback") or {})
        dist = JournalDistribution(
            window_size=int(raw.get("window_size") or 50),
            accept_pct=float(fb.get("accept_pct", 0.12)),
            major_pct=float(fb.get("major_pct", 0.42)),
            minor_pct=float(fb.get("minor_pct", 0.30)),
            reject_pct=float(fb.get("reject_pct", 0.16)),
            source="field_average_placeholder",
        )
        journal_name = None
        fallback_used = True

    scan_results = cast(dict[str, Any], row.get("scan_results") or {})
    statcheck = cast(dict[str, Any], scan_results.get("statcheck") or {})
    summary = cast(dict[str, Any], statcheck.get("summary") or {})
    statcheck_red = int(summary.get("red", 0))

    prediction, confidence = _predict_verdict(dist, statcheck_red)

    patch = {
        "journal_calibration": {
            "journal_id": journal_id,
            "journal_name": journal_name,
            "distribution": dist.model_dump(),
            "prediction": prediction,
            "confidence": confidence,
            "fallback_used": fallback_used,
            "generated_at": datetime.now(UTC).isoformat(),
        }
    }
    await _persist_scan_results(session_id, _merge_scan_results(scan_results, patch))

    return JournalCalibrationResponse(
        journal_id=journal_id,
        journal_name=journal_name,
        distribution=dist,
        prediction=prediction,
        confidence=confidence,
        fallback_used=fallback_used,
    )


__all__ = [
    "journal_calibration",
    "reviewer_3persona",
    "statcheck_run",
]
