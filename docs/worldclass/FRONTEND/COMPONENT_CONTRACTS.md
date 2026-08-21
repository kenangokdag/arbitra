# Frontend Component Contracts

## Purpose

This file makes frontend implementation explicit enough for an autonomous coding agent. Components must be typed, testable, accessible and aligned with report schema v2.

## Marketing components

### `MarketingHero`

Required props:
```typescript
interface MarketingHeroProps {
  primaryCtaHref: string;
  sampleReportHref: string;
}
```

Must render:
- one H1.
- subcopy.
- two CTAs.
- trust chips.
- product preview card.

### `OutputPreview`

Shows safe fixture only.

Required panels:
- readiness score
- fatal risk
- evidence badge
- action item count

### `UseCaseTabs`

Tabs:
- article
- conference
- thesis
- grant
- reviewer/editor

### `ConfidentialityBlock`

Must mention:
- author mode
- reviewer/editor confidential mode
- external AI consent
- retention/delete

## Wizard components

### `ReviewIntakeWizard`

Owns wizard state or uses dedicated hook.

Required behavior:
- cannot submit until privacy step complete.
- beginner and expert mode.
- preserves state when navigating back.
- maps backend errors to fields.

### `FileUploadStep`

Props:
```typescript
interface FileUploadStepProps {
  value: UploadedFileDraft | null;
  onChange(file: UploadedFileDraft | null): void;
  error?: string;
}
```

### `DocumentTypeStep`

Supports `auto`.

### `PrivacyConsentStep`

Must make confidential reviewer/editor mode explicit.

### `ReviewDepthStep`

Maps document type to recommended default.

## Cockpit components

### `LiveReviewCockpit`

Props:
```typescript
interface LiveReviewCockpitProps {
  job: ReviewJob;
  stages: ReviewStage[];
  detectedProfile?: ManuscriptProfile;
  earlyFindings?: FindingPreview[];
  degradedNotices?: DegradedNotice[];
}
```

Must render:
- StageTimeline.
- DetectedProfileCard.
- DegradedNoticeList.
- Retry/cancel where allowed.

### `StageTimeline`

Stage status type:
```typescript
type StageStatus = "queued" | "running" | "done" | "degraded" | "failed" | "skipped";
```

## Report components

### `ReviewReportView`

Must not accept free-form string as primary data model. It should render report schema v2.

Props:
```typescript
interface ReviewReportViewProps {
  report: ReviewReportV2;
  job: ReviewJob;
}
```

### `VerdictHeader`

Required:
- readiness score
- decision risk
- confidence
- privacy/external AI status
- export actions

### `FatalRisksPanel`

Rules:
- max 5 visible by default.
- every item must link to action/evidence.

### `RiskRadar`

Click dimension → filter report.

### `ReviewerCouncil`

Shows structured role outputs.

### `EvidenceMap`

Supports support level badges and drawer.

### `ActionPlanBoard`

Allows status changes if backend/local model exists. If persistence not implemented, mark as local-only with clear UI.

### `SectionReviewList`

Renders section-specific findings and actions.

### `ManuscriptDrawer`

Required:
- quote
- section
- linked finding
- close button
- Escape handling

### `EvidenceDrawer`

Required:
- source title/metadata
- support level
- provider
- confidence
- limitation

### `ProvenanceDrawer`

Required:
- schema version
- rubric version
- provider versions
- degraded stages
- privacy mode

## Testing requirements

Each exported component should have at least one of:
- unit/render test
- Storybook story if project uses Storybook
- Playwright coverage through page flow

Do not mark frontend task complete if components compile but the user journey is broken.
