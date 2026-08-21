"""SS51 guardian sorusu 2: extract_doi() fazla-rakam bug'inin 61-goldset'teki
gercek etkisini olcer. LLM'siz, ucretsiz - sadece PDF metin cikarimi + regex.

Yontem: 61 goldset PDF'ini GUNCEL (duzeltilmis) kodla parse_pdf() ile bir kez
ayristir. Her referansin RAW metnini al, ayni raw metin uzerinde HEM eski
(buggy) HEM yeni (duzeltilmis) extract_doi() mantigini calistir, karsilastir.
Fark varsa + eski sonuc yeninin SONUNA fazladan rakam eklemisse (bug deseni),
say."""

import io
import re
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def safe_print(*a, **k):
    print(" ".join(str(x) for x in a).encode("ascii", "replace").decode("ascii"), **k)


from engine.ingestion.pdf_parser import parse_pdf  # noqa: E402
from engine.ingestion import common as common_new  # noqa: E402  (GUNCEL/duzeltilmis)

# --- ESKI (buggy) extract_doi mantigi - SS51 fix'inden ONCEKI hali, birebir ---
_DOI_RE_OLD = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", re.IGNORECASE)
_DOI_WRAP_CONTINUATION_RE_OLD = re.compile(r"^ ([a-z0-9][-._;()/:A-Za-z0-9]*)")


def extract_doi_old(text: str) -> str | None:
    m = _DOI_RE_OLD.search(text)
    if not m:
        return None
    doi = m.group(1)
    rest = text[m.end():]
    while True:
        cont = _DOI_WRAP_CONTINUATION_RE_OLD.match(rest)
        if not cont or not any(c.isdigit() for c in cont.group(1)):
            break
        doi += cont.group(1)
        rest = rest[cont.end():]
    return doi.rstrip(".,;)")


GOLDSET_DIRS = [
    Path(r"C:\Users\USER\Desktop\goldset_pdfs"),
    Path(r"C:\Users\USER\Desktop\goldset_pdfs_v2"),
]


def main() -> None:
    pdf_files = []
    for d in GOLDSET_DIRS:
        if d.exists():
            pdf_files.extend(sorted(d.glob("*.pdf")))
    safe_print(f"Toplam PDF: {len(pdf_files)}")

    total_refs = 0
    total_diff = 0
    bug_pattern_diff = 0  # eski = yeni + sonuna fazladan SALT-RAKAM ek
    examples = []

    for pdf_path in pdf_files:
        try:
            data = pdf_path.read_bytes()
            manuscript = parse_pdf(data, filename=pdf_path.name)
        except Exception as exc:
            safe_print(f"  PARSE HATASI {pdf_path.name}: {exc}")
            continue

        for ref in manuscript.references:
            total_refs += 1
            raw = ref.raw or ""
            new_doi = common_new.extract_doi(raw)
            old_doi = extract_doi_old(raw)
            if new_doi != old_doi:
                total_diff += 1
                if (
                    new_doi
                    and old_doi
                    and old_doi.lower().startswith(new_doi.lower())
                    and old_doi[len(new_doi):].strip(".,;) ").isdigit()
                ):
                    bug_pattern_diff += 1
                    if len(examples) < 15:
                        examples.append((pdf_path.name, old_doi, new_doi))

    safe_print(f"\nToplam parse edilen referans: {total_refs}")
    safe_print(f"Eski/yeni DOI cikarimi FARKLI olan: {total_diff}")
    safe_print(f"Bunlarin BUG DESENINE uyanlari (eski=yeni+bitisik-fazla-rakam): {bug_pattern_diff}")
    safe_print("\nOrnekler:")
    for fn, old, new in examples:
        safe_print(f"  {fn}: eski={old!r} -> yeni={new!r}")


if __name__ == "__main__":
    main()
