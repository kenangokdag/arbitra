"""F13-S10 ROLE_MODULE: jury-consistency — Tutarlılık taraması Flash second-pass.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S10
RTF:  Page_Design/Sayfa_Plani_v2/6.5_juri_simulasyonu.rtf §Plan-Detayı (7)
"""

JURY_CONSISTENCY_BRIEF = """
Görev: Kullanıcının tüm soru-cevap çiftlerini incele; semantik olarak çelişen
cevap çiftlerini tespit et. Çelişki = aynı kavram için zıt iddia (örn. "Soru
1: A pozitif etki gösterdi" + "Soru 5: A etkisiz"). Üslup farkı değil; ANLAM
çelişkisi.

Kurallar:
  - Çelişki yoksa conflicts = [].
  - Her çelişki için q_idx_a, q_idx_b ve kısa conflict_text.
  - summary: tüm cevapların iç tutarlılık değerlendirmesi (1-2 cümle).
  - Halüsinasyon YASAK: olmayan çelişki uydurma.

Çıktı: SADECE JSON, schema:
{
  "conflicts": [{"q_idx_a": int, "q_idx_b": int, "conflict_text": str}],
  "summary": str
}
"""

__all__ = ["JURY_CONSISTENCY_BRIEF"]
