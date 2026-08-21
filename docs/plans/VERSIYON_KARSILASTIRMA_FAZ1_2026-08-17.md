# Plan: Versiyon karşılaştırma — Faz 1 (deterministik özet, kullanıcı-seçimli bağlama)

**Tarih:** 2026-08-17
**Durum:** UYGULANDI (Kenan onayı sonrası) — sonuçlar §6'da.
**Kaynak:** `docs/plans/VERSIYON_KARSILASTIRMA_ARASTIRMA_2026-08-16.md` §4 — Kenan kararı: "Faz 1'i bugün planla+uygula."
**Guardian gerekmiyor** — bulgu-eşleştirme (Faz 2, bulanık/yargısal) bu planda YOK; sadece iki `ReviewReport`'un üst-seviye alanlarını (verdict/skor) deterministik diff'lemek.
**Karar verici:** Kenan.

---

## 1. Kapsam (araştırma dokümanından)

- DB: `parent_job_id` kolonu.
- Kullanıcının KENDİ seçtiği (otomatik/sessiz DEĞİL) bağlama — upload sırasında "bu, önceki bir işimin devamı" seçimi.
- Rapor sayfasında SADECE deterministik özet: verdict değişti mi, hazırlık puanı deltası, boyut skorları deltası.
- Bulgu-eşleştirme ("hangi bulgu kapandı") bu planda YOK — Faz 2, ayrı oturum.

## 2. Backend

### 2.1 Migration `db/migrations/0045_review_parent_job.sql` (yeni, sıradaki numara — `0044` en son)
```sql
ALTER TABLE public.review_job
  ADD COLUMN IF NOT EXISTS parent_job_id uuid REFERENCES public.review_job(job_id);
CREATE INDEX IF NOT EXISTS idx_review_job_parent
  ON public.review_job (parent_job_id) WHERE parent_job_id IS NOT NULL;
```
`0042`'nin additive-önce deseniyle BİREBİR aynı (nullable, mevcut satırlar bozulmaz).

### 2.2 `api/models/review.py` — 2 yeni model
```python
class DimensionScoreDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: DimensionKey
    previous_score: float | None
    current_score: float | None
    delta: float | None  # current - previous; ikisi de yoksa None

class VersionComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parent_job_id: UUID
    previous_verdict: Verdict
    current_verdict: Verdict
    verdict_changed: bool
    previous_readiness_score: float | None  # executive_verdict'ten, v2-only
    current_readiness_score: float | None
    readiness_delta: float | None
    dimension_deltas: list[DimensionScoreDelta]

class VersionComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: UUID
    comparison: VersionComparison | None  # None = parent_job_id yok (ilk yükleme)
```

### 2.3 Yeni servis: `api/services/version_comparison_service.py`
`build_comparison(parent_job_id: UUID, previous: ReviewReport, current: ReviewReport) -> VersionComparison` — SAF fonksiyon, iki raporun `verdict`/`executive_verdict.overall_readiness_score`/`dimension_scores`'unu diff'ler. `dimension_deltas`: iki raporun `dimension_scores`'undaki key'lerin BİRLEŞİMİ (birinde olup diğerinde olmayan key → o taraf `None`, dürüst).

### 2.4 `api/services/review_service.py` — 3 küçük ekleme
1. `_insert_job(...)`'a `parent_job_id: UUID | None = None` parametresi, `row["parent_job_id"] = str(parent_job_id)` (varsa).
2. `create_and_dispatch(...)`'a `parent_job_id: UUID | None = None` — **BOLA:** insert'ten ÖNCE `parent_job_id` verilmişse sahiplik kontrolü (`_fetch_job(parent_job_id)`, `user_id` eşleşmiyorsa `LookupError` — route 404'e çevirir, mevcut `/report` deseniyle TUTARLI).
3. Yeni `get_parent_job_id(user_id, job_id) -> UUID | None` — `_fetch_job` reuse eder, sahiplik kontrolü yapar (`LookupError` yoksa/sahip değilse), `row.get("parent_job_id")` döner. **`get_report()`'un imzasına DOKUNULMUYOR** (chat.py'nin `_build_report_context`'i zaten buna bağımlı — DANISMAN_REPORT_GROUNDING_PERSONA_2026-08-16 planının riski, blast-radius'u genişletmemek için AYRI, küçük fonksiyon tercih edildi).
4. Yeni `list_user_jobs(user_id, limit=20) -> list[dict]` — `admin_list_jobs()`'un (`review_service.py:~735-747`) BİREBİR aynı deseni, `.eq("user_id", user_id)` filtresiyle.

