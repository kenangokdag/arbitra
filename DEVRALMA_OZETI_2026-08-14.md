# Arbitra — Devralma Özeti (2026-08-14)

**Kime:** Yazılım ekibi (devralacak taraf)
**Kimden:** Kenan
**Amaç:** "Kusursuz çalışıyor" iddiası DEĞİL — pipeline'ın güvenilir çalıştığını çeşitli senaryolarla göstermek ve bilinen sınırlamaları dürüstçe belgelemek.

**Tam ayrıntılı iş günlüğü:** `PDF_PIPELINE_CALISMA_GUNLUGU.md` (bu doküman onun ÖZETİ — ayrıntı/kanıt için oraya bakın, bölüm numaraları `§NN` ile referans verilmiştir).

---

## ⚠️ ÖNEMLİ — 2026-08-15/16 GÜNCELLEMESİ (devralmadan önce OKUYUN)

Bu devralma özeti 2026-08-14'te yazıldı. 2026-08-15'te canlı yeniden test sırasında **`citation_integrity` moat boyutunun güvenilirliğini sorgulayan bir bulgu** ortaya çıktı, 2026-08-16'da KISMEN düzeltildi. Detay: `PDF_PIPELINE_CALISMA_GUNLUGU.md §63-67`.

**Bulgu (2026-08-15):** `engine/ingestion/common.py`'deki bir referans-bölme regex hatası, DOI/URL satırı içeren kaynakçalarda birden fazla referansı tek girdide birleştirip yanlış bir "başlık" çıkarıyordu — motor bunu "uydurma atıf" (fabricated) diye yanlışlıkla işaretliyordu. 61-goldset'te 77 bilinen çöp-başlık örneği vardı.

**Düzeltme (2026-08-16, UYGULANDI, guardian onaylı):** Referans-bölme regex'i + başlık-çıkarma mantığı düzeltildi. **Sonuç: 77 çöp-başlıktan 0'ı kaldı** (39'u tamamen doğru başlığa döndü — "Long short-term memory", "Deep residual learning..." gibi GERÇEK, ünlü makaleler daha önce "uydurma atıf" diye işaretlenmişti — 38'i güvenli `None` oldu). Canlı OpenAlex doğrulamasında (6 orijinal "fabricated" vaka): **4/6 tamamen düzeldi, 2/6 hâlâ "fabricated" ama artık FARKLI/YENİ nedenlerle** (biri muhtemelen gerçek bir bulgu — kaynak makalenin kendi DOI hatası; diğeri YENİ, ayrı bir entry-boundary hatası — sayfa-numarası artığı, bu düzeltmenin kapsamı dışında).

**Hâlâ AÇIK olan (yazılım ekibi bilmeli):**
1. Bu düzeltme `citation_integrity`'nin "gerçek sahteciliği doğru yakaladığı KANITLANDI" anlamına GELMİYOR (guardian'ın ısrarla vurguladığı ayrım) — sadece BİLİNEN parsing-kaynaklı yanlış-pozitifleri temizledi. "Moat mimarisi var" ile "moat mimarisi çalıştığı kanıtlandı" arasındaki fark hâlâ açık.
2. §41 ve öncesindeki TÜM geçmiş "moat-doğruluk" ölçümleri (n=4 dahil) bu düzeltmeden ÖNCEKİ koda dayanıyor — yeniden ölçülmedi, caveat'li kalmalı.
3. YENİ bulunan, ayrı bir entry-boundary hatası (sayfa/dipnot-numarası artıkları) düzeltilmedi.
4. §63-64'teki moat-gate severity düzeltmesi (Fix A) artık temiz veriyle yeniden değerlendirilebilir ama henüz yapılmadı.

---

## 1) Pipeline nedir, nasıl çalışır

- **Uç noktalar:** `POST /api/review/upload` (PDF/docx/latex/zip) → `GET /{job_id}/status` (polling) → `GET /{job_id}/report` (bitince).
- **Akış:** `queued → parsing → checking_citations → checking_context → coverage → orchestrating (en uzun, 5-8 dk) → assembling → done`.
- **Motor:** iki paralel skorlama (`run_orchestration()` — 10 boyut, writer→5 critic→editor; `assess_manuscript()` — 30+ ince-taneli boyut → Finding[]) `run_pipeline()`'da birleşiyor.
- **Demo materyalleri:** `C:\Users\USER\Desktop\Arbitra\arbitra_demo_curl_komutlari.md` + `arbitra_demo_postman_collection.json` (dev-mode JWT ile, gerçek Supabase Auth kurmaya gerek yok).

