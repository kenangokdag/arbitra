"""F14 EVAL — METRİK MOTORU (saf fonksiyonlar, test edilebilir).

Girdi: motor ReviewReport listesi + GoldSet (eşleşme paper_id ↔ paper_id).
Çıktı: insan-uyum metrikleri (R-3 "Stanford kalite" kanıtı).

SAFLIK: bu modül LLM/ağ ÇAĞIRMAZ. Sadece hazır ReviewReport + GoldEntry alır,
sayı üretir → fixture'la birebir test edilir.

DÜRÜSTLÜK: OMER_DOLDURACAK işaretli insan verdict/skor KIYASLAMAYA GİRMEZ
(uydurma sayı yasağı). Yeterli gerçek veri yoksa metrik None döner + dürüst not.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, get_args

from scipy import stats  # type: ignore[import-untyped]  # zaten kurulu (scipy 1.17)

from api.models.review import DimensionKey, ReviewReport, Verdict
from eval.review.schema import OMER_PLACEHOLDER, GoldEntry, GoldSet

# Verdict'in kademe SIRASI (1-kademe-tolerans + ordinal mesafe için).
# en olumlu → en olumsuz.
_VERDICT_ORDER: tuple[Verdict, ...] = (
    "accept",
    "minor_revision",
    "major_revision",
    "reject",
)
_VERDICT_RANK: dict[Verdict, int] = {v: i for i, v in enumerate(_VERDICT_ORDER)}

_ALL_DIMENSIONS: tuple[DimensionKey, ...] = get_args(DimensionKey)


# --- sonuç şemaları (saf veri) ----------------------------------------------


@dataclass(frozen=True)
class VerdictAccuracy:
    """Motor verdict ↔ insan verdict uyumu."""

    n: int  # kıyaslanan (gerçek insan verdict'li) çift sayısı
    exact: int  # tam eşleşen
    within_one: int  # ≤1 kademe uzak (1-kademe-tolerans)
    exact_accuracy: float | None  # exact / n
    within_one_accuracy: float | None  # within_one / n


@dataclass(frozen=True)
class DimensionAgreement:
    """Tek boyut için motor skoru ↔ insan skoru uyumu."""

    dimension: DimensionKey
    n: int  # bu boyutta gerçek insan skoru olan çift sayısı
    spearman: float | None  # n<3 ya da sabit dizi → None
    pearson: float | None
    mean_abs_diff: float | None  # ortalama MUTLAK fark — hata BÜYÜKLÜĞÜ (yönsüz)
    mean_signed_diff: float | None  # ARBITRA_RESEARCH_BRIEF.md Görev D — ortalama
    # (motor − insan) — YÖN taşır: pozitif = sistematik ŞİŞİRME, negatif =
    # sistematik SIKI puanlama. mean_abs_diff ile karıştırılmamalı: "+2/-2
    # karışık hata" ile "hep +2 şişirme" ikisi de aynı mean_abs_diff'i verir
    # ama mean_signed_diff bunları ayırt eder (0'a yakın vs. +2'ye yakın).


@dataclass(frozen=True)
class MoatGroundingAccuracy:
    """citation_integrity/literature_positioning boyutlarındaki critical/major
    bulguların EvidencePack'in DETERMİNİSTİK fabricated/retracted olgularına
    DAYANIP DAYANMADIĞINI ölçer — insan-verdict'ten BAĞIMSIZ.

    2026-08-10 (bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md §37/§38): motor artık
    gerçek atıf sahteciliğini yakalıyor (EvidencePack wiring, §31/32) ama
    goldset'in insan-verdict metriği bunu ÖDÜLLENDİRMİYOR — 61 makalelik
    koşumda moat-gate'in 6 tetiklemesinden 5'i insan tarafından "accept"
    edilmiş makalelerde (hakemler atıf-sahteciliği denetlemedi/edemedi). Bu
    metrik "insanla ne kadar uyuştu" değil, "moat'ın GÜÇLÜ iddiası GERÇEKTEN
    kanıta mı dayanıyor" sorusunu ölçer — moat'ın kendi iç-tutarlılığı/DOĞRULUĞU,
    insan-verdict karşılaştırmasının göremediği bir boyut.

    'Grounded' = o makalenin EvidencePack.citation_integrity.fabricated>0 VEYA
    .retracted>0 VEYA context_findings'te support=="contradicted" olan bir kayıt
    var (academic_dimension.py'nin kendi kuralı bu üçünü de major/critical'i HAK
    EDEN gerekçe sayıyor — ilk sürümde 'contradicted' unutulmuştu, guardian
    bulgusuyla düzeltildi). Makale-seviyesinde kontrol — bulgu-seviyesinde hangi
    referans indeksine atıf yaptığını metin-eşleştirmeyle çıkarmıyoruz, kırılgan olurdu,
    bkz. dürüstlük notu modül docstring'inde).
    """

    n_flagged_papers: int  # citation_integrity/literature_positioning'de critical/major bulgu olan makale sayısı
    n_grounded_papers: int  # bunlardan EvidencePack'te gerçek fabricated/retracted karşılığı olanlar
    n_ungrounded_papers: int  # karşılığı OLMAYANLAR — potansiyel LLM aşırı-iddiası, incelenmeli
    grounded_ratio: float | None
    ungrounded_paper_ids: list[str]
    # bağlam (insan-uyum İDDİASI değil, sadece görünürlük): grounded makalelerin
    # insan kararı ne — goldset'in bu boyutu hiç ölçemediğini somutlaştırır.
    grounded_papers_human_verdicts: dict[str, str]


@dataclass(frozen=True)
class ConfusionMatrix:
    """Verdict 4x4 — satır=insan, sütun=motor."""

    labels: tuple[Verdict, ...]
    matrix: list[list[int]]  # matrix[i][j] = insan i, motor j sayısı


@dataclass
class EvalResult:
    """Tüm metriklerin toplu sonucu + dürüstlük notları."""

    verdict_accuracy: VerdictAccuracy
    dimension_agreement: list[DimensionAgreement]
    confusion: ConfusionMatrix
    moat_grounding: MoatGroundingAccuracy
    matched_paper_ids: list[str] = field(default_factory=list)
    unmatched_engine_ids: list[str] = field(default_factory=list)
    skipped_placeholder_ids: list[str] = field(default_factory=list)


# --- eşleştirme -------------------------------------------------------------


def _gold_by_id(goldset: GoldSet) -> dict[str, GoldEntry]:
    return {e.paper_id: e for e in goldset.entries}


# --- verdict doğruluğu ------------------------------------------------------


def verdict_accuracy(
    reports: dict[str, ReviewReport], goldset: GoldSet
) -> VerdictAccuracy:
    """Motor verdict == insan verdict oranı + 1-kademe-tolerans.

    OMER_DOLDURACAK işaretli (gerçek olmayan) insan verdict'leri ATLANIR.
    """
    gold = _gold_by_id(goldset)
    exact = 0
    within_one = 0
    n = 0
    for pid, report in reports.items():
        entry = gold.get(pid)
        if entry is None:
            continue
        if entry.human_verdict == OMER_PLACEHOLDER:
            continue  # gerçek değil → kıyaslama yok (uydurma yasağı)
        human: Verdict = entry.human_verdict  # type: ignore[assignment]
        n += 1
        if report.verdict == human:
            exact += 1
        if abs(_VERDICT_RANK[report.verdict] - _VERDICT_RANK[human]) <= 1:
            within_one += 1
    return VerdictAccuracy(
        n=n,
        exact=exact,
        within_one=within_one,
        exact_accuracy=(exact / n) if n else None,
        within_one_accuracy=(within_one / n) if n else None,
    )


# --- boyut uyumu ------------------------------------------------------------


def _engine_dim_scores(report: ReviewReport) -> dict[DimensionKey, float]:
    return {ds.key: ds.score for ds in report.dimension_scores}


def dimension_agreement(
    reports: dict[str, ReviewReport], goldset: GoldSet
) -> list[DimensionAgreement]:
    """Her boyut için motor skoru ↔ insan skoru Spearman/Pearson + ort. mutlak fark.

    Yalnız insan_scores'ta GERÇEKTEN bulunan boyut anahtarları kıyaslanır
    (eksik anahtar = o boyut ölçülmedi → atla). n<3 ise korelasyon None
    (anlamlı korelasyon için yetersiz örnek — dürüst).
    """
    gold = _gold_by_id(goldset)
    out: list[DimensionAgreement] = []
    for dim in _ALL_DIMENSIONS:
        engine_vals: list[float] = []
        human_vals: list[float] = []
        for pid, report in reports.items():
            entry = gold.get(pid)
            if entry is None:
                continue
            if dim not in entry.human_scores:
                continue  # bu boyut bu makalede ölçülmedi (uydurma yok)
            eng = _engine_dim_scores(report)
            if dim not in eng:
                continue  # motor bu boyutu üretmedi
            engine_vals.append(eng[dim])
            human_vals.append(float(entry.human_scores[dim]))

        n = len(engine_vals)
        spearman = _safe_corr(stats.spearmanr, engine_vals, human_vals)
        pearson = _safe_corr(stats.pearsonr, engine_vals, human_vals)
        mad: float | None = None
        signed: float | None = None
        if n:
            diffs = [e - h for e, h in zip(engine_vals, human_vals, strict=True)]
            mad = sum(abs(d) for d in diffs) / n
            signed = sum(diffs) / n
        out.append(
            DimensionAgreement(
                dimension=dim,
                n=n,
                spearman=spearman,
                pearson=pearson,
                mean_abs_diff=(round(mad, 4) if mad is not None else None),
                mean_signed_diff=(round(signed, 4) if signed is not None else None),
            )
        )
    return out


def _safe_corr(
    func: Callable[[list[float], list[float]], Any], a: list[float], b: list[float]
) -> float | None:
    """Korelasyon güvenli sarmalayıcı: n<3 ya da sabit dizi → None.

    Korelasyon en az 3 nokta ister; sabit dizide tanımsızdır (NaN). Bunları
    sessizce sayı uydurmak yerine None döneriz (dürüst yetersiz-veri).
    """
    if len(a) < 3 or len(b) < 3:
        return None
    if len(set(a)) < 2 or len(set(b)) < 2:
        return None  # sabit dizi → korelasyon tanımsız
    res = func(a, b)
    corr = float(res.statistic)
    if corr != corr:  # NaN guard
        return None
    return round(corr, 4)


# --- moat-doğruluk (insan-verdict'ten bağımsız) ------------------------------

_MOAT_INTEGRITY_DIMENSIONS = frozenset({"citation_integrity", "literature_positioning"})
# literature_depth BİLİNÇLİ OLARAK dışarıda: onun niyeti derinlik/güncellik
# (bkz. dimension_engine.py intent metni), fabricated/retracted ile grounding
# yapmak kategori-hatası olurdu (guardian SS35 bulgusu).
#
# 2026-08-10 DÜZELTME (guardian bulgusu, §38): bu yorum ÖNCEDEN "report_synthesis.py'nin
# moat-gate kapsamı da aynı gerekçeyle bu boyutu dışarıda tutuyor" diyordu — bu
# YANLIŞTI, doğrulanmadan yazılmış bir iddiaydı (report_synthesis.py'ye BAKMADAN).
# Gerçekte moat-gate'in `_CITATION_MOAT_DIMENSION_IDS`'i o SIRADA literature_depth'i
# DAHİL ediyordu — bu metrik ile moat-gate'in kapsamı TUTARSIZDI (kanıtsız bir
# "critical" literature_depth bulgusu guard'dan geçmeden moat-gate'e ulaşıp makaleyi
# "reject"e kilitleyebiliyordu). report_synthesis.py'nin `_CITATION_MOAT_DIMENSION_IDS`'i
# bu turda literature_depth'i çıkaracak şekilde DÜZELTİLDİ — artık bu metrik ile
# moat-gate'in kapsamı GERÇEKTEN eşleşiyor (iddia artık doğrulanabilir).
_MOAT_HIGH_SEVERITY = frozenset({"critical", "major"})


def moat_grounding_accuracy(
    reports: dict[str, ReviewReport], goldset: GoldSet
) -> MoatGroundingAccuracy:
    """Bkz. MoatGroundingAccuracy docstring'i — insan-verdict'ten bağımsız,
    moat'ın GÜÇLÜ iddialarının deterministik kanıta dayanıp dayanmadığını ölçer."""
    gold = _gold_by_id(goldset)
    flagged: list[str] = []
    grounded: list[str] = []
    ungrounded: list[str] = []
    human_verdicts: dict[str, str] = {}

    for pid, report in reports.items():
        has_high_sev = any(
            f.dimension in _MOAT_INTEGRITY_DIMENSIONS and f.severity in _MOAT_HIGH_SEVERITY
            for f in report.findings
        )
        if not has_high_sev:
            continue
        flagged.append(pid)
        ci = report.evidence_pack.citation_integrity
        has_contradicted = any(
            cf.support == "contradicted" for cf in report.evidence_pack.context_findings
        )
        # 2026-08-10 guardian bulgusu: academic_dimension.py'nin kendi kuralı
        # (satır ~41-42) "contradicted" atıf-bağlam bulgusunu da major/critical'i
        # HAK EDEN üçüncü bir gerekçe sayıyor — ilk sürümde bu unutulmuştu,
        # "grounded" oranını olduğundan düşük gösteriyordu.
        if ci.fabricated > 0 or ci.retracted > 0 or has_contradicted:
            grounded.append(pid)
            entry = gold.get(pid)
            if entry is not None and entry.human_verdict != OMER_PLACEHOLDER:
                human_verdicts[pid] = str(entry.human_verdict)
        else:
            ungrounded.append(pid)

    n = len(flagged)
    return MoatGroundingAccuracy(
        n_flagged_papers=n,
        n_grounded_papers=len(grounded),
        n_ungrounded_papers=len(ungrounded),
        grounded_ratio=(len(grounded) / n) if n else None,
        ungrounded_paper_ids=sorted(ungrounded),
        grounded_papers_human_verdicts=human_verdicts,
    )


