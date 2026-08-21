# F14 Hakemlik — EVAL (kalite kanıtı)

> Bu klasör, F14 hakemlik motorunun **"Stanford kalite" iddiasını ÖLÇÜLEBİLİR**
> yapar (master §6 **R-3**). Motorun bir makaleye verdiği değerlendirme (verdict +
> boyut skorları), **gerçek insan hakem** değerlendirmesiyle ne kadar uyuşuyor —
> bunu sayıyla gösterir.

---

## 1. Ne ölçülüyor?

F14 motoru bir makaleye şunları üretir (`api/models/review.py`):
- **verdict**: `accept` / `minor_revision` / `major_revision` / `reject`
- **boyut skorları** (1–10): Stanford 7 (originality, importance, claims_supported,
  soundness, clarity, community_value, contextualization) + bizim 3 deterministik
  moat boyutu (citation_integrity, coverage_completeness, statistical_consistency)

EVAL bu çıktıyı **altın-set**'teki insan değerlendirmesiyle kıyaslar ve üç metrik
üretir (`metrics.py`, saf fonksiyonlar):

| Metrik | Ne der |
|---|---|
| **verdict_accuracy** | Motor verdict'i insanla aynı mı (tam isabet) + 1-kademe-tolerans |
| **dimension_agreement** | Her boyut için motor↔insan **Spearman/Pearson** korelasyonu + ortalama mutlak fark |
| **confusion_matrix** | Verdict 4×4 (satır=insan, sütun=motor) |

**Referans (R-3 hedefi):** Stanford kendi AI hakem aracını ICLR 2025'e karşı
kalibre etti — **Spearman ≈ 0.42**, ki bu **insan-insan tavanı ~0.41**'e denk.
Yani hedef "insan kadar tutarlı", "mükemmel" değil.

---

## 2. Altın-set (`goldset.json`)

Bir **GoldEntry** = bir makale + **gerçek insan hakem** değerlendirmesi
(şema: `schema.py`, Pydantic `extra=forbid`).

