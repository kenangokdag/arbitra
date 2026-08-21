"""P03 — DimensionEngine (general academic): metodoloji-DIŞI rubrik boyutları.

QualitativeRigorEngine / QuantitativeValidityEngine'e YÖNLENMEYEN her rubrik boyutunu
(contribution, literature, theory, ethics, structure, citation, venue_fit, ...) TEK
boyut başına bir LLM geçişiyle değerlendirir → Finding[]. Böylece HER rubrik boyutu
bulgu üretir (academic_engine_spec.md §"Belge türüne göre temel rubrik" → tam kapsam).

v1 VARSAYIM (Omer bilimsel audit): academic_engine_spec yalnız boyut ETİKETLERİNİ
verir (qual/quant spec'lerinin aksine ayrıntılı kriter listesi YOK). Aşağıdaki niyet
metinleri bu etiketlerin sadık AÇILIMIDIR — yeni kriter/eşik UYDURULMADI, etiket
akademik hakemlik anlamına genişletildi. Bilinmeyen boyut id'si → etiketten türetilen
dürüst genel niyet (sessiz boşluk yok).
"""

from __future__ import annotations

from api.models.review import Manuscript
from engine.academic._engine_base import EngineResult, assess

ENGINE_VERSION = "dimension_engine.v1"

# rubric_registry.py tablolarındaki metodoloji-DIŞI boyut id'leri → değerlendirme niyeti.
# (Etiketler academic_engine_spec.md satır 93-145; niyet = etiketin sadık açılımı.)
_DIMENSION_INTENT: dict[str, str] = {
    # --- katkı / iddia ailesi (ClaimEvidenceAlignmentEngine) ---
    "contribution_originality": "Çalışmanın katkısı ve özgünlüğü açık mı? Alana ne ekliyor, "
    "mevcut işten farkı somut mu, yoksa artımsal/tekrar mı?",
    "research_question_fit": "Araştırma sorusu net mi ve çalışmanın tasarımı/kapsamıyla "
    "uyumlu mu? Soru cevaplanabilir biçimde tanımlanmış mı?",
    "theoretical_framing": "Teorik çerçeve var mı, soruyla ve yöntemle tutarlı mı, yoksa "
    "süs olarak mı kullanılmış?",
    "claim_evidence_alignment": "Yapılan iddialar sunulan kanıtla (veri/analiz) orantılı mı? "
    "Aşırı genelleme veya kanıtsız iddia var mı?",
    "novelty_to_length_ratio": "Bildirinin yeniliği uzunluğuna/kapsamına değer mi? Katkı "
    "sayfa bütçesini hak ediyor mu?",
    "contribution_clarity": "Katkı açıkça ifade edilmiş mi; okuyucu 'yeni olan ne' sorusuna "
    "net cevap bulabiliyor mu?",
    "problem_statement": "Problem net, gerekçeli ve önemli olarak ortaya konmuş mu?",
    "research_questions_hypotheses": "Araştırma soruları/hipotezleri açık, test edilebilir "
    "ve problemle bağlantılı mı?",
    "theoretical_framework": "Teorik çerçeve derinlikli, tutarlı ve çalışmayı yönlendiriyor mu?",
    "original_contribution": "Tezin özgün katkısı tanımlı ve savunulabilir mi?",
    "publication_potential": "Çalışma hakemli yayına dönüşebilir mi; hangi düzey dergi/konferans?",
    "problem_significance": "Ele alınan problem önemli ve fonlanmayı/araştırmayı hak ediyor mu?",
    "objectives": "Amaçlar açık, ölçülebilir ve problemle hizalı mı?",
    "risk_mitigation": "Riskler tanımlanmış ve azaltma planı gerçekçi mi?",
    "impact_pathway": "Etki yolu (sonuçtan faydaya) inandırıcı ve izlenebilir mi?",
    # --- literatür / atıf ailesi (CitationIntegrityEngine) ---
    "literature_positioning": "İlgili literatür yeterince taranmış ve çalışma bu literatüre "
    "doğru konumlandırılmış mı? Kritik eksik kaynak var mı?",
    "citation_integrity": "Atıflar doğru, yerinde ve iddiaları gerçekten destekliyor mu? "
    "(Deterministik atıf motoru bulgularını tamamlayan niteliksel yorum.)",
    "literature_depth": "Literatür taraması tez düzeyinde derin, güncel ve eleştirel mi?",
    # --- etik / tekrar-üretilebilirlik ailesi (EthicsTransparencyEngine) ---
    "ethics_reproducibility": "Etik onay, rıza, veri/kod paylaşımı ve tekrar-üretilebilirlik "
    "koşulları açıklanmış mı?",
    "reproducibility_artifact": "Tekrar-üretim için artefakt (kod/veri/ek malzeme) sağlanmış "
    "ve erişilebilir mi?",
    "ethics_limitations": "Etik konular ve çalışmanın sınırlılıkları dürüstçe tartışılmış mı?",
    "ethics_data_management": "Etik ve veri yönetimi planı (saklama, paylaşım, gizlilik) "
    "yeterli mi?",
    # --- yapı / sunum / uygunluk ailesi (StructureClarityEngine) ---
    "writing_structure": "Makale yapısı ve yazımı net mi; bölümler mantıklı akıyor, dil "
    "anlaşılır mı?",
    "venue_fit": "Çalışma hedef dergi/mekânın kapsamına ve düzeyine uygun mu?",
    "track_fit": "Bildiri hedef track/oturumun konusuna uygun mu?",
    "presentation_clarity": "Sunum (şekiller, tablolar, akış) açık ve anlaşılır mı?",
    "reviewer_confidence": "Hakem olarak değerlendirmeye ne kadar güvenebilirsin; eksik "
    "bilgi nedeniyle belirsizlik var mı?",
    "chapter_coherence": "Tez bölümleri birbiriyle tutarlı ve bütünlüklü mü?",
    "defense_readiness": "Tez savunmaya hazır mı; zayıf noktalar savunulabilir durumda mı?",
    "committee_question_risk": "Jürinin zorlayacağı muhtemel sorular/açıklar neler?",
    "work_packages": "İş paketleri net tanımlı, birbirine bağlı ve amaçları kapsıyor mu?",
    "team_competence": "Ekip yetkinliği önerilen işi yürütmeye uygun mu?",
    "timeline_realism": "Zaman planı gerçekçi mi; iş paketleriyle tutarlı mı?",
    "budget_coherence": "Bütçe iş paketleri ve amaçlarla tutarlı ve gerekçeli mi?",
    "dissemination": "Yaygınlaştırma/iletişim planı uygun ve hedef kitleye ulaşıyor mu?",
    "sustainability": "Sonuçların sürdürülebilirliği/ devamlılığı planlanmış mı?",
    # --- raporlama kılavuzu (ReportingGuidelineSelector) ---
    "reporting_guideline_compliance": "Çalışma türüne uygun raporlama kılavuzuna (CONSORT/"
    "PRISMA/STROBE/COREQ vb.) uyum belirtileri var mı; eksik raporlanan zorunlu öğe var mı?",
}


