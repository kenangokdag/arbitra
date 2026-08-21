"""Retraction Watch + OpenAlex atif-grafigi ile gercek moat-n adaylari uretir.
PDF_PIPELINE_CALISMA_GUNLUGU.md SS49'da dogrulanan yontem.

Adim 1: Retraction Watch CSV'den CS/Data-Science + gercek-DOI'li geri cekilmis
        makaleleri filtrele.
Adim 2: Her biri icin OpenAlex'te retraction'i dogrula + atif-yapan (citing)
        makaleleri bul.
Adim 3: Acik-erisimli + geri cekilmemis citing makaleleri topla.
Adim 4: PDF'leri indir, gercekten gecerli PDF mi dogrula.
Adim 5: GoldEntry formatinda (source="manual", human_verdict=OMER_DOLDURACAK,
        notes'ta gercek geri-cekilme kaniti) JSON uret.
"""

import csv
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

# Windows konsolun cp1254 gibi dar bir kodlamayla bogulmasini onle (baslik/URL
# metinlerinde rastgele unicode karakterler cikabiliyor) - print'i ASCII-guvenli yap.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def safe_print(*args, **kwargs) -> None:
    text = " ".join(str(a) for a in args)
    print(text.encode("ascii", "replace").decode("ascii"), **kwargs)

MAILTO = "arbitra-research@example.com"
CSV_PATH = Path(r"C:\Users\USER\Desktop\goldset_candidates\retraction_watch_sample.csv")
PDF_OUT_DIR = Path(r"C:\Users\USER\Desktop\goldset_pdfs_v3_retraction")
PDF_OUT_DIR.mkdir(parents=True, exist_ok=True)
ENTRIES_OUT = Path(r"C:\Users\USER\Desktop\arbitra-main\eval\review\retraction_moat_candidates_2026-08-13.json")

