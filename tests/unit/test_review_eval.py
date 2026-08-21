"""F14 EVAL metrik motoru — saf fonksiyon testleri (bilinen girdi → beklenen çıktı).

Kapsam: verdict_accuracy (tam + 1-kademe-tolerans), dimension_agreement
(Spearman/Pearson/ort.fark + yetersiz-veri None), confusion_matrix,
OMER_DOLDURACAK atlama, format_summary. Hiçbiri LLM/ağ ÇAĞIRMAZ.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from api.models.review import (
    CitationContextFinding,
    CitationIntegritySummary,
    DimensionScore,
    EvidencePack,
    Finding,
    ManuscriptMeta,
    ReviewProvenance,
    ReviewReport,
    Verdict,
)
from eval.review import metrics
from eval.review.schema import OMER_PLACEHOLDER, GoldEntry, GoldMeta, GoldSet

# --- fixture yardımcıları ---------------------------------------------------


def _report(
    verdict: Verdict, dims: dict[str, float] | None = None
) -> ReviewReport:
    """Minimal geçerli ReviewReport (metrik için sadece verdict + dim skor önemli)."""
    dims = dims or {}
    return ReviewReport(
        mode="author",
        language="en",
        manuscript_meta=ManuscriptMeta(),
        summary="s",
        overall_assessment="oa",
        verdict=verdict,
        dimension_scores=[
            DimensionScore(key=k, score=v, rationale="r")  # type: ignore[arg-type]
            for k, v in dims.items()
        ],
        provenance=ReviewProvenance(
            model_used="test",
            persona_version="v",
            engine_version="test",
            generated_at=datetime.now(UTC),
        ),
    )


def _finding(fid: str, *, dimension: str, severity: str) -> Finding:
    return Finding(
        finding_id=fid,
        dimension=dimension,
        severity=severity,  # type: ignore[arg-type]
        confidence=0.8,
        title=f"Finding {fid}",
        global_issue=True,
        action_item_ids=[f"{fid}.a0"],
    )


def _report_with_moat(
    verdict: Verdict,
    *,
    findings: list[Finding],
    fabricated: int = 0,
    retracted: int = 0,
    contradicted: bool = False,
) -> ReviewReport:
    rep = _report(verdict)
    context_findings = (
        [CitationContextFinding(ref_index=1, claim="x", support="contradicted")]
        if contradicted
        else []
    )
    return rep.model_copy(
        update={
            "findings": findings,
            "evidence_pack": EvidencePack(
                citation_integrity=CitationIntegritySummary(
                    total=fabricated + retracted + 1,
                    fabricated=fabricated,
                    retracted=retracted,
                ),
                context_findings=context_findings,
            ),
        }
    )


def _gold(
    pid: str,
    verdict: str,
    scores: dict[str, float] | None = None,
) -> GoldEntry:
    return GoldEntry(
        paper_id=pid,
        source="manual",
        title=f"paper {pid}",
        field="quant_social_science",
        human_verdict=verdict,  # type: ignore[arg-type]
        human_scores=scores or {},  # type: ignore[arg-type]
        human_review_excerpt="excerpt",
    )


def _goldset(entries: list[GoldEntry]) -> GoldSet:
    return GoldSet(
        meta=GoldMeta(
            version="test",
            created_at="2026-06-22",
            pilot_field="quant_social_science",
            description="test",
            real_entry_count=sum(
                1 for e in entries if e.human_verdict != OMER_PLACEHOLDER
            ),
            placeholder_entry_count=sum(
                1 for e in entries if e.human_verdict == OMER_PLACEHOLDER
            ),
        ),
        entries=entries,
    )


# --- verdict_accuracy -------------------------------------------------------


def test_verdict_accuracy_all_exact() -> None:
    reports = {
        "a": _report("accept"),
        "b": _report("reject"),
        "c": _report("minor_revision"),
    }
    gold = _goldset(
        [
            _gold("a", "accept"),
            _gold("b", "reject"),
            _gold("c", "minor_revision"),
        ]
    )
    va = metrics.verdict_accuracy(reports, gold)
    assert va.n == 3
    assert va.exact == 3
    assert va.exact_accuracy == 1.0
    assert va.within_one_accuracy == 1.0


def test_verdict_accuracy_within_one_tolerance() -> None:
    # accept(0) vs minor_revision(1) = 1 kademe → within_one ama exact değil.
    # accept(0) vs major_revision(2) = 2 kademe → ne exact ne within_one.
    reports = {
        "a": _report("accept"),  # insan minor_revision → 1 kademe
        "b": _report("accept"),  # insan major_revision → 2 kademe
        "c": _report("reject"),  # insan reject → tam
    }
    gold = _goldset(
        [
            _gold("a", "minor_revision"),
            _gold("b", "major_revision"),
            _gold("c", "reject"),
        ]
    )
    va = metrics.verdict_accuracy(reports, gold)
    assert va.n == 3
    assert va.exact == 1  # sadece c
    assert va.within_one == 2  # a (1 kademe) + c (0 kademe)
    assert va.exact_accuracy == pytest.approx(1 / 3)
    assert va.within_one_accuracy == pytest.approx(2 / 3)


def test_verdict_accuracy_skips_placeholder() -> None:
    reports = {"a": _report("accept"), "b": _report("reject")}
    gold = _goldset(
        [
            _gold("a", "accept"),
            _gold("b", OMER_PLACEHOLDER),  # gerçek değil → atlanır
        ]
    )
    va = metrics.verdict_accuracy(reports, gold)
    assert va.n == 1  # b atlandı (uydurma yasağı)
    assert va.exact == 1
    assert va.exact_accuracy == 1.0


def test_verdict_accuracy_empty_returns_none() -> None:
    reports = {"a": _report("accept")}
    gold = _goldset([_gold("a", OMER_PLACEHOLDER)])
    va = metrics.verdict_accuracy(reports, gold)
    assert va.n == 0
    assert va.exact_accuracy is None
    assert va.within_one_accuracy is None


# --- dimension_agreement ----------------------------------------------------


def test_dimension_agreement_perfect_positive_correlation() -> None:
    # motor ve insan skorları aynı sıralama → Spearman = 1.0.
    reports = {
        "a": _report("accept", {"soundness": 3.0}),
        "b": _report("accept", {"soundness": 6.0}),
        "c": _report("accept", {"soundness": 9.0}),
    }
    gold = _goldset(
        [
            _gold("a", "accept", {"soundness": 4.0}),
            _gold("b", "accept", {"soundness": 7.0}),
            _gold("c", "accept", {"soundness": 10.0}),
        ]
    )
    das = {da.dimension: da for da in metrics.dimension_agreement(reports, gold)}
    sound = das["soundness"]
    assert sound.n == 3
    assert sound.spearman == pytest.approx(1.0)
    assert sound.pearson == pytest.approx(1.0)
    # |3-4|+|6-7|+|9-10| = 3, /3 = 1.0
    assert sound.mean_abs_diff == pytest.approx(1.0)
    # ARBITRA_RESEARCH_BRIEF.md Görev D: motor hep -1 düşük puanlıyor (SIKI, şişirme değil).
    assert sound.mean_signed_diff == pytest.approx(-1.0)


def test_dimension_agreement_systematic_inflation_bias() -> None:
    # Görev D: motor HER ZAMAN insan skorundan +2 yüksek → sistematik şişirme.
    # mean_abs_diff ile mean_signed_diff AYNI (yön sabit, iptal olmuyor).
    reports = {
        "a": _report("accept", {"soundness": 8.0}),
        "b": _report("accept", {"soundness": 9.0}),
        "c": _report("accept", {"soundness": 7.0}),
    }
    gold = _goldset(
        [
            _gold("a", "accept", {"soundness": 6.0}),
            _gold("b", "accept", {"soundness": 7.0}),
            _gold("c", "accept", {"soundness": 5.0}),
        ]
    )
    das = {da.dimension: da for da in metrics.dimension_agreement(reports, gold)}
    sound = das["soundness"]
    assert sound.mean_abs_diff == pytest.approx(2.0)
    assert sound.mean_signed_diff == pytest.approx(2.0)  # pozitif = şişirme


def test_dimension_agreement_random_error_not_systematic_bias() -> None:
    # Görev D: hata büyüklüğü (mean_abs_diff) sistematik şişirmeyle AYNI olabilir
    # ama yön (mean_signed_diff) rastgele hatada birbirini iptal eder — bu ikisini
    # ayırt etmek tam olarak Görev D'nin amacı (motor hep şişiriyor mu, yoksa
    # rastgele mi sapıyor?).
    reports = {
        "a": _report("accept", {"soundness": 8.0}),  # +2
        "b": _report("accept", {"soundness": 5.0}),  # -2
        "c": _report("accept", {"soundness": 7.0}),  # 0
    }
    gold = _goldset(
        [
            _gold("a", "accept", {"soundness": 6.0}),
            _gold("b", "accept", {"soundness": 7.0}),
            _gold("c", "accept", {"soundness": 7.0}),
        ]
    )
    das = {da.dimension: da for da in metrics.dimension_agreement(reports, gold)}
    sound = das["soundness"]
    assert sound.mean_abs_diff == pytest.approx(round(4.0 / 3.0, 4))
    assert sound.mean_signed_diff == pytest.approx(0.0)  # 0'a yakın = sistematik değil


def test_dimension_agreement_perfect_negative_correlation() -> None:
    reports = {
        "a": _report("accept", {"clarity": 9.0}),
        "b": _report("accept", {"clarity": 6.0}),
        "c": _report("accept", {"clarity": 3.0}),
    }
    gold = _goldset(
        [
            _gold("a", "accept", {"clarity": 2.0}),
            _gold("b", "accept", {"clarity": 5.0}),
            _gold("c", "accept", {"clarity": 8.0}),
        ]
    )
    das = {da.dimension: da for da in metrics.dimension_agreement(reports, gold)}
    clarity = das["clarity"]
    assert clarity.spearman == pytest.approx(-1.0)


def test_dimension_agreement_insufficient_n_returns_none() -> None:
    # n<3 → korelasyon None (dürüst yetersiz-veri), ama mean_abs_diff hesaplanır.
    reports = {
        "a": _report("accept", {"soundness": 5.0}),
        "b": _report("accept", {"soundness": 8.0}),
    }
    gold = _goldset(
        [
            _gold("a", "accept", {"soundness": 6.0}),
            _gold("b", "accept", {"soundness": 7.0}),
        ]
    )
    das = {da.dimension: da for da in metrics.dimension_agreement(reports, gold)}
    sound = das["soundness"]
    assert sound.n == 2
    assert sound.spearman is None
    assert sound.pearson is None
    assert sound.mean_abs_diff == pytest.approx(1.0)  # (|5-6|+|8-7|)/2


def test_dimension_agreement_skips_unmeasured_dimension() -> None:
    # insan sadece soundness ölçtü; importance human_scores'ta YOK → n=0.
    reports = {
        "a": _report("accept", {"soundness": 5.0, "importance": 5.0}),
        "b": _report("accept", {"soundness": 6.0, "importance": 6.0}),
        "c": _report("accept", {"soundness": 7.0, "importance": 7.0}),
    }
    gold = _goldset(
        [
            _gold("a", "accept", {"soundness": 5.0}),
            _gold("b", "accept", {"soundness": 6.0}),
            _gold("c", "accept", {"soundness": 7.0}),
        ]
    )
    das = {da.dimension: da for da in metrics.dimension_agreement(reports, gold)}
    assert das["soundness"].n == 3
    assert das["importance"].n == 0  # ölçülmedi → uydurma yok
    assert das["importance"].spearman is None


# --- moat_grounding_accuracy (2026-08-10, SS37/38) --------------------------


def test_moat_grounding_flags_grounded_when_evidence_pack_confirms_fabricated() -> None:
    """critical citation_integrity bulgusu VE EvidencePack'te gercek fabricated>0
    -> grounded. Insan-verdict'ten TAMAMEN bagimsiz calisir (goldset'te insan
    karari olmasa bile grounded/ungrounded ayrimi yapilir)."""
    reports = {
        "a": _report_with_moat(
            "accept",
            findings=[_finding("f0", dimension="citation_integrity", severity="critical")],
            fabricated=1,
        ),
    }
    gold = _goldset([_gold("a", "accept")])
    mg = metrics.moat_grounding_accuracy(reports, gold)
    assert mg.n_flagged_papers == 1
    assert mg.n_grounded_papers == 1
    assert mg.n_ungrounded_papers == 0
    assert mg.grounded_ratio == pytest.approx(1.0)
    assert mg.grounded_papers_human_verdicts == {"a": "accept"}


def test_moat_grounding_counts_contradicted_context_finding_as_grounded() -> None:
    """2026-08-10 guardian bulgusu: academic_dimension.py'nin kendi kurali
    'contradicted' atif-baglam bulgusunu da major/critical'i HAK EDEN ucuncu
    bir gerekce sayiyor (fabricated/retracted ile ESIT) - ilk surumde bu
    unutulmustu, 'grounded' orani oldugundan dusuk gosteriyordu."""
    reports = {
        "a": _report_with_moat(
            "reject",
            findings=[_finding("f0", dimension="citation_integrity", severity="major")],
            fabricated=0,
            retracted=0,
            contradicted=True,
        ),
    }
    gold = _goldset([_gold("a", "reject")])
    mg = metrics.moat_grounding_accuracy(reports, gold)
    assert mg.n_grounded_papers == 1
    assert mg.n_ungrounded_papers == 0


def test_moat_grounding_flags_ungrounded_when_evidence_pack_is_clean() -> None:
    """critical citation_integrity bulgusu AMA EvidencePack fabricated=0/retracted=0
    -> ungrounded (supheli/dogrulanamamis guclu iddia, incelenmeli)."""
    reports = {
        "a": _report_with_moat(
            "reject",
            findings=[_finding("f0", dimension="citation_integrity", severity="critical")],
            fabricated=0,
            retracted=0,
        ),
    }
    gold = _goldset([_gold("a", "reject")])
    mg = metrics.moat_grounding_accuracy(reports, gold)
    assert mg.n_flagged_papers == 1
    assert mg.n_grounded_papers == 0
    assert mg.n_ungrounded_papers == 1
    assert mg.ungrounded_paper_ids == ["a"]
    assert mg.grounded_papers_human_verdicts == {}  # ungrounded -> insan-baglami eklenmez


def test_moat_grounding_excludes_literature_depth() -> None:
    """literature_depth BILINCLI disarida (derinlik/guncellik niyeti, fabricated/
    retracted ile grounding kategori-hatasi olurdu - SS35/SS38 gerekcesi)."""
    reports = {
        "a": _report_with_moat(
            "accept",
            findings=[_finding("f0", dimension="literature_depth", severity="critical")],
            fabricated=1,
        ),
    }
    gold = _goldset([_gold("a", "accept")])
    mg = metrics.moat_grounding_accuracy(reports, gold)
    assert mg.n_flagged_papers == 0  # literature_depth sayilmiyor


def test_moat_grounding_ignores_below_major_severity() -> None:
    """moderate/minor/info severity guclu iddia SAYILMAZ - sadece critical/major."""
    reports = {
        "a": _report_with_moat(
            "accept",
            findings=[_finding("f0", dimension="citation_integrity", severity="moderate")],
            fabricated=1,
        ),
    }
    gold = _goldset([_gold("a", "accept")])
    mg = metrics.moat_grounding_accuracy(reports, gold)
    assert mg.n_flagged_papers == 0


def test_moat_grounding_no_flagged_papers_returns_none_ratio() -> None:
    reports = {"a": _report("accept")}
    gold = _goldset([_gold("a", "accept")])
    mg = metrics.moat_grounding_accuracy(reports, gold)
    assert mg.n_flagged_papers == 0
    assert mg.grounded_ratio is None


def test_format_summary_includes_moat_grounding_section() -> None:
    reports = {
        "a": _report_with_moat(
            "accept",
            findings=[_finding("f0", dimension="citation_integrity", severity="critical")],
            fabricated=1,
        ),
    }
    gold = _goldset([_gold("a", "accept")])
    res = metrics.evaluate(reports, gold)
    out = metrics.format_summary(res)
    assert "Moat-doğruluk" in out
    assert "%100" in out  # 1/1 grounded


# --- confusion_matrix -------------------------------------------------------


def test_confusion_matrix_counts() -> None:
    reports = {
        "a": _report("accept"),
        "b": _report("reject"),
        "c": _report("accept"),  # insan reject → yanlış
    }
    gold = _goldset(
        [
            _gold("a", "accept"),
            _gold("b", "reject"),
            _gold("c", "reject"),
        ]
    )
    cm = metrics.confusion_matrix(reports, gold)
    idx = {v: i for i, v in enumerate(cm.labels)}
    assert cm.matrix[idx["accept"]][idx["accept"]] == 1  # a
    assert cm.matrix[idx["reject"]][idx["reject"]] == 1  # b
    assert cm.matrix[idx["reject"]][idx["accept"]] == 1  # c: insan reject, motor accept
    total = sum(sum(row) for row in cm.matrix)
    assert total == 3


# --- evaluate + format_summary ----------------------------------------------


def test_evaluate_buckets_matched_unmatched_skipped() -> None:
    reports = {
        "a": _report("accept"),  # matched
        "b": _report("reject"),  # placeholder → skipped
        "z": _report("accept"),  # altın-sette yok → unmatched
    }
    gold = _goldset([_gold("a", "accept"), _gold("b", OMER_PLACEHOLDER)])
    res = metrics.evaluate(reports, gold)
    assert res.matched_paper_ids == ["a"]
    assert res.skipped_placeholder_ids == ["b"]
    assert res.unmatched_engine_ids == ["z"]


def test_format_summary_no_data_is_honest() -> None:
    res = metrics.evaluate({}, _goldset([_gold("a", "accept")]))
    out = metrics.format_summary(res)
    assert "ÖLÇÜLEMEDİ" in out  # uydurma sayı yerine dürüst durum


def test_format_summary_reports_accuracy() -> None:
    reports = {"a": _report("accept", {"soundness": 5.0})}
    gold = _goldset([_gold("a", "accept", {"soundness": 5.0})])
    res = metrics.evaluate(reports, gold)
    out = metrics.format_summary(res, stanford_ref="Stanford 0.42")
    assert "Verdict doğruluğu" in out
    assert "Stanford 0.42" in out


# --- gerçek goldset.json yüklenebilir mi (şema uyumu) -----------------------


def test_shipped_goldset_loads_and_is_real_or_marked() -> None:
    """Paketlenen goldset.json GoldSet şemasına (extra=forbid) uyar; her girdi
    ya GERÇEK insan verdict'i ya OMER_DOLDURACAK işaretli (uydurma ara durum yok)."""
    from pathlib import Path

    from eval.review.run_eval import load_goldset

    path = Path(__file__).resolve().parents[2] / "eval" / "review" / "goldset.json"
    gs = load_goldset(path)
    assert len(gs.entries) >= 3
    valid = {"accept", "minor_revision", "major_revision", "reject", OMER_PLACEHOLDER}
    for e in gs.entries:
        assert e.human_verdict in valid
        # meta sayaçları gerçeği yansıtır
    assert gs.meta.real_entry_count == len(gs.real_entries())
