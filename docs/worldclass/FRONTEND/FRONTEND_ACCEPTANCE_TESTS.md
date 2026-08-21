# Frontend Acceptance Tests

## Required test layers

1. Type check.
2. Unit/component tests.
3. API contract tests for frontend data mapping.
4. Playwright/E2E tests for critical journeys.
5. Accessibility smoke tests.
6. Visual/manual review checklist.

## E2E critical journeys

### FE-E2E-01 — Landing clarity

Steps:
1. Visit landing.
2. Assert H1 contains review-before-reviewer promise.
3. Assert primary CTA visible.
4. Assert sample report CTA visible.
5. Assert confidentiality block exists.
6. Assert use-case cards exist.

Pass:
- User can understand product without logging in.

### FE-E2E-02 — Beginner review start

Steps:
1. Start review.
2. Upload valid fixture.
3. Keep document type auto.
4. Confirm author mode.
5. Choose full review or default.
6. Submit.

Pass:
- Job is created.
- User lands on live cockpit.

### FE-E2E-03 — Confidential reviewer protection

Steps:
1. Start review.
2. Choose reviewer/editor confidential.
3. Check external AI default.
4. Try to continue without explicit consent if external AI enabled.

Pass:
- External AI is blocked by default.
- User cannot accidentally submit confidential file to external AI.

### FE-E2E-04 — Running job cockpit

Use mocked API fixture.

Pass assertions:
- Stage timeline renders done/running/degraded/failed states.
- Detected manuscript profile appears.
- Degraded notices appear.
- No blank spinner-only page.

### FE-E2E-05 — Report cockpit

Use report v2 fixture.

Pass assertions:
- Verdict header visible.
- Fatal risks visible.
- Risk radar visible.
- Reviewer council visible.
- Evidence map visible.
- Action plan visible.

### FE-E2E-06 — Evidence and manuscript drawers

Steps:
1. Open report.
2. Click manuscript anchor.
3. Click evidence badge.

Pass:
- Manuscript drawer opens with quote.
- Evidence drawer opens with provider/support level/confidence.
- Escape closes drawers.

### FE-E2E-07 — Revision board

Pass:
- P0/P1/P2 actions visible.
- Filters work.
- Status change works or clearly marked local-only.

### FE-E2E-08 — Export authorization

Pass:
- Export button calls correct endpoint.
- Unauthorized job export is blocked.
- Confidentiality disclosure option appears when relevant.

## Accessibility checks

Minimum:
- one H1 per page.
- landmarks.
- visible focus.
- keyboard wizard completion.
- drawer focus trap.
- color not sole risk indicator.
- badges have text labels.

## Performance budgets

These are targets; exact numbers may be tuned to current stack.

- Landing JS should avoid unnecessary app-only bundles.
- Report page should virtualize or progressively render very long findings if needed.
- Avoid blocking UI while report sections load.
- Heavy charts must be lazy-loaded.

## Manual premium review checklist

A reviewer must answer yes:

1. Does landing feel like an academic review OS, not generic AI SaaS?
2. Does the wizard reduce uncertainty?
3. Does confidentiality feel central?
4. Does progress build trust?
5. Does report first screen show what matters most?
6. Are criticisms tied to anchors/evidence/actions?
7. Can user turn report into revision plan?
8. Is the UI calm, readable and premium?
9. Are error states helpful?
10. Would an expert researcher respect this interface?
