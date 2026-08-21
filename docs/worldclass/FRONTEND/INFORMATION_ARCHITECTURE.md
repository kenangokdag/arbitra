# Frontend Information Architecture

## Amaç

Bu dosya Arbitra'nın tüm landing ve iç sayfalarının ne işe yarayacağını, hangi kullanıcı sorusunu cevaplayacağını, hangi componentlerden oluşacağını ve başarı kapısını tanımlar.

## Marketing IA

### `/` veya `(marketing)/page.tsx` — Landing

Kullanıcı sorusu:
> “Bu ürün ChatGPT veya basit grammar/research tool'lardan neden farklı?”

Sayfa görevi:
- Arbitra'yı Scientific Review OS olarak konumlandırmak.
- Confidentiality-first güvenini vermek.
- Çıktı kalitesini görsel olarak göstermek.
- Kullanıcıyı sample report veya review wizard'a taşımak.

Zorunlu bloklar:
1. Hero
2. Trust bar
3. Product output preview
4. Use-case selector
5. Chatbot vs Arbitra comparison
6. Confidential reviewer mode
7. Workflow preview
8. Evidence-backed report preview
9. Final CTA

Başarı kapısı:
- İlk ekranda “hakeme gitmeden önce çalışmanın kırılma noktalarını gösterir” mesajı anlaşılır.
- Sample report CTA görünür.
- Privacy/confidentiality güven unsuru ilk 2 scroll içinde görünür.

### `/sample-report` — Güvenli örnek rapor

Kullanıcı sorusu:
> “Gerçek çıktı nasıl görünüyor?”

Sayfa görevi:
- Rapor cockpit'inin güvenli fixture ile gösterilmesi.
- Risk radar, council, evidence map, action plan bileşenlerinin çalıştığını göstermek.

Zorunlu bloklar:
- Demo verdict header.
- Fatal risks preview.
- Evidence drawer demo.
- Action plan preview.
- Export preview disabled/sample.

Başarı kapısı:
- Kullanıcı ürünü satın almadan önce çıktı kalitesini görür.
- Demo gerçek kullanıcı verisi içermez.

### `/security` — Güven ve gizlilik

Kullanıcı sorusu:
> “Yayınlanmamış makalemi buna yükleyebilir miyim?”

Sayfa görevi:
- Confidentiality mode, external AI consent, retention, audit, provider disclosure anlatmak.

Zorunlu bloklar:
- Data flow diagram.
- Author mode vs reviewer/editor confidential mode.
- External AI consent policy.
- Retention/delete policy.
- Audit/provenance explanation.

Başarı kapısı:
- Ürün güven vaatlerini abartmaz; gerçek kabiliyetleri söyler.
- Eğer local/private model henüz yoksa “coming soon” veya “enterprise/private deployment” olarak net ayrılır.

### `/use-cases/article`

Kullanıcı sorusu:
> “Makalem için ne yapar?”

Zorunlu çıktı vaatleri:
- novelty risk
- methodology fit
- citation integrity
- claim-evidence alignment
- journal readiness
- response-to-reviewers

### `/use-cases/conference`

Kullanıcı sorusu:
> “Bildirimi konferansa hazırlar mı?”

Zorunlu çıktı vaatleri:
- track fit
- novelty-to-length ratio
- technical clarity
- reviewer objections
- presentation/readability

### `/use-cases/thesis`

Kullanıcı sorusu:
> “Tezim savunmaya hazır mı?”

Zorunlu çıktı vaatleri:
- chapter health map
- theoretical coherence
- methodology defense
- committee questions
- publication potential

### `/use-cases/grant`

Kullanıcı sorusu:
> “Projem panelde nereden kırılır?”

Zorunlu çıktı vaatleri:
- panel risk
- work package coherence
- feasibility
- budget/timeline risk
- impact narrative

## App IA

### `/dashboard`

Kullanıcı sorusu:
> “Şu an hangi çalışmalarım var ve ne yapmalıyım?”

Zorunlu bloklar:
- Recent reviews.
- Continue revision.
- Critical unresolved actions.
- Start new review CTA.
- Privacy/account status.

Başarı kapısı:
- Dashboard sadece liste değil, next-best-action gösterir.

### `/review/new`

Kullanıcı sorusu:
> “Çalışmamı en doğru şekilde nasıl inceletebilirim?”

Zorunlu bloklar:
- File upload.
- Document type.
- Target.
- Privacy.
- Review depth.
- Beginner/expert switch.

Başarı kapısı:
- Kullanıcı akademik terimleri bilmese bile review başlatır.
- Privacy step bypass edilemez.

### `/review/[jobId]`

Kullanıcı sorusu:
> “Sistem şu an ne yapıyor ve güvenilir şekilde ilerliyor mu?”

Zorunlu bloklar:
- Stage timeline.
- Detected manuscript profile.
- Early warnings.
- Degraded notices.
- Cancel/retry/support id.

Başarı kapısı:
- Kullanıcı bekleme sırasında sistemin gerçek adımlarını görür.
- Hata/degraded durumda boş ekran oluşmaz.

### `/review/[jobId]/report`

Kullanıcı sorusu:
> “Hakemlikte en çok nereden kırılırım ve ne yapmalıyım?”

Zorunlu bloklar:
- Verdict header.
- Top fatal risks.
- Risk radar.
- Reviewer council.
- Evidence map.
- Action plan.
- Section reviews.
- Export.

Başarı kapısı:
- İlk ekranda karar/öncelik net görünür.
- Her kritik bulgu actionable ve kanıtlıdır.

### `/review/[jobId]/revision`

Kullanıcı sorusu:
> “Raporu revizyon işlerine nasıl dönüştüreceğim?”

Zorunlu bloklar:
- P0/P1/P2 kanban/list.
- Effort/gain filters.
- Target section filters.
- Done/ignored/needs-evidence states.
- Response-to-reviewers draft.

Başarı kapısı:
- Rapor pasif metin olmaktan çıkar.

### `/review/[jobId]/evidence`

Kullanıcı sorusu:
> “Bu eleştirinin kanıtı ne?”

Zorunlu bloklar:
- Claim table.
- Manuscript anchor.
- Citation/source support level.
- Confidence.
- Provider/provenance.

Başarı kapısı:
- Abstract-only veya unresolved kaynaklar açıkça görünür.

## Navigation rules

1. Marketing nav en fazla 5 ana link içerir: Product, Use cases, Sample report, Security, Start review.
2. App nav görev odaklıdır: Dashboard, New review, Reports, Settings.
3. Report içi navigation global nav'dan ayrıdır; section rail veya sticky tabs kullanılır.
4. Export/share butonları yalnızca authz ve confidentiality rules geçtiğinde görünür.
5. Confidentiality status app header'da görünür kalır.
