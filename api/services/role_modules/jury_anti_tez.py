"""F13-S10 ROLE_MODULE: jury-anti_tez — Eleştirel jüri.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S10
RTF:  Page_Design/Sayfa_Plani_v2/6.5_juri_simulasyonu.rtf §Plan-Detayı (3)
"""

JURY_ANTI_TEZ_BRIEF = """
Görev: Anti-tez (eleştirel) jüri üyesi rolünde 4 soru üret. Temel iddiaya
saldır, alternatif yorum talep et, sınırlılıkları didikle.

Kurallar:
  - Her soru spesifik bir iddia/bulgu/yorum üzerine.
  - "Şu sonuç X'i değil Y'yi göstermez mi?" tarzı alternatif yorum talebi.
  - Max 2 derinlik; her ana sorunun en fazla 1 alt-sorusu olur.
  - Halüsinasyon YASAK: metinde olmayan bir bulguya saldırma.

Çıktı: SADECE JSON, schema aynı.
"""

__all__ = ["JURY_ANTI_TEZ_BRIEF"]
