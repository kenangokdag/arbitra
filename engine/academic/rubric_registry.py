"""P03-T03 — RubricRegistry (academic_engine_spec §RubricRegistry).

(document_type, study_design, review_mode, strictness) → Rubric.

Bu modül PURE/DETERMİNİSTİK — LLM YOK, tam unit-testlenebilir. Spec'in "Belge
türüne göre temel rubrik" bölümündeki dimension listeleri burada v1 DEFAULT olarak
kodlanır. Ağırlıklar TEK tunable tabloda (_RUBRICS); dağınık magic number yok.

KANUN / dürüstlük:
  - document_type/study_design = "unknown" → genel fallback rubrik (her zaman bir
    şey döner; "hiç rubrik yok" sessiz boşluğu YASAK).
  - methodology ailesi (yöntem/veri/analiz) dimension'ları çalışma türüne göre doğru
    analiz motoruna yönlenir: qualitative→QualitativeRigorEngine,
    quantitative→QuantitativeValidityEngine (spec §Minimum viable academic coverage).
  - Ağırlıklar v1 DEFAULT (bilimsel kalibrasyon Omer audit'ine bırakıldı) — raw
    ağırlıklar normalize edilir, her rubriğin toplamı ~1.0; required dimension'lar
    optional'dan düşük ağırlık ALMAZ (tablo bu kurala göre yazıldı).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ENGINE_VERSION = "rubric_registry.v1"
RUBRIC_VERSION = "1.0"

Strictness = Literal["lenient", "standard", "strict"]

# --- analiz motorları (spec §Minimum viable academic coverage) --------------
# methodology ailesi dimension'larında engine'i ÇALIŞMA TÜRÜ belirler; tabloda
# bu sentinel ile işaretlenir, select_rubric çözümler.
_METHODOLOGY = "__METHODOLOGY__"

_QUALITATIVE_ENGINE = "QualitativeRigorEngine"
_QUANTITATIVE_ENGINE = "QuantitativeValidityEngine"
_GUIDELINE_ENGINE = "ReportingGuidelineSelector"
_CLAIM_ENGINE = "ClaimEvidenceAlignmentEngine"
_CITATION_ENGINE = "CitationIntegrityEngine"
_ETHICS_ENGINE = "EthicsTransparencyEngine"
_STRUCTURE_ENGINE = "StructureClarityEngine"

# Çalışma türü → methodology dimension'ının yönleneceği analiz motoru.
# qualitative/quantitative kati (spec başarı kapısı); diğerleri makul v1 default.
_METHODOLOGY_ENGINE_BY_DESIGN: dict[str, str] = {
    "qualitative": _QUALITATIVE_ENGINE,
    "case_study": _QUALITATIVE_ENGINE,
    "scoping_review": _QUALITATIVE_ENGINE,
    "quantitative": _QUANTITATIVE_ENGINE,
    "meta_analysis": _QUANTITATIVE_ENGINE,
    "systematic_review": _QUANTITATIVE_ENGINE,
    "computational_modeling": _QUANTITATIVE_ENGINE,
    "replication": _QUANTITATIVE_ENGINE,
    "registered_report": _QUANTITATIVE_ENGINE,
    "mixed_methods": _QUANTITATIVE_ENGINE,  # v1: quant kolu varsayılan (her iki motor ENG-2'de koşar)
    "theoretical": _CLAIM_ENGINE,
    "conceptual": _CLAIM_ENGINE,
    "design_science": _CLAIM_ENGINE,
    "dataset_resource": _CLAIM_ENGINE,
    "software_tool": _CLAIM_ENGINE,
    "protocol": _GUIDELINE_ENGINE,
}
# Yukarıda olmayan / unknown çalışma türü için methodology default motoru.
_DEFAULT_METHODOLOGY_ENGINE = _QUANTITATIVE_ENGINE

# strictness → required dimension raw-ağırlık çarpanı (normalize ÖNCESİ).
# Normalize her durumda toplamı 1.0'a çeker; strictness yalnız required/optional
# DENGESİNİ kaydırır (strict modda zorunlu boyutlar daha baskın).
_STRICTNESS_REQUIRED_MULTIPLIER: dict[str, float] = {
    "lenient": 0.85,
    "standard": 1.0,
    "strict": 1.30,
}


# --- typed çıktı ------------------------------------------------------------


class RubricDimension(BaseModel):
    """Tek değerlendirme boyutu — engine adı hangi analiz motoruna yönleneceğini söyler."""

    model_config = ConfigDict(extra="forbid")

    id: str
    weight: float = Field(..., ge=0.0, le=1.0)
    required: bool
    engine: str


class Rubric(BaseModel):
    """RubricRegistry çıktısı (academic_engine_spec §RubricRegistry → Çıktı)."""

    model_config = ConfigDict(extra="forbid")

    rubric_id: str
    version: str
    document_type: str
    study_design: str
    study_design_confidence: float = Field(0.0, ge=0.0, le=1.0)
    """2026-08-13 (bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md §46): assessment.py'nin
    study_design-bağlamlı severity guard'ları (örn. quant design-mismatch guard)
    için — bu confidence eşiğin altındaysa guard'lar çalışmaz (belirsiz
    sınıflandırmaya göre severity değiştirmek yeni bir hata sınıfı açar).
    Kullanıcı override'ıysa (DocumentClassification.user_study_design_override)
    çağıran 1.0 geçer (kesin değer, confidence kavramı uygulanmaz)."""
    review_mode: str
    strictness: str
    dimensions: list[RubricDimension] = Field(default_factory=list)
    expected_sections: list[str] = Field(default_factory=list)
    """G3 — bu belge/çalışma türünde GÖRÜLMESİ beklenen çekirdek bölümler (kanonik
    etiket, örn 'Methods'). build_section_reviews bunları manuscript bölümleriyle
    kıyaslar; eksik olan → status='missing' SectionReview. Boş liste = beklenen-bölüm
    iddiası YOK (kuramsal/kavramsal makale veya unknown → yanlış 'missing' üretme)."""


# --- v1 DEFAULT rubrik tabloları (TEK tunable kaynak) -----------------------
# Her giriş: (id, engine, required, raw_weight). raw_weight normalize edilir;
# required boyutlar optional'dan düşük raw ağırlık ALMAZ (kalibrasyon = Omer audit).
# Dimension isimleri spec §"Belge türüne göre temel rubrik"ten birebir türetildi.

_RawDim = tuple[str, str, bool, float]

# Journal article — spec satır 93-105.
_JOURNAL_ARTICLE: list[_RawDim] = [
    ("contribution_originality", _CLAIM_ENGINE, True, 2.0),
    ("research_question_fit", _CLAIM_ENGINE, True, 1.5),
    ("theoretical_framing", _CLAIM_ENGINE, False, 1.0),
    ("literature_positioning", _CITATION_ENGINE, True, 1.5),
    ("methodology_fit", _METHODOLOGY, True, 2.5),
    ("data_sample_adequacy", _METHODOLOGY, True, 1.5),
    ("analysis_validity", _METHODOLOGY, True, 2.0),
    ("claim_evidence_alignment", _CLAIM_ENGINE, True, 2.0),
    ("citation_integrity", _CITATION_ENGINE, True, 1.5),
    ("reporting_guideline_compliance", _GUIDELINE_ENGINE, False, 1.0),
    ("ethics_reproducibility", _ETHICS_ENGINE, True, 1.5),
    ("writing_structure", _STRUCTURE_ENGINE, False, 1.0),
    ("venue_fit", _STRUCTURE_ENGINE, False, 0.75),
]

# Conference paper — spec satır 108-115.
_CONFERENCE_PAPER: list[_RawDim] = [
    ("track_fit", _STRUCTURE_ENGINE, False, 0.75),
    ("novelty_to_length_ratio", _CLAIM_ENGINE, True, 1.5),
    ("technical_correctness", _METHODOLOGY, True, 2.5),
    ("reproducibility_artifact", _ETHICS_ENGINE, True, 1.5),
    ("presentation_clarity", _STRUCTURE_ENGINE, True, 1.0),
    ("contribution_clarity", _CLAIM_ENGINE, True, 1.5),
    ("ethics_limitations", _ETHICS_ENGINE, False, 1.0),
    ("reviewer_confidence", _STRUCTURE_ENGINE, False, 0.75),
]

# Thesis / dissertation — spec satır 118-130.
_THESIS: list[_RawDim] = [
    ("problem_statement", _CLAIM_ENGINE, True, 1.5),
    ("research_questions_hypotheses", _CLAIM_ENGINE, True, 1.5),
    ("chapter_coherence", _STRUCTURE_ENGINE, True, 1.0),
    ("literature_depth", _CITATION_ENGINE, True, 2.0),
    ("theoretical_framework", _CLAIM_ENGINE, True, 1.5),
    ("methodological_justification", _METHODOLOGY, True, 2.5),
    ("analysis_depth", _METHODOLOGY, True, 2.0),
    ("original_contribution", _CLAIM_ENGINE, True, 2.0),
    ("defense_readiness", _STRUCTURE_ENGINE, False, 1.0),
    ("committee_question_risk", _STRUCTURE_ENGINE, False, 1.0),
    ("publication_potential", _CLAIM_ENGINE, False, 1.0),
]

# Grant / project proposal — spec satır 133-145.
_GRANT_PROPOSAL: list[_RawDim] = [
    ("problem_significance", _CLAIM_ENGINE, True, 2.0),
    ("objectives", _CLAIM_ENGINE, True, 1.5),
    ("work_packages", _STRUCTURE_ENGINE, True, 1.5),
    ("feasibility", _METHODOLOGY, True, 2.0),
    ("team_competence", _STRUCTURE_ENGINE, False, 1.0),
    ("timeline_realism", _STRUCTURE_ENGINE, False, 1.0),
    ("budget_coherence", _STRUCTURE_ENGINE, False, 1.0),
    ("risk_mitigation", _CLAIM_ENGINE, True, 1.5),
    ("impact_pathway", _CLAIM_ENGINE, True, 1.5),
    ("dissemination", _STRUCTURE_ENGINE, False, 1.0),
    ("ethics_data_management", _ETHICS_ENGINE, True, 1.5),
    ("sustainability", _STRUCTURE_ENGINE, False, 1.0),
]

# Genel fallback — document_type bilinmiyor/desteklenmiyorsa (her zaman dürüst sonuç).
_GENERAL_FALLBACK: list[_RawDim] = [
    ("contribution_originality", _CLAIM_ENGINE, True, 1.5),
    ("literature_positioning", _CITATION_ENGINE, True, 1.5),
    ("methodology_fit", _METHODOLOGY, True, 2.0),
    ("claim_evidence_alignment", _CLAIM_ENGINE, True, 2.0),
    ("citation_integrity", _CITATION_ENGINE, True, 1.5),
    ("ethics_reproducibility", _ETHICS_ENGINE, True, 1.5),
    ("writing_structure", _STRUCTURE_ENGINE, False, 1.0),
]

# document_type → temel rubrik tablosu. Spec yalnız 4 türü açıkça verir; geri kalan
# desteklenen türler en yakın temel tabloya eşlenir (rubric_id gerçek türü taşır).
_RUBRICS: dict[str, list[_RawDim]] = {
    "journal_article": _JOURNAL_ARTICLE,
    "preprint": _JOURNAL_ARTICLE,       # preprint ≈ makale taslağı
    "book_chapter": _JOURNAL_ARTICLE,   # bölüm ≈ makale yapısı
    "technical_report": _JOURNAL_ARTICLE,
    "conference_paper": _CONFERENCE_PAPER,
    "thesis": _THESIS,
    "grant_proposal": _GRANT_PROPOSAL,
    "unknown": _GENERAL_FALLBACK,
}


# --- G3: beklenen-bölüm (expected sections) ---------------------------------
# v1 DEFAULT akademik konvansiyon (IMRaD türevi) — bilimsel kalibrasyon Omer
# audit'ine bırakıldı (spec docs/worldclass/SPECS/ beklenen-bölüm listesi VERMİYOR;
# bu yüzden makul varsayılan + named-constant + audit-flag). Her giriş:
# (kanonik_etiket, eşleşme_alt-dizgeleri). Bir bölüm, manuscript bölüm başlıklarından
# herhangi biri (normalize) bu alt-dizgelerden BİRİNİ içeriyorsa MEVCUT sayılır
# (eşanlamlı-toleranslı → 'Materials and Methods' da Methods'u karşılar; yanlış
# 'missing' üretmez). Çözüm-temelli, uydurma değil.
_IMRAD_EXPECTED: list[tuple[str, tuple[str, ...]]] = [
    ("Introduction", ("introduc", "background")),
    ("Methods", ("method", "materials", "methodolog", "approach", "procedure")),
    ("Results", ("result", "finding", "evaluation", "experiment", "analysis")),
    ("Discussion", ("discussion", "conclusion", "concluding")),
]

# IMRaD beklentisi YALNIZ ampirik çalışma türlerinde geçerli — kuramsal/kavramsal
# makalede Methods/Results bölümü beklemek YANLIŞ 'missing' üretir (dürüstlük).
_EMPIRICAL_DESIGNS: frozenset[str] = frozenset({
    "qualitative",
    "quantitative",
    "mixed_methods",
    "systematic_review",
    "meta_analysis",
    "scoping_review",
    "computational_modeling",
    "replication",
    "registered_report",
    "case_study",
})

# IMRaD yapısını izleyen belge türleri (grant_proposal/unknown HARİÇ — farklı yapı).
_IMRAD_DOC_TYPES: frozenset[str] = frozenset({
    "journal_article",
    "preprint",
    "book_chapter",
    "technical_report",
    "conference_paper",
    "thesis",
})

_WS_RE = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS_RE.sub(" ", (text or "").strip().lower())


def expected_sections_for(document_type: str, study_design: str) -> list[str]:
    """Belge+çalışma türünde beklenen çekirdek bölümler (kanonik etiket listesi).

    AMPİRİK çalışma + IMRaD-belge türü → ['Introduction','Methods','Results','Discussion'].
    Aksi (kuramsal/kavramsal tasarım, grant/unknown belge) → [] (beklenti yok →
    yanlış 'missing' üretilmez). v1 DEFAULT — Omer bilimsel-audit flag'i."""
    if document_type in _IMRAD_DOC_TYPES and study_design in _EMPIRICAL_DESIGNS:
        return [label for label, _ in _IMRAD_EXPECTED]
    return []


