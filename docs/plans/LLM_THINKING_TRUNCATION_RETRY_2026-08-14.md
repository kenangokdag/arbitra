# Plan: Gemini-2.5-Pro thinking-truncation'ına karşı writer/editor dayanıklılığı

**Tarih:** 2026-08-14
**Durum:** UYGULANDI (guardian 2 tur onayı sonrası) — `api/services/review_orchestration.py` (`_call_with_truncation_retry` helper'ı + `_run_writer`/`_run_editor`/`run_orchestration` güncellemesi), `tests/unit/test_review_orchestration.py` (4 yeni test: writer/editor retry-kurtarma, retry-tükenmesi-regresyon, non-truncation-hatası-retry-tetiklenmiyor). Tam unit suite çalıştırıldı (bkz. journal §59).
**Kaynak:** `PDF_PIPELINE_CALISMA_GUNLUGU.md` §57 (bu oturumda çeşitlilik testinde canlı gözlemlendi).
**Karar verici:** Kenan.

---

## 1. Problem

`review_orchestration.py`'nin writer (`_run_writer`, satır ~243-253) ve editor (`_run_editor`, satır ~354-359) çağrıları `tier="pro"` kullanıyor, `structured_output_schema=_DraftReport` bekliyor, `max_tokens=8000`.

`llm_service.py:99`'daki thinking-kapatma fix'i (`{"thinking": {"type": "disabled", "budget_tokens": 0}}`) **sadece `tier=="flash"` için geçerli** — kod içi yorum (`llm_service.py`) ve `review_orchestration.py:248-250`'nin kendi yorumu bunu doğruluyor: Gemini 2.5 Pro'nun thinking modu Vertex AI üzerinden tamamen kapatılamıyor.

**Somut, bu oturumda gözlemlenen arıza (A-seviye kanıt, `bd53ga21f.output:165-194`):**
```
LLM structured parse failed (model=gemini-pro-tiebreak, schema=_DraftReport, text_len=7294):
  Invalid JSON: EOF while parsing a string at line 67 column 84
```
`deneme.pdf` — bu oturumda daha önce ≥2 kez `verdict=accept` ile SORUNSUZ tamamlanmış aynı dosya — bu koşumda `max_tokens=8000` tavanına çarpıp JSON'ı yarıda kesti. `max_tokens` daha önce (bu proje tarihinde) 4000→8000'e çıkarılmıştı (kod yorumu: "text_len=6050 kesilmiş çıktı" ampirik gözlemiyle) — o düzeltme bu spesifik olayı ÖNLEMEDİ, sadece frekansını azalttı.

**Sınıf:** Deterministik değil — aynı girdi bazen geçiyor bazen geçmiyor (thinking-token tüketimi çağrıdan çağrıya değişken). n=1 bu oturumda gözlemlendi; gerçek frekans (%kaç çağrıda oluyor) ÖLÇÜLMEDİ — bu planın açık sınırlaması.

## 2. Neden bu bir üretim riski (sadece "nadiren oluyor" değil)

- Kullanıcıya görünen sonuç: iş `failed` statüsüyle biter, kullanıcı elle tekrar yüklemek zorunda kalır — sessiz bir veri kaybı değil ama **kötü kullanıcı deneyimi**, özellikle demo/pilot aşamasında güven kırıcı.
- Aynı dosyanın "bazen accept bazen failed" vermesi dışarıdan bakıldığında güvenilirlik zayıflığı gibi görünür — teknik nedeni (Gemini Pro thinking limiti) kullanıcı bilmiyor.

## 3. Seçenek A: `max_tokens`'ı tekrar artırmak (örn. 8000→12000)

**Lehte:**
- Tek satırlık değişiklik, aynı desenin (4000→8000) devamı.
- Bu oturumdaki arızada `text_len=7294` (8000'e YAKIN ama tam dolmamış) — yani biraz daha alan bu SPESİFİK vakayı önleyebilirdi (spekülasyon değil, gözlemlenen veriyle tutarlı bir çıkarım, ama garanti değil).

**Aleyhte:**
- **Kök nedeni ÇÖZMÜYOR, sadece tavanı ittiriyor** — thinking-token tüketimi ÖLÇÜLEMİYOR/kontrol edilemiyor (bkz §5), yani "yeterince büyük" bir sayı YOK, sadece "şimdilik yeterli görünen" bir sayı var. 4000→8000 emsali bunu zaten kanıtladı: geçici rahatlama, kalıcı çözüm değil.
- **Her çağrıda maliyet artışı** — `max_tokens` artışı sadece arızalı çağrılarda değil, TÜM writer+editor çağrılarında (yani her review'da en az 2 kez) potansiyel token bütçesini büyütüyor. Gerçek ek maliyet, thinking'in ne kadar token tükettiğine bağlı (ölçülmüyor, bkz §5) — ama yönü kesin: yukarı.
- Ömer'in bilinen maliyet hassasiyeti (CLAUDE.md proje bağlamı: "Ömer'in tercihi: maliyet nedeniyle Fable yerine Sonnet 4.6") göz önüne alınırsa, kör bir tavan artışı disiplinsiz olur.

## 4. Seçenek B: Bu spesifik hataya karşı sınırlı (1x) otomatik retry

**Mekanizma:** `_run_writer`/`_run_editor` içinde `LLMServiceError` (özellikle `"structured_output parse failed"` alt-string'i ya da ayrı bir exception alt-sınıfı ile ayırt edilerek — bkz §6 açık soru) yakalanırsa, AYNI parametrelerle 1 kez daha dene. 2. deneme de başarısız olursa mevcut davranış (yükselt → `status=failed`) korunur.

**Lehte:**
- **Maliyet SADECE arızalı çağrılarda artıyor** — başarılı çağrıların ezici çoğunluğu (bu oturumda 6/7 diversity-test vakası, retraction-candidate testlerinde 11/11) hiç ek maliyet görmüyor.
- Arızanın DOĞASINA (deterministik değil, çağrıdan çağrıya değişken thinking-tüketimi) doğrudan uyuyor — retry'da aynı girdiyle FARKLI bir thinking-tüketimi olması makul bir bahis (kanıtlanmış değil ama olayın kendi doğasından çıkan mantıklı beklenti).
- Emsali var: `api/utils/resilience.py`'deki `call_resilient()` zaten OpenAlex çağrılarında retry mantığı kullanıyor (`openalex_polite.py:169-174`, `retry_on=(httpx.HTTPError,)`) — bu, "geçici/olası-geçici hatada bir kez daha dene" AYNI desenin LLM katmanına taşınması, yeni bir mimari fikir değil.

**Aleyhte:**
- Arıza gerçekten YAPISAL ise (örn. belirli bir manuscript'in evidence pack'i her zaman thinking'i taşırıyor), retry de başarısız olur → kullanıcı 2 kat bekler (writer/editor adımı ~9dk, retry ile ~18dk'ya çıkabilir) sonra yine `failed` görür. **Bu senaryo bu oturumda TEST EDİLMEDİ** — n=1 örneklemden "retry genelde kurtarır" mı yoksa "bazı girdilerde retry de boşuna" mı olduğu bilinmiyor.
- Editor'ın retry'ı, writer taslağını YENİDEN üretmeden aynı taslak üzerinden mi çalışacak yoksa writer'dan mı başlayacak — kapsam netleştirilmeli (bkz §6).

## 5. Açık/ölçülmeyen şey (dürüstçe)

`litellm`'in `Usage` şeması `completion_tokens_details` alanı taşıyor (bu oturumda doğrulandı: `litellm.types.utils.Usage.model_fields` içinde var) — bu alan genelde `reasoning_tokens` gibi bir alt-kırılım içerir (modele göre değişir, Vertex/Gemini için bu oturumda DOĞRULANMADI, sadece şemanın VARLIĞI doğrulandı). Şu an `llm_service.py:137-138` sadece `tokens_in`/`tokens_out` (`prompt_tokens`/`completion_tokens`) kaydediyor, thinking-token kırılımını LOGLAMIYOR. Bu yüzden "thinking normalde ne kadar tüketiyor, 8000'in ne kadarını yiyor" sorusuna VERİ YOK — hem Seçenek A'nın (ne kadar artırmalı) hem Seçenek B'nin (retry gerçekten yardımcı oluyor mu) değerlendirmesi bu gözlemsellik boşluğuyla sınırlı.

## 6. Önerilen yön (guardian onayına sunulacak, kod YAZILMADI)

**Öneri: Seçenek B (sınırlı 1x retry), Seçenek A DEĞİL.** Gerekçe: maliyet-orantılı (sadece arızada öder), arızanın deterministik-olmayan doğasına uyuyor, mevcut `call_resilient()` deseniyle mimari tutarlılık. Seçenek A'nın "belki yardımcı olur" argümanı zayıf (4000→8000 emsali zaten göstermişti ki tavan artışı KALICI çözüm değil).

**Kapsam (netleştirilmesi gereken, guardian'a sorulacak):**
1. Retry SADECE writer/editor'ın `_DraftReport` structured-output parse hatasında mı, yoksa `LLMServiceError`'ın TÜM alt-türlerinde mi (network hatası dahil)? Öneri: SADECE bu spesifik hata sınıfı (parse-truncation) — network hatalarında retry'ın FAYDASI daha belirsiz, kapsam büyütmeden dar başlansın.
2. Editor retry'ı writer'ın taslağını mı tekrar kullanacak (muhtemelen evet — writer başarılıysa taslak elde, sadece editor'ın kendi çağrısı tekrarlanır) yoksa tüm zinciri mi baştan başlatacak? Öneri: sadece başarısız olan adımı (writer YA DA editor) tekrar dene, diğerini tekrar ÇALIŞTIRMA (gereksiz maliyet).
3. Gözlemsellik: retry tetiklendiğinde `degraded_features`'a görünür bir not düşülmeli mi (§41'in "sessiz degradasyon yok" disiplini)? Öneri: EVET — `"llm_retry:{writer|editor}_structured_output_truncated"` gibi bir işaret, kullanıcıya/loglara görünür kalsın.
4. **Bu planın kapsamı DIŞI (ayrı, isteğe bağlı takip):** `completion_tokens_details`'ı loglamak (§5'in boşluğu) — gözlemsellik iyileştirmesi, bu fix'in önkoşulu DEĞİL.

### 6a. GÜNCELLEME (guardian 1. tur bulgusu) — 2 gerçek plumbing boşluğu netleştirildi

**Guardian'ın bulduğu 1. hata — `call_resilient` emsali YANLIŞ/tutarsız:** Plan'ın "mimari tutarlılık" gerekçesi `call_resilient()`'ı (`api/utils/resilience.py`) emsal gösteriyordu, ama bu fonksiyon `attempts=cfg.RETRY_ATTEMPTS` (varsayılan **3**, `api/config.py:50`) kullanıyor — "1x retry" (toplam 2 deneme) değil. Ayrıca ZORUNLU bir `timeout` parametresi alıp her denemeyi `asyncio.wait_for` ile sarmalıyor (`resilience.py:109,117`) — pro-tier LLM çağrılarında (grep ile doğrulandı) ŞU AN HİÇ timeout yok, bunu eklemek YENİ bir hata modu (timeout-abort) getirir, plan'da hiç tartışılmamıştı.

**Karar (netleşti): `call_resilient` KULLANILMAYACAK. El-yapımı, bağımsız 1x retry.** Gerekçe: bu ihtiyaç dar ve spesifik (tek bir hata sınıfında, tam olarak 1 kez tekrar) — `call_resilient`'ın genel-amaçlı 3-deneme+timeout mimarisini buraya zorlamak hem maliyeti öngörülemez artırır hem de var olan (şu an timeout'suz, bilinçli öyle olan) pro-tier çağrı davranışına dokunan, bu fix'in kapsamı dışında ayrı bir riskli değişiklik ekler. Uygulama: `_run_writer`/`_run_editor` içinde `call(...)` çağrısı `try/except LLMServiceError` ile sarılır; hata mesajı `"structured_output parse failed"` içeriyorsa AYNI parametrelerle **tam olarak 1 kez** tekrar `call(...)` çağrılır (döngü değil, düz bir 2. çağrı) — 2. deneme de başarısız olursa mevcut `raise` davranışı korunur. `call_resilient`/timeout ekosistemine HİÇ dokunulmaz.

**Guardian'ın bulduğu 2. hata — `degraded_features` önerisi mimariyle uyuşmuyor:** `EvidencePack.degraded_features` (`api/models/review.py:247`) `review_service.py:492/535`'te — yani `run_orchestration()` (çağrı satır 599) çalışmadan ÖNCE — zaten DB'ye yazılmış oluyor. `run_orchestration()` bir `EvidencePack` değil `ReviewReport` döndürüyor, ve `ReviewReport` modelinde `degraded_features` alanı YOK. Var olan tek emsal (critic düşmesi notu, `review_orchestration.py:438-446`) yapılandırılmış bir listeye değil, `overall_assessment` prose'una SERBEST METİN olarak ekleniyor.

**Karar (netleşti): retry tetiklenirse `degraded_features`'a DEĞİL, mevcut critic-düşmesi emsaliyle AYNI mekanizmaya (overall_assessment'a kısa bir not) eklenecek.** Yeni bir Pydantic alanı EKLENMEYECEK (kapsam büyütme, ayrı bir şema-değişikliği kararı gerektirir). Ayrıca `logger.warning(...)` ile sunucu logunda KOŞULSUZ görünür olacak (bu, kullanıcı-yüzü rapor şemasına dokunmadan gözlemselliği sağlıyor, ucuz ve düşük riskli).

**Guardian 2. tur (dürüstlük notu, blocker değil):** Worst-case maliyet §4'te tam yazılmamıştı — HEM writer HEM editor aynı review'da parse-fail olursa retry ile toplam **4 pro-tier çağrısına** çıkabilir (normal 2 yerine, 2x değil 4x). Bu hâlâ Seçenek A'nın (her review'da kalıcı, garantili ek maliyet) altında kalıyor çünkü sadece arıza anında oluşuyor — ama rapor/kullanıcıya "en kötü ihtimalde 4x" diye net yazılmalı, "sadece arızalı çağrıda" ifadesi tek başına yeterince açık değildi.

**GUARDIAN ONAYI (2026-08-14, 2. tur): İtiraz kalmadı, kod yazma aşamasına geçilebilir.**

## 7. Test planı (kod onaylanırsa)

- Unit: `_run_writer`/`_run_editor`'ı mock'layarak İLK çağrı `LLMServiceError` fırlatsın, İKİNCİ çağrı başarılı `_DraftReport` dönsün — sonucun başarılı olduğunu doğrula.
- Unit: HER İKİ çağrı da başarısız olursa (retry de tükenirse) mevcut `status=failed` davranışının KORUNDUĞUNU doğrula (regresyon yok).
- Bu oturumda `deneme.pdf` arızası YENİDEN üretilemez (deterministik değil) — bu yüzden "gerçek arızada retry kurtarıyor mu" sorusu ampirik olarak YENİDEN test EDİLEMEZ, sadece mock-seviyesinde doğrulanabilir. Bu dürüstçe belirtilmeli, "canlı doğrulandı" denmeyecek.

---

**Sıradaki adım:** Bu plan guardian'a (`arbitra-moat-guardian`) danışılacak — moat/engine mimarisine dokunmuyor gibi görünse de (LLM çağrı-katmanı, skorlama mantığı değil) CLAUDE.md'nin "her önemli mimari/engine değişikliği" kuralı ihtiyatlı yorumlanıp danışılacak. Guardian onayı/itirazı sonrası, netleşen kapsamla kod yazılacak.
