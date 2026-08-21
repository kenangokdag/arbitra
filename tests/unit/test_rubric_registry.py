"""P03-T03 — RubricRegistry testleri (PURE, deterministik, ağ yok).

Spec başarı kapısı: makale/bildiri/tez/proje AYNI raporu almıyor → farklı dimension
setleri. Nitel/nicel → methodology farklı analiz motoruna yönleniyor.
"""

from __future__ import annotations

from engine.academic.rubric_registry import RUBRIC_VERSION, select_rubric


def _ids(document_type: str, study_design: str = "quantitative") -> set[str]:
    rubric = select_rubric(document_type=document_type, study_design=study_design)
    return {d.id for d in rubric.dimensions}


def test_doc_types_have_distinct_dimension_sets():
    """makale ≠ bildiri ≠ tez ≠ proje (spec başarı kapısı)."""
    article = _ids("journal_article")
    conference = _ids("conference_paper")
    thesis = _ids("thesis")
    grant = _ids("grant_proposal")

    sets = {
        "journal_article": frozenset(article),
        "conference_paper": frozenset(conference),
        "thesis": frozenset(thesis),
        "grant_proposal": frozenset(grant),
    }
    names = list(sets)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            assert sets[names[i]] != sets[names[j]], (
                f"{names[i]} ve {names[j]} aynı dimension setine sahip!"
            )


def test_methodology_routes_by_study_design():
    """qualitative → QualitativeRigorEngine, quantitative → QuantitativeValidityEngine."""
    qual = select_rubric(document_type="journal_article", study_design="qualitative")
    quant = select_rubric(document_type="journal_article", study_design="quantitative")

    qual_method = next(d for d in qual.dimensions if d.id == "methodology_fit")
    quant_method = next(d for d in quant.dimensions if d.id == "methodology_fit")

    assert qual_method.engine == "QualitativeRigorEngine"
    assert quant_method.engine == "QuantitativeValidityEngine"


def test_unknown_falls_back_to_general_rubric():
    rubric = select_rubric(document_type="unknown", study_design="unknown")
    assert rubric.dimensions, "unknown için boş rubrik döndü (dürüst fallback YOK)"
    assert rubric.rubric_id.startswith("unknown.")
    # genel fallback methodology'si default motora gider (unknown çalışma türü)
    method = next(d for d in rubric.dimensions if d.id == "methodology_fit")
    assert method.engine in ("QuantitativeValidityEngine", "QualitativeRigorEngine")


def test_weights_sum_to_one_per_rubric():
    for doc_type in (
        "journal_article",
        "conference_paper",
        "thesis",
        "grant_proposal",
        "unknown",
        "preprint",
    ):
        for design in ("qualitative", "quantitative", "unknown"):
            rubric = select_rubric(document_type=doc_type, study_design=design)
            total = sum(d.weight for d in rubric.dimensions)
            assert abs(total - 1.0) < 1e-6, (
                f"{doc_type}/{design} ağırlık toplamı {total} ≠ 1.0"
            )


def test_strictness_keeps_sum_normalized():
    for strictness in ("lenient", "standard", "strict"):
        rubric = select_rubric(
            document_type="thesis",
            study_design="quantitative",
            strictness=strictness,  # type: ignore[arg-type]
        )
        total = sum(d.weight for d in rubric.dimensions)
        assert abs(total - 1.0) < 1e-6


def test_rubric_id_and_version_stamped():
    rubric = select_rubric(document_type="journal_article", study_design="qualitative")
    assert rubric.rubric_id == "journal_article.qualitative.v1"
    assert rubric.version == RUBRIC_VERSION


def test_required_dimensions_present():
    """En az bir required dimension olmalı (rubrik anlamlı)."""
    rubric = select_rubric(document_type="journal_article", study_design="quantitative")
    assert any(d.required for d in rubric.dimensions)
