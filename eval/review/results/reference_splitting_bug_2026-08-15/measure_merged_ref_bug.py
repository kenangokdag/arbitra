"""2026-08-15: `_BARE_YEAR_END_RE` boşluğunun (birden fazla referansı tek
girdiye birleştirmesi, `engine/ingestion/common.py:81-83`) 61-goldset'teki
gerçek yaygınlığını ölçer. TAMAMEN OFFLINE — LLM çağrısı yok, ağ çağrısı yok,
sadece `engine.ingestion.pdf_parser.parse_pdf()` çalışır (GROBID bu ortamda
devre dışı, tüm referanslar heuristic yoldan geçiyor — `grobid_client.is_enabled()`
ile doğrulandı).

Kök neden (PDF_PIPELINE_CALISMA_GUNLUGU.md §65'te tam anlatılıyor): ICLR-tarzı
kaynakçalarda yıl+nokta'dan hemen sonra bir "doi: ..." / "URL ..." satırı
geliyor (örn. "...2016. doi: 10.18653/v1/P16-1004. URL ..."). `_BARE_YEAR_END_RE`
girdi sınırını "YIL. [BÜYÜK HARF]" kalıbıyla arıyor — "doi" küçük harfle
başladığı için eşleşme kaçıyor, 2+ gerçek referans TEK "raw" girdide birleşiyor.
Sonra `extract_authors_year_title()`'ın Vancouver-stili `.split(".")` ayrıştırıcısı
URL/kısaltma noktalarını da alan-sınırı sanıp YANLIŞ bir "başlık" çıkarıyor
(örn. "org/pdf/ 1409", "ISBN 978-1-4673-8947-1") — motor bu SAHTE başlığı
OpenAlex'teki DOĞRU DOI karşılığıyla kıyaslayıp "uydurma" diyor (YANLIŞ-POZİTİF).

İmza: bir referans girdisinin 'raw' metninde 2+ bağımsız 'YIL.' deseni VARSA,
bu girdi muhtemelen birden fazla gerçek referansın birleşmesidir (proxy —
mükemmel değil, ama her örnek elle kontrol edilebilir, `merged_candidates`
alanında `raw_preview` taşınıyor).

ÇALIŞTIRMA: `goldset61_local_filenames.json`'daki dosya adları
`C:\\Users\\USER\\Desktop\\goldset_pdfs\\` ve `goldset_pdfs_v2\\`'de aranır
(ham PDF'ler telif nedeniyle repoya commit EDİLMEDİ — goldset.json'ın
kendisi gibi, bu proje genelinde tutarlı bir konvansiyon). Bu dosyalara
sahip olmayan biri script'i ÇALIŞTIRAMAZ ama MANTIĞI okuyup denetleyebilir,
ve `merged_ref_bug_measurement.json`'daki (bu klasörde, commit edilmiş)
SONUÇLARI inceleyebilir.
"""
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from engine.ingestion.pdf_parser import parse_pdf  # noqa: E402

_YEAR_DOT_RE = re.compile(r"\b(19\d{2}|20\d{2})[a-z]?\.")
_SEARCH_DIRS = [
    Path(r"C:\Users\USER\Desktop\goldset_pdfs"),
    Path(r"C:\Users\USER\Desktop\goldset_pdfs_v2"),
]
_HERE = Path(__file__).resolve().parent

filenames = json.loads((_HERE / "goldset61_local_filenames.json").read_text(encoding="utf-8"))

results = []
for paper_id, fn in filenames.items():
    path = next((d / fn for d in _SEARCH_DIRS if (d / fn).exists()), None)
    if path is None:
        results.append({"paper_id": paper_id, "error": f"local PDF not found: {fn}"})
        continue
    data = path.read_bytes()
    try:
        ms = parse_pdf(data, filename=fn)
    except Exception as exc:
        results.append({"paper_id": paper_id, "error": str(exc)})
        continue
    n_refs = len(ms.references)
    merged_candidates = []
    for r in ms.references:
        raw = r.raw or ""
        year_hits = _YEAR_DOT_RE.findall(raw)
        # 2+ bağımsız yıl-nokta deseni = muhtemelen 2+ referans birleşik.
        if len(year_hits) >= 2:
            merged_candidates.append({
                "index": r.index,
                "n_year_dot_hits": len(year_hits),
                "extracted_title": r.title,
                "raw_len": len(raw),
                "raw_preview": raw[:150],
            })
    results.append({
        "paper_id": paper_id,
        "n_refs": n_refs,
        "n_merged_candidates": len(merged_candidates),
        "merged_candidates": merged_candidates,
    })

n_papers_affected = sum(1 for r in results if r.get("n_merged_candidates", 0) > 0)
n_total_merged = sum(r.get("n_merged_candidates", 0) for r in results)
n_errors = sum(1 for r in results if "error" in r)

print(f"=== {len(results)} makale tarandı (offline, LLM'siz) ===")
print(f"Hata (parse başarısız / PDF bulunamadı): {n_errors}")
print(f"Etkilenen makale sayısı (>=1 birleşik-görünümlü girdi): {n_papers_affected} / {len(results) - n_errors}")
print(f"Toplam birleşik-görünümlü girdi sayısı: {n_total_merged}")
print()
print("=== Detay (etkilenen makaleler) ===")
for r in sorted(results, key=lambda x: -x.get("n_merged_candidates", 0)):
    if r.get("n_merged_candidates", 0) > 0:
        print(f"{r['paper_id']}: {r['n_merged_candidates']}/{r['n_refs']} referans etkilenmiş görünüyor")

out_path = _HERE / "merged_ref_bug_measurement.json"
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print()
print("saved:", out_path)
