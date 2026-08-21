"""F13-S11 4.5 ROLE_MODULE: /api/workshop/impact-curve — 1-cümle kombine yorum.

Kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTF:    Page_Design/Sayfa_Plani_v2/4.5_akademik_etki_egrisi.rtf §Plan-Detayı (6)
"""

IMPACT_CURVE_COMMENT_BRIEF = """
Sayfa: Atölye 4.5 Akademik Etki Eğrisi · /api/workshop/impact-curve 1-cümle yorum
Akademik trend (slope %, son 5 yıl) + Google Trends slope (varsa) + ★ yıkıcı
sayısı + ♦ sleeping beauty sayısı verilir. Tek cümle kombine yorum.

Sözleşme:
  - 1 cümle, ~30-60 kelime
  - Akademik + popüler ikilemini açıkça kur: "akademik canlı ama kamu ilgisi
    düşük → akademik dergi odakla"; "ikisi paralel yükselen → yayın momentumu
    uygun"; "akademik söndü → konuyu değiştir"
  - Trends verisi yoksa (trends_available=false) sadece akademik üzerinden;
    "kamu ilgisi şu an alınamıyor" eki konabilir
  - ★/♦ sayısı yüksekse anekdot olarak ekle ("3 yıkıcı paper var")
  - Akademik üçüncü tekil

Halüsinasyon yasakları:
  - Sağlanan sayıların dışında iddia YASAK
  - Yıl, tema, metod adına yaratıcı yorum YASAK — verilen değişkenler üzerinden
  - "Gelecek yıl ..." tahmini YASAK (trend extrapolation V1'de yok)

Çıktı: SADECE JSON, schema: {"comment": str}
"""

__all__ = ["IMPACT_CURVE_COMMENT_BRIEF"]
