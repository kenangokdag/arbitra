"""F14-S1 belge alma — ham parse parçalarından Manuscript inşası.

Format parser'ları (pdf/docx/latex) gövde metni + kaynakça blok satırlarını
buraya verir; builder ortak alanları (referanslar, metin-içi atıf, meta) üretir.
Tek yerde toplanır ki tüm formatlar AYNI çıkarım kalitesini paylaşsın.

KANUN (review.py sözleşmesi): ParsedReference.status'a DOKUNMA — default
"not_found_in_index" kalır, S2 doldurur. Sen yalnız raw/title/authors/year/doi/
venue/parse_confidence yazarsın.
"""

from __future__ import annotations

from api.models.review import (
    InTextCitation,
    Manuscript,
    ManuscriptMeta,
    ParsedReference,
)
from engine.ingestion import common


def build_references(entries: list[str]) -> list[ParsedReference]:
    """Gruplanmış ham referans girdilerini ParsedReference listesine çevir.

    Her girdi için: numara önekini at, DOI/yıl/yazar/başlık ayıkla, güven hesapla.
    status/openalex/evidence ALANLARINA dokunma (S2 doldurur).
    """
    refs: list[ParsedReference] = []
    for i, entry in enumerate(entries, start=1):
        raw = entry.strip()
        if not raw:
            continue
        body = common.strip_reference_number(raw)
        doi = common.extract_doi(body)
        authors, year, title = common.extract_authors_year_title(body)
        confidence = common.reference_confidence(
            title=title, authors=authors, year=year, doi=doi
        )
        refs.append(
            ParsedReference(
                index=i,
                raw=raw,
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                venue=None,  # venue ayrımı belirsiz → uydurma yok (HK-7)
                parse_confidence=confidence,
            )
        )
    return refs


def build_in_text_citations(
    body_text: str, references: list[ParsedReference]
) -> list[InTextCitation]:
    """Gövde metninden metin-içi atıfları (numaralı + Yazar-Yıl) çıkar.

    Numaralı işaretler ([n]) referans index'ine eşlenmeye çalışılır.
    Aralık ([1-3]) ve çoklu ([1,2]) işaretlerde ilk numara ref_index olarak kullanılır
    (kesinleştirme S3'ün işi; burada yalnız ham bağlantı kurulur).
    """
    n_refs = len(references)
    citations: list[InTextCitation] = []
    for marker, sentence in common.find_intext_citations(body_text):
        ref_index = _resolve_ref_index(marker, n_refs)
        citations.append(
            InTextCitation(
                marker=marker,
                sentence=sentence,
                section=None,
                ref_index=ref_index,
            )
        )
    return citations


def _resolve_ref_index(marker: str, n_refs: int) -> int | None:
    """Numaralı işaretten ([3], [1-2], [1,4]) ilk geçerli ref_index'i çıkar.

    (Yazar, Yıl) işaretleri sayı taşımaz → None (S3 eşler).
    Numara referans aralığı dışındaysa None (uydurma eşleme yok).
    """
    if not (marker.startswith("[") and marker.endswith("]")):
        return None
    inner = marker[1:-1]
    first = ""
    for ch in inner:
        if ch.isdigit():
            first += ch
        elif first:
            break
    if not first:
        return None
    idx = int(first)
    if 1 <= idx <= n_refs:
        return idx
    return None


def assemble_manuscript(
    *,
    full_text: str,
    section_lines: list[str],
    reference_entries: list[str],
    body_for_citations: str,
    extra_warnings: list[str],
    base_confidence: float,
    title: str | None = None,
    abstract: str | None = None,
) -> Manuscript:
    """Tüm format parser'larının ortak son adımı — Manuscript kur.

    base_confidence: format-katmanı güveni (metin gerçekten okunabildi mi).
    Nihai meta.parse_confidence = base * (referans çıkarım kalitesi faktörü).
    """
    warnings = list(extra_warnings)

    references = build_references(reference_entries)
    in_text = build_in_text_citations(body_for_citations, references)
    section_titles = common.find_section_titles(section_lines)
    word_count = common.count_words(full_text)
    language = common.guess_language(full_text)

    if not references:
        warnings.append(
            "Kaynakça çıkarılamadı (başlık bulunamadı ya da blok boş) — "
            "referans listesi boş bırakıldı, uydurulmadı."
        )
    if word_count == 0:
        warnings.append("Belgede okunabilir metin bulunamadı.")

    confidence = _final_confidence(base_confidence, references, word_count)

    meta = ManuscriptMeta(
        title=title,
        abstract=abstract,
        language=language,
        section_titles=section_titles,
        word_count=word_count,
        reference_count=len(references),
        parse_confidence=confidence,
        parse_warnings=warnings,
    )
    return Manuscript(
        meta=meta,
        full_text=full_text,
        references=references,
        in_text_citations=in_text,
    )


def _final_confidence(
    base: float, references: list[ParsedReference], word_count: int
) -> float:
    """Format güveni + içerik sinyallerini birleşik parse_confidence'a çevir.

    - Metin yoksa 0 (her şey çöker).
    - Referans yoksa base'i 0.5 ile çarp (gövde okundu ama kaynakça kaçtı).
    - Referans varsa ortalama referans güveni base'e harmanlanır.
    """
    if word_count == 0:
        return 0.0
    if not references:
        return round(base * 0.5, 3)
    avg_ref = sum(r.parse_confidence for r in references) / len(references)
    # %70 format güveni + %30 referans çıkarım kalitesi.
    combined = base * 0.7 + avg_ref * 0.3
    return round(min(combined, 1.0), 3)


__all__ = [
    "assemble_manuscript",
    "build_in_text_citations",
    "build_references",
]
