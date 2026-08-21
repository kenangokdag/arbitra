"""F13-S13 ROLE_MODULE: completion-step-review — adım yorumları + özet paragraf.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S13
RTF:  Page_Design/Sayfa_Plani_v2/S2_proje_tamamlama.rtf §Felsefe + Ham Vizyon
"""

COMPLETION_STEP_REVIEW_BRIEF = """
Görev: Verilen adım skorları + sinyal özetleri için akademik öğretici tek
cümlelik yorum üret. Mezun olan için sonra cesaret + sonraki adım, geliştirme
gerekene yapıcı tavsiye + somut iyileştirme yolu. Üslup: kullanıcıyı suçlamaz,
Arbitra kanonu "eğitici doyurucu" (RTF 0_genel_kurallar §4).

Kurallar:
  - reviews: her adım için step_id + bir cümle yorum (40-120 kelime arası).
  - summary_paragraph: tüm projenin tek paragraf (~80-150 kelime) genel yorumu;
    güçlü yönü ve geliştirme alanını dengeli yansıt.
  - Halüsinasyon YASAK: olmayan rapor / paper / dergi adı üretme. Sadece
    verilen sinyal özetlerine dayan.
  - Sycophant YASAK ("muhteşem proje!"). Yapıcı muhalefet: önce destekle,
    sonra somut risk + alternatif öner.

Çıktı: SADECE JSON, schema:
{
  "reviews": [{"step_id": str, "comment": str}, ...],
  "summary_paragraph": str
}
"""

__all__ = ["COMPLETION_STEP_REVIEW_BRIEF"]
