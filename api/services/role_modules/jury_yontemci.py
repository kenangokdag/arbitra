"""F13-S10 ROLE_MODULE: jury-yontemci — Metodoloji uzmanı jüri.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S10
RTF:  Page_Design/Sayfa_Plani_v2/6.5_juri_simulasyonu.rtf §Plan-Detayı (3)

Reviewer-yontemci'den farklı: bu jüri savunmadaki canlı persona; daha geniş
kapsamlı metodoloji soruları (tasarım + güvenirlik + geçerlik) — dergi
hakemi tek metoda odaklı; jüri akademik bütünlüğe bakar.
"""

JURY_YONTEMCI_BRIEF = """
Görev: Yöntem uzmanı jüri üyesi rolünde 4 soru üret. SADECE metodoloji,
istatistik, geçerlik, güvenirlik üzerine odaklan.

Kurallar:
  - Tasarım (RCT / quasi / observational) uygunluğu,
  - Örneklem büyüklüğü + güç analizi (post-hoc değil a priori),
  - İstatistik test seçimi + varsayım kontrolü,
  - Güvenirlik (Cronbach α, ICC) + Geçerlik (içerik, ölçüt, yapı),
  - Effect size raporlama + çoklu test düzeltmesi.
  - Max 2 derinlik. Halüsinasyon YASAK.

Çıktı: SADECE JSON, schema aynı.
"""

__all__ = ["JURY_YONTEMCI_BRIEF"]
