"""F14-S1 belge alma — PDF parser (PyMuPDF + opsiyonel GROBID).

Akış:
  1. GROBID_URL env tanımlıysa → GROBID'ten TEI kaynakça (yüksek kalite).
  2. Aksi halde PyMuPDF (`import fitz`) ile metin çıkar + heuristic kaynakça.
  3. PyMuPDF kurulu değilse VEYA PDF metin içermiyorsa (taranmış/görüntü) →
     parse_warnings'e dürüst not, BOŞ referans üretme (HK-7).

KANUN:
  - OCR KAPSAM DIŞI (v1): taranmış PDF "metin yok" olarak dürüst raporlanır.
  - PyMuPDF eksikliği halüsinasyon değil, dürüst eksik → parse_warnings + base_conf 0.
  - Hata-yutma yok: dış-format hatası (bozuk PDF) sınıflandırılıp uyarıya yazılır.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from api.models.review import Manuscript
from engine.ingestion import builder, common, grobid_client

logger = logging.getLogger(__name__)

# Anlamlı metin eşiği — bunun altı "taranmış/boş" sayılır.
_MIN_TEXT_CHARS = 40

# Bazı PDF fontları aksanlı harfleri (é, ô gibi) birleşik glif yerine ayrı bir
# "modifier" aksan karakteri + temel harf olarak kodluyor (ör. "Côté" → 'C' +
# U+02C6 + 'o' + 't' + U+00B4 + 'e'). Bu karakterlerin KENDİSİ geçersiz/bozuk
# DEĞİL (gerçek Unicode kod noktaları) — ama birleşmeyen SPACING modifier
# oldukları için ekranda ayrı bir işaret gibi görünürler. Bilinen karşılık
# gelen COMBINING (birleşen) forma çevrilip NFC normalize edilir.
_STRAY_MODIFIER_TO_COMBINING = {
    "ˆ": "̂",  # MODIFIER LETTER CIRCUMFLEX ACCENT -> COMBINING CIRCUMFLEX ACCENT
    "˜": "̃",  # MODIFIER LETTER SMALL TILDE -> COMBINING TILDE
    "´": "́",  # ACUTE ACCENT (spacing) -> COMBINING ACUTE ACCENT
    "`": "̀",  # GRAVE ACCENT -> COMBINING GRAVE ACCENT
    "¨": "̈",  # DIAERESIS -> COMBINING DIAERESIS
    "¸": "̧",  # CEDILLA -> COMBINING CEDILLA
    "˘": "̆",  # BREVE
    "˙": "̇",  # DOT ABOVE
    "˚": "̊",  # RING ABOVE
    "˝": "̋",  # DOUBLE ACUTE ACCENT
    "ˇ": "̌",  # CARON
}


def _recombine_stray_diacritics(text: str) -> str:
    """PDF font kaynaklı ayrık 'modifier' aksanları temel harfle birleştirip
    NFC normalize eder (örn. 'Cˆot´e' → 'Côté'). Zaten doğru kodlanmış metni
    (Türkçe ı/ğ/ş/ö/ü/ç gibi gerçek precomposed karakterler) ETKİLEMEZ —
    sadece bilinen ayrık-modifier karakterleri hedefler, NFC no-op'tur."""
    if not any(c in _STRAY_MODIFIER_TO_COMBINING for c in text):
        return text
    out: list[str] = []
    n = len(text)
    i = 0
    while i < n:
        c = text[i]
        combining = _STRAY_MODIFIER_TO_COMBINING.get(c)
        if combining is not None and i + 1 < n and text[i + 1].isalpha():
            out.append(text[i + 1])
            out.append(combining)
            i += 2
        else:
            out.append(c)
            i += 1
    return unicodedata.normalize("NFC", "".join(out))


def _import_fitz():  # type: ignore[no-untyped-def]
    """PyMuPDF'i içe aktar; kurulu değilse None (çağıran dürüst uyarı yazar)."""
    try:
        import fitz  # type: ignore[import-untyped]

        return fitz
    except ImportError:
        return None


