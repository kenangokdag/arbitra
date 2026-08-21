# DESIGN-DECISIONS — Arbitra Review Cockpit

> **Anti-toolbox kapısı (DESIGN-LANGUAGE §0.5).** Bu 5 cevap FE kodundan ÖNCE kilitlendi (Omer onayı: plan
> PLAN_REVIEW_COCKPIT.md). `frontend-excellence-audit` FAZ 0.5 bunu denetler. Kimlik kopyalanmaz, türetilir (§0.6).
> **Not (§0.6 katman ayrımı):** Renk/tipografi = admin-konfigüre (platform kararı ertelendi); bu doküman
> ürünün **YAPISINI ve RUHUNU** kilitler — renkten bağımsız. İmza, palette değil etkileşimde.

---

## 1. RUH (tek cümle)
**"Sertçe ama dürüstçe hakemlendin — ve kabul için tam olarak ne yapacağını biliyorsun."**

Duygu: adil-katı bir hakem masası. Her yargı (a) senin metnindeki bir cümleye ve (b) bir kritere dayalı;
hiçbiri keyfi değil, hiçbiri saklı değil. Belirsizlik gizlenmez, açıkça işaretlenir — güven buradan doğar.
"Verimi yöneten araç" değil; "kararını savunabileceğin laboratuvar."

## 2. EKRANIN TEK İŞİ
**Verdict.** Tek soru: "Paperim hazır mı, ve bu yargı güvenilir mi?"
- En iri, en üstte: `executive_verdict.recommended_decision` + `one_sentence_diagnosis` + `top_fatal_risks`.
- `overall_readiness_score` (0-100) teşhisin ALTINDA — yargının kanıtı, dekoratif büyük-sayı DEĞİL.
- Diğer her şey buradan drill ile açılır. İki eşit-ağırlıklı iş yok → ekran bölünmez, omurga tek.

## 3. İMZA ANI (kopyalanamaz tek öğe)
**Kanıt çıpası.** Herhangi bir eleştiriye/bulguya tıkla → tek hamlede üçü yan yana:
1. Senin makalendeki **tam cümle** (`Finding.manuscript_anchors[].quote`, AnchorDrawer'da metin bağlamıyla),
2. **Neden** eleştirildi (`Finding.reasoning_public` + `dimension` = kriter),
3. **Fix** (`Finding.action_item_ids` → `ActionItem.instruction` + `acceptance_check`).

Rakipler (SciSpace/Elicit/Scite) yargıyı metne dürüstçe çıpalamaz. "Model böyle dedi" değil — "şu cümlen,
şu kriterde zayıf, kabul için şöyle düzelt." Cesaret yalnız burada harcanır; gerisi sessiz enstrüman.
Doğrulanmamış çıpa açıkça "UNVERIFIED" işaretlenir (`anchoring.py` limitation) — sahte güven yok.

## 4. REDDEDİLEN 3 JENERİK (açık beyan)
1. ❌ **18-bölüm dikey scroll dökümü** (mevcut `ReviewReportView.tsx`) → ✅ verdict-önce kokpit + 3 katmanlı
   aşamalı drill. Sebep: her şeyi aynı düzleme koymak = duvar = toolbox.
2. ❌ **Üstte büyük-sayı istatistik bandı** (readiness 87! · güven 92! · 14 bulgu!) → ✅ skor, tek-cümle teşhisin
   ve kararın altında bağlam içinde. Sebep: sayı yargının kanıtıdır, dekor değil.
3. ❌ **Eşit-ağırlıklı 6-kutu "boyut" kart-gridi** → ✅ editöryal argüman: verdict (iddia) → risk (severity-sıralı)
   → kanıt (çıpalı) → fix. Sebep: "aynı brief'i alan herhangi bir model 6-kutu grid üretir" → revize.

## 5. GİZLENEN KARMAŞA (aşamalı açığa çıkarma — 3 katman)
| Katman | Ne görünür | Gerçek alan |
|---|---|---|
| **1 — İlk açılış** | Verdict + tek-cümle teşhis + hazırlık skoru + 3 ölümcül risk + önerilen karar | `executive_verdict.*` |
| **2 — Talep üzerine (drill/drawer)** | Risk → bağlı bulgular → makalendeki çıpalı alıntı → neden → fix + kabul ölçütü | `risk_radar` → `findings` → `manuscript_anchors` → `action_plan` |
| **3 — Uzman katmanı (en alt, collapse)** | Reviewer council, atıf bütünlüğü tablosu, references, kapsam boşlukları, statcheck, provenance mührü, disclosure | `reviewer_council`, `evidence_pack.*`, `provenance`, `disclosure` |

## 6. EDİTÖRYAL OMURGA
Her ekran bir argüman kurar: **başlık (verdict/iddia) → kanıt (çıpalı bulgular, katmanlı) → künye
(provenance/disclosure/savunma).** Gazete sayfası gibi okunur, kontrol paneli gibi değil. Göz sırası:
verdict → ölümcül risk → drill kanıt → uzman katman. Bu sırayı tipografi + boşluk + tek-aksan taşır (renk değil).

## 7. DÜRÜSTLÜK KATMANI (özgün odak — saklamadığımız şey)
`confidence`, `limitations`, "doğrulayamadık", `degraded_features`, `judgment_reproducible=False`, çıpa-UNVERIFIED
işaretleri → hepsi kullanıcıya GÖRÜNÜR. Rakip belirsizliği saklar; biz açıkça gösteririz. Bu, "ne vereceğiz"in
çekirdeği: yargıyı + onun ne kadar güvenilir olduğunu birlikte veririz.
