"""F14-S1 belge alma — paylaşılan parse yardımcıları (saf, I/O'suz).

Tüm format parser'ları (pdf/docx/latex) bu yardımcıları paylaşır:
  - referans satırı → ParsedReference (raw/title/authors/year/doi/venue ayıklama)
  - metin-içi atıf yakalama ((Yazar, Yıl) + [n] stilleri)
  - bölüm başlığı / kelime sayısı / dil sezgisi
  - parse_confidence hesabı

KANUN (CLAUDE.md §2.3 + HK-7): "yok ≠ uydurma". Bir alan çıkarılamıyorsa None
bırakılır, ASLA tahmin edilmez. Boş referans listesi üretilmez — okunamayan girdi
parse_warnings'e dürüst yazılır.
"""

from __future__ import annotations

import re

# --- regex desenleri (modül seviyesinde derlenir) --------------------------

# DOI: 10.xxxx/yyyy — RFC-uyumlu pratik desen (Crossref önerisi)
_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", re.IGNORECASE)

# PDF satır-sarımı DOI'nin ortasına sahte bir boşluk sokabilir (örn. çıkarılan
# metin "10.1016/j. poetic.2013.08.004" olur, gerçeği "10.1016/j.poetic.2013...").
# Sadece "küçük harfle başlıyor" YETERSİZ sinyal — sıradan İngilizce/Türkçe
# metinde DOI sonrası küçük harfli kelime çok normal ("...10.1145/x for details").
# Ek şart: devam eden parça RAKAM içermeli (gerçek DOI-sarımı devamları
# "poetic.2013.08.004" gibi rakam taşır; sıradan kelimeler taşımaz) — bu
# ikinci şart olmadan test_extract_doi_basic gibi meşru cümleler bozulurdu.
_DOI_WRAP_CONTINUATION_RE = re.compile(r"^ ([a-z0-9][-._;()/:A-Za-z0-9]*)")

# 2026-08-14 (guardian bulgusu, PDF_PIPELINE_CALISMA_GUNLUGU.md §51 — Retraction
# Watch moat-n canlı testinde bulundu): yukarıdaki "rakam içermeli" şartı YETERSİZ
# kaldığı bir YENİ false-positive sınıfı açtı — DOI'den sonraki bitişik, SALT
# RAKAMLARDAN oluşan bir token (sayfa numarası, dipnot, atıf-parantez sayısı)
# de "rakam içeriyor" şartını sağlıyor ve yanlışlıkla DOI'ye eklendi (gerçek
# örnek: "10.3233/jifs-211359 27" → yanlış "10.3233/jifs-21135927" oldu, OpenAlex
# doğal olarak bulamadı). Ayırt edici sinyal: GERÇEK bir satır-sarımı devamı ya
# DOI'nin BAĞLAYICI noktalamayla (./-/_ vb.) TAMAMLANMAMIŞ görünmesiyle gelir
# (örn. "10.1016/j." + "poetic.2013..." — DOI zaten yarım görünüyor), ya da devam
# parçasının kendisi SALT rakam DEĞİLDİR (örn. "poetic.2013.08.004" nokta içerir).
# Bitişik bir sayı, DOI zaten TAMAMLANMIŞ görünüyorken (alfa-numerik bir karakterle
# bitmiş, bağlayıcı noktalama YOK) gelirse reddedilir.

# 4-haneli yıl (1900-2099); satır sonundaki noktalama temizlenir
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

# Numara-önekli referans satırı: "1. ...", "[1] ...", "(1) ..."
_NUM_PREFIX_RE = re.compile(r"^\s*(?:\[(\d{1,3})\]|\((\d{1,3})\)|(\d{1,3})[.)])\s+")

# Girdi-başlangıcı kalıbı: "Soyad, A. B., & Soyad2, C. (YIL)." ya da
# "Kurum Adı (KISALTMA). (YIL)." — yazar/kurum bloğu ardından yıl parantezi.
# Rakam İÇERMEZ (yazar bloğunda rakam olmaz; cilt/sayı/sayfa rakamları YIL
# parantezinden SONRA gelir, bu yüzden rakam görülmesi eşleşmeyi engeller —
# devam satırlarını (12(3), 320-332 gibi) yanlışlıkla girdi-başı saymayı önler).
_ENTRY_START_RE = re.compile(
    r"^[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’.,&()\-\s]{0,600}?\(\d{4}[a-z]?(?:,\s*[A-Za-zÀ-ÿ]+)?\)\.?"
)

