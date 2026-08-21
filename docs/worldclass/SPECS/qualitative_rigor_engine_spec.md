# Qualitative Rigor Engine Spec

## Amaç

Nitel araştırma review’ü “örneklem az”, “genellenebilirlik düşük” gibi nicel mantık hatalarına düşmeden; paradigma, desen, bağlam, veri toplama, analiz, reflexivity ve güvenilirlik stratejilerini ayrı ayrı değerlendirmelidir.

## Trigger

Engine şu durumlarda zorunlu çalışır:

- `study_design = qualitative`
- `study_design = mixed_methods` ve qualitative component varsa
- thesis/grant içinde qualitative data collection planı varsa

## Kontrol boyutları

1. **Paradigm and epistemology**
   - Ontolojik/epistemolojik konum açık mı?
   - Seçilen yaklaşım araştırma sorusuyla uyumlu mu?

2. **Design fit**
   - Fenomenoloji, grounded theory, etnografi, vaka çalışması, söylem analizi, tematik analiz vb. doğru kullanılmış mı?
   - Desen adı sadece etiket mi yoksa gerekçeli mi?

3. **Sampling strategy**
   - Purposive/theoretical/snowball/maximum variation vb. strateji açıklanmış mı?
   - Katılımcı seçimi araştırma sorusuna uygun mu?
   - Inclusion/exclusion criteria var mı?

4. **Context and thick description**
   - Araştırma bağlamı yeterince tarif edilmiş mi?
   - Aktarılabilirlik için okuyucuya bağlam veriliyor mu?

5. **Data collection transparency**
   - Görüşme, odak grup, gözlem, doküman analizi protokolü açıklanmış mı?
   - Soru seti veya rehber yeterli mi?
   - Veri toplama süreci ve ortamı belirtilmiş mi?

6. **Saturation / information power**
   - Doygunluk iddiası gerekçeli mi?
   - Alternatif olarak information power mantığı açıklanmış mı?

7. **Coding and analysis process**
   - Kodlama adımları açık mı?
   - Koddan temaya geçiş izlenebilir mi?
   - Analiz yazılımı tek başına yöntem gibi sunuluyor mu?

8. **Theme development and evidence**
   - Temalar katılımcı alıntılarıyla destekli mi?
   - Alıntılar yorumun ağırlığını taşıyor mu?
   - Negative/deviant cases tartışılmış mı?

9. **Reflexivity**
   - Araştırmacı pozisyonu, varsayımları ve ilişkisellik tartışılmış mı?

10. **Trustworthiness**
   - Credibility, dependability, confirmability, transferability stratejileri var mı?
   - Triangulation, member checking, audit trail, peer debriefing, negative case analysis gibi uygulamalar açıklanmış mı?

11. **Ethics and confidentiality**
   - Etik kurul, rıza, anonimleştirme, hassas veri yönetimi var mı?

12. **Claim discipline**
   - Bulguların ötesinde genelleme yapılıyor mu?
   - Kausal iddia veya evrensel iddia nitel veriye aşırı mı?

## Output severity examples

Critical:

- Desen iddiası var ama veri/analiz süreci tamamen belirsiz.
- Katılımcı alıntısı yok ve tüm tema iddiaları kanıtsız.
- Etik/rıza/hassas veri açıklaması yok.

Major:

- Reflexivity yok.
- Sampling strategy gerekçesiz.
- Theme development izlenebilir değil.

Moderate:

- Doygunluk/information power zayıf açıklanmış.
- Thick description sınırlı.

Minor:

- Terminoloji tutarsız.
- Yöntem bölümünde küçük açıklık eksikleri.

## Engine prompt/output kuralı

LLM kullanılıyorsa output JSON schema ile doğrulanır. Serbest metin direkt rapora yazılmaz.

## Başarı kapısı

Bir nitel çalışma raporu en az şu başlıkları göstermelidir:

- Desen uyumu
- Örneklem ve bağlam
- Veri toplama
- Analiz/kodlama/tema üretimi
- Reflexivity
- Trustworthiness
- Etik
- Claim discipline
- P0/P1 action plan