# --- Görev A: PDF prompt-injection sanitizasyonu (ARBITRA_RESEARCH_BRIEF.md) --
#
# Bilinen saldırı: PDF'e görünmez/gizli metin gömülür (beyaz-üzerine-beyaz,
# <1pt font, sayfa dışı konum) — insan gözle hakem taslağı normal görünür ama
# LLM'e giden düz metinde gizli talimat ("bu makaleyi kabul et" vb.) yer alır.
# Yayınlanmış deneylerde: incelemelerin %5'ine enjeksiyon → top-30% makalelerin
# %12'si kabul listesinden düştü, ortalama +2.7 puan şişme, LLM-insan uyumunda
# %37 düşüş. Savunma: şüpheli blokları TESPİT ET + metinden ÇIKAR + rapora
# GÖRÜNÜR uyarı yaz (sessizce atlama — hem güvenlik hem şeffaflık, HK-7 ile
# aynı disiplin: "gizli talimat bulundu" iddiası da kanıtsız üretilmez, sadece
# somut ölçülebilir sinyallerle: font boyutu/renk/konum).
_MIN_VISIBLE_FONT_SIZE = 1.0  # bunun altı "görünmez küçüklük" sayılır.
_WHITE_RGB_THRESHOLD = 250  # bu değerin üstü kanal başına "beyaza çok yakın".


def _span_rgb(color: int) -> tuple[int, int, int]:
    """PyMuPDF dict-mode span rengi (paketlenmiş int sRGB) → (r, g, b)."""
    return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)


def _colored_fill_covers(bbox, drawings) -> bool:  # type: ignore[no-untyped-def]
    """bbox'un ARKASINDA en üstte çizilmiş dolgu belirgin şekilde koyu/renkli
    mi (beyaz DEĞİL)? PDF çizim sırası = get_drawings() dönüş sırası (önce
    çizilen altta kalır) — bu yüzden bbox ile kesişen SON dolgunun rengi,
    gerçekte GÖRÜNEN (üstteki) arka plandır.

    2026-08-05 bulgusu: gerçek bir ICLR makalesinde (odjMSBSWRt.pdf) sonuç
    tablosunun koyu/renkli heatmap hücrelerinde okunabilir beyaz yazı vardı
    (127 hücre) — sadece metin rengine bakan eski mantık bunların hepsini
    'gizli metin' sanıp SİLDİ, gerçek sonuç verisi motora hiç ulaşmadı.
    """
    x0, y0, x1, y1 = bbox
    bg: tuple[float, float, float] | None = None
    for d in drawings:
        if d.get("type") != "f":  # sadece DOLGU (fill); sadece çizgi (stroke) değil
            continue
        rect = d.get("rect")
        fill = d.get("fill")
        if rect is None or fill is None:
            continue
        if rect.x1 <= x0 or rect.x0 >= x1 or rect.y1 <= y0 or rect.y0 >= y1:
            continue  # kesişmiyor
        bg = fill
    if bg is None:
        return False
    r, g, b = (round(c * 255) for c in bg)
    return not (r >= _WHITE_RGB_THRESHOLD and g >= _WHITE_RGB_THRESHOLD and b >= _WHITE_RGB_THRESHOLD)


def _image_covers(bbox, images) -> bool:  # type: ignore[no-untyped-def]
    """bbox bir gömülü RASTER görselin (diyagram/şekil) alanıyla kesişiyor mu?

    Kesişiyorsa üzerindeki beyaz metin muhtemelen görselin İÇİNDEKİ bir
    etikettir (örn. bir mimari diyagramında 'ReLU'/'Convolution' kutu
    etiketi) — gizli metin DEĞİL. _colored_fill_covers bunu YAKALAYAMAZ
    çünkü arka plan vektör çizim değil, rasterize edilmiş bir görsel
    (2026-08-06 bulgusu — PeerRead ICLR 2017 makalesi 549, 11 diyagram
    etiketi yanlışlıkla 'gizli metin' sanılıp silinmişti)."""
    x0, y0, x1, y1 = bbox
    for img in images:
        r = img.get("bbox")
        if r is None:
            continue
        if r[2] <= x0 or r[0] >= x1 or r[3] <= y0 or r[1] >= y1:
            continue
        return True
    return False