# Bir girdi metninde birden fazla "(YIL)." işareti varsa (satır-sınırı belirsiz
# PDF çıkarımında iki girdi tek satıra sıkışmış olabilir) alt-bölme için.
_YEAR_MARKER_RE = re.compile(r"\(\d{4}[a-z]?(?:,\s*[A-Za-zÀ-ÿ]+)?\)\.")

# _ENTRY_START_RE ile aynı kalıp ama '^' çapası YOK — merge edilmiş bir girdi
# içinde ORTADA yeni bir referansın başladığı noktaları bulmak için (finditer).
# Kelime sınırında (boşluk sonrası ya da string başı) başlamayı zorunlu kılar,
# aksi halde bir yazar soyadının ortasında yanlış eşleşme riski olur.
_ENTRY_START_INNER_RE = re.compile(
    r"(?:^|(?<=\s))[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’.,&()\-\s]{0,600}?\(\d{4}[a-z]?(?:,\s*[A-Za-zÀ-ÿ]+)?\)\.?"
)

# ICLR/NeurIPS-tarzı ("plainnat") referans girdisi: APA'nın aksine yıl,
# yazar bloğunun HEMEN ARDINDA parantez İÇİNDE değil, girdinin SONUNDA
# (venue'den sonra) ÇIPLAK bir sayı olarak gelir — örn. "Alessandro Achille
# and Stefano Soatto. Information dropout: ... IEEE transactions ..., 40
# (12):2897-2905, 2018." Bu yüzden girdi-BAŞI değil girdi-SONU aranır: yıl +
# nokta, ardından ya yeni bir yazar adının (büyük harf) başlaması ya da metin
# sonu (2026-08-05, gerçek 3 ICLR goldset PDF'inde bulundu — bkz.
# PDF_PIPELINE_CALISMA_GUNLUGU.md; eski _ENTRY_START_RE hiç eşleşmediği için
# ~50 referans tek dev bloğa yığılıyordu).
_BARE_YEAR_END_RE = re.compile(
    r"(?<!\()\b(?:19\d{2}|20\d{2})[a-z]?\."
    r"(?:(?:\s+(?:doi:\s*\S+|URL\s+\S+|ISBN\s+\S+))+\.)?"
    r"(?=\s+[A-ZÀ-ÖØ-Þ]|\s*$)"
)
# 2026-08-16 (§65-66): yukarıdaki YIL'dan sonra bazı yayıncılar (ICLR/NeurIPS
# plainnat) "doi: ..." / "URL ..." / "ISBN ..." ek-bilgi tümceleri ekliyor —
# bunlar küçük harfle ("doi") ya da büyük-ama-yeni-yazar-DEĞİL ("URL"/"ISBN")
# başladığı için eski regex'in "sonraki kelime büyük harf mi" testini
# kaçırıyordu, 2+ gerçek referans TEK girdide birleşiyordu (kanıt:
# PDF_PIPELINE_CALISMA_GUNLUGU.md §65 — peerread:iclr2017-400/487'nin
# "uydurma atıf" iddialarının TAMAMI bu birleşmeden kaynaklanan yanlış başlık
# çıkarımıydı, gerçek sahtecilik DEĞİLDİ). Yukarıdaki opsiyonel grup bu 3
# ek-bilgi önekini (gözlemlenen TÜM örnekleri kapsıyor, KAPALI bir liste
# DEĞİL) "atlayıp" gerçek bir sonraki yazar adına kadar arıyor. Mükemmellik
# iddia edilmiyor — bkz. eval/review/results/reference_splitting_bug_2026-08-15/
# (61-goldset offline ölçümü, düzeltme öncesi/sonrası karşılaştırma).

