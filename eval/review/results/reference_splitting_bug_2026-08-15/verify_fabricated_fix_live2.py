import asyncio
import io
import json
import sys

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from api.models.review import ParsedReference  # noqa: E402
from api.services.review_citation_service import resolve_reference  # noqa: E402
from engine.ingestion import common  # noqa: E402

raws = json.load(open(
    r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER-Desktop-arbitra-main\3e56c8a7-1c60-4124-9a6a-0f99102f8e39\scratchpad\iclr487_fab_raw.json",
    encoding="utf-8",
))


async def main():
    for i, raw in enumerate(raws):
        print(f"=== raw[{i}] ===")
        entries = common.group_reference_entries([raw])
        for j, e in enumerate(entries):
            body = common.strip_reference_number(e)
            authors, year, title = common.extract_authors_year_title(body)
            doi = common.extract_doi(body)
            if not doi:
                print(f"  entry[{j}]: doi yok, atlanıyor ({body[:60]!r})")
                continue
            ref = ParsedReference(index=1, raw=body, title=title, authors=authors, year=year, doi=doi)
            resolved = await resolve_reference(ref)
            print(f"  entry[{j}] title={title!r} doi={doi!r}")
            print(f"    -> status={resolved.status}")
            print(f"    -> evidence={resolved.evidence}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
