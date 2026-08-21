"""ARBITRA_RESEARCH_BRIEF.md Görev C — hivemind (fikir birliği) ölçüm testleri.

Kapsam: compute_critic_agreement — çapraz-kritik target örtüşme oranı.
LLM/ağ ÇAĞIRMAZ; saf fonksiyon, bilinen girdi → beklenen çıktı.
"""

from __future__ import annotations

from api.models.review import Critique, CritiqueIssue
from engine.academic.hivemind_metrics import compute_critic_agreement


def _critique(critic: str, targets: list[str]) -> Critique:
    return Critique(
        critic=critic,  # type: ignore[arg-type]
        issues=[CritiqueIssue(target=t, problem="p") for t in targets],
    )


def test_no_critiques_returns_zero_state() -> None:
    report = compute_critic_agreement([])
    assert report.n_critics_with_issues == 0
    assert report.total_issues == 0
    assert report.total_cross_critic_pairs == 0
    assert report.overlap_ratio is None


def test_single_critic_no_cross_pairs() -> None:
    # Tek kritik varsa çapraz-kritik çift YOK (kendi içiyle karşılaştırılmaz).
    report = compute_critic_agreement(
        [_critique("skeptik", ["Örneklem büyüklüğü", "Güç analizi eksik"])]
    )
    assert report.n_critics_with_issues == 1
    assert report.total_issues == 2
    assert report.total_cross_critic_pairs == 0
    assert report.overlap_ratio is None


def test_fully_diverse_critics_low_overlap() -> None:
    # 3 kritik, TAMAMEN farklı konulara değiniyor → düşük örtüşme (hivemind YOK).
    critiques = [
        _critique("skeptik", ["Örneklem büyüklüğü gerekçesi eksik"]),
        _critique("yontemci", ["İstatistik test seçimi uygun değil"]),
        _critique("sempatik", ["Yazım netliği güçlü"]),
    ]
    report = compute_critic_agreement(critiques)
    assert report.total_issues == 3
    assert report.total_cross_critic_pairs == 3  # C(3,2) çift, hepsi farklı kritik
    assert report.overlapping_pairs == 0
    assert report.overlap_ratio == 0.0


def test_fully_overlapping_critics_high_overlap() -> None:
    # 3 kritik, HEMEN HEMEN AYNI konuya (kelime kelime yakın) değiniyor → hivemind riski.
    same_target = "Örneklem büyüklüğü gerekçesi ve güç analizi eksikliği"
    critiques = [
        _critique("skeptik", [same_target]),
        _critique("yontemci", [same_target]),
        _critique("sempatik", [same_target]),
    ]
    report = compute_critic_agreement(critiques)
    assert report.total_cross_critic_pairs == 3
    assert report.overlapping_pairs == 3
    assert report.overlap_ratio == 1.0


def test_partial_overlap_mixed() -> None:
    # 2 kritik aynı konuya değiniyor, 1 kritik tamamen farklı → kısmi örtüşme.
    same_target = "Veri ve kod erişilebilirliği eksik"
    critiques = [
        _critique("skeptik", [same_target]),
        _critique("citation_critic", [same_target]),
        _critique("sempatik", ["Yazım netliği güçlü"]),
    ]
    report = compute_critic_agreement(critiques)
    assert report.total_issues == 3
    assert report.total_cross_critic_pairs == 3
    # skeptik-citation_critic örtüşür (aynı hedef); skeptik-sempatik ve
    # citation_critic-sempatik örtüşmez (tamamen farklı konu).
    assert report.overlapping_pairs == 1
    assert report.overlap_ratio == round(1 / 3, 4)


def test_same_critic_own_issues_not_counted_as_overlap() -> None:
    # Aynı kritiğin KENDİ issue'ları arasındaki benzerlik örtüşme SAYILMAZ
    # (hivemind kritikler-ARASI çeşitlilikle ilgili, kritiğin kendi iç
    # tutarlılığıyla değil).
    critiques = [
        _critique("skeptik", ["Örneklem büyüklüğü eksik", "Örneklem büyüklüğü eksik"]),
    ]
    report = compute_critic_agreement(critiques)
    assert report.total_issues == 2
    assert report.total_cross_critic_pairs == 0  # tek kritik, çapraz çift yok
    assert report.overlap_ratio is None


def test_empty_issues_critic_excluded_from_n_critics_with_issues() -> None:
    critiques = [
        _critique("skeptik", ["Bir sorun"]),
        _critique("sempatik", []),  # hiç itiraz yok — meşru (destekleyici)
    ]
    report = compute_critic_agreement(critiques)
    assert report.n_critics_with_issues == 1  # yalnız skeptik sayılır
    assert report.total_issues == 1
    assert report.total_cross_critic_pairs == 0  # tek issue'lu kritik, çift kuramaz
