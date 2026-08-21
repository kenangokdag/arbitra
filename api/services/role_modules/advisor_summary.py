"""F13-S2-P004 ROLE_MODULE: advisor_summary — "Danışmana Gitmeden Evvel" 4-5 paragraf.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S2-P004)
Pattern: librarian.py:32-37 + diary_pre_advisor.py (lru_cache prompt loader).
Sayfa: Page_Design/Sayfa_Plani_v2/5.1_yayin_formati.rtf §Plan-Detayı (3).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPT_PATH = (
    Path(__file__).resolve().parents[3] / "prompts" / "advisor_summary_v1.md"
)


@lru_cache(maxsize=1)
def _load_brief() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


ADVISOR_SUMMARY_BRIEF = _load_brief()


__all__ = ["ADVISOR_SUMMARY_BRIEF"]