TARGET_N = 30


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "arbitra-research/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def load_seed_dois() -> list[tuple[str, str, str]]:
    """(title, doi, reason) - CS/Data Science + real DOI olan geri cekilmis makaleler."""
    out = []
    with open(CSV_PATH, encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            subj = r.get("Subject") or ""
            doi = (r.get("OriginalPaperDOI") or "").strip()
            reason = r.get("Reason") or ""
            if ("Computer Science" in subj or "Data Science" in subj) and doi:
                out.append((r.get("Title", ""), doi, reason))
    return out


def find_citing_candidates(seed_title: str, seed_doi: str, seed_reason: str) -> list[dict]:
    """Bu geri cekilmis DOI'ye atif yapan, acik-erisimli, geri cekilmemis makaleler."""
    try:
        w = _get_json(f"https://api.openalex.org/works/https://doi.org/{seed_doi}?mailto={MAILTO}")
    except Exception:
        return []
    if not w.get("is_retracted"):
        return []  # OpenAlex'te retraction dogrulanmadi - guvenli tarafta kal

    oid = w["id"].split("/")[-1]
    seed_display = w.get("display_name", seed_title)

    try:
        citing = _get_json(
            f"https://api.openalex.org/works?filter=cites:{oid}&per-page=25&mailto={MAILTO}"
        )
    except Exception:
        return []

    out = []
    for c in citing.get("results", []):
        if c.get("is_retracted"):
            continue
        oa = c.get("open_access", {})
        if not oa.get("is_oa") or not oa.get("oa_url"):
            continue
        out.append(
            {
                "citing_title": c.get("display_name"),
                "citing_doi": c.get("doi"),
                "citing_openalex_id": c.get("id"),
                "citing_year": c.get("publication_year"),
                "oa_url": oa.get("oa_url"),
                "seed_retracted_title": seed_display,
                "seed_retracted_doi": seed_doi,
                "seed_retraction_reason": seed_reason,
            }
        )
    return out


def download_pdf(url: str, out_path: Path) -> bool:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if not data.startswith(b"%PDF"):
            return False
        out_path.write_bytes(data)
        return True
    except Exception as exc:
        safe_print(f"    indirme hatasi: {exc}")
        return False


def main() -> None:
    seeds = load_seed_dois()
    safe_print(f"Toplam tohum aday (CS/DataScience + gercek DOI): {len(seeds)}")

    import random

    random.seed(7)
    random.shuffle(seeds)

    collected: list[dict] = []
    seen_citing_dois: set[str] = set()
    seeds_checked = 0

    for title, doi, reason in seeds:
        if len(collected) >= TARGET_N * 5:  # buyuk bir tampon havuz topla (indirme basari orani ~%40)
            break
        seeds_checked += 1
        cands = find_citing_candidates(title, doi, reason)
        for c in cands:
            cd = c.get("citing_doi")
            if cd and cd not in seen_citing_dois:
                seen_citing_dois.add(cd)
                collected.append(c)
        time.sleep(0.15)
        if seeds_checked % 20 == 0:
            safe_print(f"  {seeds_checked} tohum tarandi, {len(collected)} aday havuzda...")

    safe_print(f"\n{seeds_checked} tohum tarandi, toplam {len(collected)} benzersiz aday makale bulundu.")

    # PDF indir, TARGET_N basarili olana kadar dene
    entries = []
    for i, c in enumerate(collected):
        if len(entries) >= TARGET_N:
            break
        safe_id = f"retractionwatch_{i:03d}"
        pdf_path = PDF_OUT_DIR / f"{safe_id}.pdf"
        safe_print(f"[{len(entries)+1}/{TARGET_N}] indiriliyor: {c['citing_title'][:60]!r} <- {c['oa_url']}")
        ok = download_pdf(c["oa_url"], pdf_path)
        if not ok:
            safe_print("    BASARISIZ, atlaniyor")
            continue
        safe_print(f"    OK ({pdf_path.stat().st_size} bytes)")

        entries.append(
            {
                "paper_id": f"retractionwatch:{safe_id}",
                "source": "manual",
                "title": c["citing_title"] or "(başlık yok)",
                "field": "ml",
                "pdf_url": c["oa_url"],
                "human_verdict": "OMER_DOLDURACAK",
                "human_scores": {},
                "human_review_excerpt": "",
                "notes": (
                    "GERÇEK GERİ ÇEKİLME KANITI (Retraction Watch + OpenAlex atıf-grafiği, "
                    "2026-08-13 doğrulandı — PDF_PIPELINE_CALISMA_GUNLUGU.md §49): bu makale "
                    f"{c['seed_retracted_title']!r} (DOI: {c['seed_retracted_doi']}) başlıklı, "
                    "GERÇEKTEN geri çekilmiş bir kaynağa atıf yapıyor. Geri çekilme sebebi: "
                    f"{c['seed_retraction_reason']}. Bu girdi moat_grounding_accuracy'nin ÖLÇEMEDİĞİ "
                    "yanlış-negatif (recall) testini amaçlıyor — motorun bu bilinen geri çekilmiş "
                    "atfı GERÇEKTEN yakalayıp yakalamadığı elle/ayrı bir script ile doğrulanmalı, "
                    "henüz otomatik bir metriğe bağlanmadı. human_verdict/human_scores GERÇEK "
                    "insan hakem verisi DEĞİL (bu makalelerin editoryal kararı bilinmiyor), "
                    "bilinçli olarak OMER_DOLDURACAK/boş bırakıldı."
                ),
                "_known_retracted_reference_doi": c["seed_retracted_doi"],
                "_local_pdf_path": str(pdf_path),
            }
        )
        time.sleep(0.2)

    ENTRIES_OUT.parent.mkdir(parents=True, exist_ok=True)
    ENTRIES_OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    safe_print(f"\n{len(entries)} GoldEntry-benzeri kayıt üretildi (indirilen PDF'lerle): {ENTRIES_OUT}")
    safe_print(f"PDF'ler: {PDF_OUT_DIR}")


if __name__ == "__main__":
    main()
