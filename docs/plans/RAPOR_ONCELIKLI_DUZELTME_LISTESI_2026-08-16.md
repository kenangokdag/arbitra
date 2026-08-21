# Plan: Rapor sayfasına öncelikli, aksiyona dönüştürülmüş düzeltme listesi

**Tarih:** 2026-08-16
**Durum:** UYGULANDI (Kenan onayı sonrası) — sonuçlar §5'te.
**Kaynak:** Kenan'ın bu oturumdaki isteği — "Finding/severity verisini kullanarak öncelikli, aksiyona dönüştürülmüş bir A/B/C düzeltme listesi ekleyelim."
**Kapsam kararları (Kenan, bu oturum, AskUserQuestion ile):**
1. Etiketleme: mevcut `P0/P1/P2` (yeni A/B/C taksonomisi İCAT EDİLMEYECEK).
2. Yerleşim: Katman 1 (Verdict) ile Katman 2 (risk-drill) arasında, HER ZAMAN açık.
**Karar verici:** Kenan.
**Guardian gerekmiyor** — engine/rubric/moat'a dokunmuyor, mevcut motor çıktısının (zaten var olan `action_plan`/`findings`) SADECE web sayfasında yeniden düzenlenmesi (saf sunum katmanı).

---

## 1. Araştırma sonucu (kanıtlı, A-seviye)

**Veri ZATEN var, hiç backend/engine değişikliği gerekmiyor:**
- `ReviewReport.action_plan: list[ActionItem]` (`api/models/review.py:366`) — her `ActionItem`'ın zaten `priority: P0|P1|P2` (`review.py:582`, TR etiketli + renk tokenli, `ActionItemCard.tsx:8-18`) ve `linked_finding_ids: list[str]` (`review.py:588`) alanı var.
- `Finding._enforce_high_severity_contract` (`review.py:621-635`) — severity critical/major olan HER bulgu ZATEN en az 1 action_item'a bağlı olmak ZORUNDA (şema-seviyesi zorunluluk). Yani en önemli anlarda liste boş KALAMAZ.
- `ActionItemCard.tsx` — öncelik rozeti + talimat + efor/kazanç + kabul kontrolü ile TAM tasarlanmış bir kart bileşeni ZATEN var ve kullanılıyor.

**Eksik olan SADECE sunum:** Şu an `ActionItemCard` yalnız `FindingDetail` içinde, KATMAN 2'nin risk-drill'i AÇILDIĞINDA, bulgu-bulgu dağınık gösteriliyor (`ReviewReportView.tsx:636-648`). Tek bakışta, önceliklendirilmiş, HER ZAMAN görünür bir liste yok — kullanıcı "önce ne yapmalıyım" sorusuna cevap almak için her risk satırını tek tek açmak zorunda.

## 2. Tasarım

