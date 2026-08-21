# Premium Landing Page Specification

## Landing'in görevi

Landing bir “AI research assistant” sayfası değildir. Arbitra landing'i kategori yaratmalıdır:

> “Hakeme, jüriye veya proje paneline gitmeden önce çalışmanızın nerede kırılacağını kanıtıyla görün.”

## İlk fold

### Hero copy seçenekleri

Primary TR:
> Hakeme gitmeden önce çalışmanızın nerede kırılacağını görün.

Subcopy TR:
> Arbitra; makale, bildiri, tez ve proje dosyalarını akademik rubrikler, yöntem analizi, atıf bütünlüğü, kanıt haritası ve gizlilik odaklı review akışıyla inceler.

CTA:
- Çalışmamı ön-incelet
- Örnek raporu gör

Trust microcopy:
- Confidentiality-first
- Evidence-backed critique
- Methodology-aware rubrics
- Revision action plan

Primary EN:
> See where your work will break before reviewers do.

Subcopy EN:
> Arbitra reviews articles, conference papers, theses, and grant proposals with academic rubrics, methodology checks, citation integrity, evidence maps, and confidentiality-first workflows.

## Above-the-fold layout

```text
Left:
  Eyebrow: Scientific Review OS
  H1
  Subcopy
  CTA row
  Trust chips
Right:
  Interactive report preview card
    - Readiness score
    - Top 3 fatal risks
    - Evidence-backed badge
    - Action plan count
```

Rules:
- No vague “AI-powered productivity” wording.
- No fake metrics.
- No testimonial unless gerçek ve izinli.
- No “guaranteed acceptance”.
- Confidentiality claim only as implemented.

## Section 2 — Problem framing

Headline:
> Hakemler çoğu zaman makalenizi yazım için değil, kanıt, yöntem ve iddia sınırı için kırar.

Cards:
1. Overclaimed conclusions
2. Weak method justification
3. Missing literature anchors
4. Citation mismatch
5. Unclear contribution
6. Ethics/transparency gaps

Each card includes:
- risk label
- one sentence explanation
- “Arbitra detects this by...” micro-proof

## Section 3 — Output preview

Show a realistic cockpit preview, not abstract feature icons.

Required mini-panels:
- Verdict header
- Risk radar
- Reviewer council
- Evidence map
- P0/P1/P2 action plan

Mini copy:
> Eleştiriler düz metin değil; manuscript anchor, confidence, severity ve revizyon göreviyle gelir.

## Section 4 — Use cases

Tabs/cards:
- Makale
- Bildiri
- Tez
- Proje/Grant
- Hakem/Editör modu

Each use case includes:
- “What it checks”
- “What you get”
- “Why generic AI misses it”

Example thesis card:
```text
Tez / Savunma
Checks: chapter coherence, theoretical framing, methodology defense, committee objections.
Output: defense readiness score, likely committee questions, chapter-level revision map.
```

## Section 5 — Chatbot vs Arbitra

Comparison table:

| Generic chatbot | Arbitra |
|---|---|
| Prompt'a bağlı | Document/study-type aware rubric |
| Uzun serbest metin | Structured verdict + action plan |
| Gizlilik belirsiz | Confidentiality workflow + consent |
| Kaynak desteği sınırlı | Evidence map + support levels |
| Tek cevap | Revision cockpit + export |

Rules:
- Competitor names kullanılabilir ama saldırgan değil.
- Üstünlük somut kabiliyet üzerinden gösterilir.

## Section 6 — Confidentiality-first

Headline:
> Yayınlanmamış çalışma sıradan bir dosya değildir.

Content:
- Author mode vs reviewer/editor mode.
- External AI consent.
- Retention/delete.
- Provenance and audit.

CTA:
- Güvenlik yaklaşımını oku

## Section 7 — Workflow

```text
Upload → classify → evidence retrieval → methodology checks → reviewer council → editor synthesis → revision cockpit
```

Each stage has:
- short label
- what happens
- what user sees

## Section 8 — Final CTA

Headline:
> Çalışmanızın en zayıf halkasını hakemden önce yakalayın.

CTA:
- Çalışmamı ön-incelet
- Örnek raporu gör

## Visual rules

- Editorial, calm, academic, premium.
- Typography: strong readable headings, generous line-height, long-form friendly.
- Animation: only progress/evidence reveal; no ornamental noise.
- Illustrations: product UI previews over decorative blobs.
- Trust > hype.

## Implementation targets

Likely files:

```text
web/src/app/(marketing)/page.tsx
web/src/app/(marketing)/sample-report/page.tsx
web/src/app/(marketing)/security/page.tsx
web/src/components/marketing/Hero.tsx
web/src/components/marketing/OutputPreview.tsx
web/src/components/marketing/UseCaseTabs.tsx
web/src/components/marketing/ComparisonTable.tsx
web/src/components/marketing/ConfidentialityBlock.tsx
web/src/components/marketing/WorkflowPreview.tsx
web/src/lib/brand.ts
```

If current repo uses `(marketing)/landing/page.tsx`, preserve route or redirect.

## Landing acceptance tests

1. Hero H1 includes the review-before-reviewer promise.
2. Primary CTA links to review wizard.
3. Sample report CTA links to safe demo report.
4. Confidentiality block exists before final CTA.
5. Use-case cards include article, conference, thesis, grant.
6. Chatbot comparison does not claim unsupported features.
7. Page has one H1 and valid landmarks.
8. Mobile first fold CTA is visible without horizontal scroll.
9. Lighthouse/accessibility budget passes project threshold.
10. No placeholder/mock testimonial appears in production.
