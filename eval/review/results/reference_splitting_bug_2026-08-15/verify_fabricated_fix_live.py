"""6 orijinal 'uydurma atif' referansini, DUZELTILMIS extract_authors_year_title
ile yeniden ayristirip GERCEK OpenAlex'e karsi resolve_reference() ile
yeniden cozer - artik status='fabricated' cikmiyor mu diye dogrular."""
import asyncio
import io
import sys

sys.path.insert(0, r"C:\Users\USER\Desktop\arbitra-main")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from api.models.review import ParsedReference  # noqa: E402
from api.services.review_citation_service import resolve_reference  # noqa: E402
from engine.ingestion import common  # noqa: E402

CASES = [
    ("iclr2017-400 idx4", "Li Dong and Mirella Lapata. Language to Logical Form with Neural Attention. In ACL, pp. 33\u201343, 2016. doi: 10.18653/v1/P16-1004. URL http://arxiv.org/abs/1601.01280."),
    ("iclr2017-400 idx21", "Ronald J. Williams and David Zipser. Gradient-based learning algorithms for recurrent networks and their computational complexity. Back-propagation Theory, Archit. Appl., pp. 433\u2013486, 1995. doi: 10.1080/02673039508720837."),
]


async def main():
    for name, body in CASES:
        authors, year, title = common.extract_authors_year_title(body)
        doi = common.extract_doi(body)
        ref = ParsedReference(index=1, raw=body, title=title, authors=authors, year=year, doi=doi)
        print(f"=== {name} ===")
        print(f"  yeni title={title!r} doi={doi!r}")
        resolved = await resolve_reference(ref)
        print(f"  status={resolved.status} evidence={resolved.evidence}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
