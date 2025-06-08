#!/usr/bin/env python3
import os
import polars as pl
import pathlib

RAW = pathlib.Path(__file__).parent.parent / "data/raw"

print(f"Converting CSV files in {RAW} to Parquet...")
for root, _, files in os.walk(RAW):
    for fn in files:
        if fn.endswith(".csv"):
            csv = os.path.join(root, fn)
            pq = csv[:-4] + ".parquet"
            if not os.path.exists(pq):
                df = pl.read_csv(csv)
                df.write_parquet(pq, compression="zstd")
                print(f"→ {pq}")
