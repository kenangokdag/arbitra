"""F14-S1 belge alma — saf parse fonksiyonları için unit testler.

Strateji: gerçek PDF/docx ikili dosyaları yerine, parse mantığını STRING
seviyesinde test ederiz (LaTeX gerçek kaynak, kaynakça blok satırları, metin-içi
atıf cümleleri). Böylece testler hızlı (no I/O) ve deterministik.

docx: python-docx kurulu DEĞİL (proje .venv) → docx testi "dürüst eksik uyarısı"
döndürmeyi doğrular (halüsinasyon değil, itiraf — HK-7).
pdf: pymupdf kurulu DEĞİL → aynı şekilde dürüst eksik uyarısı doğrulanır.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from engine.ingestion import common, parse_document
from engine.ingestion.builder import (
    build_in_text_citations,
    build_references,
)
from engine.ingestion.latex_parser import (
    clean_tex_to_text,
    extract_bibitems,
    extract_cite_keys,
    parse_latex,
)
from engine.ingestion.zip_handler import (
    UnsafeZipEntryError,
    ZipBombError,
    safe_extract,
)

pytestmark = pytest.mark.unit


# --- common: alan çıkarıcılar ----------------------------------------------


def test_extract_doi_basic() -> None:
    assert common.extract_doi("see 10.1145/3292500.3330701 for details") == (
        "10.1145/3292500.3330701"
    )


def test_extract_doi_strips_trailing_punctuation() -> None:
    assert common.extract_doi("doi:10.1000/xyz123.") == "10.1000/xyz123"


def test_extract_doi_none_when_absent() -> None:
    assert common.extract_doi("no doi here") is None


def test_extract_doi_merges_genuine_line_wrap_continuation() -> None:
    """§11'in orijinal hedef senaryosu (DiMaggio referansı, PDF_PIPELINE_CALISMA_
    GUNLUGU.md §11) — DAHA ÖNCE HİÇ TEST EDİLMEMİŞTİ (guardian §51 bulgusu).
    DOI bağlayıcı noktalamayla ('.') yarım görünüyor + devam parçası salt rakam
    DEĞİL (nokta içeriyor) → birleştirilmeli."""
    assert common.extract_doi("10.1016/j. poetic.2013.08.004") == (
        "10.1016/j.poetic.2013.08.004"
    )


def test_extract_doi_does_not_append_stray_trailing_number() -> None:
    """§51 (2026-08-14, gerçek Retraction Watch moat-n testinde bulunan bug):
    DOI zaten TAMAMLANMIŞ görünüyorsa (alfa-numerik bitmiş, bağlayıcı noktalama
    yok) ve boşluktan sonra SALT rakamlardan oluşan bir token geliyorsa (sayfa
    no/dipnot/atıf-parantez sayısı), bu birleştirilMEMELİ. Gerçek örnek:
    'peerread' makalesinde '10.3233/jifs-211359 27' → yanlışlıkla
    '10.3233/jifs-21135927' olmuştu, OpenAlex doğal olarak bulamadı."""
    assert common.extract_doi("10.3233/jifs-211359 27") == "10.3233/jifs-211359"
    assert common.extract_doi("10.1007/s00500-023-09312-4 14") == (
        "10.1007/s00500-023-09312-4"
    )


def test_extract_year() -> None:
    assert common.extract_year("Published in 2021 by ACM") == 2021
    assert common.extract_year("no year") is None


def test_guess_language_tr() -> None:
    text = "Bu çalışma için bir yöntem öneriyoruz ve sonuçları tartışıyoruz."
    assert common.guess_language(text) == "tr"


def test_guess_language_en() -> None:
    text = "This study proposes a method and discusses the results in detail."
    assert common.guess_language(text) == "en"


def test_count_words() -> None:
    assert common.count_words("one two three") == 3
    assert common.count_words("") == 0


# --- common: kaynakça bölümleme --------------------------------------------


def test_is_bibliography_heading() -> None:
    assert common.is_bibliography_heading("References")
    assert common.is_bibliography_heading("6. References")
    assert common.is_bibliography_heading("KAYNAKÇA")
    assert not common.is_bibliography_heading("Introduction")


def test_slice_bibliography_found() -> None:
    lines = [
        "Introduction",
        "Some body text.",
        "References",
        "[1] Smith, J. (2020). A paper.",
        "[2] Doe, A. (2019). Another paper.",
    ]
    block = common.slice_bibliography(lines)
    assert block == [
        "[1] Smith, J. (2020). A paper.",
        "[2] Doe, A. (2019). Another paper.",
    ]


def test_slice_bibliography_stops_at_appendix() -> None:
    lines = [
        "References",
        "[1] Smith, J. (2020). A paper.",
        "Appendix",
        "Extra material.",
    ]
    block = common.slice_bibliography(lines)
    assert block == ["[1] Smith, J. (2020). A paper."]


def test_slice_bibliography_none_when_no_heading() -> None:
    assert common.slice_bibliography(["just", "body", "no refs"]) is None


def test_group_reference_entries_numbered() -> None:
    block = [
        "[1] Smith, J. (2020). First paper title.",
        "Journal of Things, 1(2), 3-4.",
        "[2] Doe, A. (2019). Second paper.",
    ]
    entries = common.group_reference_entries(block)
    assert len(entries) == 2
    assert entries[0].startswith("[1]")
    assert "Journal of Things" in entries[0]  # sarılı satır birleşti
    assert entries[1].startswith("[2]")


def test_group_reference_entries_no_numbering_one_per_line() -> None:
    block = [
        "Smith, J. (2020). First paper. Journal A.",
        "Doe, A. (2019). Second paper. Journal B.",
    ]
    entries = common.group_reference_entries(block)
    assert len(entries) == 2


# --- 2026-08-16 (§65-66): referans-bölme + başlık-çıkarma yanlış-pozitif
# "uydurma atıf" bug'ının regresyon testleri. Gerçek 6 örnek: 2'si
# peerread:iclr2017-400 (idx 4/21), 4'ü peerread:iclr2017-487 (idx 7/26/29/31)
# — 61-goldset canlı koşumunda "fabricated" olarak yanlış etiketlenmişti,
# kök neden Arbitra'nın kendi ayrıştırma hatasıydı (gerçek sahtecilik DEĞİL).
# Kanıt/ölçüm: eval/review/results/reference_splitting_bug_2026-08-15/.


def test_bare_year_end_re_skips_doi_url_annotation() -> None:
    """ICLR-tarzı kaynakça: YIL'dan sonra 'doi: ...'/'URL ...' ek-tümcesi
    geliyor — girdi sınırı bu ek-tümceden SONRA, gerçek bir sonraki yazardan
    ÖNCE bulunmalı (eskiden 'doi'nin küçük harfle başlaması yüzünden hiç
    bulunamıyordu, 2 gerçek referans TEK girdide birleşiyordu)."""
    raw = (
        "Li Dong and Mirella Lapata. Language to Logical Form with Neural "
        "Attention. In ACL, pp. 33–43, 2016. doi: 10.18653/v1/P16-1004. "
        "URL http://arxiv.org/abs/1601.01280. Christoph Goller and Andreas "
        "Kuechler. Learning task-dependent distributed representations."
    )
    entries = common.group_reference_entries([raw])
    assert len(entries) == 2
    assert entries[0].startswith("Li Dong")
    assert entries[0].rstrip().endswith("01280.")
    assert entries[1].startswith("Christoph Goller")


def test_extract_authors_year_title_recovers_real_title_after_url_doi() -> None:
    """2026-08-16 bug: 'doi:'/'URL ...' ek-tümcesi + gerçek başlık, Vancouver-
    split'in URL'deki noktaları alan-sınırı sanmasından ETKİLENMEMELİ —
    gerçek başlık ('Language to Logical Form with Neural Attention')
    çıkarılmalı, bir URL parçası ('org/pdf/ 1409') DEĞİL."""
    body = (
        "Li Dong and Mirella Lapata. Language to Logical Form with Neural "
        "Attention. In ACL, pp. 33–43, 2016. doi: 10.18653/v1/P16-1004. "
        "URL http://arxiv.org/abs/1601.01280."
    )
    authors, year, title = common.extract_authors_year_title(body)
    assert authors == ["Li Dong", "Mirella Lapata"]
    assert year == 2016
    assert title == "Language to Logical Form with Neural Attention"


def test_extract_authors_year_title_protects_abbreviated_initial_period() -> None:
    """2026-08-16 bug: 'Ronald J. Williams' gibi kısaltılmış orta-adlı yazar
    isimlerindeki nokta, düz `.split(".")` ile alan-sınırı sanılıyordu —
    sonuç: authors=['Ronald J'], title='Williams and David Zipser' (yanlış).
    Artık kısaltma noktası korunmalı, gerçek yazar bloğu + başlık çıkmalı."""
    body = (
        "Ronald J. Williams and David Zipser. Gradient-based learning "
        "algorithms for recurrent networks and their computational "
        "complexity. Back-propagation Theory, Archit. Appl., pp. "
        "433–486, 1995. doi: 10.1080/02673039508720837."
    )
    authors, year, title = common.extract_authors_year_title(body)
    assert authors == ["Ronald J. Williams", "David Zipser"]
    assert year == 1995
    assert title == (
        "Gradient-based learning algorithms for recurrent networks and "
        "their computational complexity"
    )


def test_split_author_block_oxford_list_full_names() -> None:
    """2026-08-24 GERÇEK üretim bug'ı (canlı S2-fallback testinde bulundu,
    guardian: kök neden burada, review_citation_service.py'de DEĞİL): Oxford-
    liste ("A, B, C, and D") biçiminde, tek 'and' SADECE son ayraçta olduğu
    için '|' dönüşümünden sonra baştaki 'A, B, C' parçası virgülle HİÇ
    bölünmeden tek yazar sanılıyordu. Canlı veri: 'Yu Rong, Wenbing Huang,
    Tingyang Xu' TEK eleman olarak çıkıyordu (4 yazar olması gerekirken 2
    eleman) — review_citation_service.py'nin yazar-soyadı örtüşme kontrolünü
    (hem OpenAlex hem Semantic Scholar yolu, ORTAK yardımcı) 29/29 yanlış-red
    ile bozuyordu (başlık benzerliği ≥0.93, doğru makale zaten bulunmuştu)."""
    from engine.ingestion import common as c

    assert c._split_author_block(
        "Yu Rong, Wenbing Huang, Tingyang Xu, and Junzhou Huang"
    ) == ["Yu Rong", "Wenbing Huang", "Tingyang Xu", "Junzhou Huang"]


def test_split_author_block_apa_initial_style_unaffected() -> None:
    """APA 'Soyad, A. B.' deseni (virgül soyad-ad ayracı) DOKUNULMAMALI —
    2026-08-05 guardian bulgusunun koruduğu davranış (yaygın soyad tesadüfü,
    bkz. test_common_surname_coincidence_stays_fabricated) burada DEĞİŞMEZ."""
    from engine.ingestion import common as c

    assert c._split_author_block("Kim, D. and Patel, R.") == ["Kim, D.", "Patel, R."]


def test_split_author_block_and_joined_two_authors_unaffected() -> None:
    """Zaten çalışan basit 'A and B' deseni regresyona uğramamalı (bkz.
    test_extract_authors_year_title_recovers_real_title_after_url_doi)."""
    from engine.ingestion import common as c

    assert c._split_author_block("Li Dong and Mirella Lapata") == [
        "Li Dong",
        "Mirella Lapata",
    ]


@pytest.mark.parametrize(
    "garbage_title",
    [
        "URL http://dl.acm.org/citation.cfm",
        "ISBN 978-1-4673-8947-1",
        "34th Annual Conference of IEEE, pp",
        "https://arxiv.org/abs/1234",
        "www.example.com/paper",
        "doi: 10.1234/xyz",
    ],
)
def test_extract_authors_year_title_nulls_garbage_title_not_guesses(
    garbage_title: str,
) -> None:
    """HK-7: bilinen çöp-başlık kalıpları (URL/ISBN/venue-sayı-sırası önekli)
    `title` alanına YAZILMAMALI — None bırakılmalı (tahmin yok). Downstream
    (review_citation_service.py) title=None'ı zaten güvenli ele alıyor
    (sadece DOI ile çözüyor, başlık-kıyaslaması/fabrication-kontrolü hiç
    çalışmıyor) — bkz. docs/plans/REFERENCE_SPLITTING_TITLE_EXTRACTION_FIX_
    2026-08-16.md §4."""
    body = f"Some Author. {garbage_title}. 2020."
    _authors, _year, title = common.extract_authors_year_title(body)
    assert title is None


# --- builder: ParsedReference çıkarımı -------------------------------------


def test_build_references_apa_fields() -> None:
    entries = [
        "[1] Smith, J., & Jones, A. (2020). Deep learning for review. "
        "Nature, 10.1038/s41586-020-0001-2",
    ]
    refs = build_references(entries)
    assert len(refs) == 1
    r = refs[0]
    assert r.index == 1
    assert r.year == 2020
    assert r.doi == "10.1038/s41586-020-0001-2"
    assert r.title is not None and "Deep learning for review" in r.title
    assert r.authors  # en az bir yazar
    # status alanına DOKUNULMADI — default kalmalı (S2 doldurur).
    assert r.status == "not_found_in_index"
    assert 0.0 < r.parse_confidence <= 1.0


def test_build_references_confidence_higher_with_doi() -> None:
    with_doi = build_references(
        ["[1] Smith, J. (2020). A title here. 10.1000/abc"]
    )[0]
    without_doi = build_references(["[2] Smith, J. (2020). A title here."])[0]
    assert with_doi.parse_confidence > without_doi.parse_confidence


def test_build_references_skips_empty() -> None:
    assert build_references(["", "   "]) == []


def test_parsed_reference_status_untouched() -> None:
    """Sözleşme kapısı: S1 status'a asla yazmaz."""
    refs = build_references(["[1] Author, A. (2021). Title. 10.1/x"])
    assert all(r.status == "not_found_in_index" for r in refs)
    assert all(r.openalex_id is None for r in refs)
    assert all(r.evidence is None for r in refs)


