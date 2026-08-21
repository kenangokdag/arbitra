# P07 — Evaluation Lab ve Akademik Kalite Ölçümü

## Amaç

AI çıktısı ölçülür hâle gelir: hallucination, citation accuracy, rubric agreement, actionability ve regression benchmark.

## Faz kapısı

Release eval benchmark’dan geçmeden çıkamıyor.

## İlgili spec dosyaları

- `docs/worldclass/SPECS/evaluation_lab_spec.md`

## Görevler

### P07-T01_GOLDSET_AND_EVAL_SCHEMA — Goldset ve eval schema’yı dünya klası metriklerle genişlet

**Öncelik:** P0  
**Bağımlılıklar:** P06-T01_REVIEW_REPORT_SCHEMA_V2

**Dokunulacak dosyalar:**
- `eval/review/goldset.json`
- `eval/review/schema.py`
- `eval/review/metrics.py`
- `eval/review/README.md`

**Uygulama adımları:**
1. Eval labels: document_type, study_design, expected_findings, citation_truth, guideline_items, hallucination_flags, actionability score.
2. Goldset kategorileri: article, conference, thesis, grant, qualitative, quantitative, systematic.
3. Metrikleri schema’ya bağla.

**Test/doğrulama:**
- unit: eval schema validation
- unit: metrics compute on sample_reports

**Başarı tanımı:**
- Eval sadece skor değil akademik kalite boyutlarını ölçüyor.

**Bir sonraki adıma geçiş:** Sample reports üzerinde metrics deterministic çalışıyorsa.

**Durdurma koşulları:**
- Eval LLM judge only ve gold evidence yoksa.

---

### P07-T02_RELEASE_EVAL_GATE — Release eval gate ve regression thresholdları

**Öncelik:** P0  
**Bağımlılıklar:** P07-T01_GOLDSET_AND_EVAL_SCHEMA

**Dokunulacak dosyalar:**
- `eval/review/run_eval.py`
- `.github/workflows/polish_gate.yml`
- `config/faithfulness_thresholds.yaml`

**Uygulama adımları:**
1. Eval komutu CI’da opsiyonel/required mode desteklesin.
2. Thresholdlar: hallucination max, actionability min, citation precision min, schema validity 100%.
3. Regression durumunda release fail.
4. Eval report artifact üret.

**Test/doğrulama:**
- CI dry run
- unit: threshold failure exits nonzero

**Başarı tanımı:**
- Yeni prompt/model değişikliği kaliteyi düşürürse yakalanıyor.

**Bir sonraki adıma geçiş:** Eval gate en az smoke goldset ile CI’da çalıştığında.

**Durdurma koşulları:**
- Eval flaky ve release’i anlamsız kırıyorsa threshold stabilize et.

---

### P07-T03_HUMAN_EXPERT_REVIEW_LOOP — Human expert feedback loop ve calibration workflow

**Öncelik:** P1  
**Bağımlılıklar:** P07-T01_GOLDSET_AND_EVAL_SCHEMA

**Dokunulacak dosyalar:**
- `eval/review/build_goldset.py`
- `docs/worldclass/TEMPLATES/eval_card_template.md`
- `api/models/review.py`

**Uygulama adımları:**
1. Expert reviewer annotation template oluştur.
2. False positive/false negative taxonomy tut.
3. Rubric weights calibration dosyasına bağla.
4. Eval dashboard için JSON report standardize et.

**Test/doğrulama:**
- sample annotation import test
- metrics with human labels test

**Başarı tanımı:**
- Akademik kalite insan uzman kıyasına bağlanabilir.

**Bir sonraki adıma geçiş:** En az 10 örnek uzman annotation formatına alınabildiğinde.

**Durdurma koşulları:**
- Uzman feedback serbest metin olarak kayboluyorsa.

---
