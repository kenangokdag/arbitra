# Review Wizard Detailed Specification

## Purpose

The wizard must minimize friction without hiding important academic and confidentiality decisions.

## Wizard states

```typescript
type WizardMode = "beginner" | "expert";
type DocumentType = "article" | "conference" | "thesis" | "grant" | "auto";
type ReviewMode = "author_pre_review" | "editor_confidential" | "thesis_defense" | "grant_panel";
type ReviewDepth = "fast_triage" | "full_review" | "journal_ready" | "defense_simulation" | "grant_panel_simulation";
type Strictness = "supportive" | "normal" | "strict" | "brutal";
type ExternalAIConsent = "allowed" | "blocked" | "requires_private_mode";
```

## Step 1 — File

Required UI:
- Upload dropzone.
- Supported formats: PDF, DOCX, LaTeX, ZIP if implemented.
- Max size and privacy note.
- Security scan note.
- Link to security page.

Validation:
- Empty file blocked.
- Unsupported type blocked with exact reason.
- Oversized file blocked with max size.

Microcopy:
> Yayınlanmamış çalışmalar gizli olabilir. Bir sonraki adımda dosyanın size ait olup olmadığını ve external AI kullanım iznini soracağız.

## Step 2 — Document type

Cards:
- Makale
- Bildiri
- Tez
- Proje/Grant
- Emin değilim, Arbitra seçsin

Each card:
- 1 sentence description.
- What Arbitra will check.

Beginner default:
- Auto selected unless user chooses.

Expert:
- Manual study design dropdown appears.

## Step 3 — Target

Fields:
- Discipline/subfield.
- Target journal/conference/call optional.
- Review mode.
- Strictness.

Conditional behavior:
- Thesis selected → target becomes university/department/defense focus optional.
- Grant selected → call/funder/work package fields appear.
- Conference selected → track/page limit optional.

## Step 4 — Privacy and consent

This step is non-skippable.

Questions:
1. Bu dosyanın yazarı/sahibi siz misiniz?
2. Bu dosya size hakemlik/editörlük için gizli olarak mı verildi?
3. External AI provider kullanımı izinli mi?
4. Retention süresi ne olsun?

Rules:
- If reviewer/editor confidential = true, external AI defaults to blocked.
- If external AI is blocked and no private mode is available, show limitation before job start.
- Consent choice must be sent to backend and stored in ReviewJob metadata.
- UI cannot rely on frontend-only enforcement.

Consent copy:
> Gizli hakemlik dosyaları dergi/konferans politikalarına tabi olabilir. External AI kullanmadan önce ilgili politika veya editör izni gerekebilir.

## Step 5 — Depth

Options:
- Fast triage: fatal risks only.
- Full academic review: balanced complete report.
- Journal-ready audit: strict evidence/citation/methodology.
- Thesis defense simulation: chapter and committee focus.
- Grant panel simulation: feasibility, impact, budget, risk.

Default mapping:

```text
article + beginner → full academic review
conference + beginner → full academic review
thesis + beginner → thesis defense simulation
grant + beginner → grant panel simulation
reviewer/editor confidential → full review with external AI blocked by default
```

## Expert drawer

Fields:
- Manual document type.
- Manual study design.
- Rubric profile.
- Reporting guideline.
- Provider depth.
- Citation check depth.
- Output language.
- UI locale.
- Source language.
- Strictness weights.
- Include response-to-reviewers draft.
- Include export bundle.

## Summary step / start gate

Before start show:
- File name.
- Document type.
- Review mode.
- Privacy mode.
- External AI status.
- Retention.
- Estimated depth label, but no fake duration guarantee.

Start button disabled if:
- File missing.
- Privacy step unanswered.
- Confidential file + external AI allowed without explicit confirmation.
- Backend schema validation fails.

## Backend contract expectation

Request shape should include at least:

```json
{
  "document_type": "auto",
  "study_design": "auto",
  "review_mode": "author_pre_review",
  "strictness": "normal",
  "depth": "full_review",
  "privacy": {
    "is_author": true,
    "is_confidential_review_file": false,
    "external_ai_consent": "allowed",
    "retention_days": 30
  },
  "locale": {
    "source_language": "auto",
    "output_language": "tr",
    "ui_locale": "tr-TR"
  },
  "target": {
    "discipline": "",
    "venue_or_call": ""
  }
}
```

## Test cases

1. Beginner article happy path.
2. Expert manual rubric path.
3. Confidential reviewer path defaults external AI blocked.
4. Privacy step cannot be skipped.
5. Unsupported file shows useful error.
6. Backend validation error maps to specific field.
7. Mobile wizard remains usable.
8. Keyboard-only user can complete wizard.
9. User can go back without losing state.
10. Start creates job and navigates to live cockpit.
