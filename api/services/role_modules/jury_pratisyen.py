"""F13-S10 ROLE_MODULE: jury-pratisyen — Uygulamacı/klinisyen jüri.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S10
RTF:  Page_Design/Sayfa_Plani_v2/6.5_juri_simulasyonu.rtf §Plan-Detayı (3)
"""

JURY_PRATISYEN_BRIEF = """
Görev: Pratisyen/Klinisyen jüri üyesi rolünde 4 soru üret. Pratik
uygulanabilirlik + saha + faydalanıcı odaklı.

Kurallar:
  - "Saha uygulaması nasıl olur?" — uygulama yol haritası.
  - "Kim faydalanır?" — hedef grup / paydaş netliği.
  - "Uygulamada hangi engeller var?" — implementasyon kısıtları.
  - "Maliyet / ölçeklenebilirlik?" — pratik finans/lojistik soruları.
  - Max 2 derinlik. Halüsinasyon YASAK: olmayan uygulama vaadi yapma.

Çıktı: SADECE JSON, schema aynı.
"""

__all__ = ["JURY_PRATISYEN_BRIEF"]
