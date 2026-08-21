"""ARBITRA_RESEARCH_BRIEF.md Görev A — PDF injection tespitini GARANTİLİ bir
Finding'e çevirir (LLM'e bağımlı değil, deterministik).

KANUN: `engine.ingestion.pdf_parser` şüpheli/gizli metin bloklarını tespit edip
`manuscript.meta.parse_warnings`'e "GÜVENLİK:" önekiyle dürüst bir uyarı yazar.
Bu uyarı zaten writer/classifier prompt'larına enjekte edilir (LLM görür), ama
LLM'in bunu rapora GERÇEKTEN yazacağının garantisi yoktur. Bu modül, uyarı
varsa KOD SEVİYESİNDE (LLM'siz) bir Finding + ActionItem üretir — güvenlik
sinyali asla LLM'in "fark etmemesi"ne bağlı kalmaz.
"""

from __future__ import annotations

from api.models.review import ActionItem, Finding

_SECURITY_WARNING_PREFIX = "GÜVENLİK:"


def security_finding_from_warnings(
    parse_warnings: list[str],
) -> tuple[Finding, ActionItem] | None:
    """parse_warnings içinde güvenlik uyarısı varsa deterministik (Finding, ActionItem)
    çifti üretir; yoksa None (uydurma yok — HK-7)."""
    security_warnings = [w for w in parse_warnings if w.startswith(_SECURITY_WARNING_PREFIX)]
    if not security_warnings:
        return None

    summary = " ".join(security_warnings)
    action = ActionItem(
        action_id="security.pdf_injection.a0",
        priority="P0",
        effort="low",
        expected_gain="high",
        target_section=None,
        instruction=(
            "PDF'te tespit edilen şüpheli/gizli metin bloklarını (kaynak dosyada) "
            "elle inceleyin — bu bir prompt-injection girişimi olabilir. Bloklar "
            "değerlendirmeden ÇIKARILDI, ama kaynak dosyanın kendisi ayrıca "
            "incelenmelidir."
        ),
        acceptance_check="Şüpheli bloklar kaynak PDF'te elle doğrulandı.",
        linked_finding_ids=["security.pdf_injection.f0"],
    )
    finding = Finding(
        finding_id="security.pdf_injection.f0",
        dimension="integrity_security",
        severity="major",
        confidence=0.9,
        title="Potansiyel Prompt Injection Tespit Edildi",
        summary=summary,
        manuscript_anchors=[],
        reasoning_public=(
            "PDF ayrıştırma aşamasında, ölçülebilir kriterlere göre (görünmez "
            "font boyutu, beyaz-üzerine-beyaz metin, sayfa dışı konum) şüpheli "
            "metin blokları tespit edildi ve değerlendirme dışı bırakıldı. Bu, "
            "hakemlik motorunu manipüle etmeye yönelik gizli talimat girişimi "
            "olabilir (bilinen bir saldırı sınıfı — bkz. literatür: enjekte "
            "edilmiş incelemelerin puanları ortalama +2.7 şişirebiliyor)."
        ),
        limitations=[
            "Bu bulgu tespit edilen blokların İÇERİĞİNE değil, VARLIĞINA "
            "dayanır — bloklar kaldırıldığı için değerlendirilmedi; kötü "
            "niyetli olmayan (örn. yanlışlıkla beyaz renkli) bir metin de "
            "aynı sinyali üretebilir, bu yüzden 'kesin saldırı' değil "
            "'potansiyel/şüpheli' olarak raporlanır (HK-3 disiplini)."
        ],
        action_item_ids=["security.pdf_injection.a0"],
        global_issue=True,
    )
    return finding, action


__all__ = ["security_finding_from_warnings"]
