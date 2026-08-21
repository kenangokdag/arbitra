# Plan: Uydurma-atıf moat-gate'inin severity-bağımlılığını gidermek (Fix A) — Fix B askıya alındı

**Tarih:** 2026-08-15 (rev. 2 — guardian 1. tur + kullanıcı kararı sonrası)
**Durum:** PLAN — kod yazılmadı, guardian'a danışılmadan koda geçilmeyecek (CLAUDE.md plan-first kuralı).
**Kaynak:** `PDF_PIPELINE_CALISMA_GUNLUGU.md` §63-64 (canlı demo koşumunda bulundu, guardian'a danışıldı, 61-goldset'te ölçüldü).
**Karar verici:** Kenan — "Fix A'yı ilerlet, Fix B'yi askıya al" (2026-08-15).

---

## 0. Rev. 2 değişiklik özeti

- **Fix B (editörün kendi verdict'i > deterministik override) TAMAMEN ÇIKARILDI.** Guardian onaylamadı (gerçek bug'ı — editörün YAPILANDIRILMIŞ verdict'i İLE KENDİ PROSE'u arasındaki çelişkiyi — çözdüğü kanıtlanamadı; farklı bir problemi çözüyordu). Kullanıcı kararıyla askıya alındı. Ayrı bir gelecek plan konusu (bkz §6 madde 1).
- **Log-config boşluğu DÜZELTİLDİ** (ayrı, küçük, saf-gözlemsellik commit): `api/main.py`'ye `logging.basicConfig(level=logging.INFO, ...)` eklendi. Bununla `deneme.pdf` yeniden test edildi (taze koşum) — editörün kendi verdict'i bu kez `major_revision`, deterministik override de `major_revision` (ÇELİŞKİ YOK bu koşumda). **Yeni, bağımsız bulgu:** AYNI kanıt paketiyle (9 uydurma atıf) 1. koşum `accept`, 2. koşum `major_revision` verdi — hiçbiri "reject"e ulaşmadı, ikisi de FARKLI sonuç. Bu, Fix A'nın gerekliliğini (LLM yargısından bağımsız deterministik tetikleyici) BAĞIMSIZ bir kanıtla güçlendiriyor.
- **Fix A'ya guardian'ın koşulu eklendi (§3a):** count-tabanlı tetikleyici artık en az 1 `citation_integrity`/`literature_positioning` Finding'i ŞART koşuyor (Finding'siz-tetikleme riski kapatıldı).
- **Dil yumuşatıldı:** "çelişmiyor" → "makul ama kanıtlanmamış" (guardian'ın 1. tur uyarısı).
- **Test planı genişletildi (§5):** 61-goldset'in TAMAMI için önce/sonra verdict tablosu (sadece 2 bilinen vakanın değil).

---

## 1. Problem (ölçülmüş, n=1 değil)

`engine/academic/report_synthesis.py:411` (`_moat_gate`) — uydurma/geri-çekilme atıf sayısına dayalı reddet-yükseltme mantığı (`fabricated+retracted>=2 → reject`) **SADECE** ilgili bulgunun (`citation_integrity`/`literature_positioning` boyutu) severity'si ZATEN `"critical"` ise devreye giriyor. Severity="major" mı "critical" mi tamamen LLM'in (writer/editor) subjektif kararı — `Finding.severity`'yi gerçek `fabricated` sayısına bağlayan hiçbir deterministik taban yok.

**61-goldset'in yerel rapor JSON'ları offline tarandı (yeniden LLM çağrısı YAPILMADAN, `goldset_live_reports_v8/*.json`):**

| paper_id | fabricated+retracted | citation_worst_severity | verdict | Gate doğru mu tetiklendi? |
|---|---|---|---|---|
| `peerread:iclr2017-400` | 2 | major | accept | ❌ HAYIR |
| `peerread:iclr2017-487` | 4 | critical | reject | ✅ EVET |
| `deneme.pdf` (koşum 1, 2026-08-15, goldset dışı) | 9 | major | accept | ❌ HAYIR |
| `deneme.pdf` (koşum 2, 2026-08-15, log-fix sonrası yeniden test) | 9 | (n/a — bu koşumda editör kendi verdict'inde major_revision dedi, moat-gate'in bu koşumda tetiklenip tetiklenmediği ayrıca doğrulanmadı) | major_revision | — |

**Bilinen 3 gerçek "count≥2" vakasından (goldset'teki 2 + deneme.pdf) 2'sinde gate hiç tetiklenmedi (~%67 başarısızlık oranı, küçük ama gerçek örneklemde).** Bu, `deneme.pdf`'e özgü bir istisna DEĞİL. Ek olarak: AYNI kanıt paketiyle (deneme.pdf, 9 uydurma atıf) 2 farklı koşumda 2 FARKLI sonuç (accept / major_revision) — hiçbiri reject — LLM-yargı-bağımlı bu yolun run-to-run TUTARSIZ olduğunu gösteriyor.

## 2. Neden şimdiye kadar bu şekildeydi (bilinçli tasarım geçmişi, kör bir hata değil)

`report_synthesis.py:436-445`'teki yorum: "major" eşiği daha önce (§30) DENENMİŞ ve KALDIRILMIŞ — 61-goldset'in %87'sinde en az 1 major-severity citation/quant bulgusu var, "major"ı tavan olarak kullanmak verdict doğruluğunu %62'den %18'e düşürüyordu (39/49 gerçek-accept makale yanlışlıkla major_revision'a düşüyordu). Yani **severity="major" genel olarak GÜRÜLTÜLÜ bir sinyal** — bu düzeltme severity="major"ı yeniden tavan yapmaya ÇALIŞMAMALI (aynı regresyona geri döner).

**Bu planın kritik tasarım ilkesi:** severity="major"a DEĞİL, `evidence.citation_integrity.fabricated+retracted` SAYISINA (deterministik, LLM'den bağımsız bir olgu) dayanan DAR bir ek tetikleyici eklemek.

**Guardian'ın 1. tur uyarısı (dil düzeltmesi):** Bunun §30 regresyonuyla "çelişmediği" iddiası **makul ama kanıtlanmış DEĞİL** — `_SYSTEMIC_FABRICATION_COUNT_THRESHOLD=2` sabitinin kendisi zaten sadece n=2 gözlemden (1 ve 4 fabricated) türetilmiş (`report_synthesis.py:354-363`'ün kendi itirafı). Base-rate argümanı (count≥2 61 makalenin ~%3.3'ünde, major-severity ise %87'sinde — istatistiksel olarak FARKLI bir karakter) makul bir savunma ama "doğrulandı" diye SUNULMAYACAK.

## 3. Önerilen düzeltme A: `_moat_gate`'i severity'den BAĞIMSIZ, count-tabanlı ikinci bir tetikleyiciyle genişletmek

**Mevcut kod (`report_synthesis.py:411-427`):**
```python
if citation_worst == "critical":
    if evidence is None:
        return ("major_revision", "...")
    count = evidence.citation_integrity.fabricated + evidence.citation_integrity.retracted
    if count >= _SYSTEMIC_FABRICATION_COUNT_THRESHOLD:
        return ("reject", f"...")
    return ("major_revision", f"...")
```

**Önerilen değişiklik (rev. 2, guardian koşuluyla):** giriş koşulunu şuna genişlet:
```python
count = (evidence.citation_integrity.fabricated + evidence.citation_integrity.retracted) if evidence is not None else 0
count_triggers = count >= _SYSTEMIC_FABRICATION_COUNT_THRESHOLD and len(citation_findings) > 0
if citation_worst == "critical" or count_triggers:
    ...
```

### 3a. Guardian'ın Finding'siz-tetikleme itirazına karşı EK KOŞUL (rev. 2'de eklendi)

**Guardian'ın bulduğu risk:** `EvidencePack.citation_integrity.fabricated`, LLM `Finding`'lerinden BAĞIMSIZ bir DOI-çözümleme motorundan geliyor (`review_citation_service.py:516-535`). Sade bir `count>=threshold` koşulu, HİÇBİR `citation_integrity`/`literature_positioning` Finding'i (yani kullanıcının görebileceği somut bir kanıt kartı) yokken de "reject" üretebilirdi — `top_fatal_risks` sadece `findings`'ten üretiliyor (`report_synthesis.py:646-650`), yani kullanıcı "reject" görür ama HANGİ referansların uydurma olduğunu gösteren bir Finding kartı GÖREMEYEBİLİRDİ.

**Çözüm:** `count_triggers` koşuluna `len(citation_findings) > 0` şartı eklendi — yani count-tabanlı tetikleyici SADECE en az 1 `citation_integrity`/`literature_positioning` Finding'i VARSA devreye girer. Bu, **gözlemlenen HER İKİ gerçek asimetri vakasında da zaten sağlanan bir koşul** (hem `peerread:iclr2017-400` hem `deneme.pdf` koşum 1'de `citation_integrity.f0` gibi somut Finding'ler VARDI, sadece severity'leri "major"dı) — yani bu ek koşul, düzeltmenin gözlemlenen vakalardaki gücünü AZALTMIYOR, sadece guardian'ın teorik (henüz gözlemlenmemiş) Finding'siz-tetikleme riskini kapatıyor.