# Vancouver/PeerJ-tarzı ("Soyad AB, Soyad2 C. YIL. Başlık...") — APA'ya
# konumca benzer (yıl yazar bloğunun HEMEN ardından) ama parantezsiz. APA'daki
# gibi girdi-BAŞI sayılır (ICLR'nin aksine, yıl entry SONUNDA değil).
_ENTRY_START_BARE_YEAR_RE = re.compile(
    r"^[A-ZÀ-ÖØ-Þ][^.]{0,600}?\.\s*(?:19\d{2}|20\d{2})[a-z]?\.\s"
)

# Bazı yayıncılar (örn. PeerJ) her sayfa alt/üst bilgisinde tekrarlayan bir
# atıf-damgası basar ("Yazar et al. (YIL), Dergi, DOI 10.xxxx/... N/M"). PDF
# metin çıkarımında bu damga sayfa kırılımlarında kaynakça metninin ORTASINA
# sızıp gerçek referansları birbirine yapıştırıyor (2026-08-05, gerçek örnek:
# "Chang et al. (2017), PeerJ, DOI 10.7717/peerj.4181 13/17"). Yapısal olarak
# tanınır: kısa yazar öbeği + (YIL) + dergi adı + DOI + sayfa N/M — bu şekil
# gerçek bir referans girdisinde YER ALMAZ (referanslar DOI'den sonra "N/M"
# sayfa damgasıyla bitmez).
_PAGE_FOOTER_STAMP_RE = re.compile(
    r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.\-]*(?:\s+et\s+al\.)?\s*\(\d{4}[a-z]?\),"
    r"\s*[^,()]{2,60},\s*DOI\s+10\.\d{4,9}/\S+\s+\d{1,3}/\d{1,3}"
)

# Metin-içi numaralı atıf: [1], [1, 2], [1-3], [1,2,5]
_INTEXT_NUM_RE = re.compile(r"\[(\d{1,3}(?:\s*[-,]\s*\d{1,3})*)\]")

# Metin-içi (Yazar, Yıl): (Smith, 2020), (Smith & Jones, 2019), (Smith et al., 2021)
# Yazar başı büyük harf + yıl; çoklu atıf ';' ile ayrılabilir.
_INTEXT_AUTHORYEAR_RE = re.compile(
    r"\(([^()]*?[A-ZÇĞİÖŞÜ][^()]*?,\s*(?:19\d{2}|20\d{2})[a-z]?(?:[^()]*?)?)\)"
)

# Kaynakça bölüm başlıkları (EN + TR) — satır kendi başına başlık
_BIB_HEADINGS = (
    "references",
    "reference",
    "bibliography",
    "works cited",
    "literature cited",
    "kaynakça",
    "kaynaklar",
    "kaynakca",
)

# Bölümün BİTTİĞİ (kaynakçadan sonra gelebilecek) başlıklar
_POST_BIB_HEADINGS = (
    "appendix",
    "appendices",
    "acknowledgements",
    "acknowledgments",
    "ek",
    "ekler",
    "teşekkür",
    "supplementary",
    "author biographies",
)

# Yaygın bölüm başlıkları (numaralı veya düz)
_SECTION_HEADING_RE = re.compile(
    r"^\s*(?:\d{1,2}(?:\.\d{1,2})*\.?\s+)?"
    r"(abstract|introduction|background|related work|literature review|"
    r"methods?|methodology|materials and methods|results|discussion|"
    r"conclusions?|conclusion|references|bibliography|acknowledgements?|"
    r"giriş|yöntem|bulgular|tartışma|sonuç|özet|kaynakça)"
    r"\s*$",
    re.IGNORECASE,
)


