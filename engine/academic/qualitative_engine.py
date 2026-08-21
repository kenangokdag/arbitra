"""P03-T04 — QualitativeRigorEngine (qualitative_rigor_engine_spec.md).

Nitel çalışmanın 12 rigor boyutunu TEK LLM geçişiyle değerlendirir → Finding[].
Kriter metinleri spec §"Kontrol boyutları"ndan BİREBİR aktarıldı (paraphrase yok).

Mekanizma _engine_base.assess (classifier.py deseni) ile paylaşılır; consent /
LLM-hata / sözleşme-enforce dürüstlüğü orada. Bu modül yalnız KRİTERLERİ taşır.
"""

from __future__ import annotations

from api.models.review import Manuscript
from engine.academic._engine_base import EngineResult, assess

ENGINE_VERSION = "qualitative_engine.v1"
ENGINE_NAME = "QualitativeRigorEngine"

# qualitative_rigor_engine_spec.md §"Kontrol boyutları" (satır 15-65) — BİREBİR.
QUALITATIVE_CRITERIA = """\
1. Paradigm and epistemology
   - Ontolojik/epistemolojik konum açık mı?
   - Seçilen yaklaşım araştırma sorusuyla uyumlu mu?

2. Design fit
   - Fenomenoloji, grounded theory, etnografi, vaka çalışması, söylem analizi,
     tematik analiz vb. doğru kullanılmış mı?
   - Desen adı sadece etiket mi yoksa gerekçeli mi?

3. Sampling strategy
   - Purposive/theoretical/snowball/maximum variation vb. strateji açıklanmış mı?
   - Katılımcı seçimi araştırma sorusuna uygun mu?
   - Inclusion/exclusion criteria var mı?

4. Context and thick description
   - Araştırma bağlamı yeterince tarif edilmiş mi?
   - Aktarılabilirlik için okuyucuya bağlam veriliyor mu?

5. Data collection transparency
   - Görüşme, odak grup, gözlem, doküman analizi protokolü açıklanmış mı?
   - Soru seti veya rehber yeterli mi?
   - Veri toplama süreci ve ortamı belirtilmiş mi?

6. Saturation / information power
   - Doygunluk iddiası gerekçeli mi?
   - Alternatif olarak information power mantığı açıklanmış mı?

7. Coding and analysis process
   - Kodlama adımları açık mı?
   - Koddan temaya geçiş izlenebilir mi?
   - Analiz yazılımı tek başına yöntem gibi sunuluyor mu?

8. Theme development and evidence
   - Temalar katılımcı alıntılarıyla destekli mi?
   - Alıntılar yorumun ağırlığını taşıyor mu?
   - Negative/deviant cases tartışılmış mı?

9. Reflexivity
   - Araştırmacı pozisyonu, varsayımları ve ilişkisellik tartışılmış mı?

10. Trustworthiness
   - Credibility, dependability, confirmability, transferability stratejileri var mı?
   - Triangulation, member checking, audit trail, peer debriefing, negative case
     analysis gibi uygulamalar açıklanmış mı?

11. Ethics and confidentiality
   - Etik kurul, rıza, anonimleştirme, hassas veri yönetimi var mı?

12. Claim discipline
   - Bulguların ötesinde genelleme yapılıyor mu?
   - Kausal iddia veya evrensel iddia nitel veriye aşırı mı?
"""


async def assess_qualitative(
    manuscript: Manuscript,
    *,
    allow_external_ai: bool,
) -> EngineResult:
    """Nitel rigor değerlendirmesi → Finding[] + ActionItem[] + degraded sinyalleri.

    allow_external_ai False → SIFIR LLM çağrısı + degraded (içerik dışarı gitmez).
    finding.dimension LLM'in verdiği alt-boyut (reflexivity, saturation, ...) olur
    (force_dimension yok) → rapor nitel başlıklarla gelir (spec başarı kapısı)."""
    return await assess(
        label="qualitative_engine",
        mode="qualitative_rigor",
        criteria_block=QUALITATIVE_CRITERIA,
        manuscript=manuscript,
        allow_external_ai=allow_external_ai,
        id_prefix="qual",
    )


__all__ = ["ENGINE_NAME", "ENGINE_VERSION", "QUALITATIVE_CRITERIA", "assess_qualitative"]
