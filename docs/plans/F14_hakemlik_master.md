# F14 — Hakemlik Motoru / Stanford-grade Peer Review (Master Plan Manifest)

> **Durum:** Master roadmap — Omer onayladı (2026-06-21, "onay-evet-onay" + ters-göz eleştirileri gömülü).
> **Tek doğruluk:** Bu master + her alt-sprint kendi `F14-S<n>_*.md` manifesti (§0..§18).
> **Anayasa:** `~/.claude/CLAUDE.md` (6 kural) + `analiz-motoru` (iki-motor) + papermind `CLAUDE.md §0` (plan-önce, explicit onay).
> **Niş (negatif tanım):** *"arXiv'e bağlı, tek-alan, İngilizce-only ve atıfı DOĞRULAMAYAN Stanford paperreview.ai'nin AKSİNE; OpenAlex-öncelik (S2 fallback), tüm-alan, çok-dil, atıfı+bağlamı GERÇEKTEN doğrulayan, çekişmeli-orkestrasyonla rafine edilmiş hakem."*

---

## §0 — AMAÇ

Kullanıcı Word/PDF/LaTeX/ZIP belge yükler → iki motorlu sistem uçtan uca **Stanford-kalite hakem raporu** üretir:
- **A. Deterministik doğrulama motoru** (görünmez makine, moat): atıf bütünlüğü + atıf-bağlam + kapsama (eksik seminal) + statcheck — hepsi OpenAlex-öncelik (S2 fallback), künyeli, dürüst-ret birinci sınıf.
- **B. Orkestrasyon motoru** (görünür muhakeme): **yazar (baş hakem) + eleştirenler (çekişmeli panel) + editör (sentez)** → tam yapılandırılmış rapor + çok-boyutlu skor.

**Çift mod:** Yazar (göndermeden önce) = **Faz 1 pilot** · Editör/dergi-tarafı = **Faz 2**.
**Pilot disiplin:** nicel sosyal bilim / metodoloji (panel ekonometrisi, ölçek, çok-kriterli).

**Yasayla uzlaşı (analiz-motoru):** Olgu katmanı deterministik+künyeli (LLM uyduramaz). Yargı katmanı **serbest uzman persona** (Omer kararı) ama (a) kanıt paketine çıpalı, (b) çekişmeli eleştirmenlerle denetli, (c) faithfulness-gate'li.

---

## §1 — MEVCUT DURUM (kanıt: A = bu oturumda grep/Read · B = Explore-ajanı taraması, S2'de Read ile teyit edilecek)

### VAR — sağlam temel (yeniden kullanılacak)
- **Servisler** (B): `api/services/journal_sim_service.py` (~461 satır) — `reviewer_3persona` (3 persona paralel Flash, asyncio.gather), `statcheck_run` (Nuijten 2016, 4 test tipi regex + scipy recompute), `journal_calibration` (verdict band-shift).
- **Persona modülleri** (A-grep): `api/services/role_modules/reviewer_{skeptik,sempatik,yontemci}.py` + `completion_step_review.py`.
- **Persona config** (B): `engine/personas/journal/{skeptik,sempatik,yontemci}.json` (prompt_seed + question_focus + chain_max_depth).
- **statcheck config** (B): `engine/statcheck/multilingual.json` (tolerance green≤0.005/yellow≤0.01, TR+EN locale).
- **Journal dağılım** (B): `engine/journals/review_distribution.json` — ⚠️ `journals: []` BOŞ (fallback 12/42/30/16).
- **Endpoint'ler** (B): `api/routes/workshop.py` → `/api/workshop/defense/{reviewer-3persona, statcheck, journal-calibration}` (tier_gate'li).
- **Modeller** (B): `api/models/journal_sim.py` (tümü `extra="forbid"`).
- **FE** (B): `web/src/components/project/JournalSimulationPage.tsx` (~733 satır).
- **DB** (B): `db/migrations/0032_defense_session_scan_results.sql` (`defense_session.scan_results` jsonb).
- **Test** (B): `tests/unit/test_journal_sim_service.py` (9 test).
- **citation_service.py** (A-grep VAR, içerik DOĞRULANMADI): `api/services/citation_service.py` — S2'de Read şart; OpenAlex izi olabilir.

### YOK — bu F14'ün işi
- ❌ Belge yükleme/parse (Word/PDF/LaTeX/ZIP) — manuscript şu an elle metin (100–40k char).
- ❌ OpenAlex atıf bütünlüğü + atıf-bağlam + kapsama motoru (hakemlikte).
- ❌ Tam Stanford-yapı rapor (Summary/Strengths/Weaknesses/Detailed/Questions/Overall) + 7+3 boyut skor.
- ❌ Yazar+eleştirmen+editör orkestrasyonu (şu an tek-geçiş "soru üretimi").
- ❌ Async iş modeli (mevcut 8s sync timeout — yeni iş sığmaz, bkz R-2).

