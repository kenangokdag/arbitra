# App Pages Specification

## App shell

### Purpose

App shell must feel like an academic command center, not a generic dashboard.

### Required elements

- Workspace/document context.
- New review CTA.
- Confidentiality/privacy status.
- Current user's active jobs.
- Notifications only for useful academic actions.

### Header status badges

```text
Privacy: Standard / Confidential / External AI allowed / External AI blocked
Plan: Free / Pro / Institutional
Locale: report language
```

Never hide confidentiality status inside settings only.

## Dashboard

### Layout

```text
Top:
  Welcome + Start new review
  Active critical action count

Main:
  Continue where you left off
  Recent reviews
  Revision actions due
  Sample/demo review for new users

Side:
  Privacy status
  Quick links: security, sample report, settings
```

### Empty state

Bad:
> You have no reviews.

Good:
> Hakeme gitmeden önce çalışmanızın en zayıf halkasını yakalayalım.
> Makale, bildiri, tez veya proje dosyanızı yükleyin; Arbitra belge türünü ve uygun review derinliğini sizin için seçebilir.

CTA:
- İlk review'umu başlat
- Örnek raporu gör

## Review new page

See `REVIEW_WIZARD_DETAILED_SPEC.md`.

## Running job page

### Purpose

Waiting must be trust-building. User must see real stages, early signals, and limitations.

### Layout

```text
Left/main:
  Stage timeline
  Current stage detail
  Detected document profile

Right:
  Privacy/provenance panel
  Early findings
  Provider/degraded notices
```

### Stage states

- queued
- running
- done
- degraded
- failed
- skipped

### Stage examples

```text
✓ File safety scan
✓ Text and reference extraction
✓ Manuscript profile: qualitative empirical article
⏳ Citation resolution: 32/58 references
⏳ Methodology reviewer
○ Editor synthesis
```

### Degraded state copy

> Literatür kapsam analizi sınırlı çalıştı: provider quota nedeniyle bazı kaynaklar çözümlenemedi. Rapor bu bulguları “abstract-only” veya “unresolved” olarak işaretleyecek.

## Completed report page

See `REPORT_COCKPIT_DETAILED_SPEC.md`.

## Revision board page

### Purpose

Report becomes implementation plan.

### Layout options

Default list view:
- grouped by P0/P1/P2.
- filters: section, effort, expected gain, status, reviewer role.

Expert board view:
- columns: To fix, In progress, Needs evidence, Done, Ignored.

### Action item card fields

- Priority
- Finding summary
- Target section
- Exact anchor
- Instruction
- Acceptance check
- Effort
- Expected gain
- Linked evidence
- Status
- User note

### Acceptance

- 100% of high severity findings appear as P0/P1 action items.
- User can filter to “methodology P0 only”.
- Ignoring an action requires optional reason.

## Evidence page

### Purpose

Power user can inspect every claim/source relationship.

### Table columns

- Manuscript claim
- Location
- Source/citation
- Support level
- Confidence
- Issue type
- Linked finding

### Support levels

- full_text_verified
- abstract_only
- metadata_only
- unresolved
- contradictory

### Acceptance

- Abstract-only is visually distinct.
- Unresolved sources do not look verified.
- Every evidence row can open provenance details.

## Settings/privacy

### Required sections

- Retention default.
- External AI preference.
- Export/delete account data.
- Workspace privacy.
- Provider disclosure.

### Acceptance

- User can understand where data may be sent.
- Confidential reviewer/editor mode defaults are stricter than author mode.
