"""F13-S5 ROLE_MODULE: draft-skeleton — Gemini Flash IMRaD 1 paragraf.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S5
RTF:  Page_Design/Sayfa_Plani_v2/5.2_yayin_taslagi.rtf §Plan-Detayı (4)

Tek section başına 1 Flash çağrı (parallel run service tarafında). Aynı brief
4 bölüm için kullanılır; promptta `section_name` injekte edilir.
"""

DRAFT_SKELETON_BRIEF = """
Görev: Seçilen konu için tek bir akademik bölümün taslağını üret. Tek paragraf
1-pass: kullanıcı sonra 5.3 (Akademik Dil) sayfasında dili düzeltir; burada
amaç içerik iskeleti + bölümün niye gerekli olduğunun açıklaması.

Bağlam (kullanıcı body'sinde sağlanır):
  - section_name: intro | methods | findings | discussion
  - topic_title: TopicProposal.title
  - topic_balanced_question: TopicProposal.sub_questions.balanced
  - method_suggestion: TopicProposal.method_suggestion
  - evidence_chain: gap_summary + method_summary + synthesis_summary
  - section_paper_hints: bölüm için havuzdan seçilmiş 3..5 paper başlığı (SQL
    bridge — intro=top-cited, methods=metod-uyum, findings=gap-relevance,
    discussion=cd_5).

Bölüm rolleri:
  - intro: problem + motivasyon + literatür boşluğu + araştırma sorusu (RQ
    önergesi balanced'dan al).
  - methods: önerilen metod (method_suggestion + section_paper_hints'tan
    benzer metod örnekleri). Algoritmik adım listesi YASAK; sadece anlatım.
  - findings: olası bulgu örüntüsü (yorum NEUTRAL — "X bulunabilir, Y
    bulunabilir" gibi; iddialı sonuç YASAK).
  - discussion: bulguların literatür/disruption haritasıyla nasıl konuşacağı
    (cd_5 yüksek paper'ları referans ver — section_paper_hints).

Kurallar:
  - draft_paragraph: 80-180 kelime, tek paragraf, akademik ton.
  - why_explanation: 1 cümle — bölümün makaledeki rolü (ör. "Bu bölüm
    okuyucuya araştırma boşluğunu konumlandırır.").
  - section_paper_hints'tan en az 1 referans örnek metin içinde geçmeli
    (yazar-yıl veya başlık kırpması yeter; tam APA gerekmez — 5.4'te
    citation kontrol var).
  - Sağlanmamış paper'a referans YASAK.

Çıktı: SADECE JSON, schema:
{
  "draft_paragraph": str,
  "why_explanation": str
}
"""

__all__ = ["DRAFT_SKELETON_BRIEF"]
