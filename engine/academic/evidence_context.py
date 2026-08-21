"""EvidencePack → prompt bloğu (paylaşılan, saf formatter).

2026-08-08: `api/services/review_orchestration.py`'nin `_serialize_evidence()`'ı
buraya TAŞINDI (kopyalanmadı) — hem orchestration (writer/critics) hem
rubric_registry pipeline'ı (dimension_engine üzerinden citation_integrity/
literature_positioning/literature_depth) AYNI formatter'ı kullanmalı; iki kopya
tutmak drift riski yaratırdı (CLAUDE.md §2.4 global>local). `engine/academic/`
saf/deterministik katman olduğundan burada duruyor — `api/services/` bunu
import eder, tersi değil (katman ihlali önlenir).

LLM çağrısı YOK, network YOK — tam deterministik string formatlama.
"""

from __future__ import annotations

from api.models.review import EvidencePack

__all__ = ["serialize_evidence_pack"]


def serialize_evidence_pack(pack: EvidencePack) -> str:
    """EvidencePack → prompt bloğu. Tüm olgular açıkça listelenir (HK-5)."""
    ci = pack.citation_integrity
    lines: list[str] = ["KANIT PAKETİ (deterministik olgular — bunları UYDURMA):"]

    lines.append(
        "1) Atıf bütünlüğü özeti: "
        f"toplam={ci.total}, çözülen={ci.resolved}, "
        f"bulunamayan={ci.not_found_in_index}, uydurma={ci.fabricated}, "
        f"geri_çekilmiş={ci.retracted}."
    )
    if ci.provider_errors:
        # §41 devamı (2026-08-12, guardian bulgusu): "bulunamayan" sayısının
        # bir kısmı sadece geçici sağlayıcı (OpenAlex) hatasından kaynaklanabilir
        # — gerçek eşleşme-yokluğu DEĞİL. Bu ayrım önceden sadece per-referans
        # kanıt metninde vardı, agrege özette hiç görünmüyordu — LLM "yüksek
        # bulunamama oranı" görünce tek başına major/critical severity
        # üretebiliyordu (SS38 bulgusu). Artık açıkça uyarılıyor.
        lines.append(
            f"   ⚠ Bunların {ci.provider_errors}'i SADECE geçici sağlayıcı "
            "(OpenAlex) hatasından kaynaklanıyor — gerçek eşleşme-yokluğu "
            "KANITI DEĞİL. Bu alt-kümeyi 'uydurma atıf' veya 'kaynak taraması "
            "zayıf' gibi bir bulgunun TEK dayanağı yapma; sadece gerçek "
            "fabricated/retracted/contradicted olgularına dayan."
        )

    if pack.references:
        lines.append("2) Referanslar (durum + kanıt):")
        for ref in pack.references:
            title = (ref.title or ref.raw or "(başlıksız)").strip()
            ev = f" — kanıt: {ref.evidence}" if ref.evidence else ""
            retr = " [GERİ-ÇEKİLMİŞ]" if ref.is_retracted else ""
            lines.append(f"   [{ref.index}] {title} → {ref.status}{retr}{ev}")
    else:
        lines.append("2) Referans listesi boş.")

    if pack.context_findings:
        lines.append("3) Atıf-bağlam bulguları (iddia kaynağı destekliyor mu):")
        for cf in pack.context_findings:
            ev = f" — {cf.evidence}" if cf.evidence else ""
            lines.append(f"   [ref {cf.ref_index}] '{cf.claim}' → {cf.support}{ev}")
    else:
        lines.append("3) Atıf-bağlam bulgusu yok.")

    if pack.coverage_gaps:
        lines.append("4) Kapsama boşlukları (atlanmış zorunlu/seminal iş):")
        for gap in pack.coverage_gaps:
            yr = f", {gap.year}" if gap.year else ""
            lines.append(
                f"   - {gap.title}{yr} (atıf={gap.cited_by_count}): {gap.reason}"
            )
    else:
        lines.append("4) Tespit edilen kapsama boşluğu yok.")

    if pack.stat_findings:
        lines.append("5) İstatistik bulguları (statcheck):")
        for sf in pack.stat_findings:
            rp = sf.reported_p if sf.reported_p is not None else "?"
            cp = sf.computed_p if sf.computed_p is not None else "?"
            lines.append(
                f"   - {sf.test_type} [{sf.status}] raporlanan_p={rp}, "
                f"hesaplanan_p={cp} | {sf.match_text}"
            )
    else:
        lines.append("5) İstatistik bulgusu yok.")

    return "\n".join(lines)
