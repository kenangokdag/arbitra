"""Versiyon karşılaştırma — Faz 1 (VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17 §2.3).

SADECE deterministik üst-seviye diff (verdict/hazırlık puanı/boyut skoru).
Bulgu-eşleştirme ("hangi Finding kapandı") BİLİNÇLİ olarak YOK — ayrı, guardian
gerektiren bir Faz 2 kararı (plan §5, kök neden: Finding.finding_id iki motor
koşumu arasında stabil değil).
"""

from __future__ import annotations

from uuid import UUID

from api.models.review import DimensionScoreDelta, ReviewReport, VersionComparison


def build_version_comparison(
    parent_job_id: UUID,
    previous: ReviewReport,
    current: ReviewReport,
) -> VersionComparison:
    """İki ReviewReport'un verdict/hazırlık puanı/boyut skorlarını diff'ler.

    dimension_deltas: iki raporun dimension_scores'undaki key'lerin BİRLEŞİMİ —
    birinde olup diğerinde olmayan bir boyut TAHMİN EDİLMEZ, o taraf None kalır.
    """
    previous_readiness = (
        previous.executive_verdict.overall_readiness_score
        if previous.executive_verdict is not None
        else None
    )
    current_readiness = (
        current.executive_verdict.overall_readiness_score
        if current.executive_verdict is not None
        else None
    )
    readiness_delta = (
        current_readiness - previous_readiness
        if previous_readiness is not None and current_readiness is not None
        else None
    )

    previous_by_key = {d.key: d.score for d in previous.dimension_scores}
    current_by_key = {d.key: d.score for d in current.dimension_scores}
    all_keys = list(dict.fromkeys([*previous_by_key.keys(), *current_by_key.keys()]))

    dimension_deltas = [
        DimensionScoreDelta(
            key=key,
            previous_score=previous_by_key.get(key),
            current_score=current_by_key.get(key),
            delta=(
                current_by_key[key] - previous_by_key[key]
                if key in previous_by_key and key in current_by_key
                else None
            ),
        )
        for key in all_keys
    ]

    return VersionComparison(
        parent_job_id=parent_job_id,
        previous_verdict=previous.verdict,
        current_verdict=current.verdict,
        verdict_changed=previous.verdict != current.verdict,
        previous_readiness_score=previous_readiness,
        current_readiness_score=current_readiness,
        readiness_delta=readiness_delta,
        dimension_deltas=dimension_deltas,
    )


__all__ = ["build_version_comparison"]