**Neden bu, "severity floor eklemek"ten (Finding.severity'yi değiştirmek) DAHA İYİ:**
- Tek dosya, tek fonksiyon — `assessment.py`'deki dispatch/downgrade zincirine dokunmuyor.
- `Finding.severity`'nin KENDİSİ (kullanıcının finding kartında gördüğü "major" etiketi) değişmiyor — sadece `_moat_gate`'in KARAR mantığı deterministik veriyi (fabricated count) DOĞRUDAN okuyor.
- "major genel gürültülü" bulgusuyla ÇELİŞMİYOR (bkz §2) — farklı, deterministik bir sinyal + artık Finding-varlığı şartı kullanıyor.

**Testte doğrulanacak (mevcut regresyon testleri + yeni testler):**
- `count=2, severity="major", citation_findings mevcut` → artık "reject" (ÖNCEDEN: hiç tetiklenmiyordu).
- `count=2, severity="major", citation_findings BOŞ` (guardian'ın senaryosu — teorik, henüz gözlemlenmedi) → gate TETİKLENMEZ (Finding'siz-reject riski kapatıldı, davranış mevcutla AYNI kalır).
- `count=1, severity="critical"` → hâlâ "major_revision" (mevcut davranış KORUNUR — tek izole vaka sistemik sayılmaz).
- `count=0, severity="critical"` (fabrikasyon-dışı bir citation_integrity/literature_positioning critical bulgusu) → hâlâ "major_revision" (mevcut davranış KORUNUR).
- `count=4, severity="critical"` (peerread:iclr2017-487 senaryosu) → hâlâ "reject" (regresyon yok).

## 4. Fix B — ASKIYA ALINDI (kullanıcı kararı, 2026-08-15)

Önceki taslakta (rev. 1) Fix B ("editörün kendi override-öncesi verdict'i nihai karardan daha kötüyse onu al") önerilmişti. Guardian ONAYLAMADI: gerçek gözlemlenen bug (editörün YAPILANDIRILMIŞ verdict'i İLE KENDİ PROSE'u arasındaki çelişki) ile Fix B'nin çözdüğü şey (yapılandırılmış verdict İLE deterministik override arasındaki çelişki) FARKLI problemler. `deneme.pdf`'in orijinal (bug'lı) koşumunda editörün kendi verdict alanının ne dediği, log-config boşluğu yüzünden hiç kaydedilmemiş — bu veri KALICI OLARAK KAYIP (LLM `judgment_reproducible=False`, yeniden üretilemez). Log-fix sonrası YENİDEN test edildi ama bu kez editör+deterministik ZATEN eşleşti (major_revision=major_revision) — Fix B'nin orijinal bug'ı çözüp çözmeyeceği hâlâ KANITLANAMADI.

**Kullanıcı kararı: Fix B şimdilik askıya alındı, bu planın kapsamı DIŞINDA.** Ayrı bir gelecek TODO (bkz §6 madde 1).

## 5. Test planı (rev. 2 — genişletildi)

1. `report_synthesis.py` için: Fix A'nın 5 senaryosu (§3a) + mevcut `_moat_gate`/`build_executive_verdict` testleri (regresyon).
2. **61-goldset'in TAMAMI için offline önce/sonra tablosu** (yeni `_moat_gate` mantığıyla, LLM çağrısı OLMADAN, `goldset_live_reports_v8/*.json` üzerinde): her 61 makale için (eski_verdict, yeni_verdict, değişti_mi) raporlanacak — sadece 2 bilinen vakanın "değişti/değişmedi" kontrolü DEĞİL, TÜM 61 makalenin verdict'inin (varsa) hangi yönde değiştiği açıkça tablo halinde sunulacak (guardian'ın 3. madde itirazı).
3. `peerread:iclr2017-400` artık "reject" çıkarmalı; `peerread:iclr2017-487` hâlâ "reject" kalmalı (regresyon yok); geri kalan 59 makalenin HİÇBİRİNİN verdict'i değişmemeli (bunların hiçbirinde `count>=2` yok, §1'deki dağılımdan zaten biliniyor: sadece 4 makalede count>=1, sadece 2'sinde count>=2).

## 6. Kapsam dışı / ayrı TODO'lar (bu planda ÇÖZÜLMÜYOR, dürüstçe listelendi)

1. **Fix B (askıya alındı, §4)** — editörün yapılandırılmış verdict'i ile deterministik override arasındaki potansiyel tutarsızlık, ayrı bir gelecek araştırma/plan konusu.
2. Editörün kendi `_DraftReport.verdict`↔`overall_assessment` prose tutarlılığı (LLM'in TEK bir completion içindeki iç tutarsızlığı) — bu planın hiçbir parçası bunu çözmüyor, ayrı ve daha büyük bir araştırma gerektirir (keyword-tabanlı prose analizi kırılgan olur, §41b dersiyle aynı kategori).
3. `_SYSTEMIC_FABRICATION_COUNT_THRESHOLD=2`'nin kendisi hâlâ KALİBRE EDİLMEDİ — bu plan eşiği DEĞİŞTİRMİYOR, sadece eşiğe erişimi severity ön-koşulundan bağımsız hale getiriyor.

---

**Sıradaki adım:** Bu rev. 2 plan guardian'a danışılacak — Finding-varlığı koşulunun (§3a) itirazını gerçekten kapattığından ve dil/kanıt standardının (§2) yeterince dürüst olduğundan emin olmak için. Onay sonrası kod yazılacak.
