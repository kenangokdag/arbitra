"""F13-S11 4.2 ROLE_MODULE: /api/workshop/gap — hücre hikayesi 3-5 cümle Flash.

Kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTF:    Page_Design/Sayfa_Plani_v2/4.2_bosluk_profili.rtf §Plan-Detayı (g)
"""

GAP_PROFILE_STORY_BRIEF = """
Sayfa: Atölye 4.2 Boşluk Profili · /api/workshop/gap hücre hikayesi
Bir gap hücresinin ham skorlarını al, "Bu boşluğa neden girmeli?" sorusuna 3-5
cümle bir akademik hikaye yaz. Ham skor değil, hikaye.

Sözleşme:
  - 3-5 cümle, ~80-150 kelime tek paragraf
  - Sözel skor yorumu: %12 büyüme, atıf hızı yüksek, kapsam derinliği düşük gibi
  - 7-boyut radar farkları + son 5 yıl trend + komşu sinyal + yayınlanabilirlik
    girdileri arasından AKILCI seçim — hepsini sıralama
  - Cümle sonu eylem önerisi: "deneysel metodla", "literatür sentezi öncesi",
    "yayın hedefi: ..." gibi somut
  - Akademik üçüncü tekil; "ben" / "biz" yok

Halüsinasyon yasakları:
  - Sağlanan skorlarda olmayan sayı, isim, yıl YASAK
  - Tema veya metod adına gerçek alan terminolojisi YAMA yapma
  - "% X arttı" gibi nicelikler ancak sağlanan trend serisinden hesaplanabilirse

Çıktı: SADECE JSON, schema: {"story": str}
"""

__all__ = ["GAP_PROFILE_STORY_BRIEF"]
