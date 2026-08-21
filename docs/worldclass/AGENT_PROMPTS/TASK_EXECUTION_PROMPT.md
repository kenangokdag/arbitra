# Single Task Execution Prompt

Use this when assigning one task to a coding agent.

```text
Implement task <TASK_ID> from docs/worldclass/ROADMAP.yaml.

Read:
- AGENTS.md
- docs/worldclass/STATE.md
- docs/worldclass/PHASES/<relevant-phase>.md
- docs/worldclass/SPECS/<relevant-spec>.md
- docs/worldclass/CHECKLISTS/<relevant-gate>.md

Requirements:
- Touch only files required by the task unless tests require fixtures.
- Add/update tests.
- Keep backward compatibility unless the task explicitly requires breaking migration.
- Update docs/worldclass/STATE.md.
- Do not mark done if any stop condition occurs.

Return changed files, verification commands, gate status, and next task.
```
