"""F14 EVAL — başlangıç ALTIN-SET üretici (OpenReview ICLR 2025 GERÇEK veri).

Ne yapar: OpenReview public API'sinden (api2) birkaç gerçek ICLR 2025 submission
çeker, insan hakem skorlarının/ kararının ORTALAMASINI alır, GoldEntry üretir.

DÜRÜSTLÜK (papermind §2.3):
  - human_verdict yalnız GERÇEK Decision'dan gelir (Accept→accept, Reject→reject).
    ICLR'de minor/major revision YOK → bu iki kademe gerçek değilse üretilmez.
  - human_scores yalnız ICLR'in GERÇEKTEN ölçtüğü boyutlardan map edilir:
      soundness(1-4)      → soundness
      presentation(1-4)   → clarity
      contribution(1-4)   → importance
    1-4 ölçeği 1-10'a LİNEER ölçeklenir: 10-skor = 1 + (raw-1) * 9/3.
    ICLR'in ölçmediği boyut (originality, claims_supported, community_value,
    contextualization, + 3 deterministik moat boyutu) human_scores'a KONMAZ
    (uydurma yasağı; Omer pilot alandan doldurur).
  - rating (1-10) ham olarak excerpt'e yazılır (insan genel skoru; ÖLÇEK
    boyut-eşlemesi belirsiz olduğu için bir DimensionKey'e map EDİLMEZ).

Bu script ağ ister. Çıktı: goldset.json. Ağ engelliyse goldset.json'daki
mevcut (şablon) içerik korunur — script onu EZMEZ, hata yükseltir.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from eval.review.schema import GoldEntry, GoldMeta, GoldSet

_API2 = "https://api2.openreview.net"
_VENUEID = "ICLR.cc/2025/Conference"
_OUT = Path(__file__).resolve().parent / "goldset.json"

# ICLR review boyutu (1-4) → bizim DimensionKey eşlemesi + ölçek dönüşümü.
# review.py DimensionScore 1-10 ister.
_ICLR_DIM_MAP = {
    "soundness": "soundness",
    "presentation": "clarity",
    "contribution": "importance",
}


def _rescale_1_4_to_1_10(raw: float) -> float:
    """1-4 → 1-10 lineer. raw=1→1.0, raw=4→10.0."""
    return round(1.0 + (raw - 1.0) * (9.0 / 3.0), 2)


def _get(url: str) -> dict[str, Any]:
    req = urllib.request.Request(  # noqa: S310 (sabit https OpenReview hostu)
        url, headers={"User-Agent": "papermind-eval/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (trusted host)
        data: dict[str, Any] = json.loads(resp.read())
        return data


def _decision_to_verdict(decision: str) -> str | None:
    """ICLR Decision → Verdict. Accept→accept, Reject→reject. Aksi → None
    (uydurma yapmayız; bilinmeyen karar Omer'e bırakılır)."""
    d = decision.lower()
    if "accept" in d:
        return "accept"
    if "reject" in d:
        return "reject"
    return None


def _content_val(content: dict[str, Any], key: str) -> Any:
    node = content.get(key)
    if isinstance(node, dict):
        return node.get("value")
    return node


def build(limit: int = 5) -> GoldSet:
    """ICLR 2025'ten `limit` submission çek → GoldSet (gerçek skor/karar)."""
    subs = _get(f"{_API2}/notes?content.venueid={_VENUEID}&limit={limit}")["notes"]
    entries: list[GoldEntry] = []

    for sub in subs:
        forum = sub["forum"]
        content = sub["content"]
        title = _content_val(content, "title") or "(başlıksız)"
        pdf_path = _content_val(content, "pdf")
        pdf_url = f"https://openreview.net{pdf_path}" if pdf_path else None

        forum_notes = _get(f"{_API2}/notes?forum={forum}")["notes"]

        ratings: list[float] = []
        dim_raw: dict[str, list[float]] = {k: [] for k in _ICLR_DIM_MAP}
        decision_text: str | None = None
        excerpt_bits: list[str] = []

        for note in forum_notes:
            last = [iv.split("/")[-1] for iv in note.get("invitations", [])]
            c = note["content"]
            if "Official_Review" in last:
                r = _content_val(c, "rating")
                if r is not None:
                    ratings.append(float(r))
                for iclr_key in _ICLR_DIM_MAP:
                    v = _content_val(c, iclr_key)
                    if v is not None:
                        dim_raw[iclr_key].append(float(v))
            if "Decision" in last:
                decision_text = _content_val(c, "decision")

        verdict = _decision_to_verdict(decision_text) if decision_text else None

        human_scores: dict[str, float] = {}
        for iclr_key, our_key in _ICLR_DIM_MAP.items():
            vals = dim_raw[iclr_key]
            if vals:
                human_scores[our_key] = _rescale_1_4_to_1_10(mean(vals))

        if ratings:
            excerpt_bits.append(
                f"ICLR ortalama rating (1-10): {mean(ratings):.2f} "
                f"({len(ratings)} hakem)"
            )
        if decision_text:
            excerpt_bits.append(f"Karar: {decision_text}")
        excerpt = " | ".join(excerpt_bits) or "Hakem verisi alınamadı."

        entries.append(
            GoldEntry(
                paper_id=f"openreview:{forum}",
                source="openreview",
                title=str(title),
                field="ml",
                pdf_url=pdf_url,
                human_verdict=verdict or "OMER_DOLDURACAK",  # type: ignore[arg-type]
                human_scores=human_scores,  # type: ignore[arg-type]
                human_review_excerpt=excerpt,
                notes=(
                    "OpenReview ICLR 2025 gerçek veri. human_scores: "
                    "soundness/clarity/importance ICLR soundness/presentation/"
                    "contribution(1-4)'ten 1-10'a ölçeklendi. Diğer boyutlar + "
                    "minor/major_revision kademesi ICLR'de ölçülmedi → "
                    "OMER nicel-sosyal-bilim pilotundan doldurur."
                ),
            )
        )

    real = [e for e in entries if e.human_verdict != "OMER_DOLDURACAK"]
    meta = GoldMeta(
        version="0.1.0-openreview-seed",
        created_at=datetime.now(UTC).date().isoformat(),
        pilot_field="quant_social_science",
        description=(
            "Başlangıç altın-set: OpenReview ICLR 2025 gerçek hakem verisi "
            "(ML alanı tohum). PİLOT (nicel sosyal bilim) makaleleri Omer "
            "PeerJ açık-hakem / elindeki hakem-raporlu örneklerden ekleyecek."
        ),
        real_entry_count=len(real),
        placeholder_entry_count=len(entries) - len(real),
    )
    return GoldSet(meta=meta, entries=entries)


def main() -> int:
    try:
        goldset = build(limit=5)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        # Ağ engelli → mevcut goldset.json'u EZME, dürüst hata yükselt.
        print(f"AĞ HATASI: OpenReview erişilemedi: {exc}", file=sys.stderr)
        print("goldset.json değiştirilmedi (mevcut içerik korundu).", file=sys.stderr)
        return 2
    _OUT.write_text(
        json.dumps(goldset.model_dump(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"goldset.json yazıldı: {len(goldset.entries)} girdi "
        f"({goldset.meta.real_entry_count} gerçek, "
        f"{goldset.meta.placeholder_entry_count} placeholder)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
