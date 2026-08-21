# Codex Master Prompt — Arbitra World-Class Transformation

You are working inside the Arbitra repository.

Your mission is to transform Arbitra into a world-class, confidentiality-first, evidence-backed scientific review operating system for articles, conference papers, theses, and grant/project proposals.

Read first:

1. `AGENTS.md`
2. `docs/worldclass/STATE.md`
3. `docs/worldclass/ROADMAP_MASTER.md`
4. `docs/worldclass/ROADMAP.yaml`
5. The phase/spec files for the first eligible task.

Rules:

- Do not implement fake production behavior.
- Do not leave silent fallback.
- Do not produce academic claims without provenance/confidence/limitations.
- Do not skip object-level authorization.
- Do not send confidential manuscripts to external AI without explicit consent gate.
- Do not mark a task done without tests or explicit verification.

Execution:

1. Pick the highest-priority eligible task from ROADMAP.yaml.
2. State the task ID in your work summary.
3. Inspect related files before editing.
4. Implement the minimal complete slice.
5. Add/update tests.
6. Run targeted tests.
7. Update `docs/worldclass/STATE.md`.
8. Stop if a stop condition in the task is met.

Output format after completion:

```text
Task: <id>
Changed files:
- ...
Tests run:
- ...
Gate status:
- Security: pass/fail/not applicable
- Academic: pass/fail/not applicable
- UX: pass/fail/not applicable
Known limitations:
- ...
Next task:
- ...
```