### 2.1 Yeni bölüm: `PrioritizedActionSection`
`VerdictCockpit` içine, KATMAN 1 (`TopFatalRisks`'ten sonra) ile KATMAN 2 (`RiskDrillSection`) arasına eklenir.

Başlık: `LayerHeading` deseniyle ("Öncelikli düzeltmeler" / "Önce ne yapmalısın?").

**Veri hazırlığı** (mevcut `VerdictCockpit`'te zaten hesaplanan `findingById`/`actionById`'i reuse eder, tekrar hesaplama yok):
1. `report.action_plan`'ı `priority` alanına göre 3 grupla (P0, P1, P2).
2. Her grup içinde, bağlı bulgunun (varsa `linked_finding_ids[0]`, yoksa en düşük) severity'sine göre sırala — mevcut `SEVERITY_RANK` (`ReviewReportView.tsx:1625-1631`) reuse edilir, YENİ sıralama mantığı icat edilmiyor.
3. Boş grup (örn. hiç P2 yoksa) render edilmez.

**Render:** her action item için mevcut `ActionItemCard` OLDUĞU GİBİ reuse edilir (yeni kart tasarımı YOK — CLAUDE.md §3.5 "daha kolayı" + tutarlılık: kullanıcı aynı fix'i Katman 2'de drill açtığında da AYNI kartı görecek). Kartın altına, bağlı bulgu(ların) başlığı küçük metinle eklenir — `ReviewerCouncilSection`'daki mevcut desenle (`ReviewReportView.tsx:773-780`, `item.finding_ids.map((id) => findingById.get(id)?.title ?? id).join(" · ")`) BİREBİR aynı.

**Grup başlıkları:** `ActionItemCard.tsx`'teki `PRIORITY_LABEL`/`PRIORITY_TOKEN` sabitleri şu an dosya-özel (export edilmiyor) — bu planla `export const` yapılacak (tek satırlık değişiklik), yeni bir paralel etiket seti YAZILMAYACAK.

**Boş durum:** `action_plan.length === 0` → mevcut `EmptyNote` deseniyle ("Bu rapor için önceliklendirilmiş bir düzeltme aksiyonu işaretlenmedi.") — `TopFatalRisks`/`RiskDrillSection`'ın zaten yaptığı gibi, bölüm YİNE render edilir ama dürüst boş-durum gösterir.

**v1 rapor:** `action_plan` v2-only alan, `VerdictCockpit` zaten sadece `isV2` raporlarda çağrılıyor (`ReviewReportView.tsx:110-118`) — özel bir v1/v2 dallanması GEREKMİYOR, mimari zaten bunu hallediyor.

### 2.2 Bilinçli kabul edilen tekrar

Bir fix hem bu yeni listede hem de Katman 2'nin drill'inde (ilgili risk satırı açılınca) İKİ KEZ görünecek. Bu bir bug DEĞİL, Kenan'ın "her zaman açık + üstte" kararının doğal sonucu — plan bunu açıkça not ediyor, kod yorumunda da belirtilecek.

## 3. Test planı

`web/src/components/review/ReviewReportView.test.tsx`'e (mevcut `REPORT_V2_DEMO` fixture'ı zaten 1×P0 + 1×P1 action item içeriyor, `report-v2-demo.ts:263-286`):
1. Yeni bölüm render ediliyor, P0 grubu P1'den ÖNCE (DOM sırası).
2. Her action item'ın altında bağlı bulgunun başlığı görünüyor.
3. `action_plan: []` override edilmiş bir rapor varyantıyla → `EmptyNote` görünüyor, kart YOK.
4. Mevcut 8 testin regresyon YAŞAMADIĞI (yeni bölüm diğer testid'lerle çakışmıyor).

## 4. Kapsam dışı

1. **DOCX export'a aynı gruplamayı eklemek** — `report_export_service.py`'nin "Bulgular" bölümü şu an zaten linked action'ları finding altında gösteriyor ama P0/P1/P2 gruplu, bağımsız bir liste DEĞİL. Kenan sadece "rapor sayfasına" dedi (web), bu yüzden DOCX paritesi ayrı, küçük bir takip işi olarak not ediliyor — sessizce yapılmayacak, sessizce atlanmayacak.
2. Fix'lere tıklanınca ilgili bulgunun/risk satırının otomatik açılıp scroll edilmesi (interaktif çapraz-bağlantı) — ilk sürüm sadece METİN olarak bulgu başlığını gösterir, tıklanabilir link DEĞİL. İstenirse ayrı bir adımda eklenir.

## 5. Sonuçlar (uygulandı, 2026-08-16)

**Kod:** `ActionItemCard.tsx` (`PRIORITY_LABEL`/`PRIORITY_TOKEN` export edildi, tek satırlık değişiklik) + `ReviewReportView.tsx` (yeni `PrioritizedActionSection` + `_worstLinkedSeverity`, Katman 1 ile 2 arasına `<PrioritizedActionSection actions={actions} findingById={findingById} />` olarak bağlandı — mevcut `actions`/`findingById` değişkenleri reuse edildi, yeni state/prop-drilling yok).

**Testler:** `ReviewReportView.test.tsx`'e 2 yeni test — (1) Katman 1-2 arası her zaman açık, P0 grubu P1'den ÖNCE, bağlı bulgu başlığı görünüyor, drill kapalıyken bile (`finding-card` yokken `priority-actions` zaten dolu — "her zaman açık" doğrulandı); (2) `action_plan: []` → dürüst `EmptyNote`, kart yok.

**Regresyon:** `web/src/components/review/` altındaki TÜM testler — **35/35 PASS** (8 dosya, `ActionItemCard.test.tsx` dahil — export değişikliğinden etkilenmedi). `tsc --noEmit` temiz.
