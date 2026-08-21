"""G3 — SectionReview status='missing' beklenen-bölüm eksikken üretilir.

Kanıt: rubric.expected_sections (doc-type + ampirik tasarım) ile manuscript
bölümleri kıyaslanır; eksik beklenen bölüm → 'missing'. Eşanlamlı toleranslı
(Materials and Methods → Methods MEVCUT). Kuramsal tasarım → beklenti yok →
yanlış 'missing' üretilmez.
"""

from __future__ import annotations

import pytest

from api.models.review import Manuscript, ManuscriptMeta
from engine.academic.report_synthesis import build_section_reviews
from engine.academic.rubric_registry import (
    expected_sections_for,
    missing_sections,
    select_rubric,
)

pytestmark = pytest.mark.unit


def _manuscript(section_titles: list[str]) -> Manuscript:
    return Manuscript(
        meta=ManuscriptMeta(
            title="X", section_titles=section_titles, word_count=100,
            reference_count=1,
        ),
        full_text="body",
    )


# --- rubric expected_sections -----------------------------------------------


def test_empirical_journal_article_expects_imrad() -> None:
    exp = expected_sections_for("journal_article", "quantitative")
    assert exp == ["Introduction", "Methods", "Results", "Discussion"]


def test_theoretical_paper_expects_nothing() -> None:
    # Kuramsal makalede Methods/Results beklemek yanlış 'missing' üretirdi.
    assert expected_sections_for("journal_article", "theoretical") == []


def test_grant_proposal_expects_nothing() -> None:
    assert expected_sections_for("grant_proposal", "quantitative") == []


def test_select_rubric_carries_expected_sections() -> None:
    r = select_rubric(
        document_type="journal_article", study_design="quantitative"
    )
    assert "Methods" in r.expected_sections
    assert "Results" in r.expected_sections


def test_missing_sections_synonym_tolerant() -> None:
    # 'Materials and Methods' Methods'u karşılar; 'Findings' Results'ı.
    present = ["Introduction", "Materials and Methods", "Findings", "Discussion"]
    assert missing_sections(
        ["Introduction", "Methods", "Results", "Discussion"], present
    ) == []


# --- build_section_reviews 'missing' ----------------------------------------


def test_missing_section_emitted_when_expected_absent() -> None:
    rubric = select_rubric(
        document_type="journal_article", study_design="quantitative"
    )
    # Methods + Results YOK
    manuscript = _manuscript(["Introduction", "Discussion"])
    reviews = build_section_reviews([], manuscript, rubric)
    missing = [r for r in reviews if r.status == "missing"]
    missing_sections_labels = {r.section for r in missing}
    assert "Methods" in missing_sections_labels
    assert "Results" in missing_sections_labels
    # var olanlar 'missing' DEĞİL
    assert "Introduction" not in missing_sections_labels
    # her 'missing' bir what_breaks taşır (dürüst neden)
    assert all(r.what_breaks for r in missing)


def test_no_missing_when_all_present() -> None:
    rubric = select_rubric(
        document_type="journal_article", study_design="quantitative"
    )
    manuscript = _manuscript(
        ["Introduction", "Materials and Methods", "Results", "Conclusion"]
    )
    reviews = build_section_reviews([], manuscript, rubric)
    assert [r for r in reviews if r.status == "missing"] == []


def test_no_missing_for_theoretical_design() -> None:
    rubric = select_rubric(
        document_type="journal_article", study_design="theoretical"
    )
    manuscript = _manuscript(["Introduction", "Argument", "Conclusion"])
    reviews = build_section_reviews([], manuscript, rubric)
    # Beklenti yok → Methods/Results 'missing' ÜRETİLMEZ (dürüst).
    assert [r for r in reviews if r.status == "missing"] == []


def test_no_rubric_no_missing() -> None:
    # rubric verilmezse (geriye-uyum) hiç 'missing' yok.
    manuscript = _manuscript(["Introduction"])
    reviews = build_section_reviews([], manuscript)
    assert [r for r in reviews if r.status == "missing"] == []
