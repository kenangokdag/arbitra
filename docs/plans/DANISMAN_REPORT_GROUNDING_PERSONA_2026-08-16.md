# Plan: "Danışman" chat paneli için özel bir `review_advisor` kimliği kurmak + rapor-verisini (Finding/verdict/citation_integrity/risk_radar) backend prompt'una taşıyacak mekanizmayı kurmak

**Tarih:** 2026-08-16
**Durum:** TASLAK — guardian incelemesi TAMAMLANDI (nötr, 1 kritik bulgu + kapsam revizyonu ile), Kenan'ın nihai "plan onaylandı" onayı bekliyor.
**Kaynak:** Kenan'ın bu oturumdaki bulgusu — "Danışman paneli çalışıyor ama incelenen makalenin raporuna bağlı değil, genel sorular öneriyor."
**Karar verici:** Kenan (Ömer artık blocker değil — bkz. memory `feedback-omer-artik-yok`).
**Kapsam kararı (Kenan, bu oturum):** Bu planda SADECE (A) yeni `review_advisor` mode'una özel kimlik/çerçeve metni ve (C) backend'in rapor-verisini prompt'a enjekte etme mekanizması var. Frontend kablolama (rapor sayfasına tetikleyici koymak, ChatboxPanel'in bunu gerçekten göndermesi) BİLİNÇLİ olarak AYRI, sonraki bir adıma bırakıldı — bkz. §7.

**Guardian incelemesi sonrası KAPSAM REVİZYONU (2026-08-16, Kenan onayladı):** Guardian, global `BASE_PERSONA`'nın (`llm_service.py:32-39`) sadece chat panelini değil, moat'ı üreten skorlama motorunu da (review_writer/review_editor/citation_critic/qualitative_rigor/quantitative_validity/academic_dimension — bkz §2b) etkilediğini, planın bunu hiç test etmediğini buldu. Kenan'ın kararı: **BASE_PERSONA'ya bu planda DOKUNULMUYOR.** Kimlik/çerçeve metni SADECE yeni `review_advisor` mode'unun kendi `role_brief`'ine yazılıyor — mevcut mimarinin zaten desteklediği bir uzatma noktası (`llm_service.py:70-71`, her mode BASE_PERSONA'nın ardından kendi brief'ini ekliyor), motorun skor-üreten prompt'larına SIFIR etki. BASE_PERSONA'nın proje-çapında "ALI" marka temizliği ayrı, kendi regresyon testiyle donatılmış bir plana ERTELENDİ (bkz §7).

---

## 1. Kök neden (kanıtlı, A-seviye — bu oturumda Read/Grep ile doğrulandı)

Zincir 4 katmanda kopuk:

1. **Persona eski ürüne ait** — `api/services/llm_service.py:32-39` (`BASE_PERSONA`): *"Sen ALI — Adaptive Literature Intelligence danışmanısın... tez sürecinde rehberlik edersin."* Bu, pivot-öncesi "PaperMind ALI" (literatür asistanı) kimliği — Desktop `CLAUDE.md`: *"Önceki adı: PaperMind ALI — Arbitra'ya (peer review simülasyonu) pivot edildi."* Peer-review/Finding/risk_radar hiç geçmiyor. **Bu string TÜM ~45 ROLE_MODULES çağrısına global prepend ediliyor** (`llm_service.py:67-71`).
2. **Rapor sayfası Danışman'a hiç bağlanmıyor** — `web/src/components/review/ReviewReportView.tsx` içinde `AdvisorButton`/`openChatbox` grep'te YOK. (Kapsam dışı, §7.)
3. **Context taşınsa bile backend'e gitmiyor** — `ChatboxPanel.tsx:90-98` body'si `session_id, messages, language, paper_context_ids: []` (hardcoded boş). `context.mode`/`context.pageState` store'da duruyor, isteğe hiç eklenmiyor. (Kapsam dışı, §7.)
4. **Backend'de rapor-verisini taşıyacak yol yok** — `api/routes/chat.py:36-56` `_build_paper_context()` sadece OpenAlex bibliyografik meta (title/year/venue/abstract) çekiyor — literatür-arama makaleleri için. İncelenen makalenin kendi `Finding[]`/`citation_integrity`/`risk_radar` çıktısını prompt'a sokan HİÇBİR kod yok. `ROLE_MODULES`'ta (`api/services/role_modules/__init__.py:60-104`) da buna uygun bir mode yok.