## 2) Çeşitlilik testi (madde 1)

**Araç:** `eval/review/continuous_diversity_test.py` — tekrar-çalıştırılabilir, `eval/review/results/continuous_diversity_log.jsonl`'a her koşumda APPEND eder (üzerine yazmaz), böylece zaman içinde tutarlılık izlenebilir. 10 makale, 8 disiplin, 7 study_design sınıfı (aşağıdaki tablo).

**Sonuçlar (bu oturumda tamamlananlar):**

| Vaka | Disiplin | study_design (gerçek) | verdict | final_score | guard tetiklendi mi | Not |
|---|---|---|---|---|---|---|
| deneme (eğitim) | eğitim bilimleri | — | **failed** | — | — | `LLMServiceError` (JSON kesilme) — bkz §57, önceden bilinen risk, çökme değil |
| peerj-4181 | biyoloji/sağlık | quantitative (0.8) | major_revision | 7.32 | yok | — |
| peerj-cs-3113 | bilgisayar bilimi | quantitative (0.9) | major_revision | 7.32 | yok | — |
| openreview_odjMSBSWRt | ML | quantitative (0.9) | accept | 7.57 | `citation_integrity_grounding:downgraded_1` | §38 ungrounded-citation guard canlıda tetiklendi |
| peerread_iclr2017_398 | ML/CS | theoretical (0.8) | accept | 8.38 | yok | — |
| PIED physics | fizik/mühendislik | computational_modeling (0.8) | major_revision (düzeltme sonrası) | 8.02 | `quant_design_mismatch:downgraded_1` | İlk denemede NUL-byte bug ile failed (§58) — kök nedeni bulundu, düzeltildi, sunucu yeniden başlatılıp AYNI dosyayla yeniden test edildi: `done`, ayrıca §46/47 guard'ının canlıda ilk kez tetiklendiği gözlemlendi |
| PLOS qualitative (Sierra Leone) | halk sağlığı | qualitative (0.9) | reject | 5.79 | yok | — |
| PLOS meta-analiz (spor eğitimi) | beden eğitimi/spor | meta_analysis (0.95) | reject | 5.34 | yok | Motorun `meta_analysis` sınıflandırması ilk kez gözlemlendi |
| PLOS mixed-methods (COVID) | halk sağlığı/eğitim | mixed_methods (0.95) | reject | 5.26 | yok | mixed_methods boşluğu kapandı |
| PLOS mühendislik (sürdürülebilirlik) | mühendislik eğitimi | quantitative (0.8) | reject | 6.08 | yok | — |
| IJDesign (anksiyeteli bağlanma + cihaz) | tasarım araştırması/etkileşim tasarımı | **unknown** (0.2) | accept | 7.85 | yok | 4. arama turunda bulundu (CC BY, ijdesign.org) — motor bu makaleyi bilinen study_design sınıflarına GÜVENLE oturtamadı, dürüstçe "unknown+düşük güven" dedi (yanlış kategoriye zorlamadı) |

**Özet (11 vaka, 3 turda): 9/11 ilk denemede başarılı (verdict çeşitliliği: accept x3, major_revision x2, reject x4), 2'si failed — ikisi de çökme/hang DEĞİL, nazik hata, ikisi de kök nedenine inilip DÜZELTİLDİ (biri retry mekanizmasıyla, biri NUL-byte fix'iyle — bkz. aşağıda ve §57-59). 9 farklı disiplin, study_design çeşitliliği 6 bilinen sınıf (quantitative/theoretical/computational_modeling/qualitative/meta_analysis/mixed_methods) + meşru bir `unknown` vakasını kapsıyor. Güzel sanatlar/tasarım boşluğu KAPANDI (4. arama turunda, kullanıcı isteğiyle tekrar denendi).**

