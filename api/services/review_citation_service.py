"""F14-S2/S3 — atıf bütünlüğü + atıf-bağlam + kapsama motoru.

Sözleşme: api/models/review.py (DOKUNULMAZ). Bu modül ParsedReference.status/
evidence/openalex_id/is_retracted'i doldurur, CitationContextFinding + CoverageGap
+ CitationIntegritySummary üretir.

İSTEMCİ REUSE: api/services/openalex_polite.py (rate-limit + resilience + 4xx-no-retry).
Sıfırdan httpx istemcisi YAZILMADI.

EN ÖNEMLİ KURAL (R-1 / HK-3 — yanlış suçlama yasağı):
  resolved            : OpenAlex'te (DOI veya başlık+yazar+yıl) bulundu.
  not_found_in_index  : çözülemedi — ASLA suçlama değil (niş dergi/kitap/indekssiz).
  fabricated          : YALNIZ pozitif çelişki (verilen DOI başka esere/başlığa ait).
  retracted           : OpenAlex çözdü + is_retracted bayrağı True.

OpenAlex 'is_retracted' alanı canlı doğrulandı (Work top-level bool; W2741809807
çağrısı 2026-06-21). Yine de defensif okunur: work.get("is_retracted", False).

HK-4 (belirsizlik birinci sınıf): atıf-bağlam özet yoksa/yetersizse
unverifiable_from_abstract, ASLA kesin suçlama.

CLAUDE.md §3: hata-yutma yasak — OpenAlexError loglanır + dürüst not_found_in_index'e
düşülür (suçlama değil); programlama hataları yükselir.

§41 (2026-08-12, guardian bulgusu §40'ın düzeltmesi): "hata-yutma yasak" ama önceki
haliyle provider hatası ile GERÇEK eşleşme-yokluğu report seviyesinde AYIRT
EDİLEMİYORDU — ikisi de sessizce aynı not_found_in_index'e düşüyordu, hiçbir
degraded_features flag'i üretmiyordu (find_coverage_gaps'in aksine). Artık
ParsedReference.resolution_degraded + CitationIntegritySummary.provider_errors
bu ikisini ayırır; review_service.py görünür degraded_features flag'i yazar.
Ayrıca: provider-hatası sonucu ARTIK CACHE'LENMEZ (önceden 7 gün TTL'lik geçici
bir ağ hatasını "kalıcı gerçek" gibi cache'e yazıyordu — ayrı, ilişkili bir hata).
"""

from __future__ import annotations

import asyncio
import logging
import re
from difflib import SequenceMatcher
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.config import Settings, get_settings
from api.db.redis_client import CacheNamespace, cache_get, cache_set
from api.models.review import (
    CitationContextFinding,
    CitationIntegritySummary,
    CitationStatus,
    ContextSupport,
    CoverageGap,
    InTextCitation,
    ManuscriptMeta,
    ParsedReference,
    SupportLevel,
)
from api.services.llm_service import LLMServiceError, call
from api.services.openalex_polite import (
    OpenAlexError,
    _abstract_from_inverted,
    _normalize_doi,
    fetch_work_by_doi,
    search_works_raw,
)
from engine.providers.semantic_scholar import (
    SemanticScholarError,
    SemanticScholarMatch,
    search_semantic_scholar,
)

logger = logging.getLogger(__name__)

# --- eşzamanlılık + eşikler -------------------------------------------------

_CONCURRENCY = 5  # OpenAlex polite 10/sec; semaphore + altyapı limiter çift kemer.
_TITLE_MATCH_THRESHOLD = 0.82  # SequenceMatcher oranı — resolved kabulü.
_TITLE_CONFLICT_THRESHOLD = 0.45  # DOI bu eserin değil → altında ise fabricated adayı.
_YEAR_TOLERANCE = 1  # ±1 yıl baskı/online-first farkı.
_SURNAME_OVERLAP_RATIO_THRESHOLD = 0.5  # tek yaygın-soyad tesadüfünü elemek için.
_COVERAGE_MIN_CITED_BY = 500  # seminal eşiği (yüksek-atıf).
_COVERAGE_CANDIDATES = 12

_CACHE_NS = CacheNamespace.ENRICH  # 7 gün TTL — atıf çözümü yavaş değişir.
_WS_RE = re.compile(r"\s+")


# --- yardımcılar ------------------------------------------------------------


def _norm_title(title: str | None) -> str:
    """Başlık normalizasyonu — küçük harf, noktalama temiz, tek boşluk."""
    if not title:
        return ""
    t = re.sub(r"[^\w\s]", " ", title.lower(), flags=re.UNICODE)
    return _WS_RE.sub(" ", t).strip()


def _title_ratio(a: str | None, b: str | None) -> float:
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _work_title(work: dict[str, Any]) -> str | None:
    return work.get("title") or work.get("display_name")


def _work_year(work: dict[str, Any]) -> int | None:
    y = work.get("publication_year")
    return int(y) if isinstance(y, int) else None


def _work_short_id(work: dict[str, Any]) -> str | None:
    wid = work.get("id")
    return wid.rsplit("/", 1)[-1] if isinstance(wid, str) and wid else None