# --- builder: metin-içi atıf -----------------------------------------------


def test_in_text_numbered_citation_maps_to_ref() -> None:
    refs = build_references(
        ["[1] A. (2020). T1. 10.1/a", "[2] B. (2019). T2. 10.1/b"]
    )
    body = "Prior work shows gains [1]. Other studies disagree [2]."
    cits = build_in_text_citations(body, refs)
    markers = {c.marker for c in cits}
    assert "[1]" in markers
    assert "[2]" in markers
    by_marker = {c.marker: c for c in cits}
    assert by_marker["[1]"].ref_index == 1
    assert by_marker["[2]"].ref_index == 2
    assert "Prior work" in by_marker["[1]"].sentence


def test_in_text_author_year_citation() -> None:
    refs: list = []
    body = "This builds on earlier results (Smith, 2020) in the field."
    cits = build_in_text_citations(body, refs)
    assert any("Smith, 2020" in c.marker for c in cits)
    # (Yazar, Yıl) numarasızdır → ref_index None
    ay = [c for c in cits if "Smith" in c.marker][0]
    assert ay.ref_index is None


def test_in_text_numbered_out_of_range_no_fabricated_index() -> None:
    refs = build_references(["[1] A. (2020). T. 10.1/a"])
    body = "An unsupported marker appears here [9]."
    cits = build_in_text_citations(body, refs)
    nine = [c for c in cits if c.marker == "[9]"][0]
    assert nine.ref_index is None  # uydurma eşleme yok


