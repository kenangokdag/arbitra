"""F14-S1 belge alma (ingestion) motoru — public API.

Word / PDF / LaTeX / ZIP belge → yapılandırılmış `Manuscript`
(parse + kaynakça çıkarımı + metin-içi atıf + parse-güven kapısı).

Tek giriş: `parse_document(data, kind, filename) -> Manuscript`.

Sözleşme: api.models.review (Manuscript / ManuscriptMeta / ParsedReference /
InTextCitation) — DEĞİŞTİRİLMEZ, yalnız doldurulur. ParsedReference.status'a
DOKUNULMAZ (S2 doldurur).

Felsefe (mind-temeli + HK-7): "yok ≠ uydurma". Okunamayan/taranmış/boş girdi
dürüstçe parse_warnings'e yazılır; boş referans listesi uydurulmaz.
"""

from __future__ import annotations

import logging
from typing import Literal

from api.models.review import Manuscript
from engine.ingestion.docx_parser import parse_docx
from engine.ingestion.latex_parser import parse_latex
from engine.ingestion.pdf_parser import parse_pdf
from engine.ingestion.zip_handler import parse_zip

logger = logging.getLogger(__name__)

DocumentKind = Literal["pdf", "docx", "latex", "zip"]


def parse_document(
    data: bytes, kind: Literal["pdf", "docx", "latex", "zip"], filename: str
) -> Manuscript:
    """Belge baytlarını yapılandırılmış Manuscript'e çevir.

    Args:
        data: ham belge baytları (yüklenen dosya gövdesi).
        kind: belge türü — "pdf" | "docx" | "latex" | "zip".
        filename: orijinal dosya adı (loglama + .tex/.bbl ayrımı için).

    Returns:
        Manuscript — meta + full_text + references + in_text_citations.
        Okunamayan girdi boş referansla döner ama meta.parse_warnings dürüst not içerir.

    Raises:
        ValueError: bilinmeyen `kind`, ya da ZIP güvenlik ihlali
            (zip-bomb / dizin-kaçış). Beklenen dış-format hataları RAISE EDİLMEZ;
            parse_warnings'e dürüst yazılır.
    """
    logger.info("parse_document: kind=%s filename=%s (%d bayt)", kind, filename, len(data))

    if kind == "pdf":
        return parse_pdf(data, filename=filename)
    if kind == "docx":
        return parse_docx(data, filename=filename)
    if kind == "latex":
        tex_source = data.decode("utf-8", errors="replace")
        return parse_latex(tex_source, filename=filename)
    if kind == "zip":
        return parse_zip(data, filename=filename)

    raise ValueError(
        f"Bilinmeyen belge türü: {kind!r} (beklenen: pdf | docx | latex | zip)."
    )


__all__ = [
    "DocumentKind",
    "parse_document",
    "parse_docx",
    "parse_latex",
    "parse_pdf",
    "parse_zip",
]