def _year_ok(ref_year: int | None, work_year: int | None) -> bool:
    if ref_year is None or work_year is None:
        return True  # yıl eksik → yıl çelişki iddia edilemez (R-1).
    return abs(ref_year - work_year) <= _YEAR_TOLERANCE


_DOI_SHAPED_RE = re.compile(r"^10\.\d{4,9}/", re.IGNORECASE)


def _work_title_is_malformed(work: dict[str, Any]) -> bool:
    """OpenAlex kaydının başlığı güvenilir mi? (bazı kayıtlarda başlık alanı
    boş ya da DOI'nin kendisiyle doldurulmuş oluyor — gözlemlendi: LDA makalesi
    W4237791300, başlık='10.1162/jmlr.2003.3.4-5.993'). Böyle bir kayıt,
    başlık-çelişkisi kanıtı olarak GÜVENİLMEZ (yanlış "fabricated" damgası
    riski) — R-1 disiplini: kanıtın kendisi bozuksa suçlama üretilmez."""
    title = _work_title(work)
    if not title or not title.strip():
        return True
    return bool(_DOI_SHAPED_RE.match(title.strip()))


def _work_authors(work: dict[str, Any]) -> list[str]:
    return [
        a.get("author", {}).get("display_name", "")
        for a in (work.get("authorships") or [])
        if a.get("author", {}).get("display_name")
    ]


def _surname_from_ref_author(name: str) -> str:
    """Referans yazar formatı iki türlü gelebilir:
      1) 'Soyad, A. B.' (APA/virgüllü) — virgülden önceki ilk parça soyad.
      2) 'Ad Soyad' (virgülsüz tam isim — 2026-08-27 Oxford-liste fix'i
         SONRASI _split_author_block'un ürettiği doğru format, bkz
         engine/ingestion/common.py) — son kelime soyad, _surname_from_work_author
         ile AYNI sezgi.
    2026-08-28 düzeltme: (2) öncesi TÜM string "soyad" sayılıyordu ("wenbing
    huang" ≠ "huang") — S2/OpenAlex'in doğru bulduğu eşleşmeler bile yazar
    uyuşmuyor sanılıp reddediliyordu (semantic_scholar_recovered hep 0 kaldı,
    canlı prod testiyle doğrulandı: 2026-08-28, imT03YXlG2, guardian onaylı)."""
    head = name.split(",", 1)[0].strip()
    if "," in name:
        return _norm_title(head)
    parts = [p for p in head.split() if p]
    return _norm_title(parts[-1]) if parts else ""


def _surname_from_work_author(name: str) -> str:
    """OpenAlex yazar formatı 'Ad Orta Soyad' — son kelime soyad (kaba sezgi)."""
    parts = [p for p in name.strip().split() if p]
    return _norm_title(parts[-1]) if parts else ""


def _has_author_surname_overlap(ref_authors: list[str], work: dict[str, Any]) -> bool:
    """Referans ve OpenAlex eserinin yazar soyadları YETERİNCE örtüşüyor mu?

    Dil-arası başlık farkında (örn. çevrilmiş başlık) yazar soyadları dilden
    bağımsız kalır — başlık benzerliği düşük olsa bile soyad örtüşmesi güçlü
    bir 'aynı eser' sinyali olabilir (uydurma DEĞİL). AMA tek bir ortak soyad
    yeterli SAYILMAZ: yaygın soyadlar (Kim/Lee/Wang/Smith/Chen gibi) çok-
    yazarlı iki alakasız eser arasında tesadüfen çakışabilir — bu, gerçek bir
    uydurma atfı sessizce 'resolved'a çevirebilir (2026-08-05 moat guardian
    bulgusu, eşiksiz hali hiç production'a girmedi — bkz.
    PDF_PIPELINE_CALISMA_GUNLUGU.md). Bu yüzden referans yazarlarının en az
    _SURNAME_OVERLAP_RATIO_THRESHOLD oranı OpenAlex kaydında bulunmalı (tek
    yazarlı referansta bu otomatik %100 — tesadüf riski orada da var ama DOI
    zaten o kayda çözülmüş olduğundan zayıflaşan bağımsız bir kanıt katmanı)."""
    ref_surnames = {_surname_from_ref_author(a) for a in ref_authors if a}
    ref_surnames.discard("")
    if not ref_surnames:
        return False
    work_surnames = {_surname_from_work_author(a) for a in _work_authors(work)}
    work_surnames.discard("")
    overlap = ref_surnames & work_surnames
    if not overlap:
        return False
    return len(overlap) / len(ref_surnames) >= _SURNAME_OVERLAP_RATIO_THRESHOLD


def _has_author_surname_overlap_plain(ref_authors: list[str], match_authors: list[str]) -> bool:
    """`_has_author_surname_overlap`'in AYNI eşik/mantığı — S2'nin düz "Ad Soyad"
    yazar listesi için (OpenAlex work dict'i DEĞİL, bkz. semantic_scholar.py
    SemanticScholarMatch.authors). Aynı yanlış-tesadüf riski (2026-08-05 guardian
    bulgusu) burada da geçerli — eşiksiz bırakılmaz."""
    ref_surnames = {_surname_from_ref_author(a) for a in ref_authors if a}
    ref_surnames.discard("")
    if not ref_surnames:
        return False
    match_surnames = {_surname_from_work_author(a) for a in match_authors if a}
    match_surnames.discard("")
    overlap = ref_surnames & match_surnames
    if not overlap:
        return False
    return len(overlap) / len(ref_surnames) >= _SURNAME_OVERLAP_RATIO_THRESHOLD


