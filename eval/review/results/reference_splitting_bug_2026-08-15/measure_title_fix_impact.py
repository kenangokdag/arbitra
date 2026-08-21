"""Duzeltme oncesi/sonrasi title-cikarim degisikligini olcer. 61-goldset'in
TAMAMINI (offline, LLM'siz, ag cagrisi YOK) yeniden ayristirip, ONCEKI
(goldset_live_reports_v8, eski koddan uretilmis) title alanlariyla YENI
(duzeltilmis kod) title alanlarini karsilastirir - ozellikle bilinen
'cop-baslik' kaliplarina (URL/ISBN/digit-ordinal) odaklanir.

NOT (tekrar-uretilebilirlik siniri, durustce belirtilmeli): `old_reports_dir`
bu SESSION'a ozel bir klasoru (61 makalenin ORIJINAL/duzeltme-oncesi canli
kosum raporlari) isaret ediyor - bu dosyalar boyut/session-ozgulluk nedeniyle
repoya COMMIT EDILMEDI (goldset PDF'leri gibi). Bu script'i yeniden
calistirmak icin o 61 rapor JSON'unun (paper_id + evidence_pack.references
alanlarini tasiyan) yeniden uretilmesi gerekir - MANTIK/SONUC (bu klasordeki
diger dosyalar) kalicidir, bu KARSILASTIRMA script'inin GIRDISI degil.
"""
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from engine.ingestion.pdf_parser import parse_pdf  # noqa: E402

_GARBAGE_RE = re.compile(
    r"^(?:URL\b|ISBN\b|https?://|www\.|org/|pdf/|doi:|\d+(?:st|nd|rd|th)\b)",
    re.IGNORECASE,
)

_HERE = Path(__file__).resolve().parent
mapping_path = _HERE / "goldset61_local_filenames.json"
filenames = json.loads(mapping_path.read_text(encoding="utf-8"))
search_dirs = [Path(r"C:\Users\USER\Desktop\goldset_pdfs"), Path(r"C:\Users\USER\Desktop\goldset_pdfs_v2")]
old_reports_dir = Path(r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main\3e56c8a7-1c60-4124-9a6a-0f99102f8e39\scratchpad\goldset_live_reports_v8")

n_old_garbage_total = 0
n_new_still_garbage = 0
n_new_now_none = 0
n_new_now_valid_title = 0
per_paper = []

for paper_id, fn in filenames.items():
    old_report_path = None
    for p in old_reports_dir.glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("paper_id") == paper_id:
            old_report_path = p
            old_refs = d["report"]["evidence_pack"]["references"]
            break
    if old_report_path is None:
        continue

    old_garbage = {r["index"]: r.get("title") for r in old_refs if r.get("title") and _GARBAGE_RE.match(r["title"])}
    if not old_garbage:
        continue

    pdf_path = next((d / fn for d in search_dirs if (d / fn).exists()), None)
    if pdf_path is None:
        continue
    ms = parse_pdf(pdf_path.read_bytes(), filename=fn)
    new_by_index = {r.index: r.title for r in ms.references}

    n_old_garbage_total += len(old_garbage)
    paper_detail = []
    for idx, old_title in old_garbage.items():
        # NOT: index'ler duzeltme sonrasi kayabilir (entry sayisi degisebilir) -
        # bu yuzden hem index-eslesmesi HEM "artik hic boyle bir cop-baslik var mi"
        # genel kontrolu yapiliyor.
        new_title = new_by_index.get(idx)
        if new_title is None:
            n_new_now_none += 1
            status = "NONE (guvenli)"
        elif _GARBAGE_RE.match(new_title):
            n_new_still_garbage += 1
            status = f"HALA COP: {new_title!r}"
        else:
            n_new_now_valid_title += 1
            status = f"DUZELDI: {new_title!r}"
        paper_detail.append((idx, old_title, status))
    per_paper.append((paper_id, paper_detail))

print(f"=== Onceki koddan bilinen cop-baslik sayisi: {n_old_garbage_total} ===")
print(f"Duzeltme sonrasi hala cop: {n_new_still_garbage}")
print(f"Duzeltme sonrasi None (guvenli): {n_new_now_none}")
print(f"Duzeltme sonrasi GECERLI baslik: {n_new_now_valid_title}")
print()
for paper_id, details in per_paper:
    print(f"--- {paper_id} ---")
    for idx, old_title, status in details:
        print(f"  idx={idx} eski={old_title!r} -> {status}")