def _is_suspicious_span(span: dict, page_rect, drawings=None, images=None) -> str | None:  # type: ignore[no-untyped-def]
    """Bir metin span'i şüpheli mi? Şüpheliyse sebep etiketi, değilse None.

    Üç somut, ölçülebilir kriter (tahmin değil): görünmez küçüklükte font,
    beyaza-çok-yakın renk (beyaz sayfa arka planında görünmez — AMA arkasında
    koyu/renkli bir dolgu (bkz. _colored_fill_covers) ya da gömülü bir görsel
    (bkz. _image_covers) varsa okunabilir bir tablo hücresi/diyagram
    etiketidir, şüpheli DEĞİL), ya da sayfa sınırlarının tamamen dışında
    konum.
    """
    text = span.get("text", "")
    if not text.strip():
        return None
    size = span.get("size", 12.0)
    if size < _MIN_VISIBLE_FONT_SIZE:
        return "görünmez-küçüklükte-font"
    r, g, b = _span_rgb(span.get("color", 0))
    if r >= _WHITE_RGB_THRESHOLD and g >= _WHITE_RGB_THRESHOLD and b >= _WHITE_RGB_THRESHOLD:
        bbox = span.get("bbox")
        if bbox is not None and drawings and _colored_fill_covers(bbox, drawings):
            return None
        if bbox is not None and images and _image_covers(bbox, images):
            return None
        return "beyaz-üzerine-beyaz-metin"
    bbox = span.get("bbox")
    if bbox is not None:
        x0, y0, x1, y1 = bbox
        if x1 <= 0 or y1 <= 0 or x0 >= page_rect.width or y0 >= page_rect.height:
            return "sayfa-dışı-konum"
    return None


def _strip_suspicious_text(
    doc, pages_text: list[str]  # type: ignore[no-untyped-def]
) -> tuple[list[str], list[str]]:
    """Her sayfada şüpheli span'leri (dict-mode) bulur, düz-metin çıktısından
    (aynı sayfanın "text"-mode çıktısından) çıkarır. Metin eşleşmesiyle silinir
    — extraction modunu (satır yapısını referans-bölme mantığı bekliyor)
    DEĞİŞTİRMEZ, sadece tespit edilen tam metin dizisini kaldırır.

    Döner: (temizlenmiş_sayfa_metinleri, uyarılar). Şüpheli blok yoksa
    uyarılar boş (dürüst — uydurma güvenlik iddiası yok, HK-7)."""
    cleaned_pages: list[str] = []
    suspicious_count = 0
    samples: list[str] = []
    for i, page in enumerate(doc):
        page_text = pages_text[i] if i < len(pages_text) else ""
        try:
            page_dict = page.get_text("dict")
        except Exception:  # dış-lib hatası — bu sayfa için sessizce atla (fatal değil)
            cleaned_pages.append(page_text)
            continue
        # page.rect DÖNDÜRÜLMÜŞ (görüntüleme-yönlü) dikdörtgeni verir, ama
        # get_text("dict") span bbox'ları page.mediabox'ın (döndürülmemiş)
        # koordinat çerçevesindedir. page/Rotate=90/270 olan bir sayfada
        # (örn. yatay bir istatistik tablosu) bunları karıştırmak gerçek
        # içeriği "sayfa dışı" sanıp siliyordu (2026-08-05, peerj-4181.pdf'te
        # 31 yanlış-alarm — Tablo 4 hücreleri).
        page_rect = page.mediabox
        try:
            drawings = page.get_drawings()
        except Exception:  # dış-lib hatası — arka plan kontrolü olmadan devam
            drawings = []
        try:
            images = page.get_image_info()
        except Exception:  # dış-lib hatası — görsel kontrolü olmadan devam
            images = []
        suspicious_texts: list[str] = []
        for block in page_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    reason = _is_suspicious_span(span, page_rect, drawings, images)
                    if reason is None:
                        continue
                    span_text = span.get("text", "")
                    suspicious_texts.append(span_text)
                    suspicious_count += 1
                    if len(samples) < 5:
                        samples.append(f"{reason}: {span_text[:60]!r}")
        for t in suspicious_texts:
            if t and t in page_text:
                page_text = page_text.replace(t, " ")
        cleaned_pages.append(page_text)

    warnings: list[str] = []
    if suspicious_count:
        warnings.append(
            f"GÜVENLİK: PDF içinde {suspicious_count} şüpheli/gizli metin bloğu "
            "tespit edildi (görünmez font boyutu, beyaz-üzerine-beyaz metin ya "
            "da sayfa dışı konum) — bu bloklar değerlendirmeye dahil "
            "EDİLMEDİ (potansiyel prompt injection savunması). "
            f"Örnekler: {'; '.join(samples)}"
        )
        logger.warning(
            "PDF injection savunması: %d şüpheli span tespit edildi ve çıkarıldı",
            suspicious_count,
        )
    return cleaned_pages, warnings


_HEADER_FOOTER_DIGITS_RE = re.compile(r"\d+")
_MIN_HEADER_FOOTER_LINE_CHARS = 15


