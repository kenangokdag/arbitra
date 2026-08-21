"""V1 Vitrin ROLE_MODULE: Q1 makale mini-özet (5 makale × 2 cümle).

kaynak: docs/plans/V1_vitrin_sprint.md §3 V1-02
HK-2: Brief sözleşmesi — 2 cümle, kaynak metin dışına çıkma, halüsinasyon yasak.
"""

VITRIN_SUMMARY_BRIEF = """
Sayfa: Vitrin Q1 — kullanıcı bir konu sorgusu girdi, OpenAlex'ten 5 makale geldi.

Senin işin:
  - Her makale için 2-cümleyi GEÇMEYEN mini-özet üret.
  - 1. cümle: makalenin ana iddiası / bulgusu (abstract'tan).
  - 2. cümle: yöntem veya katkı (abstract'tan).
  - SADECE verilen abstract'a dayan; uydurma yasak.
  - Kullanıcı dili Türkçeyse Türkçe yaz; başka durumda İngilizce.
  - Akademik ton; jargon abartma; emoji yok.
  - Çıktı format: düz metin, 2 cümle.
"""
