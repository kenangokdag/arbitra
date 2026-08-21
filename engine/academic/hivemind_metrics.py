"""ARBITRA_RESEARCH_BRIEF.md Görev C — "hivemind" (fikir birliği) ölçümü.

Çoklu-persona/çoklu-hakem AI sistemlerinde literatürde belgelenmiş bir zaaf:
hakemler görünüşte farklı personalar taşır ("skeptik", "sempatik" vb.) ama
gerçekte neredeyse aynı noktalara odaklanır — gerçek fikir çeşitliliği yok,
sadece isim farkı var. Bu modül, 5 critic'in ürettiği issues[].target metinleri
arasındaki metinsel benzerliği ÖLÇER (embedding GEREKTİRMEDEN — mevcut
review_citation_service._title_ratio ile aynı desen, stdlib SequenceMatcher).
Yüksek örtüşme = düşük çeşitlilik = hivemind riski sinyali.

KANUN: Bu bir "doğru/yanlış" yargısı ya da bir Finding DEĞİL — sadece bir
GÖZLEM/kalibrasyon metriğidir (goldset validasyonu ve gözlemlenebilirlik
için). Kritiklerin gerçekten örtüştüğünü İDDİA ETMEZ, sadece metin benzerliği
ölçer: dürüst sınırlama — aynı sorunu farklı kelimelerle anlatan iki kritik
düşük skor alabilir (yanlış-negatif mümkün), ama bu YANLIŞ-POZİTİF/suçlama
riski TAŞIMAZ (sadece bir sayı, bir Finding ya da suçlama üretmez).
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from api.models.review import Critique

# Bu eşiğin üstündeki bir target-benzerliği "aynı konuya değiniyor" sayılır.
# review_citation_service._TITLE_MATCH_THRESHOLD (0.82) kadar sıkı değil —
# critic target'ları (örn. "Örneklem büyüklüğü gerekçesi") başlıklardan çok
# daha kısa/serbest metin, bu yüzden daha gevşek bir eşik kullanılır.
_TARGET_MATCH_THRESHOLD = 0.6


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _target_similarity(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


@dataclass(frozen=True)
class CriticAgreementReport:
    """5 critic arası çapraz-kritik örtüşme gözlemi (dürüst — yargı değil, gözlem)."""

    n_critics_with_issues: int
    total_issues: int
    overlapping_pairs: int  # farklı kritiklerden, target benzerliği eşik-üstü çift sayısı
    total_cross_critic_pairs: int  # farklı kritiklerden toplam olası çift sayısı
    overlap_ratio: float | None  # overlapping_pairs / total_cross_critic_pairs; çift yoksa None


def compute_critic_agreement(critiques: list[Critique]) -> CriticAgreementReport:
    """Critic'lerin issues[].target'ları arasında ÇAPRAZ-kritik metinsel örtüşme oranı.

    Yalnız FARKLI kritiklerden gelen issue çiftleri karşılaştırılır — aynı
    kritiğin kendi issue'ları arasındaki benzerlik sayılmaz (o örtüşme değil,
    o kritiğin kendi iç tutarlılığıdır, hivemind'la ilgisiz). Yüksek
    overlap_ratio = düşük çeşitlilik riski.
    """
    issue_pool: list[tuple[str, str]] = []  # (critic_key, target)
    for c in critiques:
        for issue in c.issues:
            issue_pool.append((c.critic, issue.target))

    n_critics_with_issues = len({c.critic for c in critiques if c.issues})
    total_issues = len(issue_pool)

    overlapping_pairs = 0
    total_cross_critic_pairs = 0
    for i in range(len(issue_pool)):
        for j in range(i + 1, len(issue_pool)):
            key_i, target_i = issue_pool[i]
            key_j, target_j = issue_pool[j]
            if key_i == key_j:
                continue  # aynı kritik — çapraz-kritik örtüşme değil
            total_cross_critic_pairs += 1
            if _target_similarity(target_i, target_j) >= _TARGET_MATCH_THRESHOLD:
                overlapping_pairs += 1

    overlap_ratio = (
        round(overlapping_pairs / total_cross_critic_pairs, 4)
        if total_cross_critic_pairs
        else None
    )
    return CriticAgreementReport(
        n_critics_with_issues=n_critics_with_issues,
        total_issues=total_issues,
        overlapping_pairs=overlapping_pairs,
        total_cross_critic_pairs=total_cross_critic_pairs,
        overlap_ratio=overlap_ratio,
    )


__all__ = ["CriticAgreementReport", "compute_critic_agreement"]