async def _resolve_via_semantic_scholar(
    ref: ParsedReference, cfg: Settings
) -> ParsedReference | None:
    """OpenAlex not_found_in_index dedikten SONRA çağrılır (bkz. resolve_all).
    Başlık yoksa aramaya gerek yok → None. S2 hata verirse (SemanticScholarError)
    loglanır, None döner — çağıran ref'i OLDUĞU GİBİ (not_found_in_index) bırakır,
    ASLA daha kötü olmaz. Eşleşme bulunursa resolved ParsedReference döner.

    Fabricated/retracted tespiti YAPILMAZ (bilinçli dar kapsam, bkz.
    semantic_scholar.py modül docstring) — sadece resolved YÜKSELTMESİ.

    2026-08-23 devamı: S2_FALLBACK_ENABLED=False (varsayılan) ise EN BAŞTA,
    hiçbir kontrol/ağ çağrısı yapmadan döner — key olsa BİLE. Kenan'ın "key
    gelene kadar bekleyecek zaman yok, ayrı bir açma/kapama anahtarı olsun"
    talebi (SEMANTIC_SCHOLAR_API_KEY boşluğu zaten devre dışı bırakıyordu,
    bu EK ve daha açık bir anahtar)."""
    if not cfg.S2_FALLBACK_ENABLED:
        return None
    if not ref.title or not _norm_title(ref.title):
        logger.info(
            "semantic_scholar SKIP (başlık yok/boş) index=%d raw=%r", ref.index, ref.raw[:80]
        )
        return None
    query = ref.title
    if ref.authors:
        query = f"{ref.title} {ref.authors[0]}"

    try:
        matches = await search_semantic_scholar(query, limit=5)
    except SemanticScholarError as exc:
        # "not configured" (key yok) BEKLENEN bir durum — WARNING değil INFO
        # (openalex.py:_map_error_status'un auth_missing ayrımıyla AYNI ruh).
        # Diğer her şey (429/network/malformed) GERÇEK arıza — WARNING kalır.
        if "not configured" in str(exc):
            logger.info("semantic_scholar SKIP (key yok) index=%d", ref.index)
        else:
            logger.warning(
                "semantic_scholar fallback failed index=%d title=%r err=%s",
                ref.index,
                ref.title,
                exc,
            )
        return None

    best: SemanticScholarMatch | None = None
    best_ratio = 0.0
    for m in matches:
        r = _title_ratio(ref.title, m.title)
        if r > best_ratio:
            best_ratio, best = r, m

    # 2026-08-23 (kullanıcı bulgusu: semantic_scholar_recovered hep 0 çıktı,
    # "muhtemelen" denmeden kanıtla) — DENENDİ ama eşleşmedi durumu ÖNCEDEN
    # hiç loglanmıyordu, sadece sert hata (SemanticScholarError) loglanıyordu.
    # Bu INFO satırı olmadan "S2'ye istek gitti mi" logdan asla anlaşılamazdı.
    if best is None or best_ratio < _TITLE_MATCH_THRESHOLD:
        logger.info(
            "semantic_scholar NO-MATCH index=%d n_candidates=%d best_ratio=%.2f title=%r",
            ref.index,
            len(matches),
            best_ratio,
            ref.title[:80],
        )
        return None
    if not _year_ok(ref.year, best.year):
        logger.info(
            "semantic_scholar YEAR-MISMATCH index=%d ref_year=%s s2_year=%s ratio=%.2f",
            ref.index,
            ref.year,
            best.year,
            best_ratio,
        )
        return None
    # Tek-yazarlı/yazar-yok referansta soyad örtüşmesi zaten boş küme →
    # kontrol atlanır (OpenAlex yolundaki DOI-çözümüyle aynı gevşeklik, ama
    # burada DOI YOK — bu yüzden başlık+yıl eşiği (_TITLE_MATCH_THRESHOLD=0.82,
    # _YEAR_TOLERANCE=±1) TEK başına yeterli kanıt sayılır; yazar varsa EK
    # doğrulama katmanı olarak kullanılır, yoksa reddedilmez.
    if ref.authors and best.authors and not _has_author_surname_overlap_plain(
        ref.authors, best.authors
    ):
        logger.info(
            "semantic_scholar AUTHOR-MISMATCH index=%d ref_authors=%r s2_authors=%r ratio=%.2f",
            ref.index,
            ref.authors,
            best.authors,
            best_ratio,
        )
        return None
    logger.info(
        "semantic_scholar UPGRADED index=%d ratio=%.2f title=%r",
        ref.index,
        best_ratio,
        ref.title[:80],
    )

    return ref.model_copy(
        update={
            "status": "resolved",
            "evidence": (
                f"OpenAlex'te bulunamadı; Semantic Scholar'da çözüldü "
                f"(başlık benzerliği {best_ratio:.2f}"
                + (f"; DOI: {best.doi}" if best.doi else "")
                + f"). Eser: '{best.title}'. NOT: bu kaynak OpenAlex'in kapsam "
                "boşluğunu (arXiv/OpenReview gibi linkler) kapatmak için "
                "kullanıldı, fabricated/retracted tespiti İÇİN kullanılmadı."
            ),
        }
    )


