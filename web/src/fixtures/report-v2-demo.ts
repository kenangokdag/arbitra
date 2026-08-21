// Arbitra v2 — GÜVENLİ demo raporu (yapısal fixture).
// Gerçek kullanıcı verisi YOK; uydurma kurgusal bir el yazması üzerinden v2
// alanlarını (executive_verdict / findings / risk_radar / reviewer_council /
// action_plan / section_reviews / disclosure) doldurur. Backend sözleşmesi:
// critical/major bulgular action_item_ids + manuscript_anchors taşımak ZORUNDA.
// review-api.ts ReviewReport tipine karşı tip-kontrollüdür.

import type { ReviewReport } from "@/lib/review-api";

export const REPORT_V2_DEMO: ReviewReport = {
  mode: "author",
  language: "tr",
  manuscript_meta: {
    title: "Uzaktan Çalışma ve Ekip Üretkenliği: Karma Yöntemli Bir İnceleme",
    abstract:
      "Bu kurgusal çalışma, uzaktan çalışma düzeninin ekip üretkenliği üzerindeki etkisini karma yöntemle inceler.",
    language: "tr",
    section_titles: ["Giriş", "Yöntem", "Bulgular", "Tartışma"],
    word_count: 7200,
    reference_count: 41,
    parse_confidence: 0.94,
    parse_warnings: [],
  },
  summary:
    "Çalışma güçlü bir araştırma sorusu sunuyor; ancak örneklem gerekçesi ve birkaç atıf desteği güçlendirilmeli.",
  strengths: [
    { category: "Özgünlük", points: ["Güncel ve alana değerli bir soru."] },
  ],
  weaknesses: [
    { category: "Yöntem", points: ["Örneklem büyüklüğü gerekçesi eksik."] },
  ],
  detailed_comments: [
    { area: "Yöntem", comment: "Güç analizi raporlanmamış.", evidence_ref: null },
  ],
  questions: ["Örneklem büyüklüğü nasıl belirlendi?"],
  overall_assessment:
    "Sağlam temelli ancak yöntem şeffaflığı ve atıf desteği açısından revizyon gerektiren bir çalışma.",
  verdict: "major_revision",
  dimension_scores: [
    { key: "soundness", score: 6.2, rationale: "Güç analizi ve örneklem gerekçesi eksik." },
    { key: "citation_integrity", score: 7.1, rationale: "Bir iddia için atıf desteği zayıf." },
  ],
  final_score: 6.6,
  evidence_pack: {
    citation_integrity: {
      total: 41,
      resolved: 38,
      not_found_in_index: 2,
      fabricated: 0,
      retracted: 1,
    },
    // G5 — referans tablosu artık uzman katmanında render edilir. Demo için
    // temsilî birkaç kayıt (gerçek raporda tüm 41 kaynak listelenir): biri
    // doğrulanmış, biri geri çekilmiş, biri indekste bulunamadı.
    references: [
      {
        index: 12,
        raw: "Doe, J., & Roe, A. (2019). Remote work and team output. Journal of Org. Behavior, 40(3), 221-240.",
        title: "Remote work and team output",
        authors: ["Doe, J.", "Roe, A."],
        year: 2019,
        doi: "10.1000/jorgbeh.2019.221",
        venue: "Journal of Organizational Behavior",
        parse_confidence: 0.96,
        status: "resolved",
        openalex_id: "W2100000001",
        is_retracted: false,
        evidence: null,
      },
      {
        index: 27,
        raw: "Smith, K. (2016). Distributed teams: a meta-analysis. Mgmt Science, 62(8), 1100-1119.",
        title: "Distributed teams: a meta-analysis",
        authors: ["Smith, K."],
        year: 2016,
        doi: "10.1000/mgmtsci.2016.1100",
        venue: "Management Science",
        parse_confidence: 0.91,
        status: "retracted",
        openalex_id: "W2100000002",
        is_retracted: true,
        evidence: "Retraction Watch kaydı: veri bütünlüğü sorunu (2021).",
      },
      {
        index: 33,
        raw: "Yılmaz, B. (2020). Uzaktan ekiplerde güven. Yayımlanmamış çalışma notu.",
        title: "Uzaktan ekiplerde güven",
        authors: ["Yılmaz, B."],
        year: 2020,
        doi: null,
        venue: null,
        parse_confidence: 0.74,
        status: "not_found_in_index",
        openalex_id: null,
        is_retracted: false,
        evidence: null,
      },
    ],
    context_findings: [
      {
        ref_index: 12,
        claim:
          "Önceki çalışmalar müdahalenin etkisini tutarlı biçimde doğrulamıştır.",
        support: "supported",
        support_level: "abstract_only",
        evidence: "Kaynağın özeti iddiayı destekler yönde; tam metin doğrulaması yapılmadı.",
        cited_abstract_excerpt:
          "The intervention produced a statistically significant improvement across cohorts...",
      },
    ],
    coverage_gaps: [],
    stat_findings: [],
  },
  provenance: {
    model_used: "demo-fixture",
    persona_version: "demo",
    engine_version: "review_report.v2-demo",
    generated_at: "2026-01-01T00:00:00Z",
    deterministic_engine: true,
    judgment_reproducible: true,
  },
  ethics_notice: null,
  editor_digest: null,

  // --- worldclass v2 alanları ---
  schema_version: "review_report.v2",
  document_classification: {
    document_type: "journal_article",
    document_type_confidence: 0.9,
    study_design: "mixed_methods",
    study_design_confidence: 0.82,
    rationale: "Hem nicel anket hem nitel görüşme verisi raporlanmış.",
    user_document_type_override: null,
    user_study_design_override: null,
  },
  executive_verdict: {
    overall_readiness_score: 66,
    recommended_decision: "major_revision",
    confidence: 0.78,
    top_fatal_risks: [
      "Örneklem büyüklüğü gerekçesi ve güç analizi eksik.",
      "Merkezi bir nedensellik iddiası için atıf desteği yetersiz.",
    ],
    one_sentence_diagnosis:
      "Değerli bir soru, ancak yöntem şeffaflığı ve atıf desteği güçlendirilmeden yayına hazır değil.",
  },
  risk_radar: [
    {
      dimension: "soundness",
      score: 62,
      severity: "critical",
      confidence: 0.8,
      why_it_matters: "Güç analizi olmadan etkinin gerçekliği değerlendirilemez.",
    },
    {
      dimension: "citation_integrity",
      score: 71,
      severity: "major",
      confidence: 0.74,
      why_it_matters: "Desteklenmeyen iddia, sonuçların güvenilirliğini zayıflatır.",
    },
    {
      dimension: "clarity",
      score: 83,
      severity: "moderate",
      confidence: 0.7,
      why_it_matters: "Bulgular bölümü yoğun; okunabilirlik iyileştirilebilir.",
    },
    {
      dimension: "originality",
      score: 88,
      severity: "minor",
      confidence: 0.66,
      why_it_matters: "Katkı net; küçük konumlandırma rötuşu yeterli.",
    },
  ],
  reviewer_council: [
    {
      role: "methodologist",
      stance: "Koşullu kabul",
      summary: "Tasarım uygun ancak güç analizi ve örneklem gerekçesi raporlanmalı.",
      key_objection: "Güç analizi yok.",
      confidence: 0.8,
      finding_ids: ["F-001"],
    },
    {
      role: "citation_auditor",
      stance: "Revizyon gerekli",
      summary: "Bir merkezi iddia yalnızca özetten desteklenmiş; tam metin doğrulaması gerek.",
      key_objection: "Atıf desteği zayıf.",
      confidence: 0.72,
      finding_ids: ["F-002"],
    },
    {
      role: "constructive_reviewer",
      stance: "Olumlu",
      summary: "Soru değerli; bulgular bölümünün yapısı sadeleştirilebilir.",
      key_objection: null,
      confidence: 0.68,
      finding_ids: ["F-003"],
    },
  ],
  findings: [
    {
      finding_id: "F-001",
      dimension: "soundness",
      severity: "critical",
      confidence: 0.8,
      title: "Güç analizi ve örneklem gerekçesi eksik",
      summary:
        "Yöntem bölümünde örneklem büyüklüğünün nasıl belirlendiği ve güç analizi raporlanmamış.",
      manuscript_anchors: [
        { anchor_id: "A-001", section: "Yöntem", quote: "Toplam 84 katılımcı çalışmaya dahil edildi." },
      ],
      reasoning_public: "Güç analizi olmadan etki büyüklüğünün anlamlılığı yorumlanamaz.",
      limitations: ["Yalnızca raporlanan metne dayalı değerlendirme."],
      action_item_ids: ["AI-001"],
      global_issue: false,
    },
    {
      finding_id: "F-002",
      dimension: "citation_integrity",
      severity: "major",
      confidence: 0.74,
      title: "Merkezi iddia için atıf desteği yetersiz",
      summary:
        "Uzaktan çalışmanın üretkenliği artırdığı iddiası yalnızca bir kaynağın özetiyle destekleniyor.",
      manuscript_anchors: [
        { anchor_id: "A-002", section: "Tartışma", quote: "Uzaktan çalışma üretkenliği belirgin biçimde artırır." },
      ],
      reasoning_public: "Tek ve yalnızca özetten doğrulanan kaynak, güçlü bir iddiayı taşıyamaz.",
      limitations: [],
      action_item_ids: ["AI-002"],
      global_issue: false,
    },
    {
      finding_id: "F-003",
      dimension: "clarity",
      severity: "moderate",
      confidence: 0.7,
      title: "Bulgular bölümü yoğun",
      summary: "Bulgular bölümünde tablo ve metin tekrarı okunabilirliği düşürüyor.",
      manuscript_anchors: [],
      reasoning_public: null,
      limitations: [],
      action_item_ids: [],
      global_issue: false,
    },
    {
      finding_id: "F-004",
      dimension: "originality",
      severity: "minor",
      confidence: 0.66,
      title: "Katkı konumlandırması güçlendirilebilir",
      summary: "Giriş, çalışmanın literatürdeki boşluğa katkısını biraz daha net vurgulayabilir.",
      manuscript_anchors: [],
      reasoning_public: null,
      limitations: [],
      action_item_ids: [],
      global_issue: false,
    },
  ],
  action_plan: [
    {
      action_id: "AI-001",
      priority: "P0",
      effort: "medium",
      expected_gain: "high",
      target_section: "Yöntem",
      instruction:
        "Örneklem büyüklüğünün nasıl belirlendiğini açıklayın ve bir güç analizi (etki büyüklüğü, alfa, güç) raporlayın.",
      acceptance_check: "Yöntem bölümünde güç analizi parametreleri ve örneklem gerekçesi yer alıyor.",
      linked_finding_ids: ["F-001"],
    },
    {
      action_id: "AI-002",
      priority: "P1",
      effort: "low",
      expected_gain: "medium",
      target_section: "Tartışma",
      instruction:
        "Merkezi nedensellik iddiasını, tam metni doğrulanmış en az iki bağımsız kaynakla destekleyin veya iddiayı yumuşatın.",
      acceptance_check: "İddia, tam metin doğrulamalı kaynaklarla destekleniyor ya da uygun şekilde sınırlandırılmış.",
      linked_finding_ids: ["F-002"],
    },
  ],
  section_reviews: [
    {
      section: "Yöntem",
      status: "weak",
      what_works: "Veri toplama prosedürü açık.",
      what_breaks: "Örneklem gerekçesi ve güç analizi eksik.",
      anchor_ids: ["A-001"],
      action_item_ids: ["AI-001"],
    },
    {
      section: "Tartışma",
      status: "weak",
      what_works: "Bulgular literatürle ilişkilendirilmiş.",
      what_breaks: "Bir iddia yeterince desteklenmemiş.",
      anchor_ids: ["A-002"],
      action_item_ids: ["AI-002"],
    },
    {
      section: "Giriş",
      status: "ok",
      what_works: "Araştırma sorusu net ve değerli.",
      what_breaks: null,
      anchor_ids: [],
      action_item_ids: [],
    },
  ],
  disclosure: {
    external_ai_used: false,
    providers: [],
    confidentiality_mode: "author_owned",
    degraded_due_to_consent: false,
    note: "Bu demo rapor harici yapay zekâ kullanmadan üretilmiş bir örnektir.",
  },
};