**Önemli bulgu (§57), DÜZELTİLDİ (§59):** `deneme.pdf` bu oturumda daha önce EN AZ 2 kez `accept` (final_score 7.5-7.62) ile başarıyla tamamlanmıştı. Bir koşumda AYNI dosya `LLMServiceError` ile `failed` oldu. Kök neden: Gemini 2.5 Pro'nun "thinking" modu tam kapatılamıyor (sadece flash tier'da kapatılabiliyor, `llm_service.py:99`), bazen `max_tokens=8000` bütçesini thinking yiyor, `_DraftReport` JSON'ı yarıda kesiliyor. **Çökme/hang DEĞİLDİ** — pipeline nazikçe `status=failed` + okunabilir hata mesajıyla bitiyordu. **Plan yazıldı, guardian 2 tur onayladı, düzeltme UYGULANDI:** writer/editor artık bu spesifik hataya karşı 1 kez otomatik retry yapıyor (`api/services/review_orchestration.py`, `_call_with_truncation_retry`), retry olursa rapora dürüst bir not düşülüyor. 857 test PASS. **Dürüst sınır:** arıza deterministik olmadığı için bu oturumda AYNI arıza yeniden üretilip "canlı doğrulandı" denemedi — sadece mock-seviyesinde doğrulandı (bkz. `docs/plans/LLM_THINKING_TRUNCATION_RETRY_2026-08-14.md`).

## 3) Hata senaryoları (madde 2)

**HTTP sınır-doğrulaması — 5/5 nazik (crash yok):**

| Senaryo | Sonuç |
|---|---|
| Boş dosya | 400 `empty_file` |
| Sahte PDF (düz metin, `.pdf` uzantılı) | 400 `file_content_mismatch` (magic-byte kontrolü) |
| 31MB dosya (limit 30MB) | 413 `file_too_large` |
| Desteklenmeyen uzantı (`.exe`) | 400 `unsupported_file_type` |
| Kesik/bozuk PDF (geçerli başlık, gövde eksik) | Kabul edildi (200), pipeline'a girdi |

**Kesik-PDF pipeline testi (SONUÇLANDI):** Magic-byte kontrolünü geçen ama gövdesi eksik bir PDF (`%PDF` başlıklı, 5000 bayta kesilmiş) kabul edildi, pipeline'a girdi. **Çökme/hang YOK** — iş `done` statüsüyle bitti. Motor sahte-güvenli bir "accept" UYDURMADI: `verdict=reject`, `final_score=4.34`, sınıflandırma `unknown/unknown` ("Belgede başlık, metin veya referans bulunamadığı için sınıflandırma yapmak mümkün değil"), özet: *"submitted file appears to be empty or in an unreadable format... a scientific evaluation is not possible... seems to be a technical error rather than a complete manuscript."* Bu iyi bir sonuç — dürüst degradasyon.

**Yeni crash bulundu ve DÜZELTİLDİ (çeşitlilik testi sırasında, madde 1'de):** Gerçek bir fizik makalesi (14224_PIED_Physics_Informed_Ex.pdf), PDF'in gömülü matematik gösterimi PyMuPDF metin çıkarımında NUL (U+0000) baytı üretiyordu — Postgres bunu kabul etmiyor, pipeline 10.8 saniyede `SupabaseQueryError` ile düşüyordu. **Kök nedeni bulundu, `engine/ingestion/pdf_parser.py`'de tek noktadan (kaynakta) düzeltildi, regresyon testi eklendi (`tests/unit/test_ingestion.py::test_parse_pdf_strips_nul_bytes_from_extracted_text`), tam test suite'i çalıştırıldı (853 passed), sunucu yeniden başlatılıp AYNI dosyayla uçtan uca yeniden doğrulandı.** Detay: `PDF_PIPELINE_CALISMA_GUNLUGU.md §58`.

**Provider-timeout (OpenAlex/LLM):** Kod incelemesiyle doğrulandı (`api/services/openalex_polite.py:154-179`, `api/services/llm_service.py:101-103`) — her ağ çağrısı açık timeout + `call_resilient()` sarmalayıcısı taşıyor, istisnalar `OpenAlexError`/`LLMServiceError`'a normalize ediliyor, `review_service.py`'nin dış try/except'i (`§`, satır 337-688) hepsini yakalayıp `status=failed` yazıyor. **Dürüst sınır:** gerçek bir ağ-kesintisi enjeksiyonuyla ampirik olarak YENİDEN test edilmedi bu oturumda (kod-kanıtlı, fiili-arıza-kanıtlı değil). Bilinen istisna: altyapı (Supabase) erişilemezse pipeline'ın kendi hata-yazma mekanizması da çalışamaz — bu daha önce gerçekten yaşandı (DNS arızası olayı, bkz. günlük) ve kod-seviyesinde düzeltilebilir bir şey değil (dış bağımlılık kesintisi).

## 4) Kopyalanabilirlik testi (madde 3, guardian'ın sorusu)

3 kaçırılan referansın ham metnini naif bir LLM'e (Arbitra'nın kendi mantığı olmadan) verdim. **3/3 doğru DOI bulundu.**