def _strip_repeating_headers_footers(pages_text: list[str]) -> list[str]:
    """Belgenin KENDİ sayfa üstbilgisi/altbilgisini (her sayfada -sayfa
    numarası dışında- birebir tekrar eden satır — örn. 'Published as a
    conference paper at ICLR 2025' ya da bir dergi atıf-damgası) tespit edip
    çıkarır. Herhangi bir yayıncıya ÖZEL değil, genel bir tekrar tespiti:
    sayfa numarası gibi rakam farkları göz ardı edilerek (rakamlar '#'e
    normalize edilir) aynı satır yeterince FARKLI sayfada görülüyorsa
    üstbilgi/altbilgi sayılır — gerçek gövde/kaynakça metni sayfa başına
    yalnızca bir kez geçer.

    2026-08-05 bulgusu: ICLR'nin 'Published as...' üstbilgisi kaynakça
    metninin ORTASINA sızıp referansları birbirine yapıştırıyordu (bkz.
    PDF_PIPELINE_CALISMA_GUNLUGU.md) — ayrı bir yayıncıya özel regex yerine
    bu genel mekanizma tercih edildi (aynı sınıf sorun her yayıncıda çıkabilir).
    """
    n_pages = len(pages_text)
    if n_pages < 3:
        return pages_text  # tekrar tespiti için yeterli sayfa yok

    norm_to_pages: dict[str, set[int]] = {}
    norm_to_originals: dict[str, set[str]] = {}
    for page_idx, pt in enumerate(pages_text):
        for ln in pt.split("\n"):
            s = ln.strip()
            if len(s) < _MIN_HEADER_FOOTER_LINE_CHARS:
                continue
            norm = _HEADER_FOOTER_DIGITS_RE.sub("#", s)
            norm_to_pages.setdefault(norm, set()).add(page_idx)
            norm_to_originals.setdefault(norm, set()).add(s)

    threshold = max(3, round(n_pages * 0.3))
    repeating: set[str] = set()
    for norm, pages in norm_to_pages.items():
        if len(pages) >= threshold:
            repeating.update(norm_to_originals[norm])
    if not repeating:
        return pages_text

    return [
        "\n".join(ln for ln in pt.split("\n") if ln.strip() not in repeating)
        for pt in pages_text
    ]


def extract_text_pymupdf(data: bytes) -> tuple[str | None, str | None, list[str]]:
    """PDF baytlarından metin çıkar.

    Döner: (full_text | None, hata_notu | None, güvenlik_uyarıları).
      - (metin, None, [...]): başarı — güvenlik_uyarıları boş olabilir
      - (None, "...", []): PyMuPDF yok / bozuk PDF / metin yok — not parse_warnings'e gider
    """
    fitz = _import_fitz()
    if fitz is None:
        return (
            None,
            (
                "PDF metin çıkarımı yapılamadı: PyMuPDF (pymupdf) kurulu değil. "
                "Kurulum: pip install pymupdf."
            ),
            [],
        )
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # PyMuPDF dış-format hatası — sınıflandırıp uyarıya yaz
        # Bilinçli boundary (dosya I/O / dış lib): yut DEĞİL, dürüst uyarıya çevir.
        logger.warning("PyMuPDF PDF açılamadı: %s", exc)
        return None, f"PDF açılamadı (bozuk ya da geçersiz dosya): {exc}", []

    try:
        pages_text: list[str] = []
        for page in doc:
            pages_text.append(page.get_text("text"))
        pages_text, security_warnings = _strip_suspicious_text(doc, pages_text)
    finally:
        doc.close()

    pages_text = _strip_repeating_headers_footers(pages_text)
    full_text = "\n".join(pages_text).strip()
    full_text = _recombine_stray_diacritics(full_text)
    # 2026-08-14: bazı PDF'lerin gömülü font/glif akışı NUL (U+0000) baytı
    # üretiyor (görünür anlamı yok, PyMuPDF metin çıkarım artefaktı). Postgres
    # text/jsonb bunu KABUL ETMİYOR ("unsupported Unicode escape sequence",
    # code 22P05) — Supabase'e Manuscript yazılırken pipeline'ı düşürüyordu
    # (gerçek örnek: 14224_PIED_Physics_Informed_Ex.pdf, review_service.py
    # _update() çağrısında SupabaseQueryError). Kaynakta (full_text derived
    # tüm alanları — title/references/citations buradan türer) temizleniyor.
    full_text = full_text.replace("\x00", "")
    if len(full_text) < _MIN_TEXT_CHARS:
        return (
            None,
            (
                "PDF metin içermiyor (muhtemelen taranmış/görüntü PDF). "
                "OCR bu sürümde kapsam dışı — kaynakça çıkarılamadı."
            ),
            security_warnings,
        )
    return full_text, None, security_warnings


