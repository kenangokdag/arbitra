"""F13-S5 ROLE_MODULE: topic-proposals — Gemini Pro 3 konu kartı.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S5
RTF:  Page_Design/Sayfa_Plani_v2/5.2_yayin_taslagi.rtf §Plan-Detayı (1)+(2)+(3)

Felsefe: kullanıcının önceki adımlarındaki gap + metod + sentez çıktısı promptun
parçası olur; LLM havadan konu uydurmaz. 3 kart üretilir; her kartta 3 mod
RQ stili (cautious/balanced/bold) zorunlu.
"""

TOPIC_PROPOSALS_BRIEF = """
Görev: Kullanıcının seçtiği gap hücresi + metod profili + (varsa) literatür
sentezi temelinde tam 3 adet yayın konusu önerisi üret. Hiçbir konu havadan
çıkmasın — gap_axis_x ↔ gap_axis_y bağlantısını ve sağlanan referansları
kullan.

Bağlam (kullanıcı body'sinde sağlanır):
  - gap_matrix_id: M1 (theme×method), M7 (theme×outcome) veya M8 (theme×theme).
  - gap_axis_x, gap_axis_y: hücrenin iki eksenin adları (theme veya metod id'leri).
  - method_profile: kullanıcının 3.3 profilinden gelen 0..5 metod adı.
  - synthesis_text: 3.4'ten gelen sentez metni (opsiyonel).
  - candidate_papers: havuzdan gelen 1..10 paper özeti
      (paper_id + title + year + abstract kısaltması).

Kurallar:
  - TAM 3 kart üret (min 3 max 3 zorunlu).
  - Her kartta sub_questions OBJECT'i üret: cautious / balanced / bold.
      * cautious: "X ile Y arasında ilişki var mı?" tipi temkinli soru.
      * balanced: "X, Y'yi nasıl etkiler?" tipi dengeli soru.
      * bold: "X, Y'yi anlamlı şekilde değiştirir." tipi iddialı önerme.
  - top_3_refs: sağlanan candidate_papers listesinden 1..3 paper_id seç —
    LİSTEDE OLMAYAN paper_id YASAK (halüsinasyon kontrol).
  - method_suggestion: method_profile'dan veya konuya uygun klasik bir metoddan
    1 cümle öneri.
  - evidence_chain.gap_summary: 1 cümle — bu konu hangi gap'ten doğdu.
  - evidence_chain.method_summary: 1 cümle — metod profili ile uyum.
  - evidence_chain.synthesis_summary: 1 cümle — synthesis_text varsa ondan
    alıntı; yoksa candidate_papers ortak temasından kısa özet.
  - title: kısa (5-15 kelime), bilimsel, slogan değil.

Halüsinasyon yasakları:
  - candidate_papers listesinde olmayan paper_id YASAK.
  - method_profile'da olmayan metod adı "tek doğru yol" gibi sunulamaz.
  - "Son yıllarda yapılan çalışmalar gösterdi ki..." gibi belirsiz iddialar
    YASAK — kanıt zinciri spesifik olmalı.

Çıktı: SADECE JSON, schema:
{
  "proposals": [
    {
      "title": str,
      "sub_questions": {"cautious": str, "balanced": str, "bold": str},
      "top_3_refs": [paper_id, ...],   // 1..3 paper_id
      "method_suggestion": str,
      "evidence_chain": {
        "gap_summary": str,
        "method_summary": str,
        "synthesis_summary": str
      }
    }
  ]  // TAM 3 eleman
}
"""

__all__ = ["TOPIC_PROPOSALS_BRIEF"]
