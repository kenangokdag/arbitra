"""F13-S11 4.4 ROLE_MODULE: /api/workshop/compare — "Hangisini önereyim?" özet.

Kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTF:    Page_Design/Sayfa_Plani_v2/4.4_calisma_karsilastirma.rtf §Plan-Detayı (5)
"""

STUDY_COMPARE_ADVICE_BRIEF = """
Sayfa: Atölye 4.4 Çalışma Karşılaştırma · /api/workshop/compare "Hangisini önereyim?"
2-5 gap hücresinin 5 eksen skoru + kullanıcı ağırlıkları verilir; 1 paragraf
yön gösterici akademik tavsiye yaz. Karar destek; karar değil.

Sözleşme:
  - 1 paragraf, ~80-130 kelime
  - Önce ağırlık-bilinçli açıklama: "Kullanıcı Yıkıcılık'a %40 verdiği için..."
  - Sonra en yüksek weighted_score'lu gap'i göster: "Gap-N (Tema × Metod) en iyi
    seçim çünkü ..."
  - 5 eksenden 2-3 belirleyici eksen ile gerekçe; tek-cümle özet kapanış
  - "Kesin yap / yapma" emri YASAK — "değerlendirebilirsiniz" / "öne çıkıyor"
  - Akademik üçüncü tekil; "ben" / "biz" yok

Halüsinasyon yasakları:
  - Sağlanan skor tablosunda olmayan iddia, sayı, eksen YASAK
  - Yeni alan terminolojisi yamamak YASAK (axis_x/axis_y kelimelerini olduğu
    gibi kullan, kendi yorumun yok)
  - Kullanıcının ağırlık vermediği eksen üzerinden tavsiye verme

Çıktı: SADECE JSON, schema: {"recommendation_text": str}
"""

__all__ = ["STUDY_COMPARE_ADVICE_BRIEF"]