def _cache_key(ref: ParsedReference) -> str | None:
    if ref.doi:
        return f"rc:doi:{_normalize_doi(ref.doi)}"
    nt = _norm_title(ref.title)
    if nt:
        return f"rc:title:{nt}:{ref.year or ''}"
    return None


# --- destek seviyesi eşlemesi (P04-T03 — 6-değer SupportLevel) --------------
# Mimari katman: SupportLevel YALNIZ atıf-çözüm sinyallerinin (CitationStatus +
# özet erişimi + atıf-bağlam yargısı) bir fonksiyonudur — bunların hepsini bu
# servis üretir (resolve_*/check_context). Bu yüzden mapper buraya konur (kanıt
# katmanı), engine/academic'e DEĞİL (o makale-değerlendirme katmanı). Saf,
# deterministik, LLM yok. evidence_provider_spec.md §Support levels semantiğine
# birebir sadık; abstract-only ASLA full_text_verified'a yükseltilmez.


def map_support_level(
    *,
    claim_needs_citation: bool = True,
    citation_status: CitationStatus | None = None,
    abstract_available: bool = False,
    full_text_verified: bool = False,
    context_support: ContextSupport | None = None,
) -> SupportLevel:
    """Atıf-çözüm sinyallerini 6-değerli SupportLevel'a eşle (deterministik).

    Sinyaller:
      claim_needs_citation — iddia atıf gerektiriyor mu (False → not_applicable).
      citation_status      — ParsedReference.status (resolve_reference çıktısı).
      abstract_available   — kaynağın özeti elde edildi mi (check_context bağlamı).
      full_text_verified   — açık full-text kaynakla doğrulandı mı (şu an False;
                             abstract'tan ASLA türetilmez — spec açık).
      context_support      — CitationContextFinding.support (atıf-bağlam yargısı).

    Öncelik sırası (yukarıdan aşağı, ilk eşleşen kazanır — belgelenmiş kural):
      1. atıf gerekmiyor                        → not_applicable
      2. bağlam açıkça ÇELİŞİYOR                 → contradictory
      3. kaynak çözülemedi / uydurma             → unresolved
         (not_found_in_index, fabricated, None — niyetlenen kaynak elde yok)
      4. çözüldü + açık full-text doğrulaması     → full_text_verified
      5. çözüldü + özet var                       → abstract_only
      6. çözüldü, sadece metadata                 → metadata_only

    NOT (spec citation-integrity rules): fabricated = verilen DOI BAŞKA esere ait
    → niyetlenen kaynak çözülemedi → 'unresolved' (full_text/abstract gibi
    SUNULMAZ; over-claim yasak). retracted = gerçek esere çözüldü (geri-çekilmiş);
    destek-seviyesi için çözülmüş sayılır (geri-çekilme ayrı bütünlük bayrağıdır).
    """
    if not claim_needs_citation:
        return "not_applicable"
    if context_support == "contradicted":
        return "contradictory"
    if citation_status in (None, "not_found_in_index", "fabricated"):
        return "unresolved"
    # Buradan sonra: çözüldü ('resolved') veya geri-çekilmiş ('retracted') —
    # gerçek esere ulaşıldı; doğrulama derinliğine göre derecelendir.
    if full_text_verified:
        return "full_text_verified"
    if abstract_available:
        return "abstract_only"
    return "metadata_only"


# --- tek referans çözümü (S2) ----------------------------------------------


def _resolve_via_work(
    ref: ParsedReference, work: dict[str, Any], *, matched_by: str
) -> ParsedReference:
    """Bulunan Work → resolved/retracted; retraction defensif okunur."""
    is_retracted = bool(work.get("is_retracted", False))
    short = _work_short_id(work)
    wtitle = _work_title(work) or "(başlıksız)"
    if is_retracted:
        return ref.model_copy(
            update={
                "status": "retracted",
                "openalex_id": short,
                "is_retracted": True,
                "evidence": (
                    f"OpenAlex çözdü ({matched_by}: {short}) ve geri-çekilme "
                    f"bayrağı taşıyor (is_retracted=true). Eser: '{wtitle}'."
                ),
            }
        )
    return ref.model_copy(
        update={
            "status": "resolved",
            "openalex_id": short,
            "is_retracted": False,
            "evidence": f"OpenAlex'te çözüldü ({matched_by}: {short}; '{wtitle}').",
        }
    )