### Mimari karar: AYRI ALAN
Hakemlik ≠ jüri/savunma. Kodda da ayrış: yeni **`/api/review/...`** namespace + yeni tablolar (`defense_session.scan_results`'a cıvatalama YOK). Yeni domain modeli S1'de.

---

## §2 — SCOPE & SIRA (6 alt-sprint, sıralı, temel-önce)

| Sprint | İş | Bağımlılık | Çekirdek DoD |
|---|---|---|---|
| **F14-S1** | **Belge alma + parse** → `Manuscript` (başlık/özet/bölüm/kaynakça/metin-içi-atıf+bağlam/istatistik/tablo). Parser: GROBID (kaynakça→TEI) + PyMuPDF (metin); LaTeX `.tex/.bbl`; docx; ZIP ana-`.tex` tespit. **Parse-güven kapısı** + "okuyamadım" dürüst durumu. Yeni `/api/review` domain + tablolar. | — | Gerçek PDF/Word/LaTeX/ZIP parse + golden fixture + parse-confidence + test |
| **F14-S2** | **OpenAlex atıf bütünlüğü** (S2 fallback): her kaynağı çöz; **3 durum: çözüldü / OpenAlex'te-yok / uydurma** (uydurma SADECE pozitif çelişki kanıtıyla). Retraction bayrağı (kaynak doğrulanacak). citation_service.py Read+değerlendir. Cache + rate-limit/backoff. | S1 | Bilinen-doğru ✅ + bilinen-uydurma ✅ + niş-kaynak "yok≠uydurma" fixture'da doğru |
| **F14-S3** | **Atıf-bağlam + kapsama:** (a) "iddia [n] kaynağı destekliyor mu" — **özet/TLDR-seviyesi**, belirsizlik birinci sınıf, asla kesin suçlama; (b) OpenAlex grafiğiyle eksik seminal iş. | S2 | Destek/çelişki/belirsiz fixture + eksik-seminal fixture |
| **F14-S4** | **Orkestrasyon:** yazar (taslak rapor + KANIT PAKETİ) → eleştirmenler (skeptik/yöntemci/sempatik + atıf-eleştirmeni + özgünlük-eleştirmeni) → editör (sentez); 1–2 tur. temp=0 + model/persona sürüm-damgası. | S2 (S3 paralel) | Pilot makalede uçtan-uca + faithfulness PASS + çıpasız-iddia eleştirmende yakalanır |
| **F14-S5** | **Rapor + skor + FE:** Stanford-yapı rapor + 7+3 boyut + verdict ("yol gösterici" çerçeve, kesin hüküm değil). FE design-rules'tan benzetilir (`DESIGN-LANGUAGE.md` + `Page_Design/Tasarim_v3` + `docs/frontend/COMPONENT_RULES.md`). Async iş + ilerleme UI. | S1–S4 | tsc/lint + tarayıcı golden-path + insan-dili künye |
| **F14-S6** | **Çift mod — editör çerçevesi (Faz 2):** aynı motor, editör çıktısı + **etik guardrail** (gizlilik + dergi-politika uyarısı). | S5 | Editör çıktısı + etik kapı |

**Eval (kalite kanıtı) S4 ile paralel başlar** (bkz §7 Açık Soru — altın-set kaynağı).

---

## §3 — ATOMİK COMMIT HARİTASI

Her alt-sprint kendi `F14-S<n>_*.md` manifestinde §0..§18 + atomik commit boundary yazar. Master seviyede yalnız sprint-sınırı: her sprint kapanışı = çalışır + test'li + DoD §9 + commit+push + `docs/STATE.md`+`DECISIONS.md` güncelle. **Sprint-içi commit haritası alt-manifestte.**

---

## §4 — HALÜSİNASYON-KOD-SEVİYESİ (HK)

- **HK-1** Tüm yeni Pydantic modeller `extra="forbid"` (ev kuralı).
- **HK-2** OpenAlex/S2 alan adları + endpoint + retraction kaynağı **Context7/canlı-doğrulama** ile teyit; ezberden API YAZMA.
- **HK-3** Atıf damgası 3-değerli: `resolved` / `not_found_in_index` / `fabricated` (yalnız pozitif çelişki). `not_found` ASLA `fabricated` gibi sunulmaz (yanlış suçlama yasağı).
- **HK-4** Atıf-bağlam çıktısı belirsizlik-etiketli: `supported` / `contradicted` / `unverifiable_from_abstract`. Kesin suçlama yalnız `contradicted`+kanıt.
- **HK-5** LLM yargı katmanı: her olgusal iddia KANIT PAKETİ'ne referanslı; referanssız iddia → editör/eleştirmen siler.
- **HK-6** Deterministik motor bit-kararlı + künyeli; rapor katmanı temp=0 + sürüm-damgalı ama "bit-kararlı değil" dürüst-işaretli (determinizm dürüstlüğü).
- **HK-7** Parse okuyamazsa "okuyamadım" der; boş/uydurma kaynakça ÜRETMEZ.

---

## §5 — BU PLAN'IN UYGULAMA YETKİSİ

Master onaylı. **Kod yazma yetkisi alt-sprint manifesti onayıyla açılır** (papermind §0). Sıradaki: `F14-S1_ingestion.md` (§0..§18) yaz → Omer onayı → S1 kod. Master onayı tek-tek sprint onayını ikame etmez; ama otonomi yasası gereği master kilitliyken minör aksilikte durmam (atla + `OPEN_WORK` + devam).

---

## §6 — RİSK KAYDI (ters-göz eleştirilerinden — 10 boşluk gömülü)

| # | Risk | Severity | Azaltma | Sprint |
|---|---|---|---|---|
| R-1 | "OpenAlex'te yok" → "uydurma" yanlış suçlaması | 🔴 | HK-3 üç-durum; uydurma yalnız pozitif çelişki | S2 |
| R-2 | Senkron 8s timeout'a sığmaz | 🔴 | Async job + durum/polling + cache + backoff | S1/S5 |
| R-3 | "Stanford kalite" ölçülmemiş iddia | 🔴 | Altın-set eval + insan-uyum metriği | S4(paralel) |
| R-4 | Güvenlik+gizlilik+etik (yayımlanmamış IP, LLM'e gönderim, kötücül dosya, editör-modu politika) | 🟠 | Upload doğrulama + saklama politikası (`POLICIES.md`) + LLM-bildirim/onay + S6 etik guardrail | S1/S6 |
| R-5 | Atıf-bağlam özet-seviyesi → yanlış suçlama | 🟠 | HK-4 belirsizlik birinci sınıf | S3 |
| R-6 | Domain karışması (hakemlik vs jüri) | 🟠 | Yeni `/api/review` namespace + tablolar | S1 |
| R-7 | LLM non-determinizm vs analiz-motoru determinizm | 🟡 | HK-6 dürüst-işaret | S4 |
| R-8 | Bozuk/taranmış PDF, ZIP ana-dosya, GROBID-TR | 🟡 | Parse-güven kapısı + OCR kararı (alt-karar) | S1 |
| R-9 | Uzun makale context aşımı | 🟡 | Bölüm-bazlı/chunk yazar stratejisi | S4 |
| R-10 | Verdict yüksek-bahis + maliyet | 🟡 | "Yol gösterici" çerçeve + disclaimer + tier/kota | S5 |

---

## §7 — AÇIK SORULAR (Omer kararı — otonomi: park + varsayılanla devam, veto bekler)

- **AS-1 (eval altın-set):** Pilot kalite kanıtı için hakem-raporlu makaleler nereden? **Varsayılan önerim:** açık kaynak (PeerJ açık-hakem / OpenReview ICLR) + senin elindeki nicel-sosyal-bilim örnekleri. → S4 öncesi netleşmeli.
- **AS-2 (editör etik):** Editör modunda (Faz 2) guardrail duruşu? **Varsayılan önerim:** açık disclaimer + "dergi politikanı kontrol et" uyarısı + gizlilik damgası; tam-otomatik hakem-yerine-koyma REDDİ. → S6 öncesi.
- **AS-3 (parser):** GROBID self-host mi, yoksa hafif PyMuPDF+regex bib-parse mi? **Varsayılan:** GROBID (atıf doğruluğu moat'ın kalbi). → S1 başında.
- **AS-4 (OCR):** Taranmış PDF desteklenecek mi? **Varsayılan:** v1 OUT (dürüst "bu PDF metin içermiyor"). → S1.

---

## §8 — R14 COUNCIL (post-approval placeholder)

Master onaylandı; her alt-sprint manifesti kendi mini-council'ını (literatür + halüsinasyon + fayda/maliyet + rakip + lokal/global, papermind 7-kontrol) açar.

---

## §9 — DoD CHECKLIST (her alt-sprint kapanışı)

- [ ] Backend ucu + test PASS (gerçek davranış, type-check ≠ test)
- [ ] Golden fixture (deterministik motor sprint'leri: S1/S2/S3)
- [ ] FE bağlıysa tsc + lint + tarayıcı golden-path
- [ ] Halüsinasyon kapısı: HK-1..HK-7 uygunluk
- [ ] Künye/provenance (her motor değeri kaynaklı)
- [ ] `docs/STATE.md` + `DECISIONS.md` güncel + commit+push
- [ ] Builder ≠ auditor: kapanışta ayrı denetim notu

---

## §10 — CLOSURE KRİTERLERİ (F14 tamamlandı = bu)

1. Yazar modu uçtan-uca CANLI: upload → deterministik doğrulama → orkestre rapor → FE.
2. Atıf motoru: bilinen-uydurma yakalar + niş-kaynağı yanlış suçlamaz (R-1 kanıtlı).
3. Eval: pilot disiplinde insan-uyum metriği raporlanmış (R-3).
4. Yazılım audit'i (ayrı ajan) + bilimsel/alan audit'i (Omer) GO.
5. prod-readiness / canliya-cikis GO → deploy.
6. Editör modu (Faz 2) etik-guardrail'li canlı VEYA bilinçli OPEN_WORK'e park.

---

## §11 — REVIZYON LOG

- **r0 (2026-06-21):** Master oluşturuldu. Omer onayı + ters-göz 10 eleştirisi (R-1..R-10) gömülü. Pilot=nicel sosyal bilim; çift-mod (yazar-pilot/editör-Faz2); serbest-persona+çıpalı-olgu; yazar+eleştiren+editör orkestrasyonu; OpenAlex-öncelik.
- **r1 (2026-06-21) — İSKELET İNŞASI (otonom fabrika):** S1-S5 uçtan-uca iskelet inşa edildi + doğrulandı.

## §13 — İNŞA DURUMU (r1, doğrulanmış)

**Yapıldı + doğrulandı (gerçek çıktı):**
- S1 ingestion (`engine/ingestion/*`): pdf/docx/latex/zip parser + parse-güven + zip-bomb koruması — **38 test PASS**. Robustluk bug bulundu+düzeltildi (bozuk docx → `BadZipFile` çökmesi → dürüst uyarı, HK-7).
- S2/S3 atıf motoru (`api/services/review_citation_service.py`, `openalex_polite.py` reuse): 3-durum damga (R-1 kanıtlı: not_found≠fabricated), atıf-bağlam (HK-4), kapsama — **14 test PASS**. `is_retracted` canlı curl doğrulandı.
- S4 orkestrasyon (`review_orchestration.py` + 4 persona): yazar→5 eleştirmen(paralel)→editör; çıpasız iddia editörce düşülür — **5 test PASS**.
- S5 servis+route+FE: `review_service.py` (async iş, durum/ilerleme), `routes/review.py` (/api/review/upload|status|report|admin), FE (yükleme + dönen-çark ilerleme + verdict-önce rapor + sol-panelli admin) — **tsc EXIT 0**, app import OK (91 route), ruff temiz.
- Migration `0041_review_domain.sql` (review_job + RLS). Bağımlılıklar: python-multipart + pymupdf + python-docx (pyproject + venv kuruldu).

**OPEN_WORK (dürüst — iskelet ≠ canlı):**
- O-1: Canlı uçtan-uca koşum yapılmadı (OpenAlex ağ + Gemini key + Supabase gerekir; unit testler mock'lu). Gerçek makaleyle smoke şart.
- O-2: `is_retracted` gerçek geri-çekilmiş Work ile canlı doğrulanmadı (alan varlığı kanıtlı, değer False döndü).
- O-3: GROBID self-host (opsiyonel, kapalı) + XML defusedxml sertleştirme (S314 noqa'lı) + OCR (taranmış PDF) v1-OUT.
- O-4: Admin paneline rol-kapısı `ADMIN_USER_IDS` ile geldi ama prod allowlist set edilmeli (boş+prod=kapalı).
- O-5: Eval altın-set (R-3/AS-1) ve heuristic eşik kalibrasyonu (seminal cited_by>500, fuzzy 0.82) gerçek veriyle ayarlanmalı.
- O-6: S6 editör modu çerçevesi: motor `mode=editor`+`ethics_notice` destekliyor; tam Faz-2 editör akışı/çıktısı henüz dar.
- O-7: review_service boru hattı için integration testi (mock'lu uçtan-uca) eklenebilir.

---

## §12 — REFERANS DOSYALAR

- Anayasa: `~/.claude/CLAUDE.md` · `analiz-motoru` SKILL · papermind `CLAUDE.md §0` · `docs/DM_RULES.md`
- Tasarım: `/Users/omer/DESIGN-LANGUAGE.md` · `Page_Design/Tasarim_v3` · `docs/frontend/COMPONENT_RULES.md`
- Mevcut hakemlik: `api/services/journal_sim_service.py` · `api/services/citation_service.py` · `api/routes/workshop.py` · `engine/personas/journal/*` · `engine/statcheck/multilingual.json`
- Rakip referans: Stanford paperreview.ai (arXiv-only, atıf-doğrulamayan — bizim moat'ımız bunun tersi)
