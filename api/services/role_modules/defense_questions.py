"""F13-S7 ROLE_MODULE: /api/workshop/defense/generate-questions — soru havuzu.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S7
RTF:  Page_Design/Sayfa_Plani_v2/6.2_savunma_formati.rtf §Plan-Detayı (3)

Felsefe (RTF): kişi-paper kanıt-bağlı; Stanford-style 2-derinlik zincir; juri
üyesinin gerçek çalışma alanından soru üretir; halüsinasyon yasak. Min 8 max
12 soru/jüri.
"""

DEFENSE_QUESTIONS_BRIEF = """
Görev: Tek bir jüri üyesi için Stanford-style 2-derinlik zincir SAVUNMA
soruları üret. Sorular jüri üyesinin gerçek çalışma alanından ve kullanıcının
manuscript bölümlerinden türetilmeli; bağlamsız jenerik soru YASAK.

Bağlam (kullanıcı body'sinde sağlanır):
  - Jüri üyesi: name + field + (opsiyonel) top paper title+abstract listesi
  - Kullanıcı manuscript_section 5 bölüm içeriği (intro/methods/findings/
    discussion/conclusion).
  - Yayın türü (makale/tez/yeterlilik/bildiri).
  - Dil (tr/en).

Kurallar:
  - 8-12 soru üret. Min 8, max 12 zorunlu.
  - Her soru bir KATEGORİYE bağlanmalı:
      method          → yöntem seçimi/uygunluğu/alternatifleri
      contribution    → çalışmanın özgün katkısı/önemi
      limitation      → sınırlılıklar, eksik kontroller, genelleme sorunları
      ethics          → etik kurul, veri gizliliği, çıkar çatışması
      field_specific  → jüri üyesinin alanına özgü teknik derinlik
  - depth=1 ana soru, depth=2 zincir takip sorusu. Her ana sorunun 0-2 adet
    follow_up_questions listesi olmalı (depth=1 sorunun follow_up'ı kendi
    içinde liste; depth=2 ayrı kayıt olarak çıkarsa o da OK — ikisi de geçerli).
  - source_paper_id: eğer soru jüri üyesinin spesifik bir paper'ından
    türediyse o paper'ın id'si; aksi halde null.
  - jury_member_index: kullanıcı body'sinde sağlanan değer; her sorunun bu
    indexi aynı olmalı.
  - Sorular kullanıcı diline uygun (tr/en); manuscript hangi dildeyse uyum.

Halüsinasyon yasakları:
  - Sağlanmayan paper'a referans YASAK (source_paper_id sağlanan listede
    olmalı veya null).
  - Manuscript'te olmayan iddia/sonuç temelli soru YASAK.
  - Jüri üyesinin alanında bilinmeyen teori/yöntem adı uydurma YASAK.
  - "Methodolojinizde X kullandınız mı?" (X manuscript'te yok) YASAK.

Çıktı: SADECE JSON, schema:
{
  "questions": [
    {
      "jury_member_index": int,
      "category": "method"|"contribution"|"limitation"|"ethics"|"field_specific",
      "question": str,
      "depth": 1|2,
      "source_paper_id": str|null,
      "follow_up_questions": [str, ...]
    }
  ]
}

Liste 8-12 elemanlı olmalı; aksi halde retry tetiklenir.
"""

__all__ = ["DEFENSE_QUESTIONS_BRIEF"]