# --- karışıklık matrisi -----------------------------------------------------


def confusion_matrix(
    reports: dict[str, ReviewReport], goldset: GoldSet
) -> ConfusionMatrix:
    """Verdict 4x4. Satır = insan, sütun = motor. Placeholder atlanır."""
    gold = _gold_by_id(goldset)
    idx = _VERDICT_RANK
    matrix = [[0 for _ in _VERDICT_ORDER] for _ in _VERDICT_ORDER]
    for pid, report in reports.items():
        entry = gold.get(pid)
        if entry is None or entry.human_verdict == OMER_PLACEHOLDER:
            continue
        human: Verdict = entry.human_verdict  # type: ignore[assignment]
        matrix[idx[human]][idx[report.verdict]] += 1
    return ConfusionMatrix(labels=_VERDICT_ORDER, matrix=matrix)


# --- toplu değerlendirme ----------------------------------------------------


def evaluate(reports: dict[str, ReviewReport], goldset: GoldSet) -> EvalResult:
    """Tüm metrikleri hesapla + eşleşme/atlama dökümünü topla."""
    gold = _gold_by_id(goldset)
    matched: list[str] = []
    unmatched: list[str] = []
    skipped: list[str] = []
    for pid in reports:
        entry = gold.get(pid)
        if entry is None:
            unmatched.append(pid)
        elif entry.human_verdict == OMER_PLACEHOLDER:
            skipped.append(pid)
        else:
            matched.append(pid)
    return EvalResult(
        verdict_accuracy=verdict_accuracy(reports, goldset),
        dimension_agreement=dimension_agreement(reports, goldset),
        confusion=confusion_matrix(reports, goldset),
        moat_grounding=moat_grounding_accuracy(reports, goldset),
        matched_paper_ids=sorted(matched),
        unmatched_engine_ids=sorted(unmatched),
        skipped_placeholder_ids=sorted(skipped),
    )