### Şu anki içerik (başlangıç tohumu)
`build_goldset.py` ile **OpenReview ICLR 2025 public API**'sinden çekilen
**5 GERÇEK submission** (ML alanı). Her girdide:
- `human_verdict`: gerçek ICLR **Decision**'dan (Accept→`accept`).
- `human_scores`: ICLR'in **gerçekten ölçtüğü** boyutlardan eşlendi —
  `soundness`/`presentation`/`contribution` (1–4) → bizim
  `soundness`/`clarity`/`importance` (1–10'a lineer ölçek).
- `human_review_excerpt`: ortalama rating + karar.

### ⚠️ Tohumun bilinçli sınırları (Omer'in göreceği)
1. **Hepsi `accept`** — `content.venueid` sorgusu kabul edilen poster/oral döner;
   tohumda **reject/revision çeşitliliği YOK**. Bu, verdict doğruluğunu tek
   sınıfta ölçer → diversite Omer'in eklemeleriyle gelmeli.
2. **Sadece 3 boyut** gerçek skor taşır (soundness/clarity/importance). Diğer
   7 boyut ICLR'de ölçülmedi → o boyutların `human_scores` anahtarı **YOK**
   (uydurma yasağı; metrik bunları otomatik kapsam-dışı bırakır).
3. **ML alanı**, pilot disiplin **nicel sosyal bilim** DEĞİL. Tohum sadece
   harness'i gerçek veriyle besler; pilot kanıt Omer'den gelir (§3).

> **Halüsinasyon yasağı:** gerçek olmayan insan skoru ASLA yazılmaz. Bilinmeyen
> alan `OMER_DOLDURACAK` ile işaretlenir; `metrics.py` bu işaretli verdict/skoru
> **kıyaslamaya almaz** (sahte sayı üretmez).

---

## 3. Altın-set nasıl büyütülür? (Omer'in görevi)

Pilot disiplin: **nicel sosyal bilim / metodoloji** (panel ekonometrisi, ölçek
geliştirme, çok-kriterli karar). Hedef **N ≥ 10** hakem-raporlu makale.

Kaynak önerileri (master §AS-1):
- **PeerJ açık-hakem**: yayımlanmış makalelerin hakem raporları + karar herkese açık.
- Elindeki **hakem-raporlu nicel-sosyal-bilim** örnekleri (dergi review'ları).

Bir girdi eklemek için `goldset.json` içine bir `GoldEntry` ekle:
```json
{
  "paper_id": "peerj:cs-1234",
  "source": "peerj",
  "title": "...",
  "field": "quant_social_science",
  "pdf_url": "https://...",
  "human_verdict": "major_revision",
  "human_scores": { "soundness": 6.0, "clarity": 7.0, "importance": 5.0 },
  "human_review_excerpt": "Hakem: yöntem sağlam ama örneklem küçük...",
  "notes": "PeerJ açık-hakem, 2 hakem ortalaması"
}
```
- Bir boyutu **gerçekten ölçemiyorsan o anahtarı KOYMA** (uydurma yok).
- `human_verdict`'i bilmiyorsan `"OMER_DOLDURACAK"` yaz.
- `meta.real_entry_count` / `placeholder_entry_count` sayaçlarını güncelle.

ICLR tohumunu yeniden çekmek için:
```bash
.venv/bin/python -m eval.review.build_goldset
```
(Ağ engelliyse script `goldset.json`'u **ezmez**, dürüst hata yükseltir.)

---

## 4. Nasıl koşulur?

### Dry-run (LLM'siz — harness gösterimi)
```bash
.venv/bin/python -m eval.review.run_eval
```
- `sample_reports.json` varsa onunla metrikleri hesaplar.
- **Paketlenen `sample_reports.json` İLLÜSTRATİFTİR** (insan skoruna gürültü
  eklenerek kurgulandı) → runner **büyük bir uyarı banner'ı** basar. Bu sayılar
  **KALİTE KANITI DEĞİL**; sadece metrik motorunun çalıştığını gösterir.

### Canlı (gerçek R-3 kanıtı — Omer key'leri gerekir)
```bash
.venv/bin/python -m eval.review.run_eval --live
```
Şu an `--live`, her altın-set girdisi için hazır `Manuscript` + `EvidencePack`
ister (S1 PDF→parse hattının bu runner'a bağlanması **ayrı iş**). O bağlanana
kadar `--live` **dürüst `NotImplementedError`** ile durur — uydurma rapor YOK.

JSON çıktı: `--json-out sonuc.json`.

---

## 5. Dosyalar

| Dosya | Görev |
|---|---|
| `schema.py` | `GoldEntry` / `GoldSet` Pydantic şeması (`extra=forbid`) + `OMER_DOLDURACAK` sentinel |
| `goldset.json` | Başlangıç altın-set (5 gerçek ICLR 2025 girdi) |
| `build_goldset.py` | OpenReview'dan gerçek tohum üretici |
| `metrics.py` | Saf metrik fonksiyonları (verdict/boyut/confusion) — test edilebilir |
| `run_eval.py` | Runner (`--live` / dry-run) + insan-dili özet |
| `sample_reports.json` | **İllüstratif** örnek motor çıktısı (dry-run için; kanıt değil) |

Test: `tests/unit/test_review_eval.py` (13 test, metrik saf fonksiyonları).
```bash
.venv/bin/python -m pytest tests/unit/test_review_eval.py -q
```

---

## 6. Moat boyutlarının ground-truth sınırı (ÖNEMLİ, 2026-08-13 kararı)

**`citation_integrity`, `statistical_consistency`, `coverage_completeness`** (Arbitra'ya
özgü 3 moat boyutu) için altın-set'te **hiçbir zaman insan-skoru olmadı ve şu an
yok** — hiçbir `GoldEntry.human_scores` bu 3 anahtarı taşımıyor (uydurma yasağı,
§2). Bu yüzden `dimension_agreement()` bu boyutlar için asla çalışmaz, sadece
Stanford'un 7 genel boyutunu (originality/importance/soundness/clarity/vb.)
kapsar.

Motorun tek moat-özel metriği **`moat_grounding_accuracy`** (`metrics.py`) —
bu, motorun ürettiği güçlü (critical/major) atıf-bütünlüğü iddialarının
`EvidencePack`'teki GERÇEK fabricated/retracted/contradicted olgularına dayanıp
dayanmadığını ölçer. Bu, **kanıt-varlığı (presence-validity)** ölçer —
"motor bir şey iddia ettiğinde arkasında gerçek kanıt var mı" — **KALİBRASYON
DEĞİL**. Bir moat boyutunun verdiği SKORUN (örn. citation_integrity=6.5) insan
bir hakemin aynı makaleye vereceği skora ne kadar yakın olduğu hiçbir zaman
ölçülmedi, çünkü karşılaştıracak gerçek insan skoru hiç toplanmadı.

**Karar (2026-08-13, guardian danışmasıyla — `PDF_PIPELINE_CALISMA_GUNLUGU.md`
§42):** Bu, moat boyutlarına özel küçük bir insan-puanlama turuyla (örn. 10-15
makalede sadece "gerçek atıf/istatistik sorunu var mı + şiddeti" sorularak)
kapatılabilir bir boşluk — ama şimdilik **bilinçli olarak ertelendi**
(kaynak/zaman kısıtı, uygun bir hakem/etiketleyici henüz yok). Bu bölüm o
karar netleşene kadar güncel tutulmalı.

## 6b. Stanford'un 7 genel boyutu içinde de kalibrasyon eşit değil

`dimension_agreement()` bu 7 boyutu (originality/importance/soundness/
clarity/vb.) kapsıyor olması, hepsinin doğrulanmış olduğu anlamına GELMİYOR:

- **clarity**: çeşitli örneklemde r=0.86 — gerçek bir sinyal var
- **soundness**: r=0.15 (çeşitli örneklemde bile) — kök nedeni bulundu
  (§44, severity kuralı bağlamdan bağımsız), henüz düzeltilmedi
- **originality**: r=0.19 (n=29-31) — kök nedeni henüz araştırılmadı
- **importance**: n=5 — örneklem çok küçük, güvenilmez

Yani "moat riskli, temel 7 boyut sağlam" okuması YANLIŞ. Şu an gerçekten
kalibre olduğu gösterilmiş tek boyut clarity, ve o da restricted-range
düzeltmesiyle.
