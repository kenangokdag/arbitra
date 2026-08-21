# F2 Day 4 — LVR Eşik Kalibrasyonu Spec (KD-13)

> **Statü**: TASLAK — Council 29 (Day 4 wrap kalibrasyon adımı), R13.9 alan sahibi BAĞLAYICI: Omer (eşik onayı) + Sercan (post-hoc impl review)
> **Bağlam**: F2 sprint manifest §3 Day 4 wrap §6.1 — `tests/fixtures/faithfulness_calibration.json` (KD-13)
> **Kapsam daraltması (önemli)**: F2 P008 Curator çağrısı `gate.check(level=SEARCH)` → sadece **2 kat aktif**: (a) jsonschema=100% binary (kalibrasyon yok, geçer/geçmez) + (b) LVR cosine ≥0.7. MiniCheck NLI + ALCE citation-recall **SUMMARY level** (F3c P022) — F2'de aktive değil. **Bu spec yalnızca LVR eşiğini kalibre eder.**
> **MiniCheck/ALCE kalibrasyonu**: F3c sprint'inde (KD-14 ile birlikte) — bu spec dışı.

---

## §0 Bağlam (3 cümle)

Faithfulness Gate spec (B-010 §1) `lvr_min_distance: 0.7` default verir, kaynak K5 + B42-045 §1; ama bu sayı **bizim corpus'umuzda + bizim Curator çıktımızda + 3 dilde** doğrulanmamış — Liu 2023 baseline'ı genel bir referans, PaperMind'a özgü değil. Day 4'te `faithfulness_calibration.json` fixture'ı 100 (claim, evidence) çifti üzerinde gerçek false-positive / false-negative oranı ölçer; eşik 0.7 yeterliyse kalır, değilse revize edilir (örn. 0.65 veya 0.75) ve `config/faithfulness_thresholds.yaml` Omer onayıyla güncellenir. Onsuz Day 4'te P008 production'a girerken Halüsinasyon Avcısı tek-veto kullanır (DM-008 R8 K5).

---

## §1 Sampling planı — 100 (claim, evidence) çifti

### §1.1 Stratifikasyon

| Eksen | Değer | Adet | Gerekçe |
|---|---|---|---|
| **Dil** | TR / EN / ID | 50 / 40 / 10 | TR pilot ana dil; EN corpus çoğunluğu; ID minörite ama representation şart |
| **Zone** | D (Disipline) / F (Field) / S (Subfield) | 30 / 40 / 30 | F en yaygın PaperCard sorgu seviyesi |
| **Year cohort** | 2010-2018 / 2019-2024 | 50 / 50 | year_verified false oranı yıllara göre değişir; eski paperlarda K1 risk artar |
| **Q-weak** | true / false | 30 / 70 | Q-weak'lerde span-evidence zayıflığı kalibrasyonun edge-case'i |
| **lang_conf** | ≥0.9 / 0.7-0.9 / <0.7 | 60 / 30 / 10 | Düşük lang_conf'ta BGE-M3 cross-lingual cosine kararsızlaşır |

**Kaynak**: 24.87M corpus'tan (Pinecone) `metadata` filter ile stratified sampling — 100 paper_id seçilir, her biri için 1 (claim, evidence) çifti üretilir. **Tekrarlanabilirlik**: `seed=20260501` (Day 4 tarihi).

### §1.2 Claim üretimi

Her seçilen paper_id için Curator-mock 1 cümlelik akademik claim üretir (örn. "X yöntemi Y veriseti üzerinde Z doğruluk verir"). Mock değil **gerçek Listener+Curator zinciri** (P004 + P008) çağrılır → `signals_13` 13 anahtarlı çıktı + claim cümlesi alınır. Bu da "production-realistic" kalibrasyon demek.

### §1.3 Evidence span üretimi

`fact_paper_sentence` parquet (N11 v2, 193,653,620 satır) içinden paper_id'ye ait cümleler çekilir; LVR validate flow'unun yapacağı gibi top-3 cosine cümle "evidence" olarak işaretlenir (K5 paper_id+span ≥0.7 cosine BGE-M3).

---

## §2 Ground-truth metodoloji — Synthetic Corruption Injection

