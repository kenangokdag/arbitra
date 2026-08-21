"""F14-S1 belge alma — Word (.docx) parser (python-docx).

Çıkarır:
  - paragraf metni (gövde)
  - başlıklar (Heading stilleri → section_titles)
  - kaynakça (References/Kaynakça başlığı sonrası paragraflar)
  - metin-içi atıf (ortak çıkarıcı)

KANUN (HK-7 + plan-first OPEN_WORK): python-docx (`docx`) proje .venv'inde KURULU
DEĞİL (doğrulandı: `.venv/bin/python -c "import docx"` → ModuleNotFoundError).
Bu yüzden import LAZY (çağrı anında) yapılır — paket eksikse `from engine.ingestion
import parse_document` yine de TEMİZ import olur; .docx parse çağrılınca dürüst
"kurulu değil" uyarısı döner (halüsinasyon değil, itiraf).

Bozuk/şifreli docx → PackageNotFoundError yakalanır, parse_warnings'e dürüst
yazılır, boş Manuscript döner (uydurma yok). Diğer hatalar yutulmaz, raise edilir.
"""

from __future__ import annotations

import io
import logging
import zipfile

from api.models.review import Manuscript
from engine.ingestion import builder, common

logger = logging.getLogger(__name__)


def _empty(warnings: list[str]) -> Manuscript:
    """Okunamayan girdi için dürüst boş Manuscript (uydurma yok)."""
    return builder.assemble_manuscript(
        full_text="",
        section_lines=[],
        reference_entries=[],
        body_for_citations="",
        extra_warnings=warnings,
        base_confidence=0.0,
    )


def parse_docx(data: bytes, *, filename: str = "manuscript.docx") -> Manuscript:
    """.docx baytları → Manuscript.

    python-docx kurulu değilse → dürüst uyarı + boş Manuscript (itiraf, uydurma yok).
    Dış-format hatası (bozuk paket) parse_warnings'e dürüst yazılır; iç beklenmeyen
    hata RAISE edilir (hata-yutma yasak).
    """
    warnings: list[str] = []
    try:
        from docx import Document  # type: ignore[import-untyped]
        from docx.opc.exceptions import (  # type: ignore[import-untyped]
            PackageNotFoundError,
        )
    except ImportError:
        warnings.append(
            "Word (.docx) parse yapılamadı: python-docx kurulu değil. "
            "Kurulum: pip install python-docx."
        )
        return _empty(warnings)

    try:
        document = Document(io.BytesIO(data))
    except (PackageNotFoundError, zipfile.BadZipFile, KeyError):
        # PackageNotFoundError: docx-wrapped; BadZipFile: zip-magic ama bozuk arşiv;
        # KeyError: zip açıldı ama docx parça eksik. Hepsi "açılamadı" — dürüst, çökme yok.
        warnings.append(
            "Word dosyası açılamadı (geçerli bir .docx paketi değil ya da bozuk)."
        )
        return _empty(warnings)

    paragraphs: list[str] = []
    heading_titles: list[str] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        paragraphs.append(text)
        style_name = (para.style.name or "") if para.style else ""
        if style_name.lower().startswith("heading") or style_name.lower() == "title":
            heading_titles.append(text)

    if not paragraphs:
        warnings.append("Word dosyasında okunabilir paragraf bulunamadı.")

    full_text = "\n".join(paragraphs)

    # Başlık: ilk 'Title' stilli paragraf, yoksa ilk başlık, yoksa None (uydurma yok).
    title = heading_titles[0] if heading_titles else None

    # Abstract: 'abstract'/'özet' başlığını izleyen paragraf.
    abstract = _find_abstract(paragraphs)

    # Kaynakça: paragraf satırlarından kaynakça bloğunu kes.
    bib_block = common.slice_bibliography(paragraphs)
    if bib_block is None:
        bib_entries: list[str] = []
        warnings.append(
            "Word belgesinde kaynakça başlığı (References/Kaynakça) bulunamadı."
        )
    else:
        bib_entries = common.group_reference_entries(bib_block)

    # Gövde (metin-içi atıf için): kaynakçayı dışla ki referans satırları atıf sanılmasın.
    body_for_citations = _body_excluding_bibliography(paragraphs)

    base_conf = 0.85  # docx metni güvenilir okunur (stil meta'sı + akış net)

    logger.info(
        "docx parse: %s — %d paragraf, %d başlık, %d referans",
        filename,
        len(paragraphs),
        len(heading_titles),
        len(bib_entries),
    )
    # section_lines: hem stil-başlıkları hem heuristik başlıklar görülsün.
    section_lines = heading_titles + paragraphs
    return builder.assemble_manuscript(
        full_text=full_text,
        section_lines=section_lines,
        reference_entries=bib_entries,
        body_for_citations=body_for_citations,
        extra_warnings=warnings,
        base_confidence=base_conf,
        title=title,
        abstract=abstract,
    )


def _find_abstract(paragraphs: list[str]) -> str | None:
    """'Abstract'/'Özet' başlığını izleyen ilk içerik paragrafını döndür."""
    for i, p in enumerate(paragraphs):
        low = p.strip().lower().strip(" .:")
        if low in ("abstract", "özet", "ozet") and i + 1 < len(paragraphs):
            return paragraphs[i + 1]
        # "Abstract: gövde" tek paragraf kalıbı
        if low.startswith("abstract:") or low.startswith("özet:"):
            return p.split(":", 1)[1].strip() or None
    return None


def _body_excluding_bibliography(paragraphs: list[str]) -> str:
    """Kaynakça başlığına kadar olan gövdeyi döndür (metin-içi atıf taraması için)."""
    body: list[str] = []
    for p in paragraphs:
        if common.is_bibliography_heading(p):
            break
        body.append(p)
    return "\n".join(body)


__all__ = ["parse_docx"]
