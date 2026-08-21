"""F14-S1 belge alma — opsiyonel GROBID istemcisi (TEI kaynakça).

GROBID, PDF'ten yapılandırılmış kaynakça (TEI-XML) çıkaran bir servistir. Eğer
GROBID_URL env değişkeni tanımlıysa PDF parser referansları GROBID'ten (yüksek
kalite) çeker; yoksa PyMuPDF heuristic'ine düşer (fallback). GROBID ZORUNLU DEĞİL.

KANUN: GROBID erişilemezse (env yok / bağlantı hatası / 4xx-5xx) None döner —
çağıran heuristic'e düşer ve parse_warnings'e dürüst not yazar. Hata yutulmaz;
beklenen dış-servis hataları sınıflandırılır, beklenmeyen hata raise edilir.

NOT: bu istemci dış HTTP I/O yapar; saf-parse testlerinde çağrılmaz (GROBID_URL
yoksa is_enabled() False → erken çıkış).
"""

from __future__ import annotations

import logging
import os
import re
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

_GROBID_ENV = "GROBID_URL"
_TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def is_enabled() -> bool:
    """GROBID_URL env tanımlı mı (servis kullanılabilir mi)."""
    return bool(os.environ.get(_GROBID_ENV, "").strip())


def base_url() -> str | None:
    """Yapılandırılmış GROBID kök URL'i (sondaki / atılır).

    Güvenlik (S310): yalnız http/https şemasına izin ver — file:/custom şema
    reddedilir (admin env yanlış set ederse SSRF/yerel-dosya okuma engellenir).
    """
    url = os.environ.get(_GROBID_ENV, "").strip()
    if not url:
        return None
    if not (url.startswith("http://") or url.startswith("https://")):
        logger.warning("GROBID_URL http/https değil — yok sayılıyor")
        return None
    return url.rstrip("/")


def fetch_references_tei(data: bytes, *, timeout: float = 30.0) -> str | None:
    """PDF baytlarını GROBID'e gönderip TEI-XML döndür; erişilemezse None.

    Bağlantı/HTTP hatası → None (heuristic fallback). Beklenmeyen hata raise.
    `requests` kuruluysa kullanılır; değilse urllib ile multipart gönderilir.
    """
    url = base_url()
    if not url:
        return None
    endpoint = f"{url}/api/processReferences"
    try:
        return _post_pdf(endpoint, data, timeout=timeout)
    except _GrobidUnavailableError as exc:
        logger.warning("GROBID erişilemedi (%s) — heuristic'e düşülüyor", exc)
        return None


class _GrobidUnavailableError(Exception):
    """GROBID servisine ulaşılamadı (bağlantı/HTTP) — fallback tetikler."""


def _post_pdf(endpoint: str, data: bytes, *, timeout: float) -> str | None:
    """Multipart PDF gönder; TEI metni döndür. Bağlantı hatası → _GrobidUnavailableError."""
    try:
        import requests  # type: ignore[import-untyped]
    except ImportError:
        requests = None  # type: ignore[assignment]

    if requests is not None:
        try:
            resp = requests.post(
                endpoint,
                files={"input": ("manuscript.pdf", data, "application/pdf")},
                timeout=timeout,
            )
        except requests.exceptions.RequestException as exc:  # type: ignore[union-attr]
            raise _GrobidUnavailableError(str(exc)) from exc
        if resp.status_code != 200:
            raise _GrobidUnavailableError(f"HTTP {resp.status_code}")
        return resp.text

    # requests yoksa stdlib urllib ile multipart.
    import urllib.error
    import urllib.request
    import uuid

    boundary = uuid.uuid4().hex
    body = _multipart_body(boundary, data)
    req = urllib.request.Request(  # noqa: S310 (şema base_url() ile http/https doğrulandı)
        endpoint,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (şema doğrulandı)
            if resp.status != 200:
                raise _GrobidUnavailableError(f"HTTP {resp.status}")
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise _GrobidUnavailableError(str(exc)) from exc


def _multipart_body(boundary: str, data: bytes) -> bytes:
    """input=PDF tek-parçalı multipart gövdesi kur."""
    pre = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="input"; '
        'filename="manuscript.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode()
    post = f"\r\n--{boundary}--\r\n".encode()
    return pre + data + post


def parse_tei_references(tei_xml: str) -> list[str]:
    """TEI-XML'den ham referans dizilerini (her biri tek satır str) çıkar.

    Her <biblStruct> bir referans; alt alanlardan (yazar/başlık/tarih/DOI) okunur
    bir ham satır kurulur — sonra builder ortak çıkarıcısı yeniden ayıklar.
    XML parse hatası → boş liste (çağıran heuristic'e düşer).
    """
    try:
        root = ET.fromstring(tei_xml)  # noqa: S314 (GROBID admin-servisi; OPEN_WORK: defusedxml ile sertleştir)
    except ET.ParseError as exc:
        logger.warning("GROBID TEI parse hatası: %s — heuristic'e düşülüyor", exc)
        return []

    entries: list[str] = []
    for bibl in root.iter(f"{{{_TEI_NS['tei']}}}biblStruct"):
        parts: list[str] = []
        authors = _tei_authors(bibl)
        if authors:
            parts.append(", ".join(authors) + ".")
        title = _tei_text(bibl, ".//tei:title")
        if title:
            parts.append(title + ".")
        date = _tei_date(bibl)
        if date:
            parts.append(f"({date}).")
        doi = _tei_doi(bibl)
        if doi:
            parts.append(doi)
        raw = " ".join(p.strip() for p in parts if p.strip())
        if raw:
            entries.append(re.sub(r"\s+", " ", raw).strip())
    return entries


def _tei_authors(bibl: ET.Element) -> list[str]:
    out: list[str] = []
    for pers in bibl.iter(f"{{{_TEI_NS['tei']}}}persName"):
        sur = pers.find("tei:surname", _TEI_NS)
        fore = pers.find("tei:forename", _TEI_NS)
        name = ""
        if sur is not None and sur.text:
            name = sur.text.strip()
            if fore is not None and fore.text:
                name = f"{sur.text.strip()}, {fore.text.strip()}"
        if name:
            out.append(name)
    return out


def _tei_text(bibl: ET.Element, path: str) -> str | None:
    el = bibl.find(path, _TEI_NS)
    if el is not None and el.text:
        return el.text.strip()
    return None


def _tei_date(bibl: ET.Element) -> str | None:
    for date in bibl.iter(f"{{{_TEI_NS['tei']}}}date"):
        when = date.get("when")
        if when:
            m = re.search(r"(19\d{2}|20\d{2})", when)
            if m:
                return m.group(1)
        if date.text:
            m = re.search(r"(19\d{2}|20\d{2})", date.text)
            if m:
                return m.group(1)
    return None


def _tei_doi(bibl: ET.Element) -> str | None:
    for idno in bibl.iter(f"{{{_TEI_NS['tei']}}}idno"):
        if (idno.get("type") or "").lower() == "doi" and idno.text:
            return idno.text.strip()
    return None


__all__ = [
    "base_url",
    "fetch_references_tei",
    "is_enabled",
    "parse_tei_references",
]
