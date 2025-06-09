from abc import ABC, abstractmethod
from typing import List, Dict, Any
from collections import defaultdict
import pandas as pd
import polars as pl
from src.extensions import duckdb_instance


class RawSignalRepository(ABC):
    @abstractmethod
    def load_raw(self, patient_id: int, week: str, night: str) -> pd.DataFrame:
        """Return the downsampled CSV as a Pandas DataFrame."""
        raise NotImplementedError


class DuckDbRawRepository(RawSignalRepository):
    def __init__(self):
        self.conn = duckdb_instance.conn

    def load_patients_structure(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Returns a nested dict of
          { patient_id: { week: [ { "file_name": ..., "size_gb": ... }, … ] }, … }
        """
        # grab every night file recorded
        query = """
            SELECT DISTINCT
              patient_id,
              week,
              file AS file_name,
              COUNT(*) AS row_count
            FROM raw.Fnorm
            GROUP BY patient_id, week, file
            ORDER BY patient_id, week, file
        """
        df = self.conn.execute(query).fetchdf()

        # build the exact same shape your UI expects
        data: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for _, row in df.iterrows():
            pid = str(int(row["patient_id"]))
            wk = row["week"]
            fn = row["file_name"]
            # we don't have the parquet filesize here, so just supply row_count (or null)
            size_gb = None
            data[pid][wk].append(
                {
                    "file_name": fn,
                    "size_gb": size_gb,
                }
            )

        # convert to plain dicts
        return {p: dict(wks) for p, wks in data.items()}

    def load_raw(self, patient_id: int, week: str, night: str) -> pd.DataFrame:
        query = "SELECT * FROM raw.Fnorm WHERE patient_id = ? AND week = ? AND file = ?"
        return self.conn.execute(query, (patient_id, week, night)).fetchdf()

    def load_location_bites(
        self, patient_id: int, week: str, night: str
    ) -> pl.DataFrame:
        # derive the actual location-Bites filename
        short = night.rsplit("Fnorm.parquet", 1)[0]
        loc_file = f"{short}location_Bites.parquet"

        query = """
            SELECT begin_idx, end_idx, duration_s
            FROM   raw.location_bites
            WHERE  patient_id = ? AND week = ? AND file = ?
            ORDER  BY begin_idx
        """
        pdf = self.conn.execute(query, (patient_id, week, loc_file)).fetchdf()
        return pl.from_pandas(pdf)

    # NEW helper for storing the 200 Hz frame
    def save_downsampled(self, df: pd.DataFrame, patient_id, week, night):
        df = df.copy()
        df.insert(0, "sample_idx", range(len(df)))
        df.insert(0, "file", night)
        df.insert(0, "week", week)
        df.insert(0, "patient_id", patient_id)

        self.conn.register("t200", df)
        self.conn.execute("INSERT OR REPLACE INTO downsampled.Fnorm SELECT * FROM t200")
        self.conn.unregister("t200")

    def exists_downsampled(self, patient_id: int, week: str, night: str) -> bool:
        query = """
            SELECT 1
            FROM   downsampled.Fnorm
            WHERE  patient_id = ? AND week = ? AND file = ?
            LIMIT  1
        """
        return (
            self.conn.execute(query, (patient_id, week, night)).fetchone() is not None
        )

    def load_downsampled(
        self,
        patient_id: int,
        week: str,
        night: str,
        start_idx: int | None = None,
        end_idx: int | None = None,
    ) -> pd.DataFrame:
        query = """
            SELECT sample_idx, MR, ML, ECG
            FROM   downsampled.Fnorm
            WHERE  patient_id = ? AND week = ? AND file = ?
        """
        params = [patient_id, week, night]

        if start_idx is not None and end_idx is not None:
            query += " AND sample_idx BETWEEN ? AND ?"
            params.extend([start_idx, end_idx])

        query += " ORDER BY sample_idx"
        return self.conn.execute(query, params).fetchdf()
