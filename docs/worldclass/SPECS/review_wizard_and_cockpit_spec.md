# Review Wizard & Cockpit Spec

## Intake wizard

### Step 1 — File

- PDF/DOCX/LaTeX/ZIP upload.
- File security/retention note.
- Max size/type validation.
- “Dosyam gizli olabilir” warning.

### Step 2 — Document type

Options:

- Makale
- Bildiri
- Tez
- Proje/Grant
- Emin değilim, Arbitra seçsin

### Step 3 — Target

- Journal/conference/call name optional.
- Discipline/subfield.
- Strictness: supportive, normal, strict, brutal.
- Review mode: author pre-review, editor/reviewer confidential, thesis defense, grant panel.

### Step 4 — Privacy

- Are you the author?
- Is this a confidential review manuscript?
- External AI allowed?
- Retention duration.
- Anonymize before external provider? Future.

### Step 5 — Depth

- Fast triage
- Full academic review
- Journal-ready audit
- Thesis defense simulation
- Grant panel simulation

## Beginner mode

Default path:

```text
Upload -> Arbitra chooses document/study type -> privacy confirmation -> full review
```

## Expert mode

Advanced drawer:

- Manual document type.
- Manual study design.
- Rubric selection.
- Guideline selection.
- Provider depth.
- Review language.
- Output format.
- Strictness weights.

## Live cockpit

Before completion, user sees:

- Stage timeline.
- Detected document profile.
- Early warnings.
- Provider/degraded notices.
- Cancel/retry if applicable.

## Completed cockpit

Report page layout:

```text
Left rail: sections and filters
Top: verdict + readiness + export
Main: fatal risks / risk radar / council / evidence / action plan
Right drawer: manuscript quote, evidence source, provenance
```

## Error states

- Upload rejected: explain exact reason.
- Provider degraded: show limitation.
- LLM consent required: show privacy action.
- Stage failed: retry/cancel/support id.
- Report unavailable: no blank page.

## Başarı kapısı

- User can start review without knowing academic terminology.
- Expert can override automation.
- Confidentiality step cannot be skipped.
- Job progress tells a truthful story.
- Final report turns into revision actions.