async def resolve_reference(
    ref: ParsedReference, *, settings: Settings | None = None
) -> ParsedReference:
    """Tek referansı OpenAlex'te çöz; status + evidence doldur (R-1 disiplini).

    Akış: DOI öncelik → DOI eser-tutarlılığı (fabricated tespiti) → başlık+yazar+yıl
    fuzzy → çözülemezse DÜRÜST not_found_in_index (suçlama değil).
    """
    cfg = settings or get_settings()
    ck = _cache_key(ref)
    if ck:
        cached = cache_get(_CACHE_NS, ck)
        if isinstance(cached, dict):
            return ref.model_copy(
                update={
                    "status": cached["status"],
                    "openalex_id": cached.get("openalex_id"),
                    "is_retracted": cached.get("is_retracted", False),
                    "evidence": cached.get("evidence"),
                }
            )

    result = await _resolve_uncached(ref, cfg)

    if ck and not result.resolution_degraded:
        # §41: provider-hatası kaynaklı sonuç CACHE'LENMEZ — geçici bir ağ
        # arızasını 7 gün boyunca "kalıcı gerçek" olarak dondurmamak için
        # (bir sonraki çağrı gerçekten yeniden denemeli, cache'teki bayat
        # hatayı tekrar tekrar döndürmemeli).
        cache_set(
            _CACHE_NS,
            ck,
            {
                "status": result.status,
                "openalex_id": result.openalex_id,
                "is_retracted": result.is_retracted,
                "evidence": result.evidence,
            },
        )
    return result


