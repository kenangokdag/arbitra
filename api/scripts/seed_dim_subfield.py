"""Seed dim_subfield from local CSV (composite PK upsert, idempotent).

Plan: docs/plans/F5_S1B_dim_subfield_bridge.md §7.1 / DM-7 (composite PK)
Kaynak: api/scripts/data/dim_subfield_seed.csv (Colab seed 2026-05-03, 252 satır)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import polars as pl
from supabase import create_client

CSV_PATH = Path(__file__).parent / "data" / "dim_subfield_seed.csv"
EXPECTED_ROWS = 252       # OQ-E doğrulandı
EXPECTED_COLLISIONS = 8   # plan §13 Q4 ile uyumlu


def main() -> int:
    if not CSV_PATH.exists():
        print(f"[FAIL] seed CSV bulunamadı: {CSV_PATH}", file=sys.stderr)
        print("       Colab cell yeniden çalıştırılıp indirilen CSV bu yola taşınmalı.", file=sys.stderr)
        return 2

    df = pl.read_csv(CSV_PATH)
    expected_cols = {"subfield_id", "field_id", "name_en", "slug", "paper_count_total"}
    if set(df.columns) != expected_cols:
        print(f"[FAIL] CSV şeması beklenenden farklı: {df.columns}", file=sys.stderr)
        return 2

    n = len(df)
    print(f"loaded {n} rows from {CSV_PATH.name}")
    if n != EXPECTED_ROWS:
        print(f"[WARN] satır sayısı {n} ≠ beklenen {EXPECTED_ROWS} — yine de devam, ama incele")

    collisions = (
        df.group_by("subfield_id").agg(pl.len().alias("n")).filter(pl.col("n") > 1).height
    )
    print(f"composite PK collision (subfield_id × n>1): {collisions} satır (beklenen {EXPECTED_COLLISIONS})")
    if collisions != EXPECTED_COLLISIONS:
        print(f"[WARN] collision sayısı {collisions} ≠ {EXPECTED_COLLISIONS} — taxonomy değişmiş olabilir")

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])

    rows = df.to_dicts()
    # composite key UPSERT — on_conflict iki kolonlu
    for i in range(0, len(rows), 100):
        chunk = rows[i : i + 100]
        supabase.table("dim_subfield").upsert(
            chunk, on_conflict="subfield_id,field_id"
        ).execute()
        print(f"upserted {i + len(chunk)} / {len(rows)}")

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
