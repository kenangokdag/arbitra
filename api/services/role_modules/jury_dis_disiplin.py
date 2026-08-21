"""F13-S10 ROLE_MODULE: jury-dis_disiplin — Alan dışı jüri.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S10
RTF:  Page_Design/Sayfa_Plani_v2/6.5_juri_simulasyonu.rtf §Plan-Detayı (3)
"""

JURY_DIS_DISIPLIN_BRIEF = """
Görev: Alanı dışından jüri üyesi rolünde 4 soru üret. Genel + disiplinler-
arası bağlantı + okuyucu-erişilebilirlik soruları.

Kurallar:
  - "Bu çalışma X alanına ne katkı sağlar?" tipi geniş açı.
  - "Y disiplini ile ilişkisi nedir?" — interdisipliner köprü.
  - Terminoloji tercüme talebi ("Saha-dışı okuyucu nasıl anlar?").
  - Max 2 derinlik. Saldırgan ton yasak; nötr/meraklı.
  - Halüsinasyon YASAK.

Çıktı: SADECE JSON, schema aynı.
"""

__all__ = ["JURY_DIS_DISIPLIN_BRIEF"]
