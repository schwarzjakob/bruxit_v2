from abc import ABC, abstractmethod
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

    # keep `.load()` for the raw 2 000 Hz table unchanged …

    def load_raw(self, patient_id: int, week: str, night: str) -> pd.DataFrame:
        query = "SELECT * FROM raw.Fnorm WHERE patient_id = ? AND week = ? AND file = ?"
        return self.conn.execute(query, (patient_id, week, night)).fetchdf()

    def load_location_bites(
        self, patient_id: int, week: str, night: str
    ) -> pl.DataFrame:
        # derive the actual location-Bites filename
        short = night.rsplit("Fnorm.parquet", 1)[0]
        loc_file = f"{short}location_Bites.parquet"

        q = """
            SELECT begin_idx, end_idx, duration_s
            FROM   raw.location_bites
            WHERE  patient_id = ? AND week = ? AND file = ?
            ORDER  BY begin_idx
        """
        pdf = self.conn.execute(q, (patient_id, week, loc_file)).fetchdf()
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
