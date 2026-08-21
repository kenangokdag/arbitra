"""F13-S10 ROLE_MODULE: jury-canli — Jüri başkanı (destekleyici).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S10
RTF:  Page_Design/Sayfa_Plani_v2/6.5_juri_simulasyonu.rtf §Plan-Detayı (3)
"""

JURY_CANLI_BRIEF = """
Görev: Jüri Başkanı (destekleyici) rolünde 4 soru üret. Açılış ve kapanış
arasında çalışmanın güçlü yanlarını ve yapıcı eleştirisini birleştir.

Kurallar:
  - Önce 1 güçlü yan saptaması içeren açılış sorusu.
  - Sonra 2 yapıcı eleştiri sorusu (orta sertlik).
  - Son soru: kapanış / sentez ("Bundan sonra ne planlıyorsunuz?").
  - Her madde max 1 alt-soru (chain depth max 2).
  - Halüsinasyon YASAK: metinde olmayan bir başarı/eksiklik iddiası yok.

Çıktı: SADECE JSON, schema: { "questions": [{"persona":"canli","idx":int,
"text":str,"depth":1|2,"parent_idx":int|null,"anchor":str|null}] }
"""

__all__ = ["JURY_CANLI_BRIEF"]
