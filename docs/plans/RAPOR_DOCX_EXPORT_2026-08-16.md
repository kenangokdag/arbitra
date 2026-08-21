# Plan: Hakem raporu için `.docx` indirme özelliği

**Tarih:** 2026-08-16
**Durum:** UYGULANDI (Kenan onayı sonrası) — sonuçlar §6'da.
**Kaynak:** Kenan'ın bu oturumdaki isteği — "rapor için .docx/.pdf indirme özelliği ekleyelim."
**Kapsam kararı (Kenan, bu oturum):** SADECE `.docx`. PDF ertelendi (WeasyPrint'in Dockerfile'a sistem paketi eklemesi gereken bir karar, ayrı ele alınacak).
**Karar verici:** Kenan.

---

## 1. Araştırma sonucu (kanıtlı, A-seviye)

- `web/src/components/review/ReviewReportView.tsx` (1821 satır) — backend'den gelen tipli `ReviewReport` JSON'unu render ediyor (`review-api.ts:511-518`, `GET /api/review/{job_id}/report`). Export için component'i "fotoğraflamaya" gerek yok — aynı `ReviewReport` Pydantic modelinden (`api/models/review.py:330-368`) bağımsız bir doküman üretilebilir.
- **`python-docx` ZATEN proje bağımlılığı** (`pyproject.toml:41`, şu an ingestion'da `.docx` OKUMAK için kullanılıyor). Aynı kütüphaneyle YAZMAK da mümkün — **yeni paket yok, Dockerfile değişmiyor.**
- Mevcut, doğrudan kopyalanabilir 2 desen var (icat etmiyoruz):
  - **Backend dosya-indirme yanıtı:** `api/routes/paper_detail.py:152-156` — `Content-Disposition: attachment; filename="..."` header'lı response deseni zaten var (şu an `PlainTextResponse` ile, biz `Response` ile aynı deseni docx media_type'ıyla kullanacağız).
  - **Frontend blob-fetch:** `web/src/lib/tts-api.ts:21-52` — `apiFetch` JSON-only olduğu için native `fetch` + `Authorization` header + `.blob()` deseni zaten var (TTS için). Aynısı docx için reuse edilecek.
  - **Frontend "diske indir" idiomu YOK** (`AudioPlayButton.tsx` blob'u `<audio src>` ile INLINE çalıyor, diske indirmiyor) — standart `URL.createObjectURL` + geçici `<a download>` + `.click()` idiomu ilk kez yazılacak (yeni kütüphane gerekmiyor, tarayıcı standardı).
  - **Auth/yetki bedava geliyor:** `api/routes/review.py:40-44` — router `dependencies=[Depends(tier_gate)]` ile tanımlı, yeni endpoint router'a eklenince tier_gate OTOMATİK uygulanır, ekstra kod gerekmez. BOLA için `review_service.get_report(user_id, job_id)` (zaten sahip-kapsamlı, review_service.py:723-730) reuse edilecek — `GET /{job_id}/report`'un (review.py:248-255) BİREBİR aynı deseni.

## 2. Backend

### 2.1 Yeni servis: `api/services/report_export_service.py`
`build_docx(report: ReviewReport, job_id: UUID) -> bytes` — `python-docx` ile.

İçerik iskeleti (V1Report'un yapısına yakın, `ReviewReportView.tsx:1024-1122`'deki bölüm sırasıyla PARALEL — ama görsel birebir eşleşme HEDEF DEĞİL):
- Başlık + karar (verdict) + final_score
- Özet
- Boyut skorları (tablo)
- Güçlü/zayıf yönler
- Detaylı yorumlar
- Yazara sorular
- Genel değerlendirme
- Atıf bütünlüğü sayaçları
- **v2 varsa ek olarak:** executive_verdict, risk_radar, findings (severity sıralı), action_plan, reviewer_council, section_reviews
- Provenance (künye)

**Dürüst sınır (plana şimdiden yazılıyor):** Frontend'deki `isV2` hesaplaması (`ReviewReportView.tsx:84-93`) TypeScript'te yaşıyor, Python'a otomatik taşınmıyor — aynı mantık backend'de KISA bir yardımcı fonksiyonla TEKRAR yazılacak (iki runtime, paylaşılan kod imkânsız). Bu bilinçli bir kod-tekrarı, riski düşük (basit boolean mantık) ama TEK bir yerde değişirse diğeri unutulabilir — ileride bir regresyon kaynağı, not düşülüyor.

**Görsel sadelik kararı:** Şiddet (severity) rozetleri gibi renkli/etkileşimli UI öğeleri docx'te düz metin etiketi olarak yazılacak (örn. "[KRİTİK]"), pixel-perfect eşleşme hedeflenmiyor — okunabilir, profesyonel bir Word dokümanı hedefi, web sayfasının birebir kopyası değil.

### 2.2 Yeni endpoint: `api/routes/review.py`
```
GET /api/review/{job_id}/export.docx
```
- `_user_id(request)` + `review_service.get_report(user_id, job_id)` (mevcut `/report` endpoint'iyle BİREBİR aynı desen, review.py:248-255).
- `LookupError` → 404 (mevcut desenle tutarlı).
- `report_export_service.build_docx(report, job_id)` çağrılır.
- `Response(content=docx_bytes, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="arbitra-rapor-{job_id}.docx"'})`.

## 3. Frontend

### 3.1 `web/src/lib/review-api.ts`
Yeni fonksiyon `fetchReviewReportDocx(jobId, signal): Promise<Blob>` — `tts-api.ts:21-52` deseniyle birebir (native fetch + Authorization + Accept header + `.blob()`).

### 3.2 `web/src/components/review/ReviewReportView.tsx`
Bir "İndir (.docx)" butonu eklenir (yer önerisi: künye şeridinin yanı ya da rapor başlığının üstündeki ince ARBITRA künye şeridi — `ReviewReportView.tsx:97-108`). Tıklayınca: fetch → blob → `URL.createObjectURL` + geçici `<a download="arbitra-rapor-{jobId}.docx">` + `.click()` + `URL.revokeObjectURL` (standart tarayıcı idiomu).

## 4. Test planı

1. **Backend birim test:** `build_docx()` bir minimal + bir v2-dolu `ReviewReport` fixture'ından geçerli `.docx` bytes üretiyor mu — `python-docx`'in kendisiyle geri okuyup verdict/başlık metninin dokümanda VAR olduğunu doğrula.
2. **Backend entegrasyon test:** `TestClient` ile `GET /api/review/{job_id}/export.docx` — `Content-Disposition`/`Content-Type` header doğrulaması, başka kullanıcının job'ı için 404 (BOLA).
3. **Frontend birim test:** `fetchReviewReportDocx` mock-fetch ile blob döndüğünü doğrular (tts-api testi varsa aynı desen).

## 5. Kapsam dışı

1. **PDF export — Kenan kararıyla ERTELENDİ, ayrı TODO.** Bekleyen ön-koşul: deploy platformu netleşmeli (`Dockerfile:1` yorumu "Railway imajı" diyor, CLAUDE.md/proje bağlamı "Render'da deploy" diyor — bu tutarsızlık §1'de not edildi). WeasyPrint kararı platforma göre değişebilir (Docker tabanlı deploy'da sistem paketi eklemek kolay, buildpack tabanlı bir platformda zor/imkânsız olabilir) — platform netleşmeden PDF yaklaşımı seçilmemeli.
2. `.docx`'in web sayfasıyla pixel-perfect görsel eşleşmesi — okunabilir/profesyonel doküman hedefleniyor, birebir kopya değil.
3. `isV2` mantığının backend/frontend arasında tek bir yerden paylaşılması (kod-tekrarı riski §2.1'de not edildi, çözümü bu planın kapsamı dışında).

## 6. Sonuçlar (uygulandı, 2026-08-16)

**Kod:** `api/services/report_export_service.py` (yeni, `build_docx`), `api/routes/review.py` (`GET /{job_id}/export.docx`, mevcut `/report`'la birebir aynı BOLA deseni, `tier_gate` router seviyesinde otomatik), `web/src/lib/review-api.ts` (`fetchReviewReportDocx`), `web/src/components/review/ReviewReportView.tsx` (İndir (.docx) butonu, künye şeridinde).

**Doğrulama sırasında bulunan/düzeltilen şey:** `engine/ingestion/docx_parser.py:9-13`'te "python-docx .venv'de KURULU DEĞİL" diye eski bir doğrulama notu vardı — kod yazmadan önce bunu bu ortamda tekrar test ettim (`python -c "import docx"`), ŞU AN kurulu ve import edilebiliyor (pyproject.toml'daki bağımlılık gerçek). Eski not artık güncel değil, muhtemelen paket sonradan eklendi — plan varsayımım (sıfır yeni bağımlılık) doğrulandı, halüsinasyon değil.

**Testler:**
- Backend: `tests/unit/test_report_export_service.py` (v1 + v2 rapor → .docx içerik doğrulaması) + `tests/unit/test_review_export_endpoint.py` (Content-Type/Content-Disposition + BOLA 404) — **4/4 PASS**.
- Frontend: `web/src/lib/review-api-docx-export.test.ts` (4 test) + mevcut `ReviewReportView.test.tsx` (8 test, buton eklenmesinden regresyon YOK) — **12/12 PASS**.
- `tsc --noEmit`: temiz (bir hata bulundu-düzeltildi: test dosyam `ApiError`'ı `review-api.ts`'ten import etmeye çalışmıştı, o dosya re-export etmiyor — `./api`'den düzeltildi).

**Regresyon:** `-k "review or export or account_deletion"` filtresiyle **114 passed** (litellm'in async teardown'undan gelen zararsız warning'ler var, test başarısı DEĞİL).

**Kapsam dışı kalanlar (§5) hâlâ açık** — PDF, deploy platformu netleşene kadar TODO.