# --- latex_parser ----------------------------------------------------------


_LATEX_DOC = r"""
\documentclass{article}
\title{A Study of Citation Parsing}
\begin{document}
\begin{abstract}
We present a method for parsing citations from manuscripts.
\end{abstract}
\section{Introduction}
Prior work established the baseline \cite{smith2020}. We extend it \citep{doe2019}.
\section{Methods}
Our approach builds on graph theory.
\begin{thebibliography}{9}
\bibitem{smith2020} Smith, J. (2020). Baseline methods. Journal of AI.
\bibitem{doe2019} Doe, A. (2019). Graph extensions. Conf on Graphs.
\end{thebibliography}
\end{document}
"""


def test_latex_extract_bibitems() -> None:
    entries = extract_bibitems(_LATEX_DOC)
    assert len(entries) == 2
    assert "Smith" in entries[0]
    assert "Doe" in entries[1]
    assert "\\bibitem" not in entries[0]  # komut temizlendi


def test_latex_clean_text_keeps_section_titles() -> None:
    text = clean_tex_to_text(_LATEX_DOC)
    assert "Introduction" in text
    assert "Methods" in text
    assert "\\section" not in text
    assert "\\cite" not in text


def test_latex_extract_cite_keys() -> None:
    keys = extract_cite_keys(_LATEX_DOC)
    assert keys == ["smith2020", "doe2019"]


