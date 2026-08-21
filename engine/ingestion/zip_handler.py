r"""F14-S1 belge alma — ZIP açıcı + içerik tipi yönlendirme.

ZIP genelde iki şeyden biridir:
  A) LaTeX projesi: ana .tex (\documentclass içeren) + opsiyonel .bbl/.bib
  B) PDF (+ ekler): tek bir gönderilen makale PDF'i

Yönlendirme:
  - \documentclass taşıyan en uygun .tex bulunursa → latex_parser (ilgili .bbl eşlenir)
  - yoksa en büyük .pdf bulunursa → pdf_parser
  - hiçbiri yoksa → dürüst uyarı + boş Manuscript

ZIP-BOMB KORUMASI (zorunlu):
  - toplam açılım boyutu sınırı (_MAX_TOTAL_UNCOMPRESSED)
  - dosya sayısı sınırı (_MAX_FILES)
  - tek dosya boyutu sınırı (_MAX_SINGLE)
  - dizin-kaçış (path traversal) reddi (../, mutlak yol)
Sınır aşımı → ValueError raise (sessiz kırpma YOK — hata-yutma yasak).
"""

from __future__ import annotations

import io
import logging
import os
import zipfile

from api.models.review import Manuscript
from engine.ingestion import builder, docx_parser, latex_parser, pdf_parser

logger = logging.getLogger(__name__)

# ZIP-bomb sınırları — makul akademik gönderi üst sınırları.
_MAX_TOTAL_UNCOMPRESSED = 200 * 1024 * 1024  # 200 MB toplam açılım
_MAX_SINGLE = 100 * 1024 * 1024  # 100 MB tek dosya
_MAX_FILES = 2000  # arşiv içi dosya sayısı


class ZipBombError(ValueError):
    """ZIP açılım sınırları aşıldı — olası zip-bomb / kötü niyetli arşiv."""


class UnsafeZipEntryError(ValueError):
    """Arşiv içinde dizin-kaçış (path traversal) ya da mutlak yol girdisi."""


def _is_unsafe_path(name: str) -> bool:
    """Girdi adı arşiv dışına yazmaya çalışıyor mu (traversal / mutlak yol)."""
    if name.startswith("/") or name.startswith("\\"):
        return True
    # normpath ile ../ çözülür; üst dizine çıkıyorsa güvensiz.
    norm = os.path.normpath(name)
    return norm.startswith("..") or norm.startswith(os.sep + "..")


def safe_extract(data: bytes) -> dict[str, bytes]:
    """ZIP baytlarını bellek içine güvenli aç → {arşiv_yolu: içerik}.

    Sınır aşımında ZipBombError / UnsafeZipEntryError raise eder (yutma yok).
    Dizin girdileri atlanır.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Geçersiz ZIP dosyası: {exc}") from exc

    infos = zf.infolist()
    if len(infos) > _MAX_FILES:
        raise ZipBombError(
            f"Arşivde çok fazla dosya ({len(infos)} > {_MAX_FILES})."
        )

    total = 0
    out: dict[str, bytes] = {}
    with zf:
        for info in infos:
            if info.is_dir():
                continue
            if _is_unsafe_path(info.filename):
                raise UnsafeZipEntryError(
                    f"Güvensiz arşiv girdisi (dizin-kaçış): {info.filename!r}"
                )
            if info.file_size > _MAX_SINGLE:
                raise ZipBombError(
                    f"Arşiv içi dosya çok büyük: {info.filename!r} "
                    f"({info.file_size} > {_MAX_SINGLE})."
                )
            total += info.file_size
            if total > _MAX_TOTAL_UNCOMPRESSED:
                raise ZipBombError(
                    f"Toplam açılım boyutu sınırı aşıldı "
                    f"(> {_MAX_TOTAL_UNCOMPRESSED} bayt) — olası zip-bomb."
                )
            out[info.filename] = zf.read(info)
    return out


def _find_main_tex(files: dict[str, bytes]) -> str | None:
    r"""\documentclass içeren en uygun .tex'i bul (ana belge).

    Birden çok aday varsa: en uzun gövdeli olan (genelde ana makale) seçilir.
    """
    candidates: list[tuple[int, str]] = []
    for name, content in files.items():
        if not name.lower().endswith(".tex"):
            continue
        try:
            text = content.decode("utf-8", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            continue
        if "\\documentclass" in text:
            candidates.append((len(text), name))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _find_bbl_for(tex_name: str, files: dict[str, bytes]) -> str | None:
    """Ana .tex ile aynı kökü taşıyan .bbl varsa onu, yoksa herhangi bir .bbl."""
    stem = os.path.splitext(os.path.basename(tex_name))[0]
    bbls = [n for n in files if n.lower().endswith(".bbl")]
    if not bbls:
        return None
    for n in bbls:
        if os.path.splitext(os.path.basename(n))[0] == stem:
            return n
    return bbls[0]


def _find_largest_pdf(files: dict[str, bytes]) -> str | None:
    """En büyük .pdf'i (ana makale varsayımı) bul."""
    pdfs = [(len(c), n) for n, c in files.items() if n.lower().endswith(".pdf")]
    if not pdfs:
        return None
    pdfs.sort(reverse=True)
    return pdfs[0][1]