**Dürüst yorum:** Bu, DOI-string-ayıklama adımının (regex, `extract_doi()`) bir LLM'den DAHA KIRILGAN olduğunu gösteriyor — düzeltmeye değerdi ama düşük-değerli bir mühendislik alanıydı. **Bu DOI-ayıklama Arbitra'nın moat iddiası DEĞİL.** Asıl moat iddiası — ayıklanan DOI'yi OpenAlex'te yapısal olarak retraction/fabrication'a karşı doğrulamak — bu testte SINANMADI (naif LLM'e "bu geri çekilmiş mi?" sorulmadı). Detay: `PDF_PIPELINE_CALISMA_GUNLUGU.md §53`.

**Guardian'ın kritik uyarısı (danışıldı):** Bu bulgu "o zaman DOI ayıklamayı LLM'e devredelim" sonucuna YANLIŞLIKLA sıçranmamalı. Test, DOI'si OLMAYAN/FABRİKE bir referansta LLM'in DOI UYDURUP UYDURMADIĞINI sınamadı — eğer uyduruyorsa (muhtemel risk), ayıklamayı LLM'e devretmek `citation_integrity`'nin temel garantisini (deterministik ayıklama → yapısal doğrulama) LLM hallüsinasyon riskiyle değiştirmiş olur. **Karar: DOI-ayıklama LLM'e devredilmeyecek**, bu fikir gündeme gelirse önce fabrike-DOI senaryosuyla test edilmeli.

## 5) Açık/çözülmemiş sınırlamalar (dürüstçe, olduğu gibi)

1. **design_validity/measurement_validity kök nedeni ÇÖZÜLMEDİ, ve 3 aday kaynağın ARAŞTIRMASI TAMAMEN KAPANDI.** Arbitra'nın kendi ürettiği bu 2 boyut skoru, insan-soundness skoruyla n=29'da hiçbir güvenilir korelasyon göstermiyor (çoklu-karşılaştırma düzeltmesi sonrası, bkz §47/48). 3 goldset-büyütme kaynağı (Retraction Watch, berenslab/iclr-dataset, MOPRD) gerçek veriyle test edildi — **üçü de kesin elendi:** Retraction Watch'ın hiç insan-skoru yok; berenslab sadece genel puan+abstract taşıyor (alt-kriter/tam-metin yok); MOPRD hem erişilemedi (site 3 denemede ECONNRESET) HEM DE erişilebilse bile çözmeyecekti (arXiv metninden doğrulandı: MOPRD'nin TEK kaynağı PeerJ, ve mevcut 6 PeerJ goldset girdimiz zaten PeerJ'in sayısal alt-kriter skoru YAYINLAMADIĞINI kanıtlıyor — `human_scores` 6/6 boş). **n=29 tıkanması hâlâ açık, ama bu 3 kaynak üzerinden ilerlemek ARTIK ANLAMSIZ — yeni bir kaynak stratejisi gerekiyor.**
2. **Moat ground-truth kalibrasyonu eksik.** `citation_integrity`/`statistical_consistency`/`coverage_completeness` boyutlarının goldset'te hiç insan-skoru karşılığı yok — held-out doğrulama bu 3 boyutu KAPSAMIYOR. Bilinçli kabul mü, ayrı bir etiketleme çalışması mı gerekiyor — karar verilmedi.
3. **Goldset-merge kararı verildi (bu oturumda), guardian onayladı:** 30 retraction-candidate kaydı `goldset.json`'a merge EDİLMEDİ, ayrı dosyada kalıyor (§54). Gerekçe: `GoldEntry` şeması `extra="forbid"` + hiçbir metrik şu an bu veriyi okumuyor. **Guardian'ın bulduğu ayrı bir küçük sorun:** bu 30 kaydın `source` alanı `"manual"` — ama şemadaki "manual" tanımı "hakem-raporlu makale" demek, bu kayıtlar öyle değil (programatik türetilmiş). Yanlış etiketleme, düzeltilmesi TODO (düşük öncelik, dosya hiçbir yerde tüketilmiyor).
4. **accept↔major_revision sınırı hâlâ en zayıf nokta** — 14/49 insan-accept makale motor tarafından major_revision sanılıyor (§29 karışıklık matrisi).
5. **In-sample kalibrasyon riski** — goldset büyümeden held-out doğrulamaya geçilemedi.
6. **`--live` eval CLI bayrağı hâlâ `NotImplementedError`** — bu, ÜRÜNÜN kendisini ENGELLEMİYOR (ürün zaten çalışıyor, bu bölümün başındaki demo materyallerine bakın), sadece `run_eval.py --live` komut satırı aracının kendi eksik bir özelliği.
7. **Gemini-2.5-Pro thinking-truncation riski: DÜZELTME UYGULANDI, ama canlı doğrulanamadı (arıza deterministik değil).** Writer/editor artık bu hataya karşı 1x otomatik retry yapıyor (§59, guardian 2 tur onaylı, 857 test PASS). Ama gerçek arıza bu oturumda YENİDEN üretilemediği için "canlı doğrulandı" DENMİYOR — sadece mock-seviyesinde doğrulandı. Yazılım ekibi üretimde bu retry'ın gerçekten yardımcı olup olmadığını (log'larda `"LLM structured-output kesilmesi"` uyarısını arayarak) izlemeli.
8. **DOI-ayıklamayı LLM'e devretme fikri açıkça REDDEDİLDİ** (madde 3, guardian uyarısı) — ama fabrike-DOI/DOI-yok senaryosuyla test edilmedi. İleride bu fikir tekrar gündeme gelirse önce o test yapılmalı.
9. ~~Güzel sanatlar/tasarım araştırmaları çeşitlilik testinde HİÇ temsil edilmiyor~~ — **KAPANDI (§62).** International Journal of Design'dan (CC BY 4.0) gerçek bir ampirik makale bulunup test edildi, çökmeden bitti (`accept`, 7.85). İlginç yan bulgu: motor bu makalenin study_design'ını `unknown` (%20 güven) olarak işaretledi — mevcut taksonomi tasarım araştırmasını net kapsamıyor, ama motor bunu DÜRÜSTÇE belirtti, yanlış kategoriye zorlamadı. Yazılım ekibi için not: `study_design` taksonomisine `design_research` gibi ayrı bir kategori eklemek isteğe bağlı bir gelecek iyileştirmesi olabilir (şu an zorunlu değil, "unknown" davranışı zaten güvenli).