def missing_sections(expected: list[str], section_titles: list[str]) -> list[str]:
    """expected etiketlerinden manuscript başlıklarında BULUNMAYANLARI döndür (sıralı).

    Eşleşme: bir başlık (normalize) etiketin alt-dizgelerinden birini içeriyorsa o
    bölüm MEVCUT. Hiçbir başlık içermiyorsa o etiket EKSİK. expected'taki sıra korunur."""
    norm_titles = [_norm(t) for t in section_titles]
    keyword_map = dict(_IMRAD_EXPECTED)
    missing: list[str] = []
    for label in expected:
        keywords = keyword_map.get(label, (_norm(label),))
        present = any(any(kw in t for kw in keywords) for t in norm_titles)
        if not present:
            missing.append(label)
    return missing


# --- seçim ------------------------------------------------------------------


def _methodology_engine(study_design: str) -> str:
    """methodology dimension'ı için çalışma türüne göre analiz motorunu çöz."""
    return _METHODOLOGY_ENGINE_BY_DESIGN.get(study_design, _DEFAULT_METHODOLOGY_ENGINE)


def _resolve_engine(raw_engine: str, study_design: str) -> str:
    if raw_engine == _METHODOLOGY:
        return _methodology_engine(study_design)
    return raw_engine


def _normalize(
    raw_dims: list[_RawDim],
    study_design: str,
    required_multiplier: float,
) -> list[RubricDimension]:
    """raw ağırlıkları normalize et (toplam ~1.0) + engine'leri çöz.

    required boyutlara strictness çarpanı uygulanır (normalize ÖNCESİ); normalize
    toplamı her durumda 1.0'a getirir."""
    weighted: list[tuple[str, str, bool, float]] = []
    for dim_id, raw_engine, required, raw_w in raw_dims:
        w = raw_w * required_multiplier if required else raw_w
        engine = _resolve_engine(raw_engine, study_design)
        weighted.append((dim_id, engine, required, w))

    total = sum(w for _, _, _, w in weighted)
    if total <= 0.0:
        # Asla olmamalı (tüm tablolarda pozitif ağırlık var) ama 0'a bölme koruması:
        # eşit dağıt (dürüst, sessiz çökme yok).
        n = len(weighted)
        equal = 1.0 / n if n else 0.0
        return [
            RubricDimension(id=d, weight=equal, required=r, engine=e)
            for d, e, r, _ in weighted
        ]

    return [
        RubricDimension(id=d, weight=w / total, required=r, engine=e)
        for d, e, r, w in weighted
    ]