def extract_doi(text: str) -> str | None:
    """Metinden ilk DOI'yi çıkar; yoksa None. Sonundaki noktalama temizlenir.

    PDF satır-sarımı DOI'yi ortadan bölebilir (sahte boşluk eklenir) — boşluktan
    hemen sonra küçük harf/rakam geliyorsa bu devamı birleştirilir (tahmin değil,
    PDF çıkarım artifaktı düzeltmesi — yeni cümle/referanslar büyük harfle başlar).

    §51 düzeltmesi: DOI zaten TAMAMLANMIŞ görünüyorsa (bağlayıcı noktalama YOK,
    alfa-numerik bir karakterle bitmiş) VE devam parçası SALT rakamsa, bu muhtemelen
    bitişik alakasız bir sayı (sayfa no/dipnot) — birleştirilmez.
    """
    m = _DOI_RE.search(text)
    if not m:
        return None
    doi = m.group(1)
    rest = text[m.end() :]
    while True:
        cont = _DOI_WRAP_CONTINUATION_RE.match(rest)
        if not cont:
            break
        piece = cont.group(1)
        if not any(c.isdigit() for c in piece):
            break
        doi_looks_complete = bool(doi) and doi[-1].isalnum()
        # Devam parçasının SONUNDAKİ cümle noktalaması (bitişik sayı çoğu zaman
        # bir cümle/dipnot sonu olur, örn. "... 27.") önce temizlenir — asıl
        # soru parça bir DOI segmenti mi yoksa salt bir sayı mı, noktalama
        # bunu gizlememeli (aşağıdaki final rstrip ile TUTARLI karakter kümesi).
        piece_core = piece.rstrip(".,;)")
        if doi_looks_complete and piece_core.isdigit():
            break  # DOI zaten bitmiş görünüyor + devam salt rakam → bitişik alakasız sayı
        doi += piece
        rest = rest[cont.end() :]
    # Cümle sonu noktalaması DOI'ye yapışmış olabilir.
    return doi.rstrip(".,;)")


def extract_year(text: str) -> int | None:
    """Metinden ilk makul yılı (1900-2099) çıkar; yoksa None."""
    m = _YEAR_RE.search(text)
    if not m:
        return None
    return int(m.group(1))


def count_words(text: str) -> int:
    """Boşlukla ayrılmış kelime sayısı."""
    return len(text.split())


def guess_language(text: str) -> str:
    """Çok kaba TR/EN sezgisi (ReviewLang = 'tr' | 'en').

    Türkçe'ye özgü karakterler (ı ğ ş ç ö ü İ) yoğunluğu eşik üstündeyse 'tr'.
    Belirsizse 'en' (model default'u). Bu bir sınıflandırıcı DEĞİL, kaba ipucu;
    yanlışsa kullanıcı düzeltebilir (son söz yazarın).
    """
    if not text:
        return "en"
    tr_chars = sum(text.count(c) for c in "ıİğĞşŞçÇöÖüÜ")
    # Türkçe sık kelimeler — karakter sezgisini destekler.
    tr_words = 0
    lowered = text.lower()
    for w in (" ve ", " bir ", " bu ", " için ", " ile ", " olarak ", " çalışma "):
        tr_words += lowered.count(w)
    letters = sum(c.isalpha() for c in text)
    if letters == 0:
        return "en"
    if tr_chars / letters > 0.005 or tr_words >= 3:
        return "tr"
    return "en"


def find_section_titles(lines: list[str]) -> list[str]:
    """Satır listesinden tanınan bölüm başlıklarını sırayla döndür (tekrarsız)."""
    titles: list[str] = []
    seen: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or len(stripped) > 80:
            continue
        if _SECTION_HEADING_RE.match(stripped):
            key = stripped.lower()
            if key not in seen:
                seen.add(key)
                titles.append(stripped)
    return titles


def is_bibliography_heading(line: str) -> bool:
    """Satır TEK BAŞINA bir kaynakça başlığı mı (numara öneki olabilir)."""
    s = line.strip().lower()
    # Numara önekini at: "6. references" / "references" / "7 kaynakça"
    s = re.sub(r"^\s*\d{1,2}(?:\.\d{1,2})*\.?\s*", "", s)
    s = s.strip(" .:")
    return s in _BIB_HEADINGS


def is_post_bibliography_heading(line: str) -> bool:
    """Satır kaynakçadan SONRA gelen bir başlık mı (kaynakça biter)."""
    s = line.strip().lower()
    s = re.sub(r"^\s*\d{1,2}(?:\.\d{1,2})*\.?\s*", "", s)
    s = s.strip(" .:")
    return s in _POST_BIB_HEADINGS


def slice_bibliography(lines: list[str]) -> list[str] | None:
    """Satır listesinden kaynakça bloğunu (başlıktan sonra) döndür.

    Kaynakça başlığı bulunamazsa None (çağıran dürüst uyarı yazar).
    Sondaki post-kaynakça başlığı (appendix vb) bloğu erken kapatır.
    """
    start: int | None = None
    for i, line in enumerate(lines):
        if is_bibliography_heading(line):
            start = i + 1  # başlık satırının kendisi hariç
    if start is None:
        return None
    block: list[str] = []
    for line in lines[start:]:
        if is_post_bibliography_heading(line):
            break
        block.append(line)
    return block


