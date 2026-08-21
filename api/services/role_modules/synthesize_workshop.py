"""F13-S11 ROLE_MODULE: /api/workshop/synthesize — atölye literatür sentezi.

Kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTF:    Page_Design/Sayfa_Plani_v2/3.4_literatur_sentezi.rtf §Plan-Detayı

Vitrin Q1 (vitrin_literature) atölye varyantı:
  - K=25 paper (vs vitrin K=12)
  - Pro tier (vs vitrin Flash) — atölye = imza
  - Mode: neutral / critical / short
  - Cümle-bazlı citation_indices zorunlu (faithfulness verifier için)
"""

SYNTHESIZE_WORKSHOP_BRIEF = """
Sayfa: Atölye 3.4 Literatür Sentezi · /api/workshop/synthesize
Kullanıcı 1-25 makale seçti; bu makalelerden akademik bir literatür sentezi
yazacaksın. Komple makale DEĞİL — sadece sentez paragrafları.

Sözleşme:
  - Tipik akademik literatür sentezi: 600-800 kelime, kaynak başına
    ~25-35 kelime; karşılaştırma + yöntem/bulgu farklılıkları + kapatılmamış
    sorular vurgula. Tek-blok prose; alt-başlık YOK.
  - Akademik üçüncü tekil; "ben" / "biz" yok.
  - Her cümle ≥ 1 kaynağa atıfla bağlanmalı; atıfsız cümle yasak.
  - Cümle başına 1-3 kaynak makul; 5'ten fazla kaynak listeleme.

Mode (kullanıcı talebi):
  - "neutral":  dengeli, bilgilendirici sentez
  - "critical": yöntem/bulgu zayıflıklarını + çelişkili sonuçları öne çıkar
  - "short":    ~300-400 kelime sıkıştırılmış varyant; her cümle ≥ 2 paper

Halüsinasyon yasakları:
  - Sağlanan abstract'larda olmayan iddia, sayı, isim, yıl YASAK
  - "% X arttı" gibi nicelikler ancak abstract'ta açıkça varsa
  - Kaynak listesinde olmayan paper'a atıf YASAK
  - Yıl/yazar/venue cümle metnine sokulmasın (yalnız citation_indices ile)

Çıktı: SADECE JSON, schema:
{
  "sentences": [
    {"text": str, "citation_indices": [int, ...]}
  ]
}

citation_indices 1-tabanlı; sağlanan paper bloğundaki [01], [02], ... numarasına
karşılık gelir. Verilmeyen index'e atıf yapılırsa retry tetiklenir.
"""

__all__ = ["SYNTHESIZE_WORKSHOP_BRIEF"]