def select_rubric(
    *,
    document_type: str,
    study_design: str,
    study_design_confidence: float = 0.0,
    review_mode: str = "author",
    strictness: Strictness = "standard",
) -> Rubric:
    """Belge + çalışma türüne göre rubrik seç (academic_engine_spec §RubricRegistry).

    Args:
        document_type: DocumentClassification.effective_document_type ('unknown' → fallback).
        study_design: DocumentClassification.effective_study_design (methodology routing).
        study_design_confidence: DocumentClassification.study_design_confidence — kullanıcı
            override'ıysa çağıran 1.0 geçmeli (kesin değer). assessment.py'nin study_design-
            bağlamlı guard'ları bunu okur (2026-08-13, §46).
        review_mode: 'author' | 'editor' — v1'de dimension setini DEĞİŞTİRMEZ (provenance'a
            taşınır; ton review_orchestration'da ayarlanır). Spec input'u olarak kabul edilir.
        strictness: 'lenient' | 'standard' | 'strict' — required boyutların baskınlığını
            ayarlar (normalize toplamı her zaman ~1.0).

    Returns:
        Rubric — rubric_id (örn 'journal_article.qualitative.v1'), version, dimensions[].
        Bilinmeyen document_type → genel fallback (rubric_id türü dürüstçe yansıtır).
    """
    raw_dims = _RUBRICS.get(document_type, _GENERAL_FALLBACK)
    multiplier = _STRICTNESS_REQUIRED_MULTIPLIER.get(strictness, 1.0)
    dimensions = _normalize(raw_dims, study_design, multiplier)

    rubric_id = f"{document_type or 'unknown'}.{study_design or 'unknown'}.v{RUBRIC_VERSION.split('.')[0]}"

    return Rubric(
        rubric_id=rubric_id,
        version=RUBRIC_VERSION,
        document_type=document_type or "unknown",
        study_design=study_design or "unknown",
        study_design_confidence=study_design_confidence,
        review_mode=review_mode,
        strictness=strictness,
        dimensions=dimensions,
        expected_sections=expected_sections_for(
            document_type or "unknown", study_design or "unknown"
        ),
    )


__all__ = [
    "ENGINE_VERSION",
    "RUBRIC_VERSION",
    "Rubric",
    "RubricDimension",
    "Strictness",
    "expected_sections_for",
    "missing_sections",
    "select_rubric",
]
