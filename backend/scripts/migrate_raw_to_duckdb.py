    #!/usr/bin/env python3
    import glob
    import os
    import duckdb
    import pandas as pd
    import pyarrow.parquet as pq

    DB_PATH = os.getenv("DUCKDB_FILE", "raw_recordings.duckdb")
    DATA_GLOB = os.path.join("data", "raw", "p*_wk*", "*.parquet")


    def main() -> None:
        con = duckdb.connect(DB_PATH)
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")

        files = sorted(glob.glob(DATA_GLOB))
        if not files:
            print("No Parquet files found.")
            return

        table_cols: list[str] = []  # running master-column list
        first = True

        for fp in files:
            print(f"Inserting {fp}...")
            df = pq.read_table(fp).to_pandas()

            # ── derive metadata ───────────────────────────
            base = os.path.basename(fp)
            patient_id = int(fp.split("/p")[1].split("_wk")[0])
            week = fp.split("_wk")[1].split("/")[0]
            night = base
            df.insert(0, "patient_id", patient_id)
            df.insert(1, "week", week)
            df.insert(2, "file", night)

            # ── grow schema if new columns appear ─────────
            new_cols = [c for c in df.columns if c not in table_cols]
            if new_cols and not first:
                for col in new_cols:
                    con.execute(f'ALTER TABLE raw.recordings ADD COLUMN "{col}" DOUBLE')
                table_cols += new_cols  # remember order

            # ── first batch: create table ─────────────────
            if first:
                table_cols = list(df.columns)  # incl. metadata
                con.register("t", df)
                con.execute("CREATE OR REPLACE TABLE raw.recordings AS SELECT * FROM t")
                con.unregister("t")
                first = False
                continue

            # ── pad missing cols then insert ──────────────
            for col in table_cols:
                if col not in df.columns:
                    df[col] = pd.NA
            df = df[table_cols]

            con.register("t", df)
            con.execute("INSERT INTO raw.recordings SELECT * FROM t")
            con.unregister("t")

        con.close()


    if __name__ == "__main__":
        main()