### §2.1 Tercih: corruption injection (manual annotation değil)

**Manuel annotation reddedilir**:
- Omer 100 çift × 5 dakika = 8.3 saat — Day 4 wrap'e sığmaz
- Annotator tutarlılığı tek annotator için Krippendorff α ölçülemez
- 3-dil (TR + EN + ID) annotator havuzu MVP'de yok

**Corruption injection seçilir** (Liu 2023 MiniCheck eval methodology + 2025 Patronus Lynx yaklaşımı): 100 "faithful" çiftin yanına 100 "unfaithful" çift sentetik üretilir → toplam 200 etiketli çift.

### §2.2 Corruption türleri (5 sınıf × 20 örnek = 100 unfaithful)

| Tür | Yöntem | Örnek (TR) | LVR beklenen |
|---|---|---|---|
| **Number swap** | Claim'deki sayıyı yakın-ama-yanlış değerle değiştir (% → %, accuracy 0.85 → 0.78) | "%85 doğruluk" → "%78 doğruluk" | düşmeli (cosine 0.4-0.6) |
| **Year change** | Year verified=true ise yılı ±3 yıl shifte; verified=false ise (YYYY) ekle | "(2022)" → "(2018)" | düşmeli (K1 scrub yakalamalı) |
| **False attribution** | Claim'deki yazar veya method ismini başka bir corpus paper'ından al | "Vaswani et al. attention" → "He et al. attention" | düşmeli (named-entity LVR ≤0.5) |
| **Contradicting verb** | Olumlu/olumsuz çevir ("yükseltir" → "düşürür", "achieves" → "fails to achieve") | "performans yükseltir" → "performans düşürür" | düşmeli (semantic flip) |
| **Out-of-corpus claim** | Evidence'da hiç geçmeyen alana ait cümle ekle (örn. medical paper'a astrofizik claim) | yan-konu cümlesi yapıştır | çok düşmeli (cosine <0.3) |

**Beklenti** (kalibrasyonun başarı kriteri): 100 faithful pair LVR ≥0.7, 100 corrupted pair LVR <0.7 (false-positive ≤%5, false-negative ≤%10).

### §2.3 Corruption pipeline kabul kriteri

- Her corruption türü ≥18 örnek **gerçekten LVR<0.7** üretmeli (yoksa corruption metodu çok zayıf, type discard)
- Sampling seed sabit (`seed=20260501`); reproducibility KD-12 R13.10 HK-7 ile uyumlu
- Corruption pipeline kodu `scripts/calibration/corrupt_claims.py` (~120 LOC) — Day 4 sabah Omer yazar, 30dk

---

## §3 Kalibrasyon prosedürü (Day 4 wrap'te tam akış)

### §3.1 Adım sırası

```
1. Sampling: scripts/calibration/sample_papers.py --n 100 --seed 20260501
   → tests/fixtures/calibration_papers_100.json
   (paper_id + metadata 8-field + 1 evidence_top3)

2. Claim üretim: P004 Listener + P008 Curator zinciri 100 paper_id'yi tüketir
   → tests/fixtures/calibration_claims_faithful.json
   (claim cümlesi + evidence_span_ids + LVR cosine)

3. Corruption: scripts/calibration/corrupt_claims.py
   → tests/fixtures/calibration_claims_corrupted.json
   (100 corrupted claim × 5 tür eşit dağıtım)

4. LVR ölç: scripts/calibration/measure_lvr.py
   → tests/fixtures/faithfulness_calibration.json
   {
     "n_total": 200,
     "n_faithful": 100,
     "n_corrupted": 100,
     "lvr_distribution": {...histogram...},
     "thresholds_evaluated": {
       "0.65": {"fp_rate": 0.07, "fn_rate": 0.04, "f1": 0.94},
       "0.70": {"fp_rate": 0.05, "fn_rate": 0.09, "f1": 0.93},
       "0.75": {"fp_rate": 0.03, "fn_rate": 0.18, "f1": 0.89}
     },
     "recommended_threshold": 0.70,
     "calibration_date": "2026-05-03",
     "seed": 20260501,
     "corpus_version": "v1.4-202604"
   }

5. Karar:
   - F1@0.7 ≥ 0.90 ise eşik 0.7 kalır (default kabul, B-010 §1 unchanged)
   - F1@0.65 veya F1@0.75 daha yüksekse Omer arbiter karar (alan sahibi BAĞLAYICI)
   - Eşik değişirse config/faithfulness_thresholds.yaml güncelle + B-010 §1 referansa "kalibrasyon: 2026-05-03 fixture" satırı ekle

6. Council 29 §-toplantısı: kalibrasyon sonucu R13 6 üye + R13.9 Omer + Sercan tablo (KD-13 kapanış)
```

