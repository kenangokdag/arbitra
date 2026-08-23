"""F14-S2/S3 — atıf bütünlüğü + bağlam motoru testleri.

R-1 / HK-3 kanıtı: "yok ≠ uydurma". KRİTİK fixture:
  - bilinen DOI → resolved
  - DOI yok + başlık eşleşmiyor → not_found_in_index (FABRICATED DEĞİL)
  - DOI verilmiş ama başka başlığa ait → fabricated (pozitif çelişki)
  - bağlam: özet destekliyor → supported; özet yok → unverifiable_from_abstract

Ağ MOCK'lanır (httpx transport enjeksiyonu — gerçek OpenAlex çağrısı YOK).
LLM `call` monkeypatch ile sahte derecelendirme döner.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from api.models.review import InTextCitation, ManuscriptMeta, ParsedReference

pytestmark = pytest.mark.unit


# --- ağ mock altyapısı ------------------------------------------------------


class _RouteTransport(httpx.AsyncBaseTransport):
    """URL+query'e göre sabit JSON/status döndüren mock transport.

    routes: list[(predicate(request)->bool, status_code, json_body)]
    İlk eşleşen kazanır; eşleşmezse 404.
    """

    def __init__(self, routes: list[tuple[Any, int, dict[str, Any]]]) -> None:
        self.routes = routes
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for pred, status, body in self.routes:
            if pred(request):
                return httpx.Response(status, text=json.dumps(body))
        return httpx.Response(404, text='{"error":"not_found"}')


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Polite email + cache no-op (redis'siz deterministik) + retry hızlı."""
    monkeypatch.setenv("OPENALEX_EMAIL", "test@example.invalid")
    monkeypatch.setenv("RETRY_ATTEMPTS", "1")
    from api.config import get_settings

    get_settings.cache_clear()

    import api.services.review_citation_service as rcs

    monkeypatch.setattr(rcs, "cache_get", lambda ns, key: None)
    monkeypatch.setattr(rcs, "cache_set", lambda ns, key, value, ttl=None: None)