def _find_docx(files: dict[str, bytes]) -> str | None:
    """En büyük .docx'i bul (LaTeX/PDF yoksa Word gönderisi olabilir)."""
    docs = [
        (len(c), n)
        for n, c in files.items()
        if n.lower().endswith(".docx") and not os.path.basename(n).startswith("~$")
    ]
    if not docs:
        return None
    docs.sort(reverse=True)
    return docs[0][1]


def parse_zip(data: bytes, *, filename: str = "submission.zip") -> Manuscript:
    """ZIP baytları → Manuscript (içerik tipini tespit edip uygun parser'a yönlendir).

    Güvenlik hataları (zip-bomb/traversal) RAISE edilir — çağıran (API katmanı)
    400/422 ile döner. İçerik tanınamazsa dürüst uyarı + boş Manuscript.
    """
    files = safe_extract(data)
    if not files:
        return builder.assemble_manuscript(
            full_text="",
            section_lines=[],
            reference_entries=[],
            body_for_citations="",
            extra_warnings=["ZIP arşivi boş (dosya yok)."],
            base_confidence=0.0,
        )

    main_tex = _find_main_tex(files)
    if main_tex is not None:
        tex_source = files[main_tex].decode("utf-8", errors="replace")
        bbl_name = _find_bbl_for(main_tex, files)
        bbl_source = (
            files[bbl_name].decode("utf-8", errors="replace") if bbl_name else None
        )
        logger.info(
            "zip→latex: ana=%s bbl=%s (%d dosya)", main_tex, bbl_name, len(files)
        )
        ms = latex_parser.parse_latex(
            tex_source, bbl_source=bbl_source, filename=main_tex
        )
        return _tag_zip_source(ms, f"ZIP içinden LaTeX projesi ({main_tex}).")

    pdf_name = _find_largest_pdf(files)
    if pdf_name is not None:
        logger.info("zip→pdf: %s (%d dosya)", pdf_name, len(files))
        ms = pdf_parser.parse_pdf(files[pdf_name], filename=pdf_name)
        return _tag_zip_source(ms, f"ZIP içinden PDF ({pdf_name}).")

    docx_name = _find_docx(files)
    if docx_name is not None:
        logger.info("zip→docx: %s (%d dosya)", docx_name, len(files))
        ms = docx_parser.parse_docx(files[docx_name], filename=docx_name)
        return _tag_zip_source(ms, f"ZIP içinden Word belgesi ({docx_name}).")

    found = ", ".join(sorted(os.path.splitext(n)[1] or "?" for n in files)[:10])
    return builder.assemble_manuscript(
        full_text="",
        section_lines=[],
        reference_entries=[],
        body_for_citations="",
        extra_warnings=[
            "ZIP içinde tanınan bir belge bulunamadı "
            f"(.tex/.pdf/.docx yok; görülen uzantılar: {found})."
        ],
        base_confidence=0.0,
    )


def _tag_zip_source(ms: Manuscript, note: str) -> Manuscript:
    """Yönlendirme kararını parse_warnings'e şeffaf not olarak ekle (künye)."""
    ms.meta.parse_warnings.append(note)
    return ms


__all__ = [
    "UnsafeZipEntryError",
    "ZipBombError",
    "parse_zip",
    "safe_extract",
]