def _has_reliable_numbering(lines: list[str]) -> bool:
    """`lines` gerçekten numaralı bir liste mi, yoksa sayfa-numarası sarım
    kalıntısı gibi yanlış-pozitif mi (örn. sayfa aralığı sarımından kalan
    '365. https://...' satırı `_NUM_PREFIX_RE` ile yanlışlıkla eşleşir)?

    Gerçek numaralı listede satırların gözle görülür bir kısmı önek taşır VE
    ilk eşleşen numara 1'e yakındır (sayfa numaraları büyük olur, liste
    numaraları 1'den başlar). Tek bir yanlış eşleşme `has_numbering=True`
    yapmasın diye ikisi birden şart.
    """
    matches = [m for ln in lines if (m := _NUM_PREFIX_RE.match(ln))]
    if not matches:
        return False
    ratio = len(matches) / len(lines)
    first_num = next(
        (int(g) for m in matches for g in m.groups() if g is not None), None
    )
    return ratio >= 0.15 and first_num is not None and first_num <= 3


def _is_entry_start_line(s: str) -> bool:
    """APA (parantezli-yıl) YA DA Vancouver/PeerJ (parantezsiz-yıl) girdi-başı
    kalıbıyla eşleşiyor mu?"""
    return bool(_ENTRY_START_RE.match(s) or _ENTRY_START_BARE_YEAR_RE.match(s))


def _split_multi_year_entry(entry: str) -> list[str]:
    """Bir girdide birden fazla '(YIL).' işareti varsa (satır-sınırı belirsiz
    PDF çıkarımında iki ayrı referans tek satıra sıkışmış olabilir — örn. bir
    girdinin sayfa-numarası sarımı bir sonraki girdinin başlangıcıyla aynı
    fiziksel satıra düşmüşse) girdi-başı kalıbına göre alt-böl."""
    if len(_YEAR_MARKER_RE.findall(entry)) <= 1:
        return [entry]
    # Girdi-başı konumlarını bul (iç konumlar dahil), aralarını böl.
    starts = [m.start() for m in _ENTRY_START_INNER_RE.finditer(entry)]
    if len(starts) <= 1 or starts[0] != 0:
        return [entry]
    parts = [entry[a:b].strip() for a, b in zip(starts, starts[1:] + [len(entry)])]
    return [p for p in parts if p]


