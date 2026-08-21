#!/usr/bin/env python3
"""Generate Markdown issue list from docs/worldclass/ROADMAP.yaml."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    data = json.loads(Path("docs/worldclass/ROADMAP.yaml").read_text(encoding="utf-8"))
    out = ["# Arbitra World-Class Roadmap Issues", ""]
    for task in data["tasks"]:
        out.append(f"## {task['id']} — {task['title']}")
        out.append("")
        out.append(f"- Phase: {task['phase']}")
        out.append(f"- Priority: {task['priority']}")
        out.append(f"- Dependencies: {', '.join(task['deps']) if task['deps'] else 'None'}")
        out.append("")
        out.append("### Touchpoints")
        for p in task["touchpoints"]:
            out.append(f"- `{p}`")
        out.append("")
        out.append("### Implementation steps")
        for i, step in enumerate(task["steps"], 1):
            out.append(f"{i}. {step}")
        out.append("")
        out.append("### Tests")
        for test in task["tests"]:
            out.append(f"- [ ] {test}")
        out.append("")
        out.append("### Done when")
        for done in task["done_when"]:
            out.append(f"- [ ] {done}")
        out.append("\n---\n")
    path = Path("docs/worldclass/TASKS/github_issues.md")
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
