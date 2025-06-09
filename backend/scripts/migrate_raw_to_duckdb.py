#!/usr/bin/env python3
import glob
import os
import duckdb
import pandas as pd
import pyarrow.parquet as pq

DB_PATH = os.getenv("DUCKDB_FILE", "data/database.duckdb")
FNORM_GLOB = os.path.join("data", "raw", "p*_wk*", "*Fnorm.parquet")
LOC_GLOB = os.path.join("data", "raw", "p*_wk*", "*location_Bites.parquet")

# the *exact* columns your raw.Fnorm table expects:
FNORM_COLUMNS = [
    "patient_id",
    "week",
    "file",
    "MR",
    "ML",
    "SU",
    "Microphone",
    "Eye",
    "ECG",
    "Pressure_Sensor",
]


def main():
    con = duckdb.connect(DB_PATH, read_only=False)

    # ingest all *Fnorm.parquet
    for fp in sorted(glob.glob(FNORM_GLOB)):
        print("Ingesting Fnorm:", fp)
        df = pq.read_table(fp).to_pandas()

        # metadata
        pid = int(fp.split("/p")[1].split("_wk")[0])
        week = fp.split("_wk")[1].split("/")[0]
        night = os.path.basename(fp)
        df.insert(0, "patient_id", pid)
        df.insert(1, "week", week)
        df.insert(2, "file", night)

        # normalize column names
        if "Pressure Sensor" in df.columns:
            df = df.rename(columns={"Pressure Sensor": "Pressure_Sensor"})

        # reindex (fill missing with null) and drop any extras
        df = df.reindex(columns=FNORM_COLUMNS, fill_value=pd.NA)

        con.register("t_f", df)
        con.execute(
            """
          INSERT INTO raw.Fnorm
          SELECT * FROM t_f
        """
        )
        con.unregister("t_f")

    # ingest location_bites (unchanged)
    for fp in sorted(glob.glob(LOC_GLOB)):
        print("Ingesting loc bites:", fp)
        loc = pq.read_table(fp).to_pandas()

        pid = int(fp.split("/p")[1].split("_wk")[0])
        week = fp.split("_wk")[1].split("/")[0]
        night = os.path.basename(fp)
        loc.insert(0, "patient_id", pid)
        loc.insert(1, "week", week)
        loc.insert(2, "file", night)

        loc = loc.rename(
            columns={
                "Location Begin": "begin_idx",
                "Location end": "end_idx",
                "Duration[s]": "duration_s",
            }
        )[["patient_id", "week", "file", "begin_idx", "end_idx", "duration_s"]]

        con.register("t_l", loc)
        con.execute(
            """
          INSERT INTO raw.location_bites
          SELECT * FROM t_l
        """
        )
        con.unregister("t_l")

    con.close()
    print("✅ Done.")


if __name__ == "__main__":
    main()