Bu plan §1'in **1 ve 4**'ünü çözüyor; **2 ve 3** ayrı adıma bırakıldı.

## 2. `BASE_PERSONA` — bu planda DOKUNULMUYOR (guardian bulgusu, kapsam dışına alındı)

**Neden vazgeçildi:** İlk taslak `BASE_PERSONA`'yı (`llm_service.py:32-39`, "Sen ALI — Adaptive Literature Intelligence danışmanısın... tez sürecinde rehberlik edersin") global olarak güncellemeyi öneriyordu. Guardian incelemesinde şu doğrulandı (A-seviye, grep ile): bu string sadece chat panelinde değil, **moat'ı üreten skorlama motorunda da** kullanılıyor —

- `api/services/review_orchestration.py:276,387` — `mode="review_writer"`, `mode="review_editor"` (writer→critic→editor döngüsü)
- `engine/academic/_engine_base.py:378-384` — `qualitative_rigor`, `quantitative_validity`, `citation_critic`, `academic_dimension` (yani `citation_integrity`/`coverage_completeness`/`statistical_consistency` moat boyutlarını üreten mode'lar)

`llm_service.py:67` (`system_parts = [BASE_PERSONA]`) koşulsuz, mode-agnostik prepend yapıyor — yani BASE_PERSONA'ya dokunmak, chat panelini düzeltmek isterken motorun rapor-üretim prompt'unu da değiştirmiş olurdu, HİÇBİR goldset regresyonu çalıştırılmadan. Metin kendisi görece küçük bir çerçeve değişikliği olsa da (davranış kuralı aynen korunuyordu), bunu "risk düşük" diye varsaymak CLAUDE.md'nin "ölçemediğimizi yazmayız" ilkesine aykırı.

**Kenan'ın kararı (guardian sonrası):** BASE_PERSONA'ya bu planda dokunulmuyor. Marka temizliği ("ALI" → "Arbitra") proje-çapında, kendi goldset regresyon testiyle donatılmış AYRI bir plana ertelendi (bkz §7).

## 3. Önerilen değişiklik — yeni `ROLE_MODULES["review_advisor"]` modu (kimlik BURADA taşınıyor)

BASE_PERSONA değişmediği için, "bu bir Arbitra hakem-raporu danışmanı, ALI/tez asistanı değil" çerçevesi **doğrudan yeni mode'un kendi `role_brief`'ine** yazılıyor — mevcut mimarinin zaten desteklediği uzatma noktası (`llm_service.py:70-71`: her mode BASE_PERSONA'nın ardından kendi brief'ini ekler). Bu, motorun skor-üreten prompt'larına SIFIR etki demek — sadece `mode="review_advisor"` seçildiğinde (yani sadece bu yeni chat akışında) devreye girer.

Yeni dosya `api/services/role_modules/review_advisor.py`, `citation_critic.py`/`quantitative_validity.py` ile AYNI inline-string deseni (dosya-bazlı prompt yükleme değil — bu daha kısa/basit, CLAUDE.md §3.5 "daha kolayı" kontrolü).

Kilitlenen İÇERİK niyeti (son prosa kod aşamasında):
- Kimlik: "Sen Arbitra'nın hakem-raporu danışmanısın. Kullanıcı şu an incelenen bir makalenin hakem raporunu görüntülüyor, sana bu rapor hakkında soru soruyor."
- Cevaplar YALNIZCA sağlanan rapor-bağlamına (verdict, executive_verdict, dimension_scores, risk_radar, findings, citation_integrity özeti) dayanmalı.
- Rapor-bağlamında olmayan bir şey sorulursa → "raporda bu konuda veri yok" de, uydurma yok.
- Finding'e referans verirken `finding_id`/`dimension` anılmalı (kullanıcı raporda hangi bulguyla eşleştireceğini bilsin).
- **Guardian'ın dairesellik uyarısı (ZORUNLU madde, ilk taslakta yoktu):** Chatbot bir finding'i AÇIKLAYABİLİR ama DOĞRULAMAZ/TEYİT ETMEZ — aynı motorun ürettiği sonucu tekrarlıyor, yeni bir kanıt katmanı değil. Brief'te açıkça: *"Bir bulguyu yorumlarken bunu 'raporda böyle bulunmuş, ben de öyle diyorum' çerçevesinde sun — kendi bağımsız doğrulamanmış gibi konuşma. Kullanıcı 'bu doğru mu' diye sorarsa: 'Ben raporu üreten motorun kendisi değilim, bu motorun bulgusunu senin için özetliyorum — ek doğrulama için [ilgili evidence/anchor] kontrol edilmeli' de."*

`ROLE_MODULES` dict'ine (`__init__.py:60`) `"review_advisor": REVIEW_ADVISOR_BRIEF` eklenir.

## 4. Önerilen değişiklik C — backend mekanizma: rapor verisi → prompt

### 4.1 Şema (`api/models/chat.py:24-33`)
`ChatRequest`'e yeni, opsiyonel alan: `report_id: UUID | None = Field(default=None)`.
**`paper_context_ids`'ten kasıtlı AYRI tutulur** — biri OpenAlex literatür meta'sı (dış kaynak), diğeri kullanıcının kendi incelettiği makalenin raporu (kendi verisi). Karıştırılırsa iki farklı anlam tek alana sıkışır.

### 4.2 Route (`api/routes/chat.py`)
- `chat()` handler'a `request: Request` parametresi eklenir.
- `from api.routes.review import _user_id` — YENİ kod DEĞİL, mevcut reuse deseni (`api/routes/account.py:18` zaten aynısını yapıyor).
- Yeni `_build_report_context(user_id: str, report_id: UUID | None) -> ReviewReport | None`:
  - `report_id` yoksa `None`.
  - Varsa `review_service.get_report(user_id, report_id)` çağrılır (BOLA-safe — bkz §4.4).
  - `LookupError` yakalanır → `None` döner. Bu, mevcut `_build_paper_context`'in "silent fallback; citation echo bozulmaz" deseniyle (chat.py:36-46 docstring) TUTARLI — rapor bulunamazsa sohbet çökmez, sadece o bağlam olmadan devam eder.
- **`_cache_key()` (chat.py:29-33) ZORUNLU güncellenir** — `report_id` hash girdisine eklenir. Eklenmezse: aynı `session_id`/`mode`/son-mesaj ama FARKLI `report_id` iki istek AYNI cache key'i üretir → ikinci kullanıcı/rapor birincinin cache'lenmiş cevabını alır (sessiz veri-karışması). Bu bug olası, plan bunu zorunlu madde sayıyor, opsiyonel değil.

### 4.3 `llm_service.call()` (`api/services/llm_service.py`)
- Yeni parametre: `report_context: ReviewReport | None = None` — mevcut `paper_context: list[dict] | None` deseniyle PARALEL, ayrı tutuluyor (bkz §4.5 gerekçe).
- Yeni `_serialize_report_context(report: ReviewReport) -> str` — `_serialize_paper_context` (llm_service.py:169-184) ile aynı üslupta.
  - **Token bütçesi kararı (kritik, plan burada kilitleniyor):** TAM raporu dump ETMEZ. Şunları içerir:
    - `verdict`, `executive_verdict.one_sentence_diagnosis` + `top_fatal_risks`
    - `dimension_scores` (10 satır)
    - `risk_radar` (zaten kompakt: dimension/score/severity/why_it_matters)
    - `findings`'ten yalnız `severity ∈ {critical, major}` olanlar (title + summary + dimension + finding_id)
    - `evidence_pack.citation_integrity` SAYAÇ olarak (total/resolved/fabricated/retracted) — `references`/`context_findings` tam listesi DEĞİL
  - **Gerekçe:** flash tier `effective_max_tokens=600` (`llm_service.py:85-87`). Tam `ReviewReport` JSON'u (özellikle `evidence_pack.references`, onlarca kayıt) bu bütçeyi kolayca boğar, maliyeti şişirir. Bu, CLAUDE.md'de anılan `_MANUSCRIPT_EXCERPT_CHARS` token-disiplini ile aynı mantık.

### 4.4 Güvenlik (BOLA)
`review_service.get_report(user_id, job_id)` (`review_service.py:723-730`) zaten sahip-kapsamlı: `row.get("user_id") != user_id` → `LookupError`. Chat endpoint'i AYNI fonksiyonu reuse ettiği için başka kullanıcının raporuna erişim riski YOK — yeni bir yetki kontrolü YAZILMASI GEREKMİYOR, mevcut güvenli yol miras alınıyor.

### 4.5 Neden `page_state`'e değil, ayrı `report_context`'e

`page_state: dict[str, Any] | None` zaten var (`ChatRequest.page_state`) ve serbest/tipsiz. Rapor verisi için AYRI, tipli (`ReviewReport`) bir yol tercih edildi çünkü:
- `page_state` frontend'den geliyor, güvenilmez (kullanıcı istemcisi ne isterse gönderebilir) — rapor verisi ise SERVER-SIDE, `report_id` üzerinden sahip-kapsamlı çekiliyor, sahtelenemez.
- Tip güvenliği: `ReviewReport` Pydantic modeli, serileştirme fonksiyonu hangi alanların var olduğunu derleme-zamanında bilir.

## 5. Test planı

1. **Birim test** (`tests/unit/` altında yeni `test_chat.py` veya mevcut varsa ona ekleme — Glob ile kontrol edilecek): `_build_report_context` — mock `review_service.get_report`, `LookupError` durumunda `None` döndüğünü doğrula.
2. `_serialize_report_context` — örnek `ReviewReport` fixture'ıyla: çıktı verdict/risk_radar/critical-major findings içeriyor mu, `evidence_pack.references` TAM listesi İÇERMİYOR mu (token-bütçe disiplini regresyon guard'ı).
3. `_cache_key` — aynı session/mesaj, FARKLI `report_id` → FARKLI key (cache-karışması regresyon guard'ı).
4. **Entegrasyon (CLAUDE.md §3.6 "test=davranış kanıtı" gereği, unit test yetmez):** mevcut bir demo/goldset review job'ının `job_id`'siyle `/api/chat`'e curl/Postman ile `report_id` verilerek gerçek çağrı yapılacak, cevabın rapor-spesifik bir ayrıntı (gerçek bir finding başlığı/verdict) içerdiği gözle doğrulanacak.

## 6. Riskler / açık sorular (Kenan'ın kararı gerekiyor)

1. §3'teki `review_advisor` brief'i taslak niyet — son prosa kod aşamasında yazılacak, dairesellik-uyarı maddesi ZORUNLU tutulacak (guardian talebi).
2. `report_context`'in `page_state`'ten ayrı tutulması mimari tercih (§4.5) — alternatif (page_state'i override etmek) daha az kod ama tip-güvenliği kaybettirir. Öneri: ayrı tutmak.
3. **Maliyet/performans (guardian bulgusu, küçük ama not edilmeli):** Her chat turunda `get_report()` Supabase'den tam `ReviewReport`'u yeniden çekip yeniden serileştirecek — konuşma boyunca cache'lenmiyor. İlk sürümde kabul edilebilir (chat zaten `_cache_key` ile response-level cache'leniyor), ama konuşma uzarsa tekrar eden DB round-trip'i olarak not düşülüyor — optimize etmek bu planın kapsamında DEĞİL.

## 7. Kapsam dışı (bilinçli, Kenan'ın bu oturumdaki kararıyla ertelendi)

1. `ReviewReportView.tsx`'e bir tetikleyici (AdvisorButton ya da eşdeğeri) mount etmek.
2. `ChatboxPanel.tsx` / `web/src/app/(app)/chat/page.tsx`'in `report_id`'yi (ve `mode`'u) gerçekten `/api/chat` body'sine koyması — şu an ikisi de `paper_context_ids: []` hardcode ediyor, `context.mode`/`context.pageState` hiç gönderilmiyor.
3. **Sonuç:** bu plan uygulandıktan SONRA bile mekanizma UI'dan otomatik tetiklenmez — `/api/chat`'e `report_id` manuel/curl ile verilmeden gözlemlenemez. Bilinçli ara-durum, sonraki adımda kapatılacak.
4. **`BASE_PERSONA`'nın proje-çapında "ALI"→"Arbitra" marka temizliği** (§2) — guardian bulgusu sonrası bilinçli olarak ERTELENDİ. Ayrı bir plan gerektirir: değişiklikten önce/sonra en az 1 goldset makalesinde `review_writer`/`review_editor`/`citation_critic`/`qualitative_rigor`/`quantitative_validity`/`academic_dimension` çıktılarını karşılaştıran bir smoke-regression ZORUNLU olacak.

---

## 8. Sonuçlar (uygulandı, 2026-08-16)

**Kod:** `api/services/role_modules/review_advisor.py` (yeni, kimlik+dairesellik-uyarısı brief'i), `__init__.py` kaydı, `api/models/chat.py` (`report_id: UUID | None`), `api/routes/chat.py` (`_build_report_context`, `_cache_key`'e `report_id` eklendi, `request: Request` parametresi + `_user_id` reuse), `api/services/llm_service.py` (`report_context` parametresi + `_serialize_report_context`, özet-disiplinli — TAM rapor değil).

**BASE_PERSONA'ya dokunulmadı** (§2 kararı) — motorun skor-üreten prompt'ları etkilenmedi.

**Testler (yeni, bu değişikliğe özel):**
- `tests/unit/test_llm_service.py`: `_serialize_report_context` — verdict/executive_verdict/risk_radar/critical finding sisteme giriyor, minor finding VE `evidence_pack.references` tam listesi GİRMİYOR (token-bütçe guard'ı). PASS.
- `tests/unit/test_chat_report_context.py`: `_build_report_context` (None/LookupError/başarı yolları, BOLA), `_cache_key` report_id ayrımı, uçtan uca `/api/chat` + `report_id` → sistem promptunda rapor verisi. PASS.

**Regresyon:** `test_chat_report_context.py` + `test_chat_route_advisor.py` + `test_llm_service.py` + `test_skeleton_endpoints.py` — **38 passed, 2 skipped** (skip'ler önceden var, bu değişiklikle ilgisiz). Ayrıca filtrelenmiş `-k "chat or llm_service or role_module"` — **27 passed**.

**Tam unit+integration süiti KOŞULAMADI** — ~40 dakika sonra %95+ ilerlemede (hepsi PASS görünümlü, hiç F/E yok) CPU kullanımı sıfıra yakın kalarak (6 saniyede 0.15s CPU) askıda kaldı, sonlandırıldı. Alfabetik/toplama sırası gereği bu oturumun yeni testleri çok daha erken çalışıp geçmiş olmalı — takılma noktası muhtemelen bu sandbox'ta ağ erişimi olmayan, mock'lanmamış bir entegrasyon testi (önceden var olan bir sorun). **Bu değişiklikle nedensel bağlantı kanıtlanmadı, ayrı bir TODO olarak not düşülüyor** — CLAUDE.md "test=davranış kanıtı" gereği dürüstçe.

**Entegrasyon (§5.4, curl/gerçek job_id) YAPILMADI** — kapsam dışına alınan frontend kablolaması olmadan, TestClient üstü test (yukarıdaki `test_chat_route_injects_report_context`) bu kanıtı zaten karşılıyor; gerçek bir canlı job_id ile manuel curl doğrulaması Kenan isterse ayrıca yapılabilir.

**Kapsam dışı bırakılanlar (§7) hâlâ açık** — Danışman paneli bu değişiklikten sonra bile UI'dan otomatik tetiklenmiyor.