### 2.5 `api/routes/review.py` — 3 uç nokta değişikliği
1. `upload_review()`'a `parent_job_id: UUID | None = Form(None)` — `create_and_dispatch`'e geçilir. `LookupError` → 404 `parent_job_not_found`.
2. Yeni `GET /jobs` (kullanıcı-kapsamlı, `/admin/jobs`'tan AYRI — path çakışması YOK, farklı segment derinliği doğrulandı): `_user_id(request)` + `review_service.list_user_jobs`. `/admin/jobs`'un (`review.py:215-218`) deseniyle BİREBİR aynı, `response_model` YOK (o da yok, tutarlı).
3. Yeni `GET /{job_id}/comparison` (`response_model=VersionComparisonResponse`): `get_parent_job_id` → yoksa `comparison=None` döner (404 DEĞİL — "henüz versiyon geçmişi yok" normal bir durum, hata değil). Varsa iki raporu `get_report()` ile çeker (REUSE, chat.py'nin de kullandığı fonksiyon), `build_version_comparison` çağırır.

## 3. Frontend

### 3.1 `web/src/lib/review-api.ts`
- Yeni tipler: `UserJob`, `UserJobsResponse`, `DimensionScoreDelta`, `VersionComparison`, `VersionComparisonResponse` (backend modelleriyle BİREBİR aynalanır, dosyanın kendi kuralı gereği).
- `uploadReview()`'a opsiyonel `parentJobId?: string` — form'a eklenir (`is_author` gibi mevcut opsiyonel alanlar deseniyle TUTARLI).
- `fetchMyReviewJobs(limit?, signal?)`, `fetchVersionComparison(jobId, signal?)`.

### 3.2 `web/src/hooks/useReview.ts`
Yeni `useVersionComparison(jobId, enabled)` — `useReviewReport`'un (satır 44-51) BİREBİR aynı deseni.

### 3.3 `web/src/app/(app)/review/page.tsx` (upload sayfası)
Opsiyonel bir bölüm: "Bu makalenin önceki bir versiyonu var mı?" — `fetchMyReviewJobs()` (mount'ta), sonuç boşsa bölüm HİÇ gösterilmez (ilk yükleme deneyimi bozulmaz). Doluysa basit bir liste/select (`source_name` + tarih), varsayılan seçim YOK (kullanıcı bilinçli seçer, otomatik/sessiz bağlama YOK — araştırma dokümanı §3'ün gerektirdiği güvenlik).

### 3.4 `web/src/app/(app)/review/[jobId]/page.tsx`
`useVersionComparison(jobId, isDone)` çağrılır, sonuç `<ReviewReportView comparison={comparisonQuery.data?.comparison ?? null} .../>` olarak PROP geçilir.

**Kritik tasarım kararı (test uyumluluğu için ZORUNLU):** `ReviewReportView` kendi içinde `useQuery` ÇAĞIRMAZ — mevcut `ReviewReportView.test.tsx` `<ReviewReportView>`'ı DOĞRUDAN, QueryClientProvider OLMADAN render ediyor (41 test). İçeride bir hook çağrısı eklemek TÜMÜNÜ kırardı. Veri üstte (`[jobId]/page.tsx`) çekilip PROP olarak geçilir — mevcut mimariyle (report/jobId zaten prop) TUTARLI.

### 3.5 `ReviewReportView.tsx`
Yeni opsiyonel prop `comparison?: VersionComparison | null` → yeni `VersionComparisonSummary` bileşeni, `comparison` truthy ise Katman 1'in üstünde/içinde render edilir (verdict değişimi + hazırlık puanı deltası + boyut deltaları — tablo). `comparison` yoksa (ilk yükleme, prop `undefined`/`null`) HİÇBİR ŞEY render edilmez — mevcut testler regresyon YAŞAMAZ (prop opsiyonel, default davranış değişmez).

## 4. Test planı

1. Backend birim: `build_version_comparison` — verdict/skor/boyut delta hesaplaması (eşit/farklı/eksik-boyut senaryoları).
2. Backend entegrasyon: `GET /{job_id}/comparison` — parent yoksa `comparison=null`, varsa dolu obje, BOLA (başkasının parent_job_id'si ile upload → 404).
3. Backend: `POST /upload` + `parent_job_id` → satırda doğru set ediliyor mu (mock).
4. Frontend: `VersionComparisonSummary` render testi (comparison var/yok).
5. Mevcut testlerin regresyon YAŞAMADIĞI (özellikle `ReviewReportView.test.tsx`'in 41 testi).

## 5. Kapsam dışı

1. Faz 2 — bulgu-eşleştirme (hangi Finding kapandı/yeni), otomatik title-benzerliği önerisi. Araştırma dokümanında zaten TODO.
2. Geçmiş (bu özellik öncesi) job'ların geriye dönük bağlanması.
3. 30 günlük retention ile çakışma (parent silinmişse comparison ne olur — `get_parent_job_id`/`get_report` zaten `LookupError` ile dürüstçe 404/None döner, ekstra kod GEREKMİYOR, ama plan bunu bilinçli kabul ediyor).

## 6. Sonuçlar (uygulandı, 2026-08-17)

**Kod:**
- `db/migrations/0045_review_parent_job.sql` — `parent_job_id` (additive, nullable) + index.
- `api/models/review.py` — `DimensionScoreDelta`, `VersionComparison`, `VersionComparisonResponse`.
- `api/services/version_comparison_service.py` (yeni) — `build_version_comparison` (saf fonksiyon).
- `api/services/review_service.py` — `_insert_job`/`create_and_dispatch`'e `parent_job_id` (BOLA: insert'ten ÖNCE sahiplik kontrolü) + yeni `get_parent_job_id`/`list_user_jobs`. `get_report()`'un imzası DOKUNULMADI (plana sadık kalındı).
- `api/routes/review.py` — `POST /upload`'a `parent_job_id` Form alanı, yeni `GET /jobs`, yeni `GET /{job_id}/comparison`.
- `web/src/lib/review-api.ts` — yeni tipler + `fetchMyReviewJobs`/`fetchVersionComparison` + `uploadReview`'a `parentJobId`.
- `web/src/hooks/useReview.ts` — yeni `useVersionComparison` (`useReviewReport` deseniyle aynı).
- `web/src/app/(app)/review/[jobId]/page.tsx` — `comparison` verisi çekilip `ReviewReportView`'a PROP olarak geçiliyor (component içinde useQuery YOK — plan §3.4'ün zorunlu kıldığı tasarım kararı).
- `web/src/app/(app)/review/page.tsx` — opsiyonel "önceki versiyon" seçici (geçmiş job yoksa hiç render edilmez, varsayılan seçim yok).
- `web/src/components/review/ReviewReportView.tsx` — yeni `VersionComparisonSummary`, `comparison` prop opsiyonel.

**Uygulama sırasında bulunan/düzeltilen regresyonlar (2 adet):**
1. `tests/unit/test_be1_idempotency_resume.py::test_idempotent_miss_inserts_new` — mock'un `_insert_job` imzası sabit-arity'ydi (7 param), benim eklediğim 8. pozisyonel argümanla (`parent_job_id`) kırılırdı. Mock'a `parent_job_id=None` eklendi.
2. `web/src/app/(app)/review/page.test.tsx` — `vi.mock("@/lib/review-api", ...)` sadece `uploadReview`'ı export ediyordu; `page.tsx`'in yeni `fetchMyReviewJobs()` çağrısı "is not a function" ile çökerdi. Mock'a `fetchMyReviewJobs` (boş liste döner) eklendi.

**Testler:** Backend — `test_version_comparison_service.py` (4), `test_review_parent_job_service.py` (6), `test_review_comparison_endpoint.py` (4). Frontend — `ReviewReportView.test.tsx`'e 4 yeni (20 toplam), `review/page.test.tsx`'e 4 yeni (8 toplam).

**Regresyon:** Backend `-k "review or export or chat or comparison or parent_job or version or idempotency or llm_service or role_module"` — **151 passed**. Frontend `review/` + `review components` — **55 passed** (10 dosya). `tsc --noEmit` temiz.

**Kapsam dışı kalanlar (§5) hâlâ açık** — Faz 2 (bulgu-eşleştirme) ayrı, kilitli TODO.