def group_reference_entries(block_lines: list[str]) -> list[str]:
    """Ham kaynakça satırlarını mantıksal referans girdilerine grupla.

    Dört strateji:
      1) Numara-önekli ("[1]", "1.", "(1)") satırlar her biri yeni girdi başlatır;
         önek taşımayan devam satırları öncekine eklenir (sarılmış satır).
         `_has_reliable_numbering` yanlış-pozitifleri (sayfa no sarımı) eler.
      2) Numarasız + APA-tarzı: bir satır "Yazar/Kurum (YIL)." kalıbıyla
         başlıyorsa yeni girdi sayılır; aksi halde önceki girdinin sarım
         devamıdır (iki-yana-yaslı PDF metninde satır uzunluğu güvenilir bir
         sinyal DEĞİLDİR — devam satırları da tam-genişlik olabilir).
         Vancouver/PeerJ-tarzı ("Soyad AB. YIL." parantezsiz) de aynı
         stratejiye (girdi-BAŞI) dahil — bkz. _ENTRY_START_BARE_YEAR_RE.
      3) Numarasız + hiçbir satır (2)'deki kalıplara uymuyorsa (ICLR/NeurIPS
         "plainnat" tarzı — yıl parantez içinde DEĞİL, girdi SONUNDA çıplak):
         tüm blok tek metne birleştirilip _BARE_YEAR_END_RE ile girdi-SONU
         noktalarından bölünür (2026-08-05 bulgusu — bkz. yukarı).

    Önce, sayfa alt/üst bilgisi atıf-damgaları (_PAGE_FOOTER_STAMP_RE) temizlenir
    — aksi halde bu damgalar gerçek girdileri birbirine yapıştırır.

    Son adım: bir girdide birden fazla '(YIL).' işareti kalmışsa (satır sınırı
    belirsizliğinden iki girdi birleşmiş olabilir) tekrar alt-bölünür.

    Boş döndürmek meşru (kaynakça başlığı var ama altı boş) — çağıran uyarı yazar.
    """
    # Sondaki/baştaki boş satırları kırp, ama iç boşlukları sınır olarak kullanma.
    lines = [ln for ln in block_lines if ln.strip() != ""]
    if not lines:
        return []

    # Sayfa alt/üst bilgisi atıf-damgalarını (varsa) temizle, boşa düşen satırları at.
    lines = [_PAGE_FOOTER_STAMP_RE.sub(" ", ln).strip() for ln in lines]
    lines = [ln for ln in lines if ln]
    if not lines:
        return []

    has_numbering = _has_reliable_numbering(lines)
    entries: list[str] = []

    if has_numbering:
        current: list[str] = []
        for ln in lines:
            if _NUM_PREFIX_RE.match(ln):
                if current:
                    entries.append(" ".join(current).strip())
                current = [ln.strip()]
            else:
                # Numarasız devam satırı: önceki girdiye sar.
                if current:
                    current.append(ln.strip())
                else:
                    current = [ln.strip()]
        if current:
            entries.append(" ".join(current).strip())
    elif any(_is_entry_start_line(ln.strip()) for ln in lines):
        # Numarasız: "Yazar (YIL)." (APA) ya da "Yazar YIL." (Vancouver/PeerJ,
        # parantezsiz) kalıbıyla başlayan satır yeni girdi; aksi halde
        # (uzunluğa bakılmaksızın) öncekinin sarım devamı.
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            if entries and not _is_entry_start_line(s):
                entries[-1] = f"{entries[-1]} {s}".strip()
            else:
                entries.append(s)
    else:
        # Hiçbir satır APA-tarzı girdi-başı kalıbına uymadı — ICLR/NeurIPS
        # "plainnat" tarzı olabilir (yıl girdi SONUNDA çıplak). Bloğu birleştirip
        # girdi-SONU noktalarından böl.
        blob = " ".join(ln.strip() for ln in lines)
        ends = [m.end() for m in _BARE_YEAR_END_RE.finditer(blob)]
        if ends:
            starts = [0] + ends[:-1]
            entries = [blob[a:b].strip() for a, b in zip(starts, ends)]
            tail = blob[ends[-1] :].strip()
            if tail:
                entries.append(tail)
        elif blob:
            entries = [blob]

    final: list[str] = []
    for e in entries:
        final.extend(_split_multi_year_entry(e))
    return [e for e in final if e]


def strip_reference_number(raw: str) -> str:
    """Referans girdisinin başındaki numara önekini ('[1]', '1.', '(1)') kaldır."""
    return _NUM_PREFIX_RE.sub("", raw, count=1).strip()


# 2026-08-16 (§65-66): Vancouver-stili ayrıştırmanın (aşağıda) "." ile bölme
# adımı URL'lerdeki ("arxiv.org", "1409.1259v2.pdf") ve DOI'lerdeki
# ("10.18653/v1/P16-1004") noktaları da alan-sınırı sanıyordu — bu, birleşik
# (bkz. _BARE_YEAR_END_RE) bir girdide olduğu gibi, TEK bir gerçek girdide
# bile yanlış başlık çıkarımına yol açabilirdi. Split ÖNCESİ bu aralıklar
# "korunur" (bu aralıklardaki noktalar bölme noktası SAYILMAZ).
_URL_OR_DOI_RE = re.compile(r"https?://\S+|" + _DOI_RE.pattern, re.IGNORECASE)

# Başlık adayı belirgin bir çöp-önekiyle (URL/ISBN/sayfa-aralığı parçası)
# BAŞLIYORSA, gerçek bir başlık DEĞİLDİR — tahmin etmek yerine None bırakılır
# (HK-7). Dar/gözlemlenen-örnek-tabanlı bir liste — kapsamlı bir NLP
# sınıflandırıcısı DEĞİL.
_GARBAGE_TITLE_PREFIX_RE = re.compile(
    r"^(?:URL\b|ISBN\b|https?://|www\.|org/|pdf/|doi:|\d+(?:st|nd|rd|th)\b)",
    re.IGNORECASE,
)


