# Design System Tokens and Component Language

## Design direction

Arbitra's UI language: **editorial authority + analytical cockpit + confidentiality trust**.

It should feel closer to:
- an academic journal editorial system,
- a legal/financial-grade analysis terminal,
- a premium research dashboard,

not a colorful generic AI SaaS template.

## Token philosophy

All styling should use semantic tokens. Avoid one-off Tailwind values for core surfaces, severity, evidence and confidence states.

## CSS variable proposal

```css
:root {
  --arb-surface-base: ...;
  --arb-surface-raised: ...;
  --arb-surface-editorial: ...;
  --arb-surface-inset: ...;

  --arb-text-primary: ...;
  --arb-text-secondary: ...;
  --arb-text-muted: ...;
  --arb-text-inverse: ...;

  --arb-border-subtle: ...;
  --arb-border-strong: ...;
  --arb-border-focus: ...;

  --arb-risk-critical-bg: ...;
  --arb-risk-critical-text: ...;
  --arb-risk-major-bg: ...;
  --arb-risk-major-text: ...;
  --arb-risk-moderate-bg: ...;
  --arb-risk-moderate-text: ...;
  --arb-risk-minor-bg: ...;
  --arb-risk-minor-text: ...;

  --arb-evidence-verified-bg: ...;
  --arb-evidence-abstract-bg: ...;
  --arb-evidence-metadata-bg: ...;
  --arb-evidence-unresolved-bg: ...;

  --arb-confidence-high: ...;
  --arb-confidence-medium: ...;
  --arb-confidence-low: ...;

  --arb-radius-card: 18px;
  --arb-radius-panel: 24px;
  --arb-shadow-panel: ...;
  --arb-space-page-x: clamp(1rem, 3vw, 3rem);
}
```

Values must be selected in implementation according to existing theme; this spec defines semantic slots.

## Typography

Rules:
- Long academic text must have readable line length.
- Use editorial heading scale.
- Report body should support dense but scannable content.
- Avoid all-caps overuse.
- Monospace only for IDs/provenance, not body copy.

## Core primitives

### `ArbitraPageShell`

Props:
- title
- description
- privacyStatus
- actions
- children

### `EditorialPanel`

Used for major content blocks.

### `RiskBadge`

Props:
- severity: critical | major | moderate | minor
- priority: P0 | P1 | P2
- label

### `EvidenceBadge`

Props:
- supportLevel: full_text_verified | abstract_only | metadata_only | unresolved | contradictory

### `ConfidenceMeter`

Props:
- value 0..1
- label
- showNumeric

### `ManuscriptAnchorLink`

Props:
- section
- paragraph
- quotePreview
- onOpen

### `ActionItemCard`

Props:
- priority
- title
- targetSection
- effort
- expectedGain
- status
- acceptanceCheck

### `ReviewerCouncilCard`

Props:
- role
- stance
- summary
- confidence
- linkedFindings

### `StageTimeline`

Props:
- stages: Stage[]
- currentStage
- degradedNotices

## Motion rules

Allowed:
- stage progress transitions
- drawer open/close
- subtle hover/focus states
- skeleton loading

Forbidden:
- random floating decorative animations
- auto-playing distracting hero effects
- motion that conveys false processing precision

## Density modes

Report page should support:
- default: balanced
- compact: expert density
- focus: one finding at a time

## Accessibility rules

1. Color cannot be sole severity signal.
2. Badges include text labels.
3. Drawers trap focus and close via Escape.
4. Report sections have headings and landmarks.
5. Skip links exist for long report pages.
6. Keyboard-only flow must complete wizard.
7. Minimum WCAG AA contrast target.

## Anti-patterns

- Random gradient cards.
- Fake glassmorphism that hurts readability.
- Long unstructured AI prose.
- Icons without labels.
- Confidence hidden in tooltip only.
- Red-only severity.
- Terms like “magic”, “instant”, “guaranteed acceptance”.