def _humanize(dim_id: str) -> str:
    """Bilinmeyen boyut id'si için dürüst genel niyet (etiketten türetilir)."""
    label = dim_id.replace("_", " ").strip()
    return (
        f"'{label}' boyutunu akademik hakem gözüyle değerlendir: bu yönden makalenin "
        "güçlü/zayıf yanları nedir, somut kanıta bağla."
    )


def intent_for(dim_id: str) -> str:
    """Boyut id'si → değerlendirme niyet metni (bilinmeyen → dürüst genel niyet)."""
    return _DIMENSION_INTENT.get(dim_id, _humanize(dim_id))


async def assess_dimension(
    dimension_id: str,
    manuscript: Manuscript,
    *,
    allow_external_ai: bool,
    evidence_context: str | None = None,
) -> EngineResult:
    """Tek bir (metodoloji-dışı) rubrik boyutunu değerlendir → Finding[].

    finding.dimension = dimension_id (force_dimension) → her rubrik boyutu kendi
    başlığıyla bulgu üretir (tam kapsam). allow_external_ai False → SIFIR LLM + degraded.

    evidence_context: doluysa (2026-08-08 — bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md §32)
    `_build_prompt()` tarafından "ÖNCEDEN HESAPLANMIŞ DETERMİNİSTİK KANIT" bloğu olarak
    prompt'a eklenir. Çağıran (assessment.py) SADECE CitationIntegrityEngine'e yönlenen
    boyutlar (citation_integrity/literature_positioning/literature_depth) için doldurur —
    diğer boyutlarda (ethics/writing/venue_fit vb.) EvidencePack'in ilgili olgusu yok,
    None kalır (bkz. assessment.py CITATION_ENGINE dispatch mantığı)."""
    criteria_block = f"BOYUT: {dimension_id}\nNİYET: {intent_for(dimension_id)}"
    return await assess(
        label=f"dimension_engine:{dimension_id}",
        mode="academic_dimension",
        criteria_block=criteria_block,
        manuscript=manuscript,
        allow_external_ai=allow_external_ai,
        id_prefix=dimension_id,
        force_dimension=dimension_id,
        evidence_context=evidence_context,
    )


__all__ = ["ENGINE_VERSION", "assess_dimension", "intent_for"]