def _split_on_field_periods(text: str) -> list[str]:
    """'.' karakterlerinden alan-ayraçlarına göre böler — ama URL/DOI İÇİNDEKİ
    noktaları VE kısaltılmış yazar baş-harfi noktalarını ("Ronald J.") alan
    sınırı SAYMAZ (2026-08-16, §65-66 bulgusu — düz `str.split(".")` bu
    ikisini ayırt edemiyordu, yanlış başlık/yazar çıkarımına yol açıyordu)."""
    protected = [m.span() for m in _URL_OR_DOI_RE.finditer(text)]

    def _in_protected(pos: int) -> bool:
        return any(a <= pos < b for a, b in protected)

    parts: list[str] = []
    start = 0
    for m in re.finditer(r"\.", text):
        pos = m.start()
        if _in_protected(pos):
            continue
        # "... J." — hemen öncesi boşluk + TEK büyük harf ise (yazar orta-adı
        # kısaltması), bölme noktası SAYMA. Girdi TEK büyük harfle BAŞLIYORSA
        # da aynı kural (örn. "M. J. Shafiee, ..." bir girdinin ilk harfi).
        if pos >= 2 and text[pos - 2] in " \t" and text[pos - 1].isupper():
            continue
        if pos == 1 and text[0].isupper():
            continue
        parts.append(text[start:pos])
        start = pos + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def extract_authors_year_title(body: str) -> tuple[list[str], int | None, str | None]:
    """Numarasız referans gövdesinden (yazarlar, yıl, başlık) sezgisel ayıkla.

    KANUN: tahmin yok. Net bir kalıp yoksa alan None / boş bırakılır.

    Desteklenen yaygın kalıplar:
      "Surname, A. B., & Surname2, C. (2020). Title. Venue, ..."  (APA)
      "Surname AB, Surname2 C. Title. Venue. 2020;..."             (Vancouver)
    Başlık: yıl parantezinden sonraki ilk cümle (APA) ya da yazar-bloğundan
    sonraki ilk cümle.
    """
    authors: list[str] = []
    year: int | None = None
    title: str | None = None

    # APA kalıbı: yazar bloğu ... (YIL). Başlık.
    apa = re.match(
        r"^(?P<authors>.+?)\s*\((?P<year>19\d{2}|20\d{2})[a-z]?\)\.?\s*(?P<rest>.*)$",
        body,
    )
    if apa:
        year = int(apa.group("year"))
        authors = _split_author_block(apa.group("authors"))
        rest = apa.group("rest").strip()
        cand_title = _first_sentence(rest)
        # 2026-08-16 (§65-66): Vancouver dalıyla AYNI çöp-önek kontrolü —
        # APA kalıbında da ("... (YIL). URL: https://...") aynı sınıf hata
        # görülebiliyor.
        if cand_title and not _GARBAGE_TITLE_PREFIX_RE.match(cand_title):
            title = cand_title
        return authors, year, title

    # Vancouver kalıbı: "Yazarlar. Başlık. Venue. YIL;..."
    # Yıl genelde sonlara doğru; başlık ilk '.' bloklarından biri.
    year = extract_year(body)
    parts = _split_on_field_periods(body)
    if len(parts) >= 2:
        # İlk parça yazar bloğu varsayımı, ikinci parça başlık varsayımı.
        cand_authors = _split_author_block(parts[0])
        if cand_authors:
            authors = cand_authors
            cand_title = parts[1]
            if len(cand_title) > 8 and not _GARBAGE_TITLE_PREFIX_RE.match(cand_title):
                title = cand_title
    return authors, year, title


