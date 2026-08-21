# Frontend Design System Spec — Premium Arbitra Experience

## Amaç

Arbitra UI “template SaaS” gibi değil, premium akademik kalite platformu gibi hissettirmelidir: sakin, otoriter, kanıt odaklı, editorial, güven veren ve kullanım sürtünmesi düşük.

## Görsel prensipler

1. **Editorial authority:** Akademik dergi/journal hissi; fazla oyuncak gradient yok.
2. **Evidence-first:** Badges, anchors, provenance ve confidence görsel olarak okunabilir.
3. **Calm severity:** Riskler alarmist değil, profesyonel tonla gösterilir.
4. **Progressive disclosure:** Yeni başlayan için sade; uzman için detay açılır.
5. **Readable density:** Uzun akademik raporlar nefes almalı.
6. **No random Tailwind:** Token ve component standardı dışına çıkılmaz.

## Token kategorileri

- `surface.base`
- `surface.raised`
- `surface.editorial`
- `text.primary`
- `text.secondary`
- `text.muted`
- `border.subtle`
- `risk.critical`
- `risk.major`
- `risk.moderate`
- `risk.minor`
- `evidence.verified`
- `evidence.abstractOnly`
- `evidence.unresolved`
- `confidence.high`
- `confidence.medium`
- `confidence.low`

## Core components

### RiskBadge

Shows severity and semantic priority.

### EvidenceBadge

Shows support level: full-text, abstract-only, metadata-only, unresolved.

### ConfidenceMeter

Numerical + qualitative confidence.

### ManuscriptAnchorLink

Clicking opens exact manuscript location or quote drawer.

### ActionItemCard

Shows P0/P1/P2, effort, expected gain, target section.

### ReviewerCouncilCard

Role persona, stance, summary, findings.

### StageTimeline

Review stage status: done/running/degraded/failed/skipped.

## Landing page blocks

1. Hero with clear promise.
2. Trust proof: confidentiality, evidence, methodology, revision.
3. Output preview.
4. Chatbot vs Arbitra comparison.
5. Use cases: article, conference, thesis, grant.
6. Confidential reviewer mode.
7. CTA + sample report.

## Accessibility

- Keyboard navigation.
- Visible focus states.
- Proper headings/landmarks.
- Color is not sole signal.
- Long report sections have skip links.
- Buttons/links have accessible names.

## Başarı kapısı

- Kullanıcı ilk 10 saniyede ürünün farkını anlar.
- Wizard kullanıcıyı boğmaz.
- ReportView kalabalık ama kontrol edilebilir.
- Risk/evidence/action görsel dili tutarlıdır.