async def _resolve_uncached(ref: ParsedReference, cfg: Settings) -> ParsedReference:
    # 1) DOI yolu — en güçlü kanıt.
    if ref.doi:
        try:
            work = await fetch_work_by_doi(ref.doi, settings=cfg)
        except OpenAlexError as exc:
            # Ağ/servis hatası → dürüst not_found_in_index (suçlama DEĞİL); loglanır.
            logger.warning(
                "resolve_reference DOI fetch failed index=%d doi=%s err=%s",
                ref.index,
                ref.doi,
                exc,
            )
            return ref.model_copy(
                update={
                    "status": "not_found_in_index",
                    "evidence": (
                        "OpenAlex DOI sorgusu servis hatası verdi; çözülemedi. "
                        "Mevcut olmadığı anlamına GELMEZ (geçici hata)."
                    ),
                    "resolution_degraded": True,
                }
            )
        if work is None:
            # DOI OpenAlex'te yok → indekssiz olabilir; suçlama değil.
            return ref.model_copy(
                update={
                    "status": "not_found_in_index",
                    "evidence": (
                        f"Verilen DOI ({_normalize_doi(ref.doi)}) OpenAlex'te "
                        "bulunamadı; mevcut olmadığı anlamına gelmez (niş/indekssiz olabilir)."
                    ),
                }
            )
        # DOI bulundu — ama verilen başlık eserle çelişiyor mu? (fabricated tespiti)
        if ref.title:
            ratio = _title_ratio(ref.title, _work_title(work))
            wyear = _work_year(work)
            short = _work_short_id(work)
            if ratio < _TITLE_CONFLICT_THRESHOLD:
                if _work_title_is_malformed(work):
                    # OpenAlex kaydının kendi başlığı güvenilmez (boş/DOI-şekilli)
                    # → başlık karşılaştırması anlamsız, suçlama üretilemez.
                    return ref.model_copy(
                        update={
                            "status": "not_found_in_index",
                            "evidence": (
                                f"DOI ({_normalize_doi(ref.doi)}) OpenAlex'te bir "
                                f"kayda çözüldü ({short}) ama o kaydın başlık alanı "
                                "eksik/bozuk (örn. DOI'nin kendisiyle dolu) — "
                                "güvenilir bir karşılaştırma yapılamıyor, kesin "
                                "eşleşme iddia edilemez (suçlama değil)."
                            ),
                        }
                    )
                if _has_author_surname_overlap(ref.authors, work):
                    # Başlık metni çok farklı görünse de (örn. dil-arası çeviri —
                    # kaynakça İngilizce çeviri başlık kullanmış, OpenAlex orijinal
                    # dilde kaydetmiş) yazar soyadı örtüşmesi güçlü bir "aynı eser"
                    # kanıtı — dil bağımsız. Uydurma İDDİASI DEĞİL.
                    return ref.model_copy(
                        update={
                            "status": "resolved",
                            "openalex_id": short,
                            "is_retracted": bool(work.get("is_retracted", False)),
                            "evidence": (
                                f"OpenAlex'te çözüldü (DOI: {short}). Başlık metni "
                                f"farklı görünüyor (benzerlik {ratio:.2f}) ama yazar "
                                "soyadları örtüşüyor — muhtemelen dil-arası çeviri "
                                "başlık farkı (uydurma atıf iddiası DEĞİLDİR)."
                            ),
                        }
                    )
                # Başlık gerçekten farklı bir esere işaret ediyor VE yazar
                # örtüşmesi de yok → gerçek pozitif çelişki (fabricated).
                return ref.model_copy(
                    update={
                        "status": "fabricated",
                        "openalex_id": short,
                        "is_retracted": bool(work.get("is_retracted", False)),
                        "evidence": (
                            f"POZİTİF ÇELİŞKİ: verilen DOI ({_normalize_doi(ref.doi)}) "
                            f"OpenAlex'te BAŞKA esere ait ({short}: "
                            f"'{_work_title(work)}', yıl {wyear}). "
                            f"Kaynakçadaki başlık: '{ref.title}' (yıl {ref.year}). "
                            f"Başlık benzerliği {ratio:.2f} < {_TITLE_CONFLICT_THRESHOLD}, "
                            "yazar soyadı örtüşmesi de yok."
                        ),
                    }
                )
            if not _year_ok(ref.year, wyear):
                # Başlık çelişmiyor ama yıl uyuşmuyor. İki alt durum:
                #   (a) başlık GÜÇLÜ eşleşiyor (>= match eşiği) → muhtemelen
                #       online-first/baskı tarihi farkı (çok yaygın, akademik
                #       yayıncılıkta normal) — bu bir uydurma İDDİASI DEĞİL,
                #       dürüst bir düzeltme/doğrulama önerisi olarak sunulur
                #       (HK-3 "yok ≠ uydurma" ilkesinin doğal uzantısı:
                #       "yıl farkı ≠ uydurma").
                #   (b) başlık orta bölgede (ne net eşleşme ne net çelişki) →
                #       kesin eşleşme iddia edilemez, dürüst not_found.
                if ratio >= _TITLE_MATCH_THRESHOLD:
                    return ref.model_copy(
                        update={
                            "status": "resolved",
                            "openalex_id": short,
                            "is_retracted": bool(work.get("is_retracted", False)),
                            "evidence": (
                                f"OpenAlex'te çözüldü (DOI: {short}; başlık "
                                f"benzerliği {ratio:.2f}). YIL FARKI: kaynakçada "
                                f"{ref.year}, OpenAlex'te {wyear} — muhtemelen "
                                "online-first/baskı tarihi farkı; yazarın "
                                "kontrol etmesi önerilir (uydurma atıf iddiası "
                                "DEĞİLDİR, düzeltme önerisidir)."
                            ),
                        }
                    )
                return ref.model_copy(
                    update={
                        "status": "not_found_in_index",
                        "evidence": (
                            f"DOI OpenAlex'te bir esere çözüldü ({short}) ama "
                            f"başlık benzerliği ({ratio:.2f}) sınırda ve yıl da "
                            f"uyuşmuyor (kaynakçada {ref.year}, OpenAlex'te "
                            f"{wyear}) — kesin eşleşme iddia edilemiyor "
                            "(suçlama değil, dürüst belirsizlik)."
                        ),
                    }
                )
        return _resolve_via_work(ref, work, matched_by="DOI")

    # 2) Başlık+yazar+yıl fuzzy yolu.
    if ref.title and _norm_title(ref.title):
        query = ref.title
        if ref.authors:
            query = f"{ref.title} {ref.authors[0]}"
        try:
            works = await search_works_raw(query, limit=5, settings=cfg)
        except OpenAlexError as exc:
            logger.warning(
                "resolve_reference title search failed index=%d title=%r err=%s",
                ref.index,
                ref.title,
                exc,
            )
            return ref.model_copy(
                update={
                    "status": "not_found_in_index",
                    "evidence": (
                        "OpenAlex başlık araması servis hatası verdi; çözülemedi. "
                        "Mevcut olmadığı anlamına GELMEZ (geçici hata)."
                    ),
                    "resolution_degraded": True,
                }
            )
        best: dict[str, Any] | None = None
        best_ratio = 0.0
        for w in works:
            r = _title_ratio(ref.title, _work_title(w))
            if r > best_ratio:
                best_ratio, best = r, w
        if best is not None and best_ratio >= _TITLE_MATCH_THRESHOLD and _year_ok(
            ref.year, _work_year(best)
        ):
            return _resolve_via_work(
                ref, best, matched_by=f"başlık+yazar+yıl ~{best_ratio:.2f}"
            )
        # Eşleşme yeterince güçlü değil → DÜRÜST not_found (R-1 — fabricated DEĞİL).
        return ref.model_copy(
            update={
                "status": "not_found_in_index",
                "evidence": (
                    # 2026-08-23 düzeltme (guardian bulgusu): önceden "OpenAlex/S2'de"
                    # diyordu ama S2 bu fonksiyonda HİÇ çağrılmıyor (resolve_all'da,
                    # AYRI bir adım olarak, sadece bu status not_found_in_index
                    # kaldığında denenir) — kanıtsız iddia düzeltildi.
                    "OpenAlex'te başlık+yazar+yıl ile yeterince güçlü eşleşme "
                    f"bulunamadı (en iyi benzerlik {best_ratio:.2f} < "
                    f"{_TITLE_MATCH_THRESHOLD}); mevcut olmadığı anlamına gelmez "
                    "(Semantic Scholar fallback'i ayrıca denenir)."
                ),
            }
        )

    # 3) DOI yok + başlık yok → çözecek anahtar yok.
    return ref.model_copy(
        update={
            "status": "not_found_in_index",
            "evidence": (
                "Referansta DOI ve çözülebilir başlık yok; OpenAlex'te aranamadı. "
                "Mevcut olmadığı anlamına gelmez."
            ),
        }
    )


# --- toplu çözüm (S2) -------------------------------------------------------