### §3.2 Kabul kriteri (Council 29 GREEN şartı)

- ✅ 200 etiketli çift fixture'da var (100 faithful + 100 corrupted, 5 tür eşit)
- ✅ Stratifikasyon §1.1 ile uyumlu (TR/EN/ID + zone + year + q_weak + lang_conf)
- ✅ Eşik kararı F1 ≥0.90 (yoksa Halüsinasyon Avcısı RED)
- ✅ Reproducibility: `seed=20260501` ile tekrar koşulduğunda aynı dağılım (HK-7)
- ✅ Recommended_threshold sayısı `config/faithfulness_thresholds.yaml`'a yansır

### §3.3 Beklenmedik durumlar

| Durum | Davranış |
|---|---|
| F1 < 0.85 her eşikte | LVR tek başına yetersiz; **Faz 2'ye MiniCheck NLI proxy** (KD-14) acil; F2 P008 production'a sokulmaz, KD-13 RED kapatılır |
| TR örneklerde LVR sistematik düşük (cross-lingual BGE-M3 zayıf) | TR-only eşik (`lvr_min_distance_tr: 0.65`) ayrı config alanı; çok-dilli ayrım Faz 2 (KD eklenir) |
| Corruption type discard (örn. year change LVR'yi düşürmüyor) | K1 yıl scrub regex zaten temizliyor demektir → o tür kalibrasyondan çıkar; n_corrupted 80'e düşer; eşik kararı 80 corrupted üzerinden |
| year_verified=false oranı sample'da çok yüksek (%50+) | corpus realite — paper.year_verified Day 4 öncesi cron başlatılmamış; sample yeniden alınır year_verified=true ağırlıklı |

---

## §4 Fixture şema (`tests/fixtures/faithfulness_calibration.json`)

```json
{
  "version": "1.0",
  "calibration_date": "2026-05-03",
  "seed": 20260501,
  "corpus_version": "v1.4-202604",
  "n_total": 200,
  "n_faithful": 100,
  "n_corrupted": 100,
  "stratification": {
    "lang": {"tr": 50, "en": 40, "id": 10},
    "zone": {"D": 30, "F": 40, "S": 30},
    "year_cohort": {"2010-2018": 50, "2019-2024": 50},
    "q_weak": {"true": 30, "false": 70},
    "lang_conf": {"high": 60, "mid": 30, "low": 10}
  },
  "corruption_types": {
    "number_swap": 20,
    "year_change": 20,
    "false_attribution": 20,
    "contradicting_verb": 20,
    "out_of_corpus": 20
  },
  "samples": [
    {
      "id": "faithful_001",
      "paper_id": "2.07.103.T11466.0.0.C.M.M.tr.R.v1",
      "claim": "...",
      "evidence_span_ids": ["sentence_id_1", "sentence_id_2", "sentence_id_3"],
      "lvr_cosine": 0.84,
      "label": "faithful",
      "lang": "tr",
      "zone": "S",
      "year": 2022,
      "q_weak": false,
      "lang_conf": 0.94
    },
    {
      "id": "corrupted_001",
      "paper_id": "2.07.103.T11466.0.0.C.M.M.tr.R.v1",
      "claim": "...",
      "evidence_span_ids": ["sentence_id_1", "sentence_id_2", "sentence_id_3"],
      "corruption_type": "number_swap",
      "original_value": "%85",
      "corrupted_value": "%78",
      "lvr_cosine": 0.52,
      "label": "unfaithful",
      "lang": "tr",
      "zone": "S",
      "year": 2022,
      "q_weak": false,
      "lang_conf": 0.94
    }
  ],
  "thresholds_evaluated": {
    "0.60": {"tp": 95, "fp": 12, "tn": 88, "fn": 5, "f1": 0.918},
    "0.65": {"tp": 93, "fp": 7, "tn": 93, "fn": 7, "f1": 0.930},
    "0.70": {"tp": 91, "fp": 5, "tn": 95, "fn": 9, "f1": 0.929},
    "0.75": {"tp": 82, "fp": 3, "tn": 97, "fn": 18, "f1": 0.886}
  },
  "recommended_threshold": 0.65,
  "council_29_decision": "Omer arbiter; 0.65 onaylandı; B-010 §1 default 0.70 → 0.65 revize"
}
```

---

## §5 Critical files (Day 4 wrap'te yaratılır)

### Yeni (Omer 30+30+30+30 dk = 2h)
- `scripts/calibration/sample_papers.py` (~80 LOC) — stratified sampling
- `scripts/calibration/corrupt_claims.py` (~120 LOC) — 5 tür corruption
- `scripts/calibration/measure_lvr.py` (~60 LOC) — LVR ölç + threshold sweep
- `tests/fixtures/faithfulness_calibration.json` (oto-üretim, ~200KB)

### Touch (kalibrasyon sonrası)
- `config/faithfulness_thresholds.yaml` — `lvr_min_distance` revize (eğer 0.7 değişirse)
- `docs/backend/faithfulness_gate_spec.md` §1 — kalibrasyon referansı
- `docs/STATE.md` §7 Bilinen Borçlar — KD-13 KAPANDI satırı
- `docs/DECISIONS.md` — yeni B-NNN entry (kalibrasyon sonucu + eşik kararı)

### Read-only referans
- `docs/backend/faithfulness_gate_spec.md` (B-010)
- `docs/plans/F2_day2_4_compressed_sprint.md` Council 28
- N11 v2 `fact_paper_sentence` parquet (193,653,620 cümle)

---

## §6 Council 29 — R13 (Day 4 wrap kalibrasyon kapanışı, plan-time taslak)

> Bu Council R13.9 alan sahibi tablosu — Omer arbiter binding vote bekleniyor (eşik karar). Aşağıdaki verdict'ler **plan-time tahmin**; gerçek koşum sonucu Day 4'te doldurulur.

| # | Üye | Tahmini Verdict | Gerekçe (plan-time) |
|---|---|---|---|
| 1 | **Halüsinasyon Avcısı** | 🟢 yeşil (eşik kalibre olduğunda) | Corruption injection 5 tür standart yöntem (Liu 2023 + Patronus Lynx); fixture reproducibility var (seed); F1≥0.9 koşulu enforce |
| 2 | **Akademik İsabet** | 🟡 sarı | 100 faithful pair Curator-mock'tan değil GERÇEK Curator zincirinden gelmeli (P004+P008 çağrı); aksi mock-bias olur. **Düzeltme**: Adım 2'de mock-Listener kullanma; gerçek HF Qwen + BGE-M3 zinciri |
| 3 | **Fayda-Maliyet Hakemi** | 🟢 yeşil | Manual annotation 8.3h vs corruption injection 30dk script + 5dk koşum; 16× daha hızlı + reproducible |
| 4 | **Daha İyisi Var Mı?** | 🟡 sarı | 200 çift küçük örneklem; 95% CI ±%3.5 — kabul edilebilir Pilot/Faz 2 ekstra 300 çift eklenir. **KD-NN: Faz 2 örneklem 500'e çıkar.** |
| 5 | **Global Çözüm Mühendisi** | 🟢 yeşil | 3-dil + 5 tür + 5 stratifikasyon ekseni global cover; TR-only düşükse Faz 2 ayrı config alanı (`lvr_min_distance_tr`) |
| 6 | **Son Kullanıcı Avukatı** | 🟢 yeşil | Akademisyen "%X doğrulanmış" görmek ister; kalibre eşik runtime gerçeği yansıtır, hayal değil |
| **A** | **Sercan (BAĞLAYICI, post-hoc)** | 🟡 sarı (plan-time) | Corruption pipeline 5 tür temiz; fixture şema standart; ama `out_of_corpus` türünde semantic relevance düşürmek zor (yan-konu cümlesi rastgele eklenmek yerine `Pinecone neighbor query --negative` ile en uzak konu seçilmeli). **Düzeltme**: corrupt_claims.py'de `out_of_corpus` için Pinecone "farthest neighbor" sorgu helper |
| **A** | **Omer (BAĞLAYICI, arbiter)** | ⏳ Day 4'te karar | Recommended threshold 0.7 yeterliyse onay; F1<0.9 ise revize karar; multi-dil sapma varsa ayrı eşik kararı |

**Plan-time karar (R13.5)**: 4 GREEN + 3 YELLOW (3+ YELLOW = Omer arbiter zorunlu — alan sahibi seat bu spec için ZATEN açık, kalibrasyon sonucu üzerinden Council 29'da Omer karar verir).
**Empirik test gerekli mi?** EVET — bu spec'in kendisi empirik kalibrasyon koşumu; spec PASS = `tests/fixtures/faithfulness_calibration.json` yazılı + Omer eşik onayı.

**Düzeltmeler (Day 4 öncesi spec'e işlenecek)**:
- (a) §3.1 Adım 2'ye "mock-Listener yasak; gerçek P004 zinciri" satırı (Akademik İsabet YELLOW)
- (b) §3.1 Adım 3 corrupt_claims.py'de `out_of_corpus` türünde Pinecone farthest-neighbor helper (Sercan YELLOW)
- (c) Faz 2 ek-iş: KD-NN (yeni) örneklem 500'e çıkarılır (Daha İyisi YELLOW)

---

## §7 Açık iş listesi (kalibrasyon Day 4 öncesi)

- [ ] **Omer**: §3.1 Adım 2 mock-Listener yasak satırı spec'e işle (R13 Akademik İsabet düzeltmesi); Day 4 sabah ilk 5dk
- [ ] **Omer**: `out_of_corpus` corruption türü için Pinecone farthest-neighbor helper imzası (Sercan A-row YELLOW); Day 4 sabah 10dk
- [ ] **Omer**: 4 script ($1+$2+$3 = ~260 LOC) Day 4 wrap'te yaz; 2h budget
- [ ] **Omer**: Council 29 §-toplantısı kalibrasyon sonucu üzerinden eşik onayı (recommended_threshold karar)
- [ ] **Sercan post-hoc**: corrupt_claims.py 5 tür coverage review (özellikle TR named-entity attribution)
- [ ] **KD-NN (yeni)**: Faz 2 örneklem 200→500 + ek MiniCheck NLI eşik kalibrasyonu (F3c sprint'inde)

---

## §8 Halüsinasyon kod-seviyesi (HK-1..HK-7) uyum

| HK | Bu spec'te uygulama |
|---|---|
| HK-1 Pydantic forbid | `CalibrationFixture` Pydantic model — 4 script çıktısı bu modelle validate edilir, extra=forbid |
| HK-2 source comment | corrupt_claims.py 5 tür docstring'inde "Liu 2023 MiniCheck eval §3.2 + Patronus Lynx §4 corruption taxonomy" referansı |
| HK-3 external service empirik | Sampling P004 + P008 gerçek HF Qwen çağırır (mock yasak); Pinecone neighbor query gerçek (mock yok) |
| HK-4 runtime assertion | measure_lvr.py'de `assert n_total == 200` + `assert all(corruption_type in 5_known_types)` |
| HK-5 manifest verify | sample_papers.py corpus_version'ı `b012_metadata.json` manifest'inden okur, hardcoded değil |
| HK-6 type-strict | mypy strict; `Any` leak yok |
| HK-7 reproducibility seed | seed=20260501 sabit; HF Qwen `temperature=0` deterministik; yeniden koşum aynı fixture |

---

**Final commitment**: Bu spec onaylandıysa Omer Day 4 wrap'te 2h içinde kalibrasyon koşumunu tamamlar; Council 29 sonucu KD-13 KAPANIR; F2 PASS branch'ı Sercan post-hoc PR review'a hazırlanır. **Plan dışı edit yok** — herhangi bir değişiklik bu spec revize edilerek yapılır (R1 / DM-008 plan-first).
