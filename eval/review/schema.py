"""F14 EVAL — ALTIN-SET şeması (Pydantic, extra=forbid).

Bir altın-set girdisi = bir makale + İNSAN hakem(ler)inin gerçek değerlendirmesi
(verdict + boyut skorları). Motor bu makaleyi değerlendirir; metrics.py motor
çıktısını buradaki insan değerlendirmesiyle kıyaslar (R-3 uyum metriği).

HALÜSİNASYON YASAĞI (papermind §2.3): insan skoru GERÇEK değilse asla uydurulmaz
— `OMER_DOLDURACAK` sentinel'i ile işaretlenir. Metrik motoru bu sentinel'li
alanları KAPSAM DIŞI bırakır (kıyaslama yapmaz), uydurma sayı üretmez.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# review.py'deki kanonik enum/literal'leri TEK doğruluk olarak yeniden kullan.
from api.models.review import DimensionKey, Verdict

# --- sentinel: "insan henüz doldurmadı" -------------------------------------

# İnsan verdict/skoru henüz GERÇEK veriyle dolmadıysa bu işaret konur.
# Metrik motoru bu işaretli girdileri/alanları kıyaslamadan ÇIKARIR.
OMER_PLACEHOLDER = "OMER_DOLDURACAK"

GoldSource = Literal["openreview", "peerj", "peerread", "manual"]
"""peerread: allenai/PeerRead (GitHub) - ICLR/NeurIPS/ACL/CoNLL arşiv
snapshot'ı, canlı OpenReview kazımasından farklı — 2026-08-06, goldset
50-makale genişlemesi."""
"""Altın-set kaynağı. openreview/peerj = gerçek açık-hakem; manual = Omer'in
pilot alandan (nicel sosyal bilim) elle eklediği hakem-raporlu makale."""


class GoldEntry(BaseModel):
    """Tek altın-set girdisi: makale + insan hakem değerlendirmesi.

    human_verdict: gerçek değilse OMER_PLACEHOLDER.
    human_scores: SADECE gerçekten ölçülmüş boyutlar doldurulur; ölçülmeyen
        boyut anahtarı sözlüğe KONMAZ (uydurma yok). Boş dict = tüm boyutlar
        Omer'i bekliyor.
    """

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    source: GoldSource
    title: str
    field: str  # pilot disiplin etiketi, örn. "quant_social_science", "ml"
    pdf_url: str | None = None
    # GERÇEK insan verdict'i ya da OMER_PLACEHOLDER.
    human_verdict: Verdict | Literal["OMER_DOLDURACAK"]
    # boyut → 1-10 insan skoru. Anahtar yoksa = o boyut ölçülmedi (Omer doldurur).
    human_scores: dict[DimensionKey, float] = Field(default_factory=dict)
    human_review_excerpt: str
    notes: str = ""


class GoldMeta(BaseModel):
    """Altın-set künyesi — provenance + dürüstlük damgası."""

    model_config = ConfigDict(extra="forbid")

    version: str
    created_at: str  # ISO tarih
    pilot_field: str  # ana pilot disiplin (master §pilot: nicel sosyal bilim)
    description: str
    real_entry_count: int = 0  # human_verdict GERÇEK olan girdi sayısı
    placeholder_entry_count: int = 0  # OMER_DOLDURACAK işaretli girdi sayısı
    stanford_reference: str = (
        "Stanford AI reviewer ICLR 2025'e karşı Spearman 0.42 "
        "(insan-insan tavanı ~0.41)"
    )


class GoldSet(BaseModel):
    """Altın-set = girdi listesi + künye."""

    model_config = ConfigDict(extra="forbid")

    meta: GoldMeta
    entries: list[GoldEntry] = Field(default_factory=list)

    def real_entries(self) -> list[GoldEntry]:
        """human_verdict'i GERÇEK olan (placeholder OLMAYAN) girdiler."""
        return [e for e in self.entries if e.human_verdict != OMER_PLACEHOLDER]


__all__ = [
    "OMER_PLACEHOLDER",
    "GoldEntry",
    "GoldMeta",
    "GoldSet",
    "GoldSource",
]