## 6) Kanıt/kaynak haritası

- Tam iş günlüğü: `PDF_PIPELINE_CALISMA_GUNLUGU.md` (§41-62)
- Goldset büyütme araştırması: `goldset_yeni_adaylar.md`
- Kopyalanabilirlik testi: `scratchpad/copyability_test.py` + `copyability_test_results.json`
- Hata senaryoları: `scratchpad/error_scenarios_test.py` + `error_scenarios_results.json`
- Çeşitlilik döngüsü (tekrar kullanılabilir, 10 vaka): `eval/review/continuous_diversity_test.py` → `eval/review/results/continuous_diversity_log.jsonl`
- NUL-byte fix + regresyon testi: `engine/ingestion/pdf_parser.py` (satır ~333-340) + `tests/unit/test_ingestion.py::test_parse_pdf_strips_nul_bytes_from_extracted_text`
- Thinking-truncation retry fix + plan: `docs/plans/LLM_THINKING_TRUNCATION_RETRY_2026-08-14.md` + `api/services/review_orchestration.py` (`_call_with_truncation_retry`)
- MOPRD araştırması (arXiv PDF indirilip okundu, sonuç: erişilemez VE çözüm sağlamazdı): `scratchpad/moprd_arxiv.pdf`
- Retraction-candidate goldset adayları: `eval/review/retraction_moat_candidates_2026-08-13.json`
- Demo materyalleri: `C:\Users\USER\Desktop\Arbitra\`

## 7) Commit durumu

Bu oturumdaki TÜM kod ve dokümantasyon değişiklikleri commit edildi (3 commit, `master` branch'ine):
- `67563c7` — NUL-byte fix + ilk diversity script (7 vaka) + handoff dokümanı
- `c4ccd03` — thinking-truncation retry mekanizması + plan dokümanı
- `57aa0ca` — çeşitlilik testi 10 vakaya genişletme (meta-analiz, mixed-methods, mühendislik) + güncellenmiş `continuous_diversity_log.jsonl` + journal/handoff güncellemeleri
- `ff921fc` — devralma özetindeki eski commit-durumu notunun güncellenmesi
- (bu commit) — çeşitlilik testi 11. vaka: güzel sanatlar/tasarım araştırması (International Journal of Design)