async def resolve_all(
    refs: list[ParsedReference], *, settings: Settings | None = None
) -> tuple[list[ParsedReference], CitationIntegritySummary]:
    """Tüm referansları eşzamanlılık-sınırlı çöz + özet say (FE rozet).

    2026-08-23: OpenAlex not_found_in_index derse Semantic Scholar fallback'i
    AYRI, kendi (çok daha temkinli) eşzamanlılık sınırıyla denenir — OpenAlex
    akışı (_one içindeki resolve_reference çağrısı) HİÇ değiştirilmedi."""
    cfg = settings or get_settings()
    sem = asyncio.Semaphore(_CONCURRENCY)
    # S2'nin gözlemlenen agresif rate-limiti (bkz. semantic_scholar.py modül
    # docstring) yüzünden OpenAlex'in _CONCURRENCY=5'inden BAĞIMSIZ, çok daha
    # dar bir eşzamanlılık — S2_RATE_LIMITER zaten global sıralıyor ama ek bir
    # semaphore, aynı anda çok sayıda coroutine'in kuyrukta birikmesini
    # (ve hepsinin timeout'a yakın beklemesini) önler.
    s2_sem = asyncio.Semaphore(2)

    async def _one(r: ParsedReference) -> ParsedReference:
        async with sem:
            result = await resolve_reference(r, settings=cfg)
        if result.status != "not_found_in_index":
            return result
        async with s2_sem:
            upgraded = await _resolve_via_semantic_scholar(result, cfg)
        return upgraded if upgraded is not None else result

    resolved = await asyncio.gather(*(_one(r) for r in refs))
    resolved_list = list(resolved)

    summary = CitationIntegritySummary(total=len(resolved_list))
    for r in resolved_list:
        if r.status == "resolved":
            summary.resolved += 1
            # _resolve_via_semantic_scholar'ın evidence metninde HEP bu işaretçi
            # var (bkz. yukarısı) — OpenAlex'in kendi evidence metinleri bunu
            # asla üretmez, güvenilir bir ayrım sinyali.
            if "Semantic Scholar" in (r.evidence or ""):
                summary.semantic_scholar_recovered += 1
        elif r.status == "not_found_in_index":
            summary.not_found_in_index += 1
        elif r.status == "fabricated":
            summary.fabricated += 1
        elif r.status == "retracted":
            summary.retracted += 1
        if r.resolution_degraded:
            # §41: not_found_in_index sayacının İÇİNDE saklı kalan, sağlayıcı
            # hatası kaynaklı alt-küme — çağıran (review_service.py) bunu
            # görünür degraded_features flag'ine çevirir.
            summary.provider_errors += 1
    return resolved_list, summary


# --- atıf-bağlam (S3) -------------------------------------------------------


class _ContextGrade(BaseModel):
    """LLM derecelendirme çıktısı — 3-değerli; belirsizlik birinci sınıf (HK-4)."""

    model_config = ConfigDict(extra="forbid")

    support: ContextSupport
    evidence: str = Field("")


_CONTEXT_PROMPT = (
    "Görev: bir akademik makaledeki İDDİA cümlesini, atıf yapılan kaynağın ÖZETİYLE "
    "karşılaştır. SADECE özetten çıkarılabileni değerlendir.\n"
    "Çıktı JSON: {{\"support\": \"supported|contradicted|unverifiable_from_abstract\", "
    "\"evidence\": \"<kısa gerekçe>\"}}\n"
    "KURAL: Özet iddiayı açıkça doğruluyorsa 'supported'. Özet iddiayla açıkça "
    "çelişiyorsa 'contradicted'. Özet konuyu hiç ele almıyorsa/yetersizse "
    "'unverifiable_from_abstract' — ASLA tahminle suçlama yapma.\n\n"
    "İDDİA: {claim}\n\nKAYNAK ÖZET: {abstract}\n"
)


async def _grade_context(
    finding_ref: ParsedReference,
    claim: str,
    abstract: str | None,
    cfg: Settings,
) -> tuple[ContextSupport, str | None, str | None]:
    """Tek iddia-kaynak çifti → (support, evidence, abstract_excerpt). HK-4 dürüst."""
    if not abstract or len(abstract.strip()) < 40:
        return (
            "unverifiable_from_abstract",
            "Kaynağın özeti yok veya çok kısa; iddia özetten teyit edilemez.",
            None,
        )
    excerpt = abstract[:400]
    try:
        resp = await call(
            _CONTEXT_PROMPT.format(claim=claim, abstract=excerpt),
            tier="flash",
            structured_output_schema=_ContextGrade,
            settings=cfg,
        )
    except LLMServiceError as exc:
        # LLM hatası → dürüst belirsizlik (suçlama DEĞİL); loglanır.
        logger.warning(
            "context grade LLM failed ref_index=%d err=%s", finding_ref.index, exc
        )
        return (
            "unverifiable_from_abstract",
            "Derecelendirme servisi yanıt veremedi; özetten teyit edilemedi.",
            excerpt,
        )
    parsed = resp.parsed_output
    if not isinstance(parsed, _ContextGrade):
        return (
            "unverifiable_from_abstract",
            "Derecelendirme çıktısı çözümlenemedi; özetten teyit edilemedi.",
            excerpt,
        )
    return parsed.support, (parsed.evidence or None), excerpt