def _inject_transport(
    transport: httpx.AsyncBaseTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_cls = httpx.AsyncClient

    def _factory(*a: Any, **kw: Any) -> httpx.AsyncClient:
        kw["transport"] = transport
        return real_cls(*a, **kw)

    import api.services.openalex_polite as op

    monkeypatch.setattr(op.httpx, "AsyncClient", _factory)


def _work(
    *,
    wid: str = "W123",
    title: str = "A Title",
    year: int = 2020,
    is_retracted: bool = False,
    cited_by: int = 10,
    abstract_inverted: dict[str, list[int]] | None = None,
    authors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"https://openalex.org/{wid}",
        "title": title,
        "display_name": title,
        "publication_year": year,
        "is_retracted": is_retracted,
        "cited_by_count": cited_by,
        "abstract_inverted_index": abstract_inverted,
        "authorships": [
            {"author": {"display_name": name}} for name in (authors or [])
        ],
    }


# --- S2 resolve_reference ---------------------------------------------------


async def test_known_doi_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bilinen DOI + tutarlı başlık → resolved."""
    work = _work(wid="W42", title="Attention Is All You Need", year=2017)
    transport = _RouteTransport(
        [(lambda r: "/works/doi:" in str(r.url), 200, work)]
    )
    _inject_transport(transport, monkeypatch)

    from api.services.review_citation_service import resolve_reference

    ref = ParsedReference(
        index=0,
        raw="Vaswani et al. 2017",
        title="Attention Is All You Need",
        year=2017,
        doi="10.5555/3295222.3295349",
    )
    out = await resolve_reference(ref)
    assert out.status == "resolved", out.evidence
    assert out.openalex_id == "W42"
    assert out.is_retracted is False


async def test_no_doi_title_mismatch_is_not_found_not_fabricated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R-1 KANIT: DOI yok + arama eşleşmiyor → not_found_in_index, FABRICATED DEĞİL."""
    # Arama tamamen ilgisiz bir eser döndürür (düşük benzerlik).
    transport = _RouteTransport(
        [
            (
                lambda r: r.url.path == "/works" and "search" in dict(r.url.params),
                200,
                {"results": [_work(wid="W9", title="Completely Unrelated Topic XYZ")]},
            )
        ]
    )
    _inject_transport(transport, monkeypatch)

    from api.services.review_citation_service import resolve_reference

    ref = ParsedReference(
        index=1,
        raw="Obscure niche book 1998",
        title="A Niche Monograph On Local Folklore",
        authors=["Yılmaz"],
        year=1998,
        doi=None,
    )
    out = await resolve_reference(ref)
    assert out.status == "not_found_in_index", out.evidence
    assert out.status != "fabricated"
    assert out.evidence and "anlamına gelmez" in out.evidence


async def test_doi_belongs_to_other_work_is_fabricated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOI OpenAlex'te BAŞKA başlığa ait → fabricated (pozitif çelişki kanıtıyla)."""
    # DOI çözülüyor ama dönen eserin başlığı referansla tamamen çelişiyor.
    other = _work(wid="W777", title="Photosynthesis In Deep Sea Algae", year=1995)
    transport = _RouteTransport(
        [(lambda r: "/works/doi:" in str(r.url), 200, other)]
    )
    _inject_transport(transport, monkeypatch)

    from api.services.review_citation_service import resolve_reference

    ref = ParsedReference(
        index=2,
        raw="Smith 2021, Quantum Gravity Review",
        title="A Comprehensive Review Of Quantum Gravity",
        year=2021,
        doi="10.1234/fake.doi",
    )
    out = await resolve_reference(ref)
    assert out.status == "fabricated", out.evidence
    assert out.openalex_id == "W777"
    assert out.evidence and "ÇELİŞKİ" in out.evidence


async def test_common_surname_coincidence_stays_fabricated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Moat guardian bulgusu (2026-08-05): DOI başka, alakasız bir esere ait +
    5 yazarlı referansın sadece biri (yaygın soyad 'Kim') OpenAlex kaydındaki
    5 alakasız yazardan biriyle tesadüfen çakışıyor. Tek eşleşme (oran 1/5=0.2)
    _SURNAME_OVERLAP_RATIO_THRESHOLD (0.5) altında kalmalı — gerçek bir
    uydurma atıf sessizce 'resolved'a çevrilmemeli."""
    other = _work(
        wid="W777",
        title="Photosynthesis In Deep Sea Algae",
        year=1995,
        authors=["Sarah Kim", "John Roberts", "Maria Fernandez", "Wei Zhang", "Anna Novak"],
    )
    transport = _RouteTransport(
        [(lambda r: "/works/doi:" in str(r.url), 200, other)]
    )
    _inject_transport(transport, monkeypatch)

    from api.services.review_citation_service import resolve_reference

    ref = ParsedReference(
        index=5,
        raw="Kim, D., Patel, R., Nguyen, T., Silva, F., & Ivanov, S. 2021",
        title="A Comprehensive Review Of Quantum Gravity",
        authors=["Kim, D.", "Patel, R.", "Nguyen, T.", "Silva, F.", "Ivanov, S."],
        year=2021,
        doi="10.1234/fake.doi",
    )
    out = await resolve_reference(ref)
    assert out.status == "fabricated", out.evidence
    assert out.openalex_id == "W777"


async def test_majority_surname_overlap_with_translated_title_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gerçek Godoy vakası (bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md #13): başlık
    dil-arası çeviri yüzünden çok farklı görünüyor ama yazarların TAMAMI
    (oran 1.0 >= eşik) örtüşüyor → resolved, uydurma iddiası değil."""
    work = _work(
        wid="W42",
        title="Temas E Padrões Temporais Na Formação De Professores",
        year=2021,
        authors=["Elenilton Vieira Godoy", "Fábio Gerab", "Vinício de Macedo Santos"],
    )
    transport = _RouteTransport(
        [(lambda r: "/works/doi:" in str(r.url), 200, work)]
    )
    _inject_transport(transport, monkeypatch)

    from api.services.review_citation_service import resolve_reference

    ref = ParsedReference(
        index=6,
        raw="Godoy, E., Gerab, F., & Santos, V. 2021",
        title="Themes And Patterns In Teacher Education",
        authors=["Godoy, E.", "Gerab, F.", "Santos, V."],
        year=2021,
        doi="10.5555/godoy",
    )
    out = await resolve_reference(ref)
    assert out.status == "resolved", out.evidence
    assert out.openalex_id == "W42"
    assert out.evidence and "dil-arası" in out.evidence


async def test_surname_overlap_ratio_boundary_at_threshold_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sınır durumu: 2 yazarlı referansın 1'i örtüşüyor (oran tam 0.5,
    _SURNAME_OVERLAP_RATIO_THRESHOLD'a EŞİT) → eşik >= oldugu için resolved."""
    work = _work(
        wid="W88",
        title="Different Language Title Entirely",
        year=2019,
        authors=["Ayşe Yılmaz", "Someone Else"],
    )
    transport = _RouteTransport(
        [(lambda r: "/works/doi:" in str(r.url), 200, work)]
    )
    _inject_transport(transport, monkeypatch)

    from api.services.review_citation_service import resolve_reference

    ref = ParsedReference(
        index=7,
        raw="Yılmaz, A. & Kaya, B. 2019",
        title="Tamamen Farklı Bir Başlık Metni",
        authors=["Yılmaz, A.", "Kaya, B."],
        year=2019,
        doi="10.5555/boundary",
    )
    out = await resolve_reference(ref)
    assert out.status == "resolved", out.evidence


async def test_retracted_work(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAlex çözer + is_retracted=true → retracted."""
    work = _work(wid="W55", title="Retracted Study On X", year=2014, is_retracted=True)
    transport = _RouteTransport(
        [(lambda r: "/works/doi:" in str(r.url), 200, work)]
    )
    _inject_transport(transport, monkeypatch)

    from api.services.review_citation_service import resolve_reference

    ref = ParsedReference(
        index=3,
        raw="Author 2014 retracted",
        title="Retracted Study On X",
        year=2014,
        doi="10.9/retracted",
    )
    out = await resolve_reference(ref)
    assert out.status == "retracted"
    assert out.is_retracted is True


async def test_doi_not_in_openalex_is_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOI OpenAlex'te yok (404) → not_found_in_index (suçlama değil)."""
    transport = _RouteTransport([])  # her şey 404
    _inject_transport(transport, monkeypatch)

    from api.services.review_citation_service import resolve_reference

    ref = ParsedReference(
        index=4, raw="X", title="Some Title", year=2000, doi="10.0/missing"
    )
    out = await resolve_reference(ref)
    assert out.status == "not_found_in_index"


async def test_doi_provider_error_marks_resolution_degraded_and_not_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§41 KANIT: DOI sorgusu servis hatası verirse (5xx/timeout/ağ) status
    not_found_in_index'e düşer AMA resolution_degraded=True işaretlenir — gerçek
    eşleşme-yokluğundan (404, zayıf benzerlik) AYIRT edilebilir. Sonuç ayrıca
    CACHE'LENMEZ (geçici hatayı 7 gün 'kalıcı gerçek' gibi dondurmamak için)."""
    import api.services.review_citation_service as rcs

    async def _boom(doi: str, *, settings: Any = None) -> Any:
        raise rcs.OpenAlexError("openalex fetch_work_by_doi failed: 503")

    monkeypatch.setattr(rcs, "fetch_work_by_doi", _boom)

    cache_calls: list[Any] = []
    monkeypatch.setattr(rcs, "cache_set", lambda *a, **k: cache_calls.append(a))

    ref = ParsedReference(
        index=0, raw="x", title="Some Title", year=2020, doi="10.1/err"
    )
    out = await rcs.resolve_reference(ref)
    assert out.status == "not_found_in_index"
    assert out.resolution_degraded is True
    assert not cache_calls, "provider-hatası cache'lenmemeli (7 gün TTL zehirlenmesi)"


async def test_title_search_provider_error_marks_resolution_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§41 KANIT: DOI yok + başlık araması servis hatası verirse aynı ayrım
    geçerli (bu ikinci çözüm yolu — DOI yolundan bağımsız)."""
    import api.services.review_citation_service as rcs

    async def _boom(query: str, *, limit: int = 5, settings: Any = None) -> Any:
        raise rcs.OpenAlexError("openalex search failed: timeout")

    monkeypatch.setattr(rcs, "search_works_raw", _boom)

    ref = ParsedReference(index=1, raw="y", title="No DOI Paper", year=2021, doi=None)
    out = await rcs.resolve_reference(ref)
    assert out.status == "not_found_in_index"
    assert out.resolution_degraded is True


async def test_genuine_not_found_is_not_marked_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Karşıt kanıt: GERÇEK eşleşme-yokluğu (404) degraded İŞARETLENMEZ — sadece
    provider hatası işaretlenir, ikisi karıştırılmamalı."""
    transport = _RouteTransport([])  # her şey 404
    _inject_transport(transport, monkeypatch)

    from api.services.review_citation_service import resolve_reference

    ref = ParsedReference(
        index=4, raw="X", title="Some Title", year=2000, doi="10.0/missing"
    )
    out = await resolve_reference(ref)
    assert out.status == "not_found_in_index"
    assert out.resolution_degraded is False


async def test_resolve_all_counts_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_all → provider_errors sayacı doğru toplanır (not_found_in_index
    sayacının İÇİNDE saklı kalan alt-küme, review_service.py bunu görünür
    degraded_features flag'ine çevirir)."""
    import api.services.review_citation_service as rcs

    async def _boom(doi: str, *, settings: Any = None) -> Any:
        raise rcs.OpenAlexError("fail")

    async def _s2_empty(query: str, *, limit: int = 5, settings: Any = None) -> list[Any]:
        return []

    monkeypatch.setattr(rcs, "fetch_work_by_doi", _boom)
    # 2026-08-23: not_found_in_index artık S2 fallback'ini TETİKLER (bkz.
    # resolve_all) — bu test dosyasının kuralı "gerçek ağ çağrısı YOK" (L9),
    # S2'yi de mock'lamak gerekiyor (boş sonuç = OpenAlex-hatası SONRASI S2 de
    # bulamadı, sayaçlar değişmez).
    monkeypatch.setattr(rcs, "search_semantic_scholar", _s2_empty)

    refs = [
        ParsedReference(index=0, raw="a", title="T", year=2020, doi="10.1/e1"),
        ParsedReference(index=1, raw="b", title="T", year=2020, doi="10.1/e2"),
    ]
    out_refs, summary = await rcs.resolve_all(refs)
    assert summary.provider_errors == 2
    assert summary.not_found_in_index == 2
    assert all(r.resolution_degraded for r in out_refs)


async def test_resolve_all_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_all → doğru özet sayaçları."""
    resolved_work = _work(wid="W1", title="Good Paper", year=2019)
    transport = _RouteTransport(
        [(lambda r: "/works/doi:10.1/ok" in str(r.url), 200, resolved_work)]
    )
    _inject_transport(transport, monkeypatch)

    from api.services.review_citation_service import resolve_all

    refs = [
        ParsedReference(index=0, raw="a", title="Good Paper", year=2019, doi="10.1/ok"),
        ParsedReference(index=1, raw="b", title="Good Paper", year=2019, doi="10.1/ok"),
    ]
    out_refs, summary = await resolve_all(refs)
    assert summary.total == 2
    assert summary.resolved == 2
    assert len(out_refs) == 2


# --- S3 atıf-bağlam ---------------------------------------------------------


async def test_context_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    """Özet iddiayı destekliyor → supported."""
    # abstract_inverted: "transformers outperform rnns on translation"
    abstract = {
        "transformers": [0],
        "outperform": [1],
        "rnns": [2],
        "on": [3],
        "translation": [4],
        "significantly": [5],
        "across": [6],
        "benchmarks": [7],
        "and": [8],
        "datasets": [9],
        "in": [10],
        "experiments": [11],
    }
    work = _work(wid="W42", title="T", abstract_inverted=abstract)
    transport = _RouteTransport([(lambda r: "/works/W42" in str(r.url), 200, work)])
    _inject_transport(transport, monkeypatch)

    # LLM call mock → supported
    import api.services.review_citation_service as rcs

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        schema = kw["structured_output_schema"]
        return type(
            "R",
            (),
            {"parsed_output": schema(support="supported", evidence="özet doğruluyor")},
        )()

    monkeypatch.setattr(rcs, "call", _fake_call)

    ref = ParsedReference(
        index=0, raw="x", title="T", year=2017, doi=None, status="resolved",
        openalex_id="W42",
    )
    in_text = [
        InTextCitation(
            marker="[0]",
            sentence="Transformers outperform RNNs on translation.",
            ref_index=0,
        )
    ]
    findings = await rcs.check_context(in_text, [ref])
    assert len(findings) == 1
    assert findings[0].support == "supported"
    assert findings[0].cited_abstract_excerpt is not None
    # support_level KANITI: map_support_level check_context içinden ÇAĞRILIYOR;
    # resolved + özet var + çelişki yok → abstract_only (full_text DEĞİL — spec).
    assert findings[0].support_level == "abstract_only"


async def test_context_no_abstract_is_unverifiable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HK-4 KANIT: kaynağın özeti yok → unverifiable_from_abstract (suçlama DEĞİL)."""
    work = _work(wid="W42", title="T", abstract_inverted=None)
    transport = _RouteTransport([(lambda r: "/works/W42" in str(r.url), 200, work)])
    _inject_transport(transport, monkeypatch)

    import api.services.review_citation_service as rcs

    async def _should_not_call(*a: Any, **k: Any) -> Any:
        raise AssertionError("Özet yokken LLM çağrılmamalı")

    monkeypatch.setattr(rcs, "call", _should_not_call)

    ref = ParsedReference(
        index=0, raw="x", title="T", year=2017, status="resolved", openalex_id="W42"
    )
    in_text = [
        InTextCitation(marker="[0]", sentence="Bold claim here.", ref_index=0)
    ]
    findings = await rcs.check_context(in_text, [ref])
    assert len(findings) == 1
    assert findings[0].support == "unverifiable_from_abstract"
    # resolved ama özet YOK → metadata_only (çözüldü ama derinlik yalnız künye).
    assert findings[0].support_level == "metadata_only"


async def test_context_not_found_ref_is_unresolved_support_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """KANIT (support_level canlı): çözülemeyen kaynağa atıf → unresolved.

    check_context çözülemeyen ref için özet çekmez (suçlama üretmemek için) →
    bağlam 'unverifiable_from_abstract' kalır; map_support_level citation_status'a
    bakar ve not_found_in_index → unresolved verir.
    """
    # Ağ hiç çağrılmamalı (openalex_id yok); LLM de çağrılmamalı (özet yok).
    transport = _RouteTransport([])
    _inject_transport(transport, monkeypatch)

    import api.services.review_citation_service as rcs

    async def _should_not_call(*a: Any, **k: Any) -> Any:
        raise AssertionError("Çözülemeyen kaynak için LLM çağrılmamalı")

    monkeypatch.setattr(rcs, "call", _should_not_call)

    ref = ParsedReference(
        index=0, raw="x", title="T", status="not_found_in_index", openalex_id=None
    )
    in_text = [InTextCitation(marker="[0]", sentence="Bold claim.", ref_index=0)]
    findings = await rcs.check_context(in_text, [ref])
    assert len(findings) == 1
    assert findings[0].support_level == "unresolved"


async def test_context_contradicted_is_contradictory_support_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """KANIT (support_level canlı): bağlam ÇELİŞİYORSA → contradictory.

    Kaynak resolved + özeti var ama LLM 'contradicted' derse, çözüm-derinliğinden
    bağımsız olarak çelişki kazanır (map_support_level öncelik kuralı).
    """
    abstract = {
        "this": [0], "abstract": [1], "directly": [2], "contradicts": [3],
        "the": [4], "claim": [5], "with": [6], "opposite": [7],
        "findings": [8], "reported": [9], "across": [10], "samples": [11],
    }
    work = _work(wid="W42", title="T", abstract_inverted=abstract)
    transport = _RouteTransport([(lambda r: "/works/W42" in str(r.url), 200, work)])
    _inject_transport(transport, monkeypatch)

    import api.services.review_citation_service as rcs

    async def _fake_call(prompt: str, **kw: Any) -> Any:
        schema = kw["structured_output_schema"]
        return type(
            "R",
            (),
            {"parsed_output": schema(support="contradicted", evidence="özet çelişiyor")},
        )()

    monkeypatch.setattr(rcs, "call", _fake_call)

    ref = ParsedReference(
        index=0, raw="x", title="T", year=2017, status="resolved", openalex_id="W42"
    )
    in_text = [
        InTextCitation(marker="[0]", sentence="The claim holds universally.", ref_index=0)
    ]
    findings = await rcs.check_context(in_text, [ref])
    assert len(findings) == 1
    assert findings[0].support == "contradicted"
    assert findings[0].support_level == "contradictory"


# --- S3 kapsama -------------------------------------------------------------


async def test_coverage_gap_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Yüksek-atıflı seminal eser kaynakçada yok → CoverageGap döner."""
    seminal = _work(wid="W999", title="Seminal Foundational Work", year=2012, cited_by=50000)
    transport = _RouteTransport(
        [
            (
                lambda r: r.url.path == "/works" and "search" in dict(r.url.params),
                200,
                {"results": [seminal]},
            )
        ]
    )
    _inject_transport(transport, monkeypatch)

    from api.services.review_citation_service import find_coverage_gaps

    meta = ManuscriptMeta(title="Deep Learning For Vision")
    refs = [
        ParsedReference(index=0, raw="x", title="Some Other Paper", openalex_id="W1")
    ]
    gaps = await find_coverage_gaps(meta, refs)
    assert len(gaps) == 1
    assert gaps[0].openalex_id == "W999"
    assert gaps[0].cited_by_count == 50000


async def test_coverage_no_topic_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Honest: konu yoksa boş liste (uydurma yok)."""
    from api.services.review_citation_service import find_coverage_gaps

    meta = ManuscriptMeta(title=None, abstract=None)
    gaps = await find_coverage_gaps(meta, [])
    assert gaps == []


# --- Semantic Scholar fallback (2026-08-23) ---------------------------------
# Kullanıcı onaylı plan: OpenAlex not_found_in_index derse S2 dene, OpenAlex
# akışına dokunma, S2 asla fabricated için kullanılmaz, S2 arızası SESSİZCE
# (ref not_found_in_index'te kalır) yutulur ama loglanır. Ağ MOCK'lanır
# (search_semantic_scholar monkeypatch — gerçek S2 çağrısı YOK, dosya kuralı L9).


def _s2_match(
    *, title: str, year: int, authors: list[str], doi: str | None = None
) -> Any:
    from engine.providers.semantic_scholar import SemanticScholarMatch

    return SemanticScholarMatch(
        title=title, year=year, authors=authors, doi=doi, paper_id="s2-1"
    )


async def _not_found_via_openalex_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yardımcı: OpenAlex'i hatalı yap → resolve_all'un her referansı S2'ye
    düşürmesini garanti eder (title+year varsa)."""
    import api.services.review_citation_service as rcs

    async def _boom(doi: str, *, settings: Any = None) -> Any:
        raise rcs.OpenAlexError("fail")

    monkeypatch.setattr(rcs, "fetch_work_by_doi", _boom)


async def test_semantic_scholar_upgrades_not_found_to_resolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAlex bulamadı ama S2 güçlü bir başlık+yıl+yazar eşleşmesi buldu →
    resolved'a yükseltilir, evidence provenance'ı açıkça belirtir, sayaç artar."""
    import api.services.review_citation_service as rcs

    await _not_found_via_openalex_error(monkeypatch)

    async def _s2_found(query: str, *, limit: int = 5, settings: Any = None) -> list[Any]:
        return [
            _s2_match(
                title="Attention Is All You Need",
                year=2017,
                authors=["Ashish Vaswani", "Noam Shazeer"],
                doi="10.5555/example",
            )
        ]

    monkeypatch.setattr(rcs, "search_semantic_scholar", _s2_found)

    refs = [
        ParsedReference(
            index=0,
            raw="x",
            title="Attention Is All You Need",
            authors=["Vaswani, A."],
            year=2017,
            doi="10.1/missing",
        )
    ]
    out_refs, summary = await rcs.resolve_all(refs)
    assert out_refs[0].status == "resolved"
    assert "Semantic Scholar" in (out_refs[0].evidence or "")
    assert summary.resolved == 1
    assert summary.not_found_in_index == 0
    assert summary.semantic_scholar_recovered == 1


async def test_semantic_scholar_no_match_stays_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S2 de bulamazsa (ya da zayıf eşleşme) → not_found_in_index'te KALIR,
    daha kötü olmaz (best-effort, regresyon yok)."""
    import api.services.review_citation_service as rcs

    await _not_found_via_openalex_error(monkeypatch)

    async def _s2_empty(query: str, *, limit: int = 5, settings: Any = None) -> list[Any]:
        return []

    monkeypatch.setattr(rcs, "search_semantic_scholar", _s2_empty)

    refs = [
        ParsedReference(index=0, raw="x", title="Some Obscure Paper", year=2020, doi="10.1/x")
    ]
    out_refs, summary = await rcs.resolve_all(refs)
    assert out_refs[0].status == "not_found_in_index"
    assert summary.not_found_in_index == 1
    assert summary.semantic_scholar_recovered == 0


async def test_semantic_scholar_error_does_not_crash_stays_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S2 arızası (ağ/429/timeout) hiçbir istisna sızdırmaz — referans OLDUĞU
    GİBİ not_found_in_index kalır (sessiz-güvenli-degrade, çağırana crash yok)."""
    import api.services.review_citation_service as rcs
    from engine.providers.semantic_scholar import SemanticScholarError

    await _not_found_via_openalex_error(monkeypatch)

    async def _s2_boom(query: str, *, limit: int = 5, settings: Any = None) -> list[Any]:
        raise SemanticScholarError("rate_limited (429)")

    monkeypatch.setattr(rcs, "search_semantic_scholar", _s2_boom)

    refs = [
        ParsedReference(index=0, raw="x", title="Some Paper", year=2020, doi="10.1/x")
    ]
    out_refs, summary = await rcs.resolve_all(refs)  # crash ATMAMALI
    assert out_refs[0].status == "not_found_in_index"
    assert summary.semantic_scholar_recovered == 0


async def test_semantic_scholar_author_mismatch_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Başlık benzese bile yazar soyadı hiç örtüşmüyorsa REDDEDİLİR — 2026-08-05
    guardian bulgusunun (eşiksiz soyad-örtüşmesi yanlış-eşleşme riski) AYNISI
    S2 için de geçerli, düzeltilmiş halinin regresyonu test edilir."""
    import api.services.review_citation_service as rcs

    await _not_found_via_openalex_error(monkeypatch)

    async def _s2_wrong_author(
        query: str, *, limit: int = 5, settings: Any = None
    ) -> list[Any]:
        return [
            _s2_match(
                title="Attention Is All You Need",
                year=2017,
                authors=["Someone Completely Different"],
            )
        ]

    monkeypatch.setattr(rcs, "search_semantic_scholar", _s2_wrong_author)

    refs = [
        ParsedReference(
            index=0,
            raw="x",
            title="Attention Is All You Need",
            authors=["Vaswani, A."],
            year=2017,
            doi="10.1/x",
        )
    ]
    out_refs, _summary = await rcs.resolve_all(refs)
    assert out_refs[0].status == "not_found_in_index"


async def test_semantic_scholar_never_touches_fabricated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_all'da fabricated sonucu S2'ye HİÇ gitmez (kod yolu:
    `if result.status != "not_found_in_index": return result`) — S2
    çağrılırsa test patlar (mock hiç çağrılmamalı)."""
    import api.services.review_citation_service as rcs

    # Bilinen-doğru fabricated fixture'ı (test_common_surname_coincidence_
    # stays_fabricated ile AYNI desen — kanıtlanmış davranış, tahmin değil):
    # alakasız başlık/yıl/yazar + DOI başka bir esere çözülüyor.
    other = _work(
        wid="W777",
        title="Photosynthesis In Deep Sea Algae",
        year=1995,
        authors=["Sarah Kim", "John Roberts", "Maria Fernandez", "Wei Zhang", "Anna Novak"],
    )
    transport = _RouteTransport(
        [(lambda r: "/works/doi:" in str(r.url), 200, other)]
    )
    _inject_transport(transport, monkeypatch)

    async def _s2_should_not_be_called(
        query: str, *, limit: int = 5, settings: Any = None
    ) -> list[Any]:
        raise AssertionError("S2 fabricated sonucu için ÇAĞRILMAMALI")

    monkeypatch.setattr(rcs, "search_semantic_scholar", _s2_should_not_be_called)

    refs = [
        ParsedReference(
            index=5,
            raw="Kim, D., Patel, R., Nguyen, T., Silva, F., & Ivanov, S. 2021",
            title="A Comprehensive Review Of Quantum Gravity",
            authors=["Kim, D.", "Patel, R.", "Nguyen, T.", "Silva, F.", "Ivanov, S."],
            year=2021,
            doi="10.1234/fake.doi",
        )
    ]
    out_refs, summary = await rcs.resolve_all(refs)
    assert out_refs[0].status == "fabricated", out_refs[0].evidence
    assert summary.fabricated == 1
    assert summary.semantic_scholar_recovered == 0
