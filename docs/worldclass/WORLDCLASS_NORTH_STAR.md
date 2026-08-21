# Arbitra North Star — Dünya Klası Ürün Tanımı

## Tek cümlelik ürün tanımı

**Arbitra, akademik çalışmanın hakeme, jüriye veya proje paneline gitmeden önce nerede kırılacağını kanıtlarıyla gösteren; makale, bildiri, tez ve proje dosyaları için belge türüne özel bilimsel review, atıf bütünlüğü, yöntem geçerliliği, etik/gizlilik kontrolü ve uygulanabilir revizyon planı üreten premium akademik kalite platformudur.**

## Rakiplerden ayrışma

Arbitra literatür arama motoru değildir. Chatbot değildir. Grammar checker değildir. Dergi yönetim sistemi değildir. Arbitra'nın ayrı kategorisi şudur:

> Scientific Review Operating System.

Diğer araçlar paper bulur, özetler veya yayın sürecini yönetir. Arbitra çalışmanın akademik olarak nereden eleştirileceğini ve nasıl güçlendirileceğini gösterir.

## Ürünün vaadi

Kullanıcı Arbitra'ya dosya verdiğinde şu cevapları almalıdır:

1. Çalışmamın en zayıf beş akademik noktası ne?
2. Hakem beni nereden vurur?
3. Bu eleştiriler dosyanın neresine dayanıyor?
4. Literatür, yöntem, veri, etik veya atıfta gerçek açık var mı?
5. Bu açığı kapatmak için bugün ne yapmalıyım?
6. Hangi düzeltme kabul şansımı en çok artırır?
7. Hangi eleştiri ölümcül, hangisi polish?
8. Rapor ne kadar güvenilir, hangi veri/providera dayanıyor?
9. Dosyam ve gizli bilgilerim güvende mi?
10. Raporu danışmana, jüriye, dergiye veya proje paneline nasıl çevirebilirim?

## Ürün felsefesi

Arbitra'nın tonu yargılayıcı değil, keskin ve yapıcıdır. Sistem kullanıcıyı aşağılamaz; akademik kör noktalarını saklamaz. Her eleştiri şu formatta olmalıdır:

```text
Problem: Ne kırılıyor?
Evidence: Manuscript içinde nerede?
Reason: Akademik olarak neden sorun?
Risk: Hakem bunu nasıl formüle eder?
Fix: Kullanıcı ne yapmalı?
Impact: Düzeltirse ne kazanır?
Confidence: Sistem buna ne kadar emin?
Limit: Bu bulgunun sınırı ne?
```

## Dünya klası olmayan davranışlar

- “Literatürü güçlendirin” gibi generic öneriler.
- Exact manuscript anchor olmadan sert eleştiri.
- Kaynak veya atıf uydurmak.
- Abstract-only kontrolü full-text doğrulama gibi sunmak.
- Production'da mock auth veya fake provider.
- Kullanıcıyı gizlilik/external AI konusunda bilgilendirmemek.
- Sadece uzun rapor üretip revizyon yönetimi vermemek.
- Her belge türüne aynı rubriği uygulamak.
- Spinner ile bekletip canlı akademik progres göstermemek.
- Landing'de “AI research assistant” gibi sıradan konumlanmak.

## Başarı metrikleri

### Ürün metrikleri

- Upload-to-first-value süresi: kullanıcı ilk anlamlı bulguyu 60 saniye içinde görmeli.
- Report actionability: high-severity eleştirilerin %95'i somut action item içermeli.
- Beginner completion: yeni kullanıcıların %80'i yardımsız full review başlatabilmeli.
- Expert configuration: uzman kullanıcı hedef venue/rubric/privacy/depth seçebilmelidir.
- Export usage: tamamlanan raporların önemli kısmı PDF/DOCX/Markdown/LaTeX export alabilmeli.

### Akademik metrikler

- Claim-evidence alignment precision.
- Citation resolution accuracy.
- Reporting guideline compliance detection accuracy.
- Human expert rubric agreement.
- Hallucination rate.
- Action item usefulness score.
- Qualitative rigor coverage.
- Quantitative/statistical consistency coverage.

### Güvenlik metrikleri

- Object-level authorization test coverage: %100 kritik endpoint.
- Production mock/fallback gate: %0 tolerans.
- External AI consent logging: %100 confidential flow.
- Retention/delete request success.
- Audit event coverage.

### UX metrikleri

- Time-to-understand: landing ve review wizard ilk 10 saniyede anlaşılır.
- Perceived premium: UI audit score.
- Accessibility: keyboard navigation, contrast, semantic landmarks.
- Friction: wizard adımları minimum ama güvenlik/akademik ihtiyaçlar eksiksiz.

## Ürün modları

1. **Author Pre-Review:** Yazarın makale/bildiri/tez/projesini submission öncesi güçlendirir.
2. **Reviewer/Editor Confidential Mode:** Gizli hakemlik dosyası için external AI kapalı/izinli, disclosure-aware inceleme.
3. **Thesis Defense Simulator:** Jüri soruları, chapter riskleri, savunma hazırlığı.
4. **Grant Panel Simulator:** Hakem paneli, iş paketleri, bütçe, feasibility, impact.
5. **Revision Cockpit:** Düzeltme taskları, versiyon karşılaştırma, response-to-reviewers.

## Nihai ürün hissi

Kullanıcı rapor ekranına girdiğinde şunu hissetmeli:

> “Bu sistem dosyamı gerçekten okumuş. Sadece AI konuşmuyor; hakem gibi düşünüyor, metodolog gibi sorguluyor, editör gibi sentezliyor ve danışman gibi yol gösteriyor.”
