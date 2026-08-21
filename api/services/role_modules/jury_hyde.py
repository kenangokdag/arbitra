"""F13-S10 ROLE_MODULE: jury-hyde — HyDE 5 hipotetik cevap üretimi.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S10
RTF:  Page_Design/Sayfa_Plani_v2/6.5_juri_simulasyonu.rtf §Plan-Detayı (5)

HyDE (Hypothetical Document Embeddings, Gao et al. 2022): retrieval query
embed'i sentetik mükemmel cevap embed'i ile beslemek tek soru cümlesinden
daha iyi semantic match getirir.
"""

JURY_HYDE_BRIEF = """
Görev: Verilen jüri sorusu için 5 farklı hipotetik MÜKEMMEL akademik cevap
üret. Her hipotetik gerçek bir uzmanın 1-2 cümlede vereceği cevap olsun.
Bu hipotetikler bge-m3 embed'i ile literatür chunk arama (fanout) için
kullanılacak; kanıt değildir, sadece retrieval query genişletme.

Kurallar:
  - 5 hipotetik, her biri farklı bakış / yöntem / sonuç vurgusuyla.
  - Cümle uzunluğu makul (~30-100 kelime).
  - key_concepts: hipotetiklerde geçen 5-10 anahtar kavram (retrieval enrich).
  - Halüsinasyon YASAK: belirli paper/yıl/yazar uydurma — soyut + kavramsal.

Çıktı: SADECE JSON, schema:
{ "hypotheticals": [str x 5], "key_concepts": [str, ...] }
"""

__all__ = ["JURY_HYDE_BRIEF"]
