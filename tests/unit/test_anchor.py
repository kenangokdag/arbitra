"""P005 Anchor PMID 12-segment partial match unit tests (K6)."""

import pytest

from api.services.anchor import (
    PLACEHOLDER,
    PMID_SEGMENT_COUNT,
    PartialPMID,
    PmidAnchor,
    extract_partial_from_query,
    parse_pmid,
    score_match,
)

pytestmark = pytest.mark.unit


# ---------- parse_pmid ----------


def test_parse_full_12_segment_pmid() -> None:
    raw = "med.psy.depresyon.T-001.T-002.T-003.2024.Q1.I2.tr.E.1"
    parsed = parse_pmid(raw)
    assert parsed is not None
    assert parsed.D == "med"
    assert parsed.F == "psy"
    assert parsed.Y == "2024"
    assert parsed.Q == "Q1"
    assert parsed.L == "tr"
    assert parsed.V == "1"


def test_parse_wrong_segment_count_returns_none() -> None:
    assert parse_pmid("med.psy.depresyon") is None  # 3 segment
    assert parse_pmid("a.b.c.d.e.f.g.h.i.j.k.l.m") is None  # 13 segment


def test_parse_empty_segment_becomes_none() -> None:
    raw = "med..depresyon.0.0.0.2024.Q1.I2.tr.E.1"
    parsed = parse_pmid(raw)
    assert parsed is not None
    assert parsed.F is None  # boş segment
    assert parsed.D == "med"


def test_parse_wildcard_segment_preserved() -> None:
    raw = "med.*.*.T-001.0.0.2024.Q1.I2.tr.*.1"
    parsed = parse_pmid(raw)
    assert parsed is not None
    assert parsed.F == "*"
    assert parsed.S == "*"
    assert parsed.R == "*"


def test_parse_placeholder_question_mark_preserved() -> None:
    raw = "med.psy.?.T-001.0.0.?.Q1.I2.tr.E.1"
    parsed = parse_pmid(raw)
    assert parsed is not None
    assert parsed.S == "?"
    assert parsed.Y == "?"


def test_parse_empty_input_returns_none() -> None:
    assert parse_pmid("") is None


# ---------- score_match ----------


def test_score_full_match_returns_1() -> None:
    pmid = parse_pmid("med.psy.depresyon.T-1.T-2.T-3.2024.Q1.I2.tr.E.1")
    assert pmid is not None
    score = score_match(pmid, pmid)
    assert score == pytest.approx(1.0)


def test_score_partial_match() -> None:
    """Query 4 segment, corpus 4 eşleşen + 8 farklı → 1.0 (denominator 4 query segment)."""
    query = PartialPMID(D="med", F="psy", Y="2024", L="tr")
    corpus = parse_pmid("med.psy.depresyon.T-1.T-2.T-3.2024.Q1.I2.tr.E.1")
    assert corpus is not None
    score = score_match(query, corpus)
    assert score == pytest.approx(1.0)


def test_score_wildcard_is_dont_care() -> None:
    """Wildcard `*` denominator'a girmez (don't-care semantiği) → tamamı `*` ise 0.0."""
    query = PartialPMID(D="*", F="*", Y="*")
    corpus = PartialPMID(D="med", F="psy", Y="2024")
    # Query'de denominator=0 → 0.0
    assert score_match(query, corpus) == pytest.approx(0.0)


def test_score_wildcard_skipped_exact_segments_count() -> None:
    """Wildcard skip; exact segment denominator'a girer."""
    query = PartialPMID(D="med", F="*", Y="2024")  # 2 exact + 1 wildcard
    corpus = PartialPMID(D="med", F="psy", Y="2024")
    # Denominator = 2 (D + Y), 2 match → 1.0
    assert score_match(query, corpus) == pytest.approx(1.0)


def test_score_placeholder_question_mark_skipped() -> None:
    """`?` placeholder (K9) denominator'a girmez."""
    query = PartialPMID(D="med", F="?", Y="2024")
    corpus = PartialPMID(D="med", F="psy", Y="2024")
    score = score_match(query, corpus)
    # 2 query segment (D + Y), 2 match → 1.0
    assert score == pytest.approx(1.0)


def test_score_zero_overlap() -> None:
    query = PartialPMID(D="cs", F="ai")
    corpus = PartialPMID(D="med", F="psy")
    score = score_match(query, corpus)
    assert score == pytest.approx(0.0)


def test_score_half_match() -> None:
    query = PartialPMID(D="med", F="psy", Y="2024", Q="Q1")
    corpus = PartialPMID(D="med", F="psy", Y="2010", Q="Q3")
    score = score_match(query, corpus)
    assert score == pytest.approx(0.5)  # 2/4


