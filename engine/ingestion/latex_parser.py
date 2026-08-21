r"""F14-S1 belge alma — LaTeX (.tex / .bbl) parser.

Çıkarır:
  - gövde metni (komutlar temizlenmiş, \section başlıkları korunmuş)
  - kaynakça: \bibitem (gömülü thebibliography) VEYA ayrı .bbl içeriği
  - metin-içi atıf: \cite{...}, \citep{...}, \citet{...} → çevre cümle

KANUN: LaTeX yorum satırı (% ...) atılır; kaçırılmış yüzde (\%) korunur.
Hata-yutma yok — bozuk girdi parse_warnings'e dürüst yazılır.
"""

from __future__ import annotations

import logging
import re

from api.models.review import Manuscript
from engine.ingestion import builder

logger = logging.getLogger(__name__)

# \cite / \citep / \citet / \citeauthor ... {key1,key2}
_CITE_RE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")

# \bibitem[label]{key} gövde
_BIBITEM_RE = re.compile(r"\\bibitem\s*(?:\[[^\]]*\])?\s*\{[^}]*\}")

# \title{...}
_TITLE_RE = re.compile(r"\\title\s*\{(.+?)\}", re.DOTALL)

# \begin{abstract} ... \end{abstract}
_ABSTRACT_RE = re.compile(
    r"\\begin\{abstract\}(.+?)\\end\{abstract\}", re.DOTALL
)

# \section{...}, \subsection{...} başlıkları
_SECTION_CMD_RE = re.compile(
    r"\\(?:sub){0,2}section\*?\s*\{(.+?)\}"
)

# thebibliography ortamı
_THEBIB_RE = re.compile(
    r"\\begin\{thebibliography\}.*?(?P<body>.*?)\\end\{thebibliography\}",
    re.DOTALL,
)

# Genel \komut{arg} ve \komut — temizlik için
_BRACED_CMD_RE = re.compile(r"\\[a-zA-Z]+\s*\{([^{}]*)\}")
_BARE_CMD_RE = re.compile(r"\\[a-zA-Z]+\*?")
_COMMENT_RE = re.compile(r"(?<!\\)%.*")


def strip_comments(tex: str) -> str:
    """LaTeX yorumlarını (kaçırılmamış %) kaldır."""
    out_lines = [_COMMENT_RE.sub("", ln) for ln in tex.splitlines()]
    return "\n".join(out_lines)