def test_parse_latex_full() -> None:
    ms = parse_latex(_LATEX_DOC, filename="main.tex")
    assert ms.meta.title == "A Study of Citation Parsing"
    assert ms.meta.abstract is not None and "parsing citations" in ms.meta.abstract
    assert ms.meta.reference_count == 2
    assert len(ms.references) == 2
    assert ms.references[0].year == 2020
    assert ms.references[1].year == 2019
    # bölüm başlıkları yakalandı
    titles_lower = [t.lower() for t in ms.meta.section_titles]
    assert any("introduction" in t for t in titles_lower)
    # metin-içi atıf (cite işaretleri parantezde göründü)
    assert ms.meta.parse_confidence > 0.5
    assert ms.meta.language == "en"


def test_parse_latex_empty_source_honest_warning() -> None:
    ms = parse_latex("", filename="empty.tex")
    assert ms.meta.reference_count == 0
    assert ms.references == []
    assert any("boş" in w.lower() for w in ms.meta.parse_warnings)
    assert ms.meta.parse_confidence == 0.0


def test_parse_latex_no_bibitem_warns() -> None:
    src = r"\documentclass{article}\begin{document}Body only.\end{document}"
    ms = parse_latex(src, filename="nobib.tex")
    assert ms.references == []
    assert any("bibitem" in w.lower() for w in ms.meta.parse_warnings)


