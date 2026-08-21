"""F13-S6 ROLE_MODULE: /api/workshop/manuscript/auto-draft — 1 paragraf taslak.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S6
RTF:  Page_Design/Sayfa_Plani_v2/6.1_yayin_icerigi_doldurma.rtf §Plan-Detayı (4)

Felsefe (RTF): boş bölümde "AI ile taslak üret" butonu — Gemini Flash önceki
adım çıktılarını (3.4 sentez, 3.3 metod, 4.4 gap, 4.5 etki, 5.1 özet) tek
paragraf akademik taslağa çevirir. Otomatik kayıt YOK; kullanıcı kabul ederse
PUT /manuscript/{section_type} ile yazar.
"""

MANUSCRIPT_AUTO_DRAFT_BRIEF = """
Görev: Akademik makalenin tek bölümü için 1 paragraf TASLAK üret. Bu metin
manuscript_section.content olarak değil, kullanıcıya öneri olarak dönecek;
kullanıcı kabul ederse kendisi kaydedecek.

Sözleşme:
  - 80-180 kelime; tek paragraf; alt-başlık YOK.
  - Akademik üçüncü tekil; "ben" / "biz" yok.
  - SADECE sağlanan "Önceki adım çıktıları" bloğunda yazılana dayan; başka
    iddia ekleme. Sayı, isim, atıf YASAK (kullanıcı 5.4'te ekler).
  - Bölüm tipine göre ton:
      intro       → çalışmanın motivasyonu + boşluğu (gap) çerçeveler.
      methods     → yöntem yaklaşımının nedeni; spesifik teknik detay yok.
      findings    → bulgu yorumu (önceki "etki eğrisi" yorumuna sadık).
      discussion  → bulguları gap kararına bağlar; sınırlılıklara değin.
      conclusion  → çalışma katkısı + ileri araştırma önerisi.

Halüsinasyon yasakları:
  - Sağlanmayan istatistik/yıl/yazar/metod adı YASAK.
  - Önceki adım çıktısı boşsa: "Önceki adımlardan yeterli içerik yok; lütfen
    bu bölümü manuel doldurun." cümlesi tek başına dönsün (placeholder
    halüsinasyon yerine itiraf).
  - Lorem ipsum, demo metin, sahte örnek YASAK — quality-check kırmızı görür.

Çıktı: düz metin (1 paragraf). JSON, kod bloku, prefix/suffix YOK.
"""

__all__ = ["MANUSCRIPT_AUTO_DRAFT_BRIEF"]
