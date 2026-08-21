"""engine/academic/evidence_context.py — saf formatter testleri.

2026-08-08: `serialize_evidence_pack()` `api/services/review_orchestration.py`'den
buraya taşındı (§31/§32) — bu testler taşımanın davranışı KORUDUĞUNU kanıtlar.
LLM/network yok, tam deterministik.
"""

from __future__ import annotations

import pytest

from api.models.review import (
    CitationContextFinding,
    CitationIntegritySummary,
    CoverageGap,
    EvidencePack,
    ParsedReference,
    StatFinding,
)
from engine.academic.evidence_context import serialize_evidence_pack

pytestmark = pytest.mark.unit


def test_empty_pack_is_honest_not_fabricated() -> None:
    """Boş EvidencePack → her bölüm için dürüst 'yok/boş' mesajı, UYDURMA yok."""
    text = serialize_evidence_pack(EvidencePack())
    assert "toplam=0, çözülen=0, bulunamayan=0, uydurma=0, geri_çekilmiş=0" in text
    assert "Referans listesi boş." in text
    assert "Atıf-bağlam bulgusu yok." in text
    assert "Tespit edilen kapsama boşluğu yok." in text
    assert "İstatistik bulgusu yok." in text


def test_populated_pack_surfaces_all_five_sections() -> None:
    pack = EvidencePack(
        citation_integrity=CitationIntegritySummary(
            total=5, resolved=3, not_found_in_index=1, fabricated=1, retracted=0
        ),
        references=[
            ParsedReference(
                index=1,
                raw="Smith 2020",
                title="Uydurma Referans XYZ",
                status="fabricated",
                evidence="DOI başka esere ait",
            ),
            ParsedReference(
                index=2,
                raw="Jones 2019",
                title="Retracted Study",
                status="retracted",
                is_retracted=True,
            ),
        ],
        context_findings=[
            CitationContextFinding(
                ref_index=1,
                claim="X, Y'yi kanıtlar",
                support="contradicted",
                evidence="Özet X'in tersini söylüyor",
            )
        ],
        coverage_gaps=[
            CoverageGap(
                openalex_id="W123",
                title="Seminal Work",
                year=2015,
                cited_by_count=500,
                reason="Doğrudan ilgili ama hiç atıf yok",
            )
        ],
        stat_findings=[
            StatFinding(
                test_type="t-test",
                reported_p=0.04,
                computed_p=0.06,
                status="red",
                match_text="t(48)=2.01, p=.04",
            )
        ],
    )
    text = serialize_evidence_pack(pack)

    assert "toplam=5, çözülen=3, bulunamayan=1, uydurma=1, geri_çekilmiş=0" in text
    assert "Uydurma Referans XYZ" in text and "fabricated" in text
    assert "Retracted Study" in text and "GERİ-ÇEKİLMİŞ" in text
    assert "X, Y'yi kanıtlar" in text and "contradicted" in text
    assert "Seminal Work" in text and "atıf=500" in text
    assert "t(48)=2.01" in text


def test_first_line_is_kanit_paketi_header() -> None:
    """_build_prompt/dispatcher bu metni tek bir bağlam bloğu olarak gömüyor -
    ilk satır sabit bir başlık taşımalı (downstream'de tanınabilir olması için)."""
    text = serialize_evidence_pack(EvidencePack())
    assert text.startswith("KANIT PAKETİ (deterministik olgular")


def test_provider_errors_surfaced_with_explicit_caveat() -> None:
    """§41 devamı (guardian bulgusu): provider_errors>0 ise LLM'e AÇIKÇA
    uyarılmalı — 'bulunamayan' sayısının bir kısmı geçici sağlayıcı hatası,
    gerçek eşleşme-yokluğu kanıtı DEĞİL. Aksi halde SS38'in bulduğu desen
    (yüksek not_found_in_index tek başına major/critical tetikliyor) tekrar
    edebilir."""
    pack = EvidencePack(
        citation_integrity=CitationIntegritySummary(
            total=10, resolved=4, not_found_in_index=6, provider_errors=3
        )
    )
    text = serialize_evidence_pack(pack)
    assert "bulunamayan=6" in text
    assert "3" in text and "geçici sağlayıcı" in text
    assert "KANITI DEĞİL" in text


def test_no_provider_errors_no_caveat_line() -> None:
    """provider_errors=0 → uyarı satırı hiç eklenmemeli (yanlış-pozitif yok,
    gereksiz gürültü LLM'e gönderilmemeli)."""
    pack = EvidencePack(
        citation_integrity=CitationIntegritySummary(
            total=5, resolved=4, not_found_in_index=1, provider_errors=0
        )
    )
    text = serialize_evidence_pack(pack)
    assert "geçici sağlayıcı" not in text