def test_parse_latex_separate_bbl() -> None:
    tex = r"""\documentclass{article}\begin{document}
Body cites \cite{x2021}.\end{document}"""
    bbl = r"""\begin{thebibliography}{1}
\bibitem{x2021} Xavier, P. (2021). External bbl entry. J. Test.
\end{thebibliography}"""
    ms = parse_latex(tex, bbl_source=bbl, filename="main.tex")
    assert ms.meta.reference_count == 1
    assert "Xavier" in ms.references[0].raw


# --- zip_handler: güvenlik + yönlendirme -----------------------------------


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_zip_routes_to_latex() -> None:
    data = _make_zip(
        {
            "main.tex": _LATEX_DOC.encode("utf-8"),
            "figure.png": b"\x89PNG\r\n",
        }
    )
    ms = parse_document(data, "zip", "submission.zip")
    assert ms.meta.reference_count == 2
    assert any("LaTeX" in w for w in ms.meta.parse_warnings)


def test_zip_empty_archive() -> None:
    data = _make_zip({})
    ms = parse_document(data, "zip", "empty.zip")
    assert ms.references == []
    assert any("boş" in w.lower() for w in ms.meta.parse_warnings)


def test_zip_unrecognized_content() -> None:
    data = _make_zip({"notes.txt": b"hello", "data.csv": b"a,b,c"})
    ms = parse_document(data, "zip", "misc.zip")
    assert ms.references == []
    assert any("tanınan" in w.lower() for w in ms.meta.parse_warnings)


def test_zip_path_traversal_rejected() -> None:
    # Doğrudan zipfile ile kötü-niyetli girdi yaz (writestr traversal'a izin verir).
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../etc/evil.tex", b"\\documentclass{article}")
    with pytest.raises(UnsafeZipEntryError):
        safe_extract(buf.getvalue())