def test_score_zero_denominator_returns_zero() -> None:
    query = PartialPMID()  # tüm None
    corpus = PartialPMID(D="med")
    score = score_match(query, corpus)
    assert score == pytest.approx(0.0)


# ---------- PartialPMID.to_string ----------


def test_to_string_renders_12_segment_with_placeholder() -> None:
    pmid = PartialPMID(D="med", F="psy", Y="2024")
    out = pmid.to_string()
    assert out.count(".") == PMID_SEGMENT_COUNT - 1
    parts = out.split(".")
    assert parts[0] == "med"
    assert parts[1] == "psy"
    assert parts[6] == "2024"
    # Diğer eksik segment'ler `?` placeholder
    assert parts[2] == PLACEHOLDER
    assert parts[11] == PLACEHOLDER


def test_non_null_count() -> None:
    pmid = PartialPMID(D="med", F="psy", Y="2024", L="tr")
    assert pmid.non_null_count() == 4


# ---------- extract_partial_from_query ----------


def test_extract_pmid_from_text() -> None:
    query = "Bana göster med.psy.depresyon.T-1.T-2.T-3.2024.Q1.I2.tr.E.1 paperı"
    partial = extract_partial_from_query(query)
    assert partial is not None
    assert partial.D == "med"
    assert partial.Y == "2024"


def test_extract_no_pmid_in_query_returns_none() -> None:
    assert extract_partial_from_query("makine öğrenmesi tıp uygulaması") is None
    assert extract_partial_from_query("") is None


def test_extract_with_wildcards() -> None:
    query = "Konu: med.psy.*.*.*.*.2024.Q1.I2.tr.*.1"
    partial = extract_partial_from_query(query)
    assert partial is not None
    assert partial.S == "*"
    assert partial.R == "*"


# ---------- PmidAnchor.match (in-memory corpus) ----------


@pytest.fixture
def sample_corpus() -> list[str]:
    return [
        "med.psy.depresyon.T-1.T-2.T-3.2024.Q1.I2.tr.E.1",
        "med.psy.anksiyete.T-1.T-2.T-3.2023.Q1.I1.en.E.1",
        "cs.ai.transformer.T-4.T-5.T-6.2024.Q1.I2.en.M.1",
        "med.cardio.aritmi.T-7.T-8.T-9.2022.Q2.I1.tr.E.2",
        "soc.eco.enflasyon.T-10.T-11.T-12.2025.Q1.I1.tr.E.1",
    ]


async def test_anchor_match_full_pmid_in_query(sample_corpus: list[str]) -> None:
    anchor = PmidAnchor(corpus=sample_corpus)
    query = "Show me med.psy.depresyon.T-1.T-2.T-3.2024.Q1.I2.tr.E.1 details"
    result = await anchor.match(query)
    assert len(result) >= 1
    # En yüksek skor full-match olan
    assert result[0] == "med.psy.depresyon.T-1.T-2.T-3.2024.Q1.I2.tr.E.1"


async def test_anchor_match_wildcard_filter(sample_corpus: list[str]) -> None:
    anchor = PmidAnchor(corpus=sample_corpus)
    # D=med + F=psy + diğer hepsi wildcard → 2 match (depresyon + anksiyete)
    query = "Konu: med.psy.*.*.*.*.*.*.*.*.*.*"
    result = await anchor.match(query, top_k=10)
    assert len(result) == 2
    assert any("depresyon" in pmid for pmid in result)
    assert any("anksiyete" in pmid for pmid in result)


async def test_anchor_match_no_pmid_in_query_returns_empty(sample_corpus: list[str]) -> None:
    anchor = PmidAnchor(corpus=sample_corpus)
    result = await anchor.match("makine öğrenmesi")
    assert result == []


async def test_anchor_match_top_k_clamp(sample_corpus: list[str]) -> None:
    anchor = PmidAnchor(corpus=sample_corpus)
    query = "med.*.*.*.*.*.*.*.*.*.*.*"  # 3 corpus paper match
    result = await anchor.match(query, top_k=2)
    assert len(result) == 2


async def test_anchor_match_empty_corpus_returns_empty() -> None:
    anchor = PmidAnchor(corpus=[])
    result = await anchor.match("med.psy.depresyon.T-1.T-2.T-3.2024.Q1.I2.tr.E.1")
    assert result == []


async def test_anchor_match_threshold_filters_low_score(sample_corpus: list[str]) -> None:
    """Wildcard don't-care; D=med + F=cardio denominator=2; tek cardio paper full match (2/2=1.0)."""
    anchor = PmidAnchor(corpus=sample_corpus, threshold=0.9)
    query = "med.cardio.*.*.*.*.*.*.*.*.*.*"
    result = await anchor.match(query)
    # cardio paper: D+F match (2/2=1.0); psy paper'ler: D match F mismatch (1/2=0.5 < 0.9)
    assert len(result) == 1
    assert "cardio" in result[0]