def clean_tex_to_text(tex: str) -> str:
    r"""LaTeX komutlarını kaldırıp düz okunabilir metne indir.

    \section{X} → X (başlık korunur), \cite{..} → atılır (işaret gövdede tutulmaz;
    metin-içi atıf ham .tex'ten ayrı çıkarılır), genel \cmd{arg} → arg.
    """
    text = strip_comments(tex)
    # gövde ortamını işaretle: \begin{document}..\end{document} varsa onu al.
    doc = re.search(r"\\begin\{document\}(.+?)\\end\{document\}", text, re.DOTALL)
    if doc:
        text = doc.group(1)
    # thebibliography'yi gövdeden çıkar (ayrı işlenir).
    text = _THEBIB_RE.sub("", text)
    # section başlıklarını içeriğiyle değiştir (başlık satırı kalsın).
    text = _SECTION_CMD_RE.sub(lambda m: f"\n{m.group(1)}\n", text)
    # cite komutlarını kaldır (metinde [?] gürültüsü bırakma).
    text = _CITE_RE.sub("", text)
    # braced komutları arg'larıyla değiştir (textbf, emph, ...).
    for _ in range(3):  # iç içe sarılı komutlar için birkaç tur
        new = _BRACED_CMD_RE.sub(lambda m: m.group(1), text)
        if new == text:
            break
        text = new
    # geri kalan çıplak komutları temizle.
    text = _BARE_CMD_RE.sub("", text)
    # matematik & süs karakter temizliği.
    text = text.replace("\\&", "&").replace("\\%", "%").replace("\\_", "_")
    text = re.sub(r"[{}$]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_bibitems(source: str) -> list[str]:
    r"""\bibitem'lerden referans girdilerini çıkar (.tex thebibliography veya .bbl).

    İki \bibitem arasındaki gövde bir referanstır. \bibitem yoksa boş döner.
    """
    src = strip_comments(source)
    # thebibliography ortamı varsa onunla sınırla, yoksa tüm kaynak (.bbl).
    m = _THEBIB_RE.search(src)
    scope = m.group("body") if m else src
    if "\\bibitem" not in scope:
        return []
    # \bibitem işaretiyle böl; ilk parça (önsöz) atılır.
    parts = _BIBITEM_RE.split(scope)
    entries: list[str] = []
    for part in parts[1:]:
        cleaned = _clean_bibitem_body(part)
        if cleaned:
            entries.append(cleaned)
    return entries


def _clean_bibitem_body(body: str) -> str:
    r"""Tek \bibitem gövdesini düz metne indir (\newblock, komutlar temizlenir)."""
    body = body.replace("\\newblock", " ")
    for _ in range(3):
        new = _BRACED_CMD_RE.sub(lambda m: m.group(1), body)
        if new == body:
            break
        body = new
    body = _BARE_CMD_RE.sub("", body)
    body = body.replace("\\&", "&").replace("\\%", "%")
    body = re.sub(r"[{}$]", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    return body


def extract_cite_keys(tex: str) -> list[str]:
    r"""Tüm \cite anahtarlarını (yinelenmesiz, sıralı) döndür — teşhis için."""
    keys: list[str] = []
    seen: set[str] = set()
    for m in _CITE_RE.finditer(strip_comments(tex)):
        for key in m.group(1).split(","):
            k = key.strip()
            if k and k not in seen:
                seen.add(k)
                keys.append(k)
    return keys


def parse_latex(
    tex_source: str, *, bbl_source: str | None = None, filename: str = "main.tex"
) -> Manuscript:
    """LaTeX kaynağı → Manuscript.

    bbl_source verilirse (ayrı .bbl dosyası) kaynakça oradan; yoksa .tex
    içindeki thebibliography'den.
    """
    warnings: list[str] = []
    if not tex_source.strip():
        warnings.append("LaTeX kaynağı boş.")
        return builder.assemble_manuscript(
            full_text="",
            section_lines=[],
            reference_entries=[],
            body_for_citations="",
            extra_warnings=warnings,
            base_confidence=0.0,
        )

    title_m = _TITLE_RE.search(strip_comments(tex_source))
    title = _clean_inline(title_m.group(1)) if title_m else None

    abstract_m = _ABSTRACT_RE.search(strip_comments(tex_source))
    abstract = clean_tex_to_text(abstract_m.group(1)) if abstract_m else None

    body_text = clean_tex_to_text(tex_source)

    # Kaynakça kaynağı seçimi: ayrı .bbl > gömülü thebibliography.
    bib_entries = extract_bibitems(bbl_source) if bbl_source else []
    if not bib_entries:
        bib_entries = extract_bibitems(tex_source)
    if not bib_entries:
        warnings.append(
            "LaTeX'te \\bibitem bulunamadı (BibTeX .bib doğrudan derlenmemiş "
            "olabilir; .bbl veya thebibliography gerekli)."
        )

    # Metin-içi atıf: ham .tex'teki \cite işaretleri + çevre cümle.
    body_for_citations = _cite_aware_text(tex_source)

    section_lines = body_text.splitlines()
    base_conf = 0.9  # LaTeX kaynak metni güvenilir okunur

    logger.info(
        "latex parse: %s — %d bibitem, title=%s",
        filename,
        len(bib_entries),
        bool(title),
    )
    return builder.assemble_manuscript(
        full_text=body_text,
        section_lines=section_lines,
        reference_entries=bib_entries,
        body_for_citations=body_for_citations,
        extra_warnings=warnings,
        base_confidence=base_conf,
        title=title,
        abstract=abstract,
    )


def _cite_aware_text(tex_source: str) -> str:
    r"""Gövde metni — ama \cite{key} işaretlerini okunur bir işarete çevir.

    \citep{smith20} → (smith20) ki (Yazar,Yıl) deseni değil ama numaralı/işaretli
    atıf çevre-cümle yakalaması için işaret görünür kalsın. Burada \cite'i kaba bir
    '[CITE]' yerine anahtarı parantezde tutarız ki çevre cümle anlamlı olsun.
    """
    text = strip_comments(tex_source)
    doc = re.search(r"\\begin\{document\}(.+?)\\end\{document\}", text, re.DOTALL)
    if doc:
        text = doc.group(1)
    text = _THEBIB_RE.sub("", text)
    text = _SECTION_CMD_RE.sub(lambda m: f"\n{m.group(1)}\n", text)
    # \cite{a,b} → (a, b) — çevre cümlede işaret olarak kalır.
    text = _CITE_RE.sub(lambda m: f"({m.group(1)})", text)
    for _ in range(3):
        new = _BRACED_CMD_RE.sub(lambda m: m.group(1), text)
        if new == text:
            break
        text = new
    text = _BARE_CMD_RE.sub("", text)
    text = text.replace("\\&", "&").replace("\\%", "%")
    text = re.sub(r"[{}$]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_inline(s: str) -> str:
    """Tek satırlık alanı (title) komut/süs temizle."""
    for _ in range(2):
        s = _BRACED_CMD_RE.sub(lambda m: m.group(1), s)
    s = _BARE_CMD_RE.sub("", s)
    s = re.sub(r"[{}$]", "", s)
    return re.sub(r"\s+", " ", s).strip()


__all__ = [
    "clean_tex_to_text",
    "extract_bibitems",
    "extract_cite_keys",
    "parse_latex",
    "strip_comments",
]
