# Frontend Implementation Prompt for Codex / Claude

Use this prompt after installing the worldclass pack.

```text
You are working on the Arbitra frontend. Read these files first:
- AGENTS.md
- docs/worldclass/FRONTEND/FRONTEND_WORLDCLASS_BLUEPRINT.md
- docs/worldclass/FRONTEND/INFORMATION_ARCHITECTURE.md
- docs/worldclass/FRONTEND/LANDING_PAGE_SPEC.md
- docs/worldclass/FRONTEND/REVIEW_WIZARD_DETAILED_SPEC.md
- docs/worldclass/FRONTEND/REPORT_COCKPIT_DETAILED_SPEC.md
- docs/worldclass/FRONTEND/FRONTEND_AGENT_TASKS.yaml
- docs/worldclass/CHECKLISTS/FRONTEND_WORLDCLASS_GATE.md

Goal:
Transform the frontend from a toolbox-like upload/report UI into a premium Scientific Review OS experience.

Non-negotiables:
1. Do not build generic SaaS visuals.
2. Do not render reports as one giant AI text blob.
3. Do not allow confidential reviewer/editor files to bypass privacy consent.
4. Every high-severity report finding must show manuscript anchor, evidence/provenance, confidence and action item.
5. Landing must explain Arbitra's category in the first fold.
6. Wizard must support beginner and expert modes.
7. Running jobs must show stage-based cockpit, not only spinner/progress bar.
8. Add tests for each critical journey.

Start with FE00-T01_FRONTEND_INVENTORY from docs/worldclass/FRONTEND/FRONTEND_AGENT_TASKS.yaml. Then proceed in dependency order. After each task:
- run typecheck/lint/tests available in the repo,
- update docs/worldclass/STATE.md,
- do not mark task complete if acceptance criteria fail.
```
