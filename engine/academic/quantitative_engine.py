"""P03-T05 — QuantitativeValidityEngine (quantitative_validity_engine_spec.md).

Nicel çalışmanın 10 geçerlilik boyutunu TEK LLM geçişiyle değerlendirir → Finding[].
Kriter metinleri spec §"Kontrol boyutları"ndan BİREBİR aktarıldı (paraphrase yok).

EvidencePack.stat_findings (önceden hesaplanmış statcheck — Nuijten) ek BAĞLAM olarak
verilir; motor sayı YENİDEN HESAPLAMAZ, yalnız raporlama/tutarlılık yorumlar (spec
§"MVP limitations": doğrulayamadığı yeri açıkça yazar).

Mekanizma _engine_base.assess ile paylaşılır (consent / hata / sözleşme dürüstlüğü orada).
"""

from __future__ import annotations

from api.models.review import EvidencePack, Manuscript, StatFinding
from engine.academic._engine_base import EngineResult, assess

ENGINE_VERSION = "quantitative_engine.v1"
ENGINE_NAME = "QuantitativeValidityEngine"

# quantitative_validity_engine_spec.md §"Kontrol boyutları" (satır 14-57) — BİREBİR.
QUANTITATIVE_CRITERIA = """\
1. Design validity
   - Kesitsel, deneysel, gözlemsel, longitudinal, quasi-experimental tasarım doğru
     tanımlanmış mı?
   - Araştırma sorusu tasarımla uyumlu mu?

2. Sample and power
   - Örneklem büyüklüğü gerekçeli mi?
   - Power analysis veya precision rationale var mı?
   - Attrition/missingness raporlanmış mı?

3. Measurement validity
   - Ölçüm araçları geçerli/güvenilir mi?
   - Değişken operasyonelleştirme açık mı?

4. Analysis plan
   - İstatistiksel test/model seçimi veri tipine uygun mu?
   - Varsayımlar test edilmiş mi?
   - Multiple comparisons riski var mı?

5. Statistical consistency
   - p-value/test statistic/df uyumu.
   - CI/p-value/effect direction uyumu.
   - Metin-tablo-figür sayı tutarlılığı.

6. Effect size and uncertainty
   - Etki büyüklüğü raporlanmış mı?
   - Güven aralıkları veya belirsizlik ölçüleri var mı?

7. Missing data and outliers
   - Missing data stratejisi açıklanmış mı?
   - Outlier handling şeffaf mı?

8. Causal language discipline
   - Gözlemsel tasarımda nedensel dil aşırı mı?
   - Confounding veya identification stratejisi var mı?

9. Reproducibility
   - Data/code availability.
   - Preregistration veya protocol uyumu.

10. Reporting quality
   - Ana sonuçlar effect size + uncertainty ile sunulmuş mu?
   - "Significant/non-significant" dili aşırı mı?
"""


def _stat_context(stat_findings: list[StatFinding]) -> str:
    """Deterministik statcheck bulgularını LLM'e BAĞLAM bloğu olarak ver (yeniden hesap yok)."""
    if not stat_findings:
        return (
            "Önceden hesaplanmış statcheck bulgusu YOK. p-value tutarlılığını ancak "
            "makalede raporlanan değerlerle yorumla; eksik istatistiği yeniden HESAPLAMA, "
            "raporlama-eksikliği uyarısı olarak işaretle."
        )
    lines = ["statcheck (Nuijten) deterministik sonuçları — bunları yorumla, yeniden hesaplama:"]
    for s in stat_findings:
        rep = "?" if s.reported_p is None else s.reported_p
        comp = "?" if s.computed_p is None else s.computed_p
        lines.append(
            f"  [{s.status}] {s.test_type}: reported_p={rep} computed_p={comp} "
            f"| {s.match_text}"
        )
    return "\n".join(lines)


async def assess_quantitative(
    manuscript: Manuscript,
    evidence: EvidencePack,
    *,
    allow_external_ai: bool,
) -> EngineResult:
    """Nicel geçerlilik değerlendirmesi → Finding[] + ActionItem[] + degraded sinyalleri.

    evidence.stat_findings ek bağlam (statcheck). allow_external_ai False → SIFIR LLM
    çağrısı + degraded. finding.dimension LLM alt-boyutu (sample_and_power,
    causal_language_discipline, ...) → rapor method-validity başlıklarıyla gelir."""
    return await assess(
        label="quantitative_engine",
        mode="quantitative_validity",
        criteria_block=QUANTITATIVE_CRITERIA,
        manuscript=manuscript,
        allow_external_ai=allow_external_ai,
        id_prefix="quant",
        evidence_context=_stat_context(evidence.stat_findings),
        max_tokens=8000,
    )


__all__ = [
    "ENGINE_NAME",
    "ENGINE_VERSION",
    "QUANTITATIVE_CRITERIA",
    "assess_quantitative",
]
