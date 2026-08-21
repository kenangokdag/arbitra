# Report Cockpit Detailed Specification

## Purpose

The report page must be the strongest part of Arbitra. This is where the user should feel “wow”: not because of decoration, but because the product turns academic critique into a prioritized, evidence-backed revision strategy.

## Report hierarchy

```text
1. Verdict header
2. Top fatal risks
3. Risk radar
4. Reviewer council
5. Evidence map
6. Action plan
7. Section-by-section review
8. Export and disclosure
```

## Top bar — Verdict header

Required fields:
- Document type and study design.
- Readiness score.
- Likely decision / defense / panel risk.
- Confidence.
- Review mode.
- Privacy/external AI status.
- Export actions.

Example TR:
> Karar tahmini: Major revision riski yüksek
> En kritik neden: Yöntem gerekçesi ve iddia-kanıt uyumu zayıf

Rules:
- Do not imply guaranteed acceptance/rejection.
- Show confidence and limitation.
- Show degraded badge if provider/stage incomplete.

## Top fatal risks panel

Show maximum 5 items.

Each fatal risk card:
- Severity: P0/P1.
- Finding title.
- Why it matters.
- Manuscript anchor.
- Recommended fix.
- Confidence.
- Linked action item.

Bad finding:
> Yöntem kısmı zayıf.

Good finding:
> P0 — Örneklem stratejisi iddia edilen aktarılabilirliği desteklemiyor.
> Anchor: Methods, paragraph 4.
> Why: Katılımcı seçiminin neden bu araştırma sorusu için uygun olduğu açıklanmamış.
> Fix: Örneklem stratejisini, dahil/haric kriterlerini ve bağlam gerekçesini ekleyin.
> Acceptance: Okur, neden bu katılımcı grubunun araştırma sorusuna cevap verdiğini anlayabiliyor.

## Risk radar

Dimensions depend on document/study type.

Core dimensions:
- Contribution
- Literature
- Methodology
- Evidence alignment
- Citation integrity
- Ethics/transparency
- Clarity
- Venue/defense/panel fit

Qualitative dimensions:
- Research design fit
- Sampling rationale
- Data collection transparency
- Coding/analysis rigor
- Reflexivity
- Trustworthiness
- Thick description

Grant dimensions:
- Objectives
- Work packages
- Feasibility
- Budget/timeline
- Team capability
- Impact
- Risk mitigation

Rules:
- Radar is summary, not the only evidence.
- Clicking dimension filters report.
- Low confidence dimensions show dotted/uncertain state or badge.

## Reviewer council

Roles:
- Methodology reviewer
- Field expert
- Skeptical reviewer
- Constructive reviewer
- Citation auditor
- Ethics reviewer
- Statistics/analysis reviewer
- Editor synthesizer

Each card:
- Role
- Stance
- 2-3 sentence synthesis
- Key objection
- Confidence
- Linked findings

Rules:
- Persona should not be theatrical.
- No “funny character” UI.
- Academic authority tone.

## Evidence map

Table or graph-like list.

Columns:
- Claim/finding
- Manuscript anchor
- Source/evidence anchor
- Support level
- Confidence
- Limitation

Support level badges:
- Full text verified
- Abstract only
- Metadata only
- Unresolved
- Contradictory

Rules:
- Abstract-only can never look equivalent to verified.
- Evidence drawer opens exact source/provenance.
- If source is unavailable, say so.

## Action plan

ActionItem fields:

```typescript
interface ActionItem {
  id: string;
  priority: "P0" | "P1" | "P2";
  title: string;
  target_section: string;
  instruction: string;
  acceptance_check: string;
  effort: "low" | "medium" | "high";
  expected_gain: "low" | "medium" | "high";
  linked_finding_ids: string[];
  linked_evidence_ids: string[];
  status: "todo" | "in_progress" | "done" | "ignored";
}
```

UI:
- grouped by priority by default.
- filter by section, role, effort, gain.
- copy task.
- mark done.
- export selected tasks.

Acceptance:
- Every high severity finding has at least one action.
- Generic actions are rejected.

## Section-by-section review

Sections:
- Abstract
- Introduction
- Literature review
- Methods
- Results/findings
- Discussion
- Limitations
- References
- Ethics/transparency

For thesis:
- Chapter 1..n.
- Defense readiness.
- Committee questions.

For grant:
- Objectives.
- Work packages.
- Timeline.
- Budget.
- Impact.
- Risks.

Each section card:
- score/status
- what works
- what breaks
- exact anchors
- actions

## Drawers

### Manuscript drawer

Opens when user clicks anchor.

Shows:
- Section name.
- Quote/snippet.
- Finding context.
- Link to action.

### Evidence drawer

Shows:
- Source metadata.
- Provider.
- Support level.
- Retrieved date/snapshot.
- Limitation.
- Linked claims.

### Provenance drawer

Shows:
- Review schema version.
- Rubric version.
- Model/provider used.
- Degraded stages.
- Privacy mode.

## Export panel

Formats:
- Markdown first.
- PDF.
- DOCX.
- LaTeX checklist.
- Response-to-reviewers.
- Supervisor/editor summary.

Rules:
- Export requires authz check.
- Confidentiality disclosure included if relevant.
- Export can include/exclude evidence details.

## Empty/degraded/error states

No blank panels.

Examples:
- Evidence unavailable: “Bu kaynak çözümlenemedi; ilgili bulgu düşük güvenle işaretlendi.”
- Citation provider degraded: “Atıf analizi kısmi tamamlandı; unresolved kaynaklar listelenmiştir.”
- Report schema mismatch: show safe fallback and error id, not raw JSON.

## Frontend files likely touched

```text
web/src/components/review/ReviewReportView.tsx
web/src/components/review/VerdictHeader.tsx
web/src/components/review/FatalRisksPanel.tsx
web/src/components/review/RiskRadar.tsx
web/src/components/review/ReviewerCouncil.tsx
web/src/components/review/EvidenceMap.tsx
web/src/components/review/ActionPlanBoard.tsx
web/src/components/review/SectionReviewList.tsx
web/src/components/review/ManuscriptDrawer.tsx
web/src/components/review/ProvenanceDrawer.tsx
web/src/lib/review-api.ts
web/src/types/review.ts
```

## Report acceptance tests

1. Report v2 fixture renders verdict, risk radar, council, evidence, action plan.
2. High severity finding without action item fails schema or renders blocking warning in dev/test.
3. Clicking manuscript anchor opens drawer.
4. Clicking evidence support opens evidence drawer.
5. Abstract-only evidence is visually distinct.
6. Export button calls authorized endpoint.
7. Degraded stage badge appears when report metadata says degraded.
8. Mobile report has usable section navigation.
9. Keyboard user can navigate cards/drawers.
10. No raw JSON is displayed to end user.
