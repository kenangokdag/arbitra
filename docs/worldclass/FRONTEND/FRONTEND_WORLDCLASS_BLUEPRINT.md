# Arbitra Frontend World-Class Blueprint

## Hüküm

Mevcut P05/P06 roadmap frontend yönünü veriyordu; bu dosya frontend tarafını bağlayıcı ürün sözleşmesine çevirir. Bir agent bu dosyayı okuduğunda yalnızca “sayfa güzelleştirme” yapmayacak; Arbitra'yı premium, güven veren, akademik olarak derin ve sürtünmesiz bir Scientific Review OS deneyimine dönüştürecektir.

## Kuzey yıldızı

Arbitra frontend'i şu hissi vermelidir:

> “Bu sistem çalışmamı gerçekten anladı, akademik risklerimi dürüstçe gösterdi, her eleştiriyi kanıta bağladı ve beni hakeme/savunmaya/panele hazır hale getirdi.”

Frontend'in görevi sadece backend çıktısını göstermek değildir. Frontend:

1. kullanıcının gizlilik ve akademik bağlamını doğru alır,
2. review motorunun ne yaptığını şeffaf gösterir,
3. raporu uygulanabilir revizyon işlerine dönüştürür,
4. yeni başlayanları boğmadan yönlendirir,
5. uzmanlara kontrol verir,
6. her kritik iddia için anchor/provenance/confidence gösterir,
7. premium ve kurumsal güven hissi üretir.

## Değiştirilemez ürün ilkeleri

1. **No generic SaaS template.** Arbitra dashboard'u sıradan upload kartları ve gradient hero'lardan oluşamaz.
2. **No chatbot framing.** Arbitra “AI assistant” değil, akademik kalite ve hakemlik işletim sistemidir.
3. **No passive report.** Rapor okunup kapanan bir metin değil; risk, kanıt ve revizyon cockpit'idir.
4. **No hidden privacy decision.** Gizli hakemlik dosyalarında external AI kararı açık rıza olmadan alınamaz.
5. **No unexplained score.** Her skorun gerekçesi, kanıtı, confidence seviyesi ve aksiyonu olmalıdır.
6. **No expert-only UX.** Kullanıcı akademik terminolojiyi bilmese de doğru review başlatabilmelidir.
7. **No beginner-only UX.** Uzman kullanıcı rubric, guideline, strictness, provider depth ve dil ayarlarını kontrol edebilmelidir.
8. **No dead waiting.** Job devam ederken spinner değil, canlı review cockpit gösterilir.
9. **No uncited criticism.** Kritik bulgu exact manuscript anchor olmadan premium raporda gösterilemez.
10. **No inaccessible density.** Uzun raporlar section nav, filters, drawers, skip links ve responsive layout olmadan yayınlanamaz.

## Frontend olgunluk seviyesi

### Seviye 0 — Toolbox

- Tek upload formu.
- Spinner.
- Uzun düz rapor.
- Generic kartlar.
- Gizlilik ayarları belirsiz.

Bu seviye yasaktır.

### Seviye 1 — Guided tool

- Wizard vardır.
- Basit progress vardır.
- Rapor bölümlere ayrılır.

Bu MVP için kabul edilebilir ama dünya klası değildir.

### Seviye 2 — Review OS

- Landing net kategori yaratır.
- Wizard beginner/expert ayrımı yapar.
- Confidentiality flow merkezde olur.
- Progress gerçek workflow stage'leriyle akar.
- Rapor verdict, risk radar, reviewer council, evidence map ve action plan içerir.

Bu P05/P06 minimum hedefidir.

### Seviye 3 — World-class cockpit

- Kullanıcı rapordan revizyon board'a geçer.
- Her finding task'a dönüşür.
- Manuscript quote ve evidence drawer tek tıkla açılır.
- Report export, response-to-reviewers, version comparison çalışır.
- Accessibility, performance, empty/error states üretim kalitesindedir.

Bu launch hedefidir.

## Ana deneyim yolculuğu

```text
Landing
  ↓
Sample report / trust proof
  ↓
Start review
  ↓
Guided intake wizard
  ↓
Confidentiality and consent checkpoint
  ↓
Live review cockpit
  ↓
Report cockpit
  ↓
Revision action board
  ↓
Export / response-to-reviewers / version compare
```

## Kullanıcı segmentleri

### Yeni başlayan akademisyen / yüksek lisans öğrencisi

