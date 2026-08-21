"""F13-S1-P004 ROLE_MODULE: diary_pre_advisor — Stage A son 30 gün özet.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S1-P004)
Pattern: librarian.py:32-37 (lru_cache prompt loader).
Sayfa: Page_Design/Sayfa_Plani_v2/S1_arastirma_defteri.rtf §(4) Defter Modu.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPT_PATH = (
    Path(__file__).resolve().parents[3] / "prompts" / "diary_pre_advisor_v1.md"
)


@lru_cache(maxsize=1)
def _load_brief() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


DIARY_PRE_ADVISOR_BRIEF = _load_brief()


__all__ = ["DIARY_PRE_ADVISOR_BRIEF"]
