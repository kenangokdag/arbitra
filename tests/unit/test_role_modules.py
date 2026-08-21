"""api/services/role_modules/*.py — brief metinlerinde kritik talimatların
sessizce silinmediğini kanıtlayan sığ ama ucuz regresyon bekçileri.

Bunlar LLM davranışını test ETMEZ (deterministik değil, mock-LLM testleri
prompt içeriğini görmez — ROLE_MODULES sistem promptu llm_service.call()
içinde birleştirilir, tests/unit/test_academic_engines.py'nin monkeypatch'lediği
_engine_base.call bunu görmez). Sadece talimat metninin VAR olduğunu kanıtlar.
"""

from __future__ import annotations

import pytest

from api.services.role_modules.academic_dimension import ACADEMIC_DIMENSION_BRIEF

pytestmark = pytest.mark.unit


def test_academic_dimension_brief_differentiates_citation_status_severity() -> None:
    """2026-08-09 (bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md SS33): 'not_found_in_index'
    tek basina critical/major severity'yi hak ETMEMELI (HK-3: 'yok != uydurma'),
    'fabricated'/'retracted'/'contradicted' hak EDEBILIR - bu ayrimin metinden
    sessizce silinmedigini kanitlar."""
    brief = ACADEMIC_DIMENSION_BRIEF
    assert "uydurma" in brief.lower() and "critical/major" in brief
    assert "bulunamayan" in brief.lower()
    # not_found_in_index icin critical/major'i ACIKCA reddeden dil var mi.
    assert "HAK ETMEZ" in brief
    # fabricated/retracted/contradicted icin critical/major'i hak eder diyen dil var mi.
    assert "HAK EDER" in brief


def test_academic_dimension_brief_still_documents_evidence_packet_usage() -> None:
    """2026-08-08 fix'inin (SS31/SS32) kanit-kullanim talimati bu yeni severity
    ayriminda kaybolmadi."""
    assert "KANIT PAKETİ" in ACADEMIC_DIMENSION_BRIEF
    assert "literature_depth" in ACADEMIC_DIMENSION_BRIEF


def test_academic_dimension_brief_severity_scale_is_decision_anchored_not_adjectival() -> None:
    """2026-08-09 (bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md SS35): eski tanim
    'critical (olumcul eksik) - major (ciddi zayiflik)' gibi sifatlardan
    ibaretti, capasizdi (guardian SS31 bulgusu). Yeni tanim somut bir
    editor-karari testine (zorunlu revizyon sarti mi, opsiyonel not mu)
    baglaniyor - bu testin amaci bu capanin sessizce silinmemesini saglamak."""
    brief = ACADEMIC_DIMENSION_BRIEF
    assert "EDİTÖR-KARARI" in brief
    assert "zorunlu revizyon" in brief.lower()
    assert "EMİN DEĞİLSEN" in brief
    # eski, capasiz sifat-tanimi geri gelmemeli.
    assert "critical (boyut için ölümcül eksik)" not in brief


def test_academic_dimension_brief_has_anti_inflation_calibration_rule() -> None:
    """SS31'in sistem-genelinde bulgusu (61 makalenin %95'inde en az 1
    critical/major - ayirt edici degil) brief'e acikca yazilmali, yoksa
    fix'in GEREKCESI kaybolur ve biri gelecekte bu kurali 'gereksiz'
    sanip silebilir."""
    assert "%95" in ACADEMIC_DIMENSION_BRIEF
    assert "abart" in ACADEMIC_DIMENSION_BRIEF.lower()