İhtiyaç:
- “Neyi seçmem gerektiğini bilmiyorum.”
- “Hakem neye takılır bilmiyorum.”
- “Uzun raporu nasıl düzelteceğimi bilmiyorum.”

UX çözümü:
- “Arbitra benim için seçsin” default path.
- Akademik terimler tooltips ile açıklanır.
- P0/P1/P2 revision planı verir.
- En kritik 5 risk ilk ekranda görünür.

### Uzman araştırmacı

İhtiyaç:
- Disiplin, yöntem, guideline ve target venue kontrolü.
- Atıf ve kanıt derinliği.
- Strict/brutal review.

UX çözümü:
- Expert drawer.
- Rubric/guideline override.
- Evidence depth ayarı.
- Claim-evidence table.

### Tez yazarı

İhtiyaç:
- Bölüm bütünlüğü.
- Savunma riski.
- Jüri soruları.

UX çözümü:
- Thesis mode.
- Chapter health map.
- Defense readiness.
- Committee question simulator.

### Proje/grant hazırlayan ekip

İhtiyaç:
- Panel skoru.
- Work package, timeline, budget, impact riski.

UX çözümü:
- Grant panel simulation.
- WP dependency map.
- Budget coherence warnings.
- Reviewer objections.

### Hakem/editör

İhtiyaç:
- Confidentiality.
- External AI policy.
- Desk-reject risk.
- Scope/ethics flags.

UX çözümü:
- Reviewer/editor confidential mode.
- External AI default off.
- AI-use disclosure.
- Audit/provenance.

## Route hedef mimarisi

```text
web/src/app/
  (marketing)/
    page.tsx                         # premium landing
    sample-report/page.tsx           # demo report with safe fixture
    security/page.tsx                # privacy/security trust page
    use-cases/article/page.tsx
    use-cases/conference/page.tsx
    use-cases/thesis/page.tsx
    use-cases/grant/page.tsx
  (app)/
    dashboard/page.tsx               # recent reviews + next actions
    review/new/page.tsx              # guided wizard
    review/[jobId]/page.tsx          # live job cockpit while running
    review/[jobId]/report/page.tsx   # completed report cockpit
    review/[jobId]/revision/page.tsx # action board
    review/[jobId]/evidence/page.tsx # evidence map deep view
    settings/privacy/page.tsx
    settings/workspace/page.tsx
```

Eğer mevcut repo route yapısı farklıysa agent mevcut route'ları kırmadan bu hedef mimariye en yakın şekilde refactor yapar ve redirect/backward compatibility sağlar.

## Global layout standardı

### Marketing layout

- Editorial hero.
- Large readable typography.
- Strong trust proof.
- Product output previews.
- No noisy animations.
- CTA always tells the next academic outcome, not just “Get started”.

### App layout

- Left rail or top workspace nav.
- Clear current artifact: document, job, report, revision.
- Persistent privacy/confidentiality status badge.
- Persistent export/share controls only when safe.
- Responsive split panes for report/evidence/manuscript.

### Report layout

```text
Desktop:
┌───────────────────────────────────────────────────────────────┐
│ Verdict header: readiness, decision risk, confidence, exports  │
├─────────────┬───────────────────────────────────────┬─────────┤
│ Section nav │ Main report cockpit                    │ Drawer  │
│ Filters     │ Risk radar / council / evidence / plan │ Quote   │
│             │                                       │ Source  │
└─────────────┴───────────────────────────────────────┴─────────┘

Mobile:
- Verdict header
- Sticky section tabs
- Cards stacked
- Drawer becomes full-screen sheet
- Export tucked below verdict
```

## Dünya klası frontend başarı tanımı

Frontend ancak şu koşullarda “world-class” sayılır:

1. İlk fold ürünü 10 saniyede anlatır.
2. Yeni kullanıcı 3 dakikadan kısa sürede doğru review başlatır.
3. Confidential reviewer/editor mode yanlışlıkla external AI'a veri gönderemez.
4. Spinner yerine stage-based cockpit vardır.
5. Raporun ilk ekranı “ne kadar kötü/iyi ve önce ne yapmalıyım?” sorusunu cevaplar.
6. Her P0/P1 finding exact manuscript anchor + action item + confidence içerir.
7. Evidence drawer source support level'ı gösterir.
8. ReportView typed schema render eder, string blob değildir.
9. A11y: keyboard navigation, visible focus, heading landmarks, color-not-only signal.
10. E2E testler landing, wizard, confidentiality, cockpit, report ve export path'ini kapsar.
