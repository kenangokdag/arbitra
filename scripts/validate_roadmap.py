#!/usr/bin/env python3
"""Validate docs/worldclass/ROADMAP.yaml.

The file is JSON-compatible YAML in this pack, so this script uses stdlib json.
Run from repo root:
    python scripts/validate_roadmap.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

REQUIRED_TASK_FIELDS = {
    "id", "phase", "priority", "title", "deps", "touchpoints",
    "steps", "tests", "done_when", "advance_when", "stop_if"
}


def main() -> int:
    path = Path("docs/worldclass/ROADMAP.yaml")
    if not path.exists():
        print(f"Missing {path}", file=sys.stderr)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    phases = set(data.get("phases", {}).keys())
    tasks = data.get("tasks", [])
    ids = [t.get("id") for t in tasks]
    errors: list[str] = []

    if len(ids) != len(set(ids)):
        errors.append("Duplicate task IDs found")

    id_set = set(ids)
    for t in tasks:
        missing = REQUIRED_TASK_FIELDS - set(t.keys())
        if missing:
            errors.append(f"{t.get('id')}: missing fields {sorted(missing)}")
        if t.get("phase") not in phases:
            errors.append(f"{t.get('id')}: unknown phase {t.get('phase')}")
        if t.get("priority") not in {"P0", "P1", "P2"}:
            errors.append(f"{t.get('id')}: invalid priority {t.get('priority')}")
        for dep in t.get("deps", []):
            if dep not in id_set:
                errors.append(f"{t.get('id')}: missing dependency {dep}")
        for list_field in ["touchpoints", "steps", "tests", "done_when", "stop_if"]:
            if not isinstance(t.get(list_field), list) or not t.get(list_field):
                errors.append(f"{t.get('id')}: {list_field} must be non-empty list")

    if errors:
        print("ROADMAP VALIDATION FAILED")
        for e in errors:
            print(f"- {e}")
        return 1

    print(f"ROADMAP OK: {len(tasks)} tasks across {len(phases)} phases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