def test_zip_too_many_files_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    import engine.ingestion.zip_handler as zh

    monkeypatch.setattr(zh, "_MAX_FILES", 3)
    data = _make_zip({f"f{i}.txt": b"x" for i in range(5)})
    with pytest.raises(ZipBombError):
        safe_extract(data)


def test_zip_total_size_limit_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    import engine.ingestion.zip_handler as zh

    monkeypatch.setattr(zh, "_MAX_TOTAL_UNCOMPRESSED", 10)
    data = _make_zip({"big.txt": b"x" * 100})
    with pytest.raises(ZipBombError):
        safe_extract(data)


def test_safe_extract_normal() -> None:
    data = _make_zip({"a.tex": b"hello", "b.bbl": b"world"})
    files = safe_extract(data)
    assert files == {"a.tex": b"hello", "b.bbl": b"world"}


# --- parse_document: yönlendirme + dürüst eksik bağımlılık ------------------


def test_parse_document_latex_kind() -> None:
    ms = parse_document(_LATEX_DOC.encode("utf-8"), "latex", "main.tex")
    assert ms.meta.reference_count == 2


def test_parse_document_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        parse_document(b"x", "html", "x.html")  # type: ignore[arg-type]


def test_parse_document_pdf_missing_pymupdf_honest() -> None:
    """pymupdf .venv'de kurulu değil → boş referans + dürüst uyarı (HK-7).

    pymupdf İLERİDE kurulursa bu test, bozuk-PDF dürüst uyarısını doğrular
    (her iki durumda da: boş referans + en az bir uyarı + güven 0).
    """
    ms = parse_document(b"%PDF-1.4 not a real pdf body", "pdf", "fake.pdf")
    assert ms.references == []
    assert ms.meta.parse_confidence == 0.0
    assert ms.meta.parse_warnings  # dürüst not var
    assert any(
        ("pymupdf" in w.lower())
        or ("metin" in w.lower())
        or ("açılamadı" in w.lower())
        or ("okunamadı" in w.lower())
        for w in ms.meta.parse_warnings
    )


def test_parse_pdf_strips_nul_bytes_from_extracted_text() -> None:
    """2026-08-14 bug: bazı PDF'lerin gömülü font/glif akışı PyMuPDF metin
    çıkarımında NUL (U+0000) baytı üretiyor (görünür anlamı yok, extraction
    artefaktı). Postgres text/jsonb bunu KABUL ETMİYOR ("unsupported Unicode
    escape sequence", code 22P05) — gerçek örnek: 14224_PIED_Physics_Informed_
    Ex.pdf, review_service.py._update() Supabase yazımında pipeline'ı
    düşürüyordu (SupabaseQueryError). fitz ile GERÇEK bir PDF oluşturup NUL
    bayt içeren metin gömüyoruz — mock değil, gerçek PyMuPDF round-trip.
    """
    fitz = pytest.importorskip("fitz", reason="pymupdf kurulu değilse bu test atlanır")
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "Title Here\n\nAbstract\nSome text with a NUL byte here: [X] and more "
        "padding text to exceed the minimum text-length threshold for sure."
    ).replace("X", "\x00")
    page.insert_text((50, 72), text, fontsize=11)
    data = doc.tobytes()
    doc.close()

    ms = parse_document(data, "pdf", "synthetic_nul.pdf")

    assert "\x00" not in ms.full_text
    assert ms.meta.title is None or "\x00" not in ms.meta.title


def test_parse_document_docx_corrupt_honest() -> None:
    """Bozuk/geçersiz .docx → dürüst 'açılamadı' uyarısı + boş Manuscript, çökme yok (HK-7)."""
    ms = parse_document(b"PK\x03\x04 fake docx", "docx", "fake.docx")
    assert ms.references == []
    assert ms.meta.parse_confidence == 0.0
    assert ms.meta.parse_warnings
    assert any(
        ("python-docx" in w.lower()) or ("açılamadı" in w.lower())
        for w in ms.meta.parse_warnings
    )
