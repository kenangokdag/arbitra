"""seed_dim_field — warehouse parquet → public.dim_field idempotent upsert.

Plan referansı : docs/plans/F5_S0_dim_field_taxonomy.md §C
Brain referansı: K-007 (dim_field), K-010 (sistem iç dili EN),
                 K-011 (DB tek dil EN, ileri yönlü), K-019 (level-1, ~26 satır)
DM_RULES       : R4 (zero-hallucination) · R7 (atomic commit) · R10 (RLS)

Kaynak parquet (extract_dim_field.py çıktısı):
    ~/Desktop/PaperMind_V2/03_outputs/dim_field_seed.parquet
    kolonlar: name_en (Utf8), paper_count_total (Int64)

Hedef tablo:
    public.dim_field (field_id PK, name_en UNIQUE, slug UNIQUE,
                      paper_count_total int, timestamps)

Davranış:
    - service_role client ile upsert (RLS bypass; on_conflict=field_id)
    - field_id (underscore) + slug (dash) deterministik — 2. çalıştırma idempotent
    - Çıktı: row count + 1. ve 2. çalıştırma "inserted/updated" rapor

Çalıştırma:
    cd ~/dev/arbitra
    uv run python -m api.scripts.seed_dim_field
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import polars as pl

from api.db.supabase_client import get_supabase_admin

DEFAULT_PARQUET = (
    Path.home() / "Desktop" / "PaperMind_V2" / "03_outputs" / "dim_field_seed.parquet"
)
PARQUET_PATH = Path(os.environ.get("DIM_FIELD_SEED_PARQUET", str(DEFAULT_PARQUET)))

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def derive_field_id(name_en: str) -> str:
    """Plan §7: field_id = re.sub(r'[^a-z0-9]+', '_', name_en.lower()).strip('_')."""
    return _NON_ALNUM.sub("_", name_en.strip().lower()).strip("_")


def derive_slug(name_en: str) -> str:
    """URL-safe slug (dashes) — UI dropdown value."""
    return _NON_ALNUM.sub("-", name_en.strip().lower()).strip("-")


def load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"seed parquet yok: {path}")
    df = pl.read_parquet(path)
    expected = {"name_en", "paper_count_total"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"parquet kolon eksik: {missing}; got={df.columns}")

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()
    for r in df.iter_rows(named=True):
        name_en = (r["name_en"] or "").strip()
        if len(name_en) < 2:
            continue
        field_id = derive_field_id(name_en)
        slug = derive_slug(name_en)
        if not field_id or not slug:
            raise ValueError(f"boş id/slug: name_en={name_en!r}")
        if field_id in seen_ids or slug in seen_slugs:
            raise ValueError(
                f"çakışma: name_en={name_en!r} field_id={field_id!r} slug={slug!r}"
            )
        seen_ids.add(field_id)
        seen_slugs.add(slug)
        rows.append(
            {
                "field_id": field_id,
                "name_en": name_en,
                "slug": slug,
                "paper_count_total": int(r["paper_count_total"]),
            }
        )
    if not (20 <= len(rows) <= 500):
        raise ValueError(f"A4 FAIL: {len(rows)} satır 20..500 dışı (K-019)")
    return rows


def main() -> int:
    try:
        rows = load_rows(PARQUET_PATH)
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    client = get_supabase_admin()

    pre = client.table("dim_field").select("field_id", count="exact").execute()
    pre_count = pre.count or 0

    resp = (
        client.table("dim_field")
        .upsert(rows, on_conflict="field_id")
        .execute()
    )
    written = len(resp.data or [])

    post = client.table("dim_field").select("field_id", count="exact").execute()
    post_count = post.count or 0

    inserted = max(0, post_count - pre_count)
    updated = written - inserted

    print(f"PASS — upsert {written} satır → public.dim_field")
    print(f"  pre_count  = {pre_count}")
    print(f"  post_count = {post_count}")
    print(f"  inserted   = {inserted}")
    print(f"  updated    = {updated}")
    print(f"  source     = {PARQUET_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
