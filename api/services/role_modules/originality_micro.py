"""F13-S11 4.3 ROLE_MODULE: /api/workshop/originality — kart başına lazy mikro-yorum.

Kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTF:    Page_Design/Sayfa_Plani_v2/4.3_ozgunluk_degerlendirmesi.rtf §Plan-Detayı (5)

V1'de bu endpoint kart başına mikro-yorum DÖNDÜRMÜYOR (lazy load FE tarafında ayrı
çağrı yapacak — RTF "?" simgesi → tık → 1 Flash); bu brief gelecek mikro-yorum
endpoint'i ya da reuse için tutulur. Şu an originality_service mikro-yorum
çağrısı yapmıyor.
"""

ORIGINALITY_MICRO_BRIEF = """
Sayfa: Atölye 4.3 Özgünlük · per-paper "Bu paper neden ★/♦?" mikro-yorum
Bir akademik makaleyi (paper) kullanıcıya 1 cümle ile açıkla. Verilen ham
metriklerden anlam çıkar, halüsinasyon yok.

Sözleşme:
  - Tek cümle, ~25-40 kelime
  - Türü açıkça söyle: ★ Yıkıcı (Funk-Owen CD index) VEYA ♦ Sleeping Beauty
    (B-coefficient)
  - cd_5 > 0 → yıkıcı, yenilik öncesi alanın referansını silen paper
    cd_5 < 0 → konsolide edici, mevcut referansları güçlendiren paper
  - b yüksek + t_m büyük → uzun süre uyumuş, geç keşfedilen paper
  - Akademik üçüncü tekil; "ben" / "biz" / "biz öneriyoruz" yok

Halüsinasyon yasakları:
  - Sağlanan abstract'ta olmayan iddia, sayı, isim, yıl YASAK
  - Bilinmeyen alan tahmini YASAK ("muhtemelen kanser araştırması" gibi)
  - Sadece verilen ham veri + metrik üzerinden cümle kur

Çıktı: SADECE JSON, schema: {"comment": str}
"""

__all__ = ["ORIGINALITY_MICRO_BRIEF"]