async def check_context(
    in_text: list[InTextCitation],
    refs: list[ParsedReference],
    *,
    settings: Settings | None = None,
) -> list[CitationContextFinding]:
    """Metin-içi iddialar ↔ atıf kaynağının özeti → CitationContextFinding (HK-4).

    Yalnız resolved/retracted (openalex_id'si olan) referanslar için özet çekilir;
    çözülemeyen referans için bağlam denetimi yapılmaz (suçlama üretmemek için).
    """
    cfg = settings or get_settings()
    by_index = {r.index: r for r in refs}

    # Çözülmüş ref'lerin özetlerini çek (tek tek; W-id'den).
    from api.services.openalex_polite import fetch_work_by_id  # local — döngüsel önleme

    sem = asyncio.Semaphore(_CONCURRENCY)

    async def _abstract_for(ref: ParsedReference) -> str | None:
        if not ref.openalex_id:
            return None
        async with sem:
            try:
                work = await fetch_work_by_id(ref.openalex_id, settings=cfg)
            except OpenAlexError as exc:
                logger.warning(
                    "context abstract fetch failed ref_index=%d err=%s", ref.index, exc
                )
                return None
        if work is None:
            return None
        return _abstract_from_inverted(work.get("abstract_inverted_index"))

    # Hangi ref_index'ler için iddia var?
    relevant = [
        c for c in in_text if c.ref_index is not None and c.ref_index in by_index
    ]
    abstract_cache: dict[int, str | None] = {}
    needed = sorted({c.ref_index for c in relevant if c.ref_index is not None})
    abstracts = await asyncio.gather(
        *(_abstract_for(by_index[i]) for i in needed)
    )
    for i, a in zip(needed, abstracts, strict=True):
        abstract_cache[i] = a

    findings: list[CitationContextFinding] = []

    async def _one(c: InTextCitation) -> CitationContextFinding:
        ref = by_index[c.ref_index]  # type: ignore[index]
        abstract = abstract_cache.get(c.ref_index)
        support, evidence, excerpt = await _grade_context(
            ref, c.sentence, abstract, cfg  # type: ignore[arg-type]
        )
        # 6-değerli kanıt seviyesini GERÇEK sinyallerden türet (map_support_level
        # canlı): atıf-çözüm durumu + özet erişimi + bağlam yargısı. Metin-içi atıf
        # mevcut (relevant filtresi) → iddia atıf gerektiriyor. full_text_verified
        # sinyali yok → False (abstract'tan ASLA full_text türetilmez; spec açık).
        support_level = map_support_level(
            claim_needs_citation=True,
            citation_status=ref.status,
            abstract_available=bool(abstract and abstract.strip()),
            full_text_verified=False,
            context_support=support,
        )
        return CitationContextFinding(
            ref_index=c.ref_index,  # type: ignore[arg-type]
            claim=c.sentence,
            support=support,
            support_level=support_level,
            evidence=evidence,
            cited_abstract_excerpt=excerpt,
        )

    findings = list(await asyncio.gather(*(_one(c) for c in relevant)))
    return findings


# --- kapsama boşlukları (S3) ------------------------------------------------


async def find_coverage_gaps(
    manuscript_meta: ManuscriptMeta,
    refs: list[ParsedReference],
    *,
    settings: Settings | None = None,
) -> list[CoverageGap]:
    """Makale konusundan yüksek-atıflı seminal işleri bul; kaynakçada OLMAYANLARI dön.

    Honest (HK): konu yoksa veya aday bulunmazsa BOŞ liste döner — uydurma yok.
    Eşleştirme: cited_by_count yüksek + başlık kaynakçadakilerle eşleşmiyor.
    """
    cfg = settings or get_settings()
    topic = (manuscript_meta.title or "").strip()
    if not topic and manuscript_meta.abstract:
        topic = manuscript_meta.abstract.strip()[:200]
    if not topic:
        return []

    # BE-2 / P02-T05: provider arızasını YUTMA. Eskiden burada `return []` vardı →
    # "kapsama boşluğu yok" gibi görünüyordu (sessiz fallback). Artık RE-RAISE;
    # çağıran (review_service) bunu GÖRÜNÜR degraded_features olarak işaretler.
    candidates = await search_works_raw(
        topic,
        limit=_COVERAGE_CANDIDATES,
        filters=[f"cited_by_count:>{_COVERAGE_MIN_CITED_BY}"],
        sort="cited_by_count:desc",
        settings=cfg,
    )

    # Kaynakçada olan eserlerin id + başlık seti.
    cited_ids = {r.openalex_id for r in refs if r.openalex_id}
    cited_titles = [r.title for r in refs if r.title]

    gaps: list[CoverageGap] = []
    for w in candidates:
        short = _work_short_id(w)
        if short and short in cited_ids:
            continue
        wtitle = _work_title(w)
        # Başlık fuzzy — kaynakçada zaten var mı (id eşleşmese de)?
        if wtitle and any(
            _title_ratio(wtitle, ct) >= _TITLE_MATCH_THRESHOLD for ct in cited_titles
        ):
            continue
        if not short or not wtitle:
            continue
        cited_by = int(w.get("cited_by_count") or 0)
        gaps.append(
            CoverageGap(
                openalex_id=short,
                title=wtitle,
                year=_work_year(w),
                cited_by_count=cited_by,
                reason=(
                    f"Konu '{topic[:60]}' için yüksek-atıflı seminal eser "
                    f"({cited_by} atıf) kaynakçada yer almıyor."
                ),
            )
        )

    return gaps


__all__ = [
    "check_context",
    "find_coverage_gaps",
    "map_support_level",
    "resolve_all",
    "resolve_reference",
]