def _split_author_block(block: str) -> list[str]:
    """Yazar bloğunu tek tek yazarlara böl — yaygın ayraçlar.

    Kabul: "& and ; ," karışımı. Çok agresif bölme (başlık kelimelerini yazar
    sanma) riskine karşı: yazar parçası en az bir büyük harf içermeli ve makul
    uzunlukta olmalı; aksi halde tüm blok atılır (None davranışı).
    """
    block = block.strip().rstrip(",")
    if not block:
        return []
    # "et al." → tek bir işaret olarak korunur.
    block = re.sub(r"\bet al\.?\b", "et al.", block, flags=re.IGNORECASE)
    # & ve 'and' ayraçlarını virgüle indir, sonra virgülle böl — ama "Surname, A."
    # APA kalıbında virgül soyad-ad ayracı olduğundan, bunu ayrı ele almak gerek.
    # Pragmatik strateji: ';' ile bölebiliyorsak en güvenlisi o.
    if ";" in block:
        raw_authors = re.split(r"\s*;\s*", block)
    else:
        # APA: "Surname, A. B., & Surname2, C." → '&'/'and' birincil ayraç.
        norm = re.sub(r"\s*&\s*|\s+and\s+", "|", block)
        # "|" varsa çoklu yazar; yoksa tek yazar/virgül-belirsiz → tek blok bırak.
        raw_authors = (
            [a.strip() for a in norm.split("|")] if "|" in norm else [block]
        )
    out: list[str] = []
    for a in raw_authors:
        a = a.strip().strip(",").strip()
        if not a:
            continue
        if a.lower() in ("et al.", "et al"):
            out.append("et al.")
            continue
        if not any(c.isupper() for c in a):
            continue
        if len(a) > 80:  # cümle parçası, yazar değil
            continue
        out.append(a)
    return out


def _first_sentence(text: str) -> str | None:
    """Metnin ilk cümlesini ('.' veya '?' veya '!' ile biten) döndür."""
    text = text.strip()
    if not text:
        return None
    m = re.match(r"^(.+?[.?!])(\s|$)", text)
    cand = m.group(1).strip() if m else text
    cand = cand.rstrip(".").strip()
    return cand or None


def reference_confidence(
    *, title: str | None, authors: list[str], year: int | None, doi: str | None
) -> float:
    """Tek referansın parse güveni (0-1) — kaç alanı sağlamlıkla çıkardık.

    Ağırlık: DOI 0.35 (en kesin), başlık 0.3, yıl 0.2, yazar 0.15.
    """
    score = 0.0
    if doi:
        score += 0.35
    if title:
        score += 0.30
    if year:
        score += 0.20
    if authors:
        score += 0.15
    return round(min(score, 1.0), 3)


def split_sentences(text: str) -> list[str]:
    """Kaba cümle bölme (metin-içi atıf çevre cümlesi için).

    Kısaltma (e.g., i.e., vb., Fig.) içeren kenar durumlar tam çözülmez —
    çevre-cümle yakalama için 'yeterince iyi' kalıp.
    """
    # Paragraf/satır sonlarını boşluğa indir.
    flat = re.sub(r"\s+", " ", text).strip()
    if not flat:
        return []
    # Nokta/soru/ünlem + boşluk + büyük harf veya '[' sınırında böl.
    pieces = re.split(r"(?<=[.?!])\s+(?=[\[(A-ZÇĞİÖŞÜ])", flat)
    return [p.strip() for p in pieces if p.strip()]


def find_intext_citations(
    text: str, *, section: str | None = None
) -> list[tuple[str, str]]:
    """Metinden (marker, çevre_cümle) çiftlerini çıkar — numaralı + (Yazar,Yıl).

    Section parametresi yalnız çağırana kolaylık; burada kullanılmaz (InTextCitation
    nesnesini parser kurar). Aynı cümlede birden çok işaret varsa her biri ayrı çift.
    """
    out: list[tuple[str, str]] = []
    for sentence in split_sentences(text):
        for m in _INTEXT_NUM_RE.finditer(sentence):
            out.append((m.group(0), sentence))
        for m in _INTEXT_AUTHORYEAR_RE.finditer(sentence):
            out.append((m.group(0), sentence))
    return out


__all__ = [
    "count_words",
    "extract_authors_year_title",
    "extract_doi",
    "extract_year",
    "find_intext_citations",
    "find_section_titles",
    "group_reference_entries",
    "guess_language",
    "is_bibliography_heading",
    "is_post_bibliography_heading",
    "reference_confidence",
    "slice_bibliography",
    "split_sentences",
    "strip_reference_number",
]