# Başlığın BİTTİĞİ (gövde/özet başladığı) bölüm işaretleri.
_TITLE_STOP_RE = re.compile(
    r"^\s*(abstract|özet|keywords|anahtar kelimeler)\b", re.IGNORECASE
)
_MAX_TITLE_CHARS = 300
_MAX_TITLE_LINES = 4


def _extract_title(full_text: str) -> str | None:
    """PDF'in ilk satırlarından başlığı sezgisel çıkar.

    PyMuPDF düz-metin modu font/stil bilgisi taşımaz (docx Heading stili ya da
    LaTeX \\title{} gibi güvenilir bir işaret yok), bu yüzden basit bir sezgi
    kullanılır: belge başından, ilk boş satıra ya da 'Abstract/Özet/Keywords'
    gibi bir bölüm işaretine kadar olan satırlar başlık kabul edilir. Çok
    uzarsa (muhtemelen gövde metnine kaymış, başlık değil) None döner —
    tahmin yerine dürüst boşluk (HK-7).
    """
    title_lines: list[str] = []
    for line in full_text.splitlines():
        stripped = line.strip()
        if not stripped:
            if title_lines:
                break
            continue
        if _TITLE_STOP_RE.match(stripped):
            break
        title_lines.append(stripped)
        if len(title_lines) >= _MAX_TITLE_LINES:
            break
    if not title_lines:
        return None
    title = " ".join(title_lines).strip()
    if not title or len(title) > _MAX_TITLE_CHARS:
        return None
    return title


def parse_pdf(data: bytes, *, filename: str = "manuscript.pdf") -> Manuscript:
    """PDF baytları → Manuscript (GROBID varsa kaynakça oradan, yoksa heuristic)."""
    warnings: list[str] = []

    full_text, text_err, security_warnings = extract_text_pymupdf(data)
    warnings.extend(security_warnings)

    if full_text is None:
        # Metin çıkarılamadı — boş referans, dürüst uyarı (HK-7).
        warnings.append(text_err or "PDF okunamadı.")
        return builder.assemble_manuscript(
            full_text="",
            section_lines=[],
            reference_entries=[],
            body_for_citations="",
            extra_warnings=warnings,
            base_confidence=0.0,
        )

    lines = full_text.splitlines()

    # Kaynakça kaynağı: önce GROBID (varsa), sonra heuristic.
    bib_entries: list[str] = []
    if grobid_client.is_enabled():
        tei = grobid_client.fetch_references_tei(data)
        if tei is not None:
            bib_entries = grobid_client.parse_tei_references(tei)
            if bib_entries:
                logger.info("GROBID: %d referans çıkarıldı", len(bib_entries))
            else:
                warnings.append(
                    "GROBID yanıtından referans çıkarılamadı — heuristic'e düşüldü."
                )
        else:
            warnings.append(
                "GROBID erişilemedi — PyMuPDF heuristic kaynakçaya düşüldü."
            )

    if not bib_entries:
        bib_block = common.slice_bibliography(lines)
        if bib_block is None:
            warnings.append(
                "PDF metninde kaynakça başlığı (References/Bibliography/Kaynakça) "
                "bulunamadı."
            )
        else:
            bib_entries = common.group_reference_entries(bib_block)

    # Gövde (metin-içi atıf): kaynakça öncesi metin.
    body_for_citations = _body_before_bibliography(lines)

    title = _extract_title(full_text)

    # PDF güveni: metin akışı genelde kırık (sütun/üstbilgi) → orta-yüksek.
    base_conf = 0.7

    logger.info(
        "pdf parse: %s — %d karakter, %d referans, title=%s (grobid=%s)",
        filename,
        len(full_text),
        len(bib_entries),
        bool(title),
        grobid_client.is_enabled(),
    )
    return builder.assemble_manuscript(
        full_text=full_text,
        section_lines=lines,
        reference_entries=bib_entries,
        body_for_citations=body_for_citations,
        extra_warnings=warnings,
        base_confidence=base_conf,
        title=title,
    )


def _body_before_bibliography(lines: list[str]) -> str:
    """Kaynakça başlığına kadar olan metin (metin-içi atıf taraması için)."""
    body: list[str] = []
    for line in lines:
        if common.is_bibliography_heading(line):
            break
        body.append(line)
    return "\n".join(body)


__all__ = ["extract_text_pymupdf", "parse_pdf"]