# --- insan-dili özet --------------------------------------------------------


def format_summary(result: EvalResult, *, stanford_ref: str = "") -> str:
    """Metrikleri insan-dili rapora çevir (son-kullanıcı dili, jargonsuz)."""
    va = result.verdict_accuracy
    lines: list[str] = ["=== F14 HAKEMLİK — KALİTE KANITI (insan-uyum) ==="]

    if va.n == 0:
        if not result.matched_paper_ids and not result.skipped_placeholder_ids:
            why = "motor henüz hiçbir altın-set makalesini değerlendirmedi (canlı koşum bekliyor)"
        elif result.skipped_placeholder_ids and not result.matched_paper_ids:
            why = "eşleşen makalelerin insan kararı OMER_DOLDURACAK (Omer doldurunca ölçülür)"
        else:
            why = "kıyaslanacak gerçek insan kararı + motor çıktısı çifti yok"
        lines.append(f"Verdict doğruluğu: ÖLÇÜLEMEDİ — {why}.")
    else:
        ex = f"%{va.exact_accuracy * 100:.0f}" if va.exact_accuracy is not None else "?"
        w1 = (
            f"%{va.within_one_accuracy * 100:.0f}"
            if va.within_one_accuracy is not None
            else "?"
        )
        lines.append(
            f"Verdict doğruluğu: {ex} tam isabet, {w1} bir-kademe-tolerans "
            f"({va.exact}/{va.n} tam, {va.within_one}/{va.n} yakın)."
        )

    lines.append("")
    lines.append("Boyut uyumu (motor skoru ↔ insan skoru):")
    any_dim = False
    for da in result.dimension_agreement:
        if da.n == 0:
            continue
        any_dim = True
        sp = f"r={da.spearman:.2f}" if da.spearman is not None else "r=yetersiz-veri"
        mad = (
            f"ort. fark={da.mean_abs_diff:.2f}"
            if da.mean_abs_diff is not None
            else "ort. fark=?"
        )
        bias = (
            f"şişirme={da.mean_signed_diff:+.2f}"
            if da.mean_signed_diff is not None
            else "şişirme=?"
        )
        lines.append(f"  - {da.dimension}: {sp}, {mad}, {bias} (n={da.n})")
    if not any_dim:
        lines.append(
            "  (Hiçbir boyutta gerçek insan skoru yok — Omer doldurunca hesaplanır.)"
        )

    mg = result.moat_grounding
    lines.append("")
    lines.append("Moat-doğruluk (atıf sahteciliği — insan-verdict'ten BAĞIMSIZ):")
    if mg.n_flagged_papers == 0:
        lines.append("  Hiçbir makalede critical/major atıf-bütünlüğü bulgusu yok.")
    else:
        gr = f"%{mg.grounded_ratio * 100:.0f}" if mg.grounded_ratio is not None else "?"
        lines.append(
            f"  {mg.n_flagged_papers} makalede güçlü (critical/major) atıf-bütünlüğü "
            f"iddiası; {gr} kanıta dayalı ({mg.n_grounded_papers}/{mg.n_flagged_papers} "
            f"EvidencePack'te gerçek fabricated/retracted karşılığı var)."
        )
        if mg.n_ungrounded_papers:
            lines.append(
                f"  UYARI: {mg.n_ungrounded_papers} makalede kanıtsız güçlü iddia — "
                f"incele: {', '.join(mg.ungrounded_paper_ids)}"
            )
        if mg.grounded_papers_human_verdicts:
            by_verdict: dict[str, int] = {}
            for v in mg.grounded_papers_human_verdicts.values():
                by_verdict[v] = by_verdict.get(v, 0) + 1
            lines.append(
                "  Kanıta dayalı tespitlerin insan kararı dağılımı "
                f"(goldset'in kör noktası): {by_verdict}"
            )

    lines.append("")
    lines.append(
        f"Eşleşen makale: {len(result.matched_paper_ids)} | "
        f"motor var-altın yok: {len(result.unmatched_engine_ids)} | "
        f"insan-bekliyor (atlandı): {len(result.skipped_placeholder_ids)}"
    )

    if stanford_ref:
        lines.append("")
        lines.append(f"Referans: {stanford_ref}")
    return "\n".join(lines)


__all__ = [
    "ConfusionMatrix",
    "DimensionAgreement",
    "EvalResult",
    "MoatGroundingAccuracy",
    "VerdictAccuracy",
    "confusion_matrix",
    "dimension_agreement",
    "evaluate",
    "format_summary",
    "moat_grounding_accuracy",
    "verdict_accuracy",
]
