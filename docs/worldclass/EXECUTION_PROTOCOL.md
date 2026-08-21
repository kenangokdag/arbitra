# Autonomous Execution Protocol

Bu protokol, Arbitra kod tabanında insan müdahalesi minimum olacak şekilde kaliteli ve güvenli ilerlemek için kullanılır.

## Ana prensip

Agent asla “büyük dönüşümü tek seferde yapmaya” çalışmaz. Her adım küçük, doğrulanabilir, geri alınabilir ve gate'lenebilir olmalıdır.

## Başlangıç ritüeli

Her çalışma oturumu şu dosyaları sırayla okur:

1. `AGENTS.md`
2. `docs/worldclass/STATE.md`
3. `docs/worldclass/ROADMAP.yaml`
4. İlgili faz dosyası: `docs/worldclass/PHASES/Pxx_*.md`
5. İlgili teknik spec: `docs/worldclass/SPECS/*.md`
6. İlgili checklist: `docs/worldclass/CHECKLISTS/*.md`

## Görev seçme algoritması

```pseudo
load STATE
load ROADMAP.yaml
candidate_tasks = tasks where status != done
eligible_tasks = candidate_tasks where dependencies are done
sort by priority: P0 > P1 > P2, then phase order, then risk reduction
choose first task
read touchpoints
inspect code
implement minimal complete slice
add tests
run gates
update STATE
```

## Task completion definition

Bir task'ın `status: done` olması için:

- Kod değişikliği tamamlandı.
- Veri modeli gerekiyorsa migration var.
- Frontend/backend contract eşleşiyor.
- Test eklendi/güncellendi.
- İlgili gate checklist geçti.
- Docs veya spec değiştiyse güncellendi.
- `STATE.md` içinde değişiklik ve test sonuçları yazıldı.

## Branching strategy

Önerilen branch isimleri:

```text
worldclass/p00-kill-prod-mock-auth
worldclass/p01-openalex-provider-layer
worldclass/p02-durable-review-workflow
worldclass/p03-academic-rubric-registry
worldclass/p04-review-cockpit-ui
```

## Commit message format

```text
<task-id>: <short imperative summary>

Why:
- ...

Changed:
- ...

Verified:
- ...
```

## İlerleme kapıları

### Gate 1: Safety

- Production build'de mock auth yok.
- Env yanlışsa fail-closed.
- Authz owner boundary test edildi.
- Confidential mode external AI consent olmadan provider çağırmıyor.

### Gate 2: Academic

- Çıktı belge türüne göre özelleşti.
- High-severity critique anchor + action item taşıyor.
- Confidence/limitation alanı boş değil.
- Kaynak bulunmadıysa “unverified” olarak işaretleniyor.

### Gate 3: UX

- Wizard varsayılan akışı yeni başlayan için kolay.
- Expert ayarlar saklı ama erişilebilir.
- Progress kullanıcıya gerçek stage bilgisi veriyor.
- Report view ilk bakışta fatal riskleri gösteriyor.

### Gate 4: Reliability

- Job restart/retry/idempotency tasarlandı veya uygulandı.
- Provider timeout/rate-limit/degraded states yönetiliyor.
- Logs/metrics/audit events var.

### Gate 5: Tests

- Unit test.
- Integration test.
- Contract test.
- Eval/smoke veya snapshot test.

## Human escalation gerektiren durumlar

- Gerçek production secret veya vendor hesabı gerekiyor.
- Veri silme/retention migration'ı riskli.
- Üçüncü parti API ücret/limit kararı gerekiyor.
- Marka kararı product owner tarafından değiştiriliyor.
- Hukuki metin/terms/privacy policy son onayı gerekiyor.

## Agent'ın kendi kendine yapması gerekenler

- Belirsiz ama güvenli default seçmek.
- Küçük ADR yazmak.
- Todo bırakmadan açık follow-up task oluşturmak.
- Kod içinde “temporary” hack bırakmamak.
- Test fixture üretmek.
- UI için skeleton/empty/error states eklemek.
- Fallback'i kullanıcıya görünür yapmak.

## Yasaklı davranışlar

- “Sonra test eklenir” demek.
- Üretilen raporda fake confidence kullanmak.
- Provider hatasını boş liste gibi göstermek.
- `except Exception: pass` yazmak.
- Frontend'de user id/token uydurmak.
- Bir migration'ı geri dönüşsüz yapmak.
- Static text'e gömülü marka/locale karışıklığı bırakmak.
