# backend/src/infrastructure/repositories/duckdb_raw_repository.py
import pandas as pd
from src.extensions import duckdb_instance

from .raw_signal_repository import RawSignalRepository


class DuckDbRawRepository(RawSignalRepository):
    def __init__(self):
        self.conn = duckdb_instance.conn

    # keep `.load()` for the raw 2 000 Hz table unchanged …

    def load_raw(self, patient_id: int, week: str, night: str) -> pd.DataFrame:
        query = "SELECT * FROM raw.recordings WHERE patient_id = ? AND week = ? AND file = ?"
        return self.conn.execute(query, (patient_id, week, night)).fetchdf()

    # NEW helper for storing the 200 Hz frame
    def save_downsampled(self, df: pd.DataFrame, patient_id, week, night):
        df = df.copy()
        df.insert(0, "sample_idx", range(len(df)))
        df.insert(0, "file", night)
        df.insert(0, "week", week)
        df.insert(0, "patient_id", patient_id)

        self.conn.register("t200", df)
        self.conn.execute("INSERT OR REPLACE INTO ds.signal_200hz SELECT * FROM t200")
        self.conn.unregister("t200")

    def exists_downsampled(self, patient_id: int, week: str, night: str) -> bool:
        query = """
            SELECT 1
            FROM   ds.signal_200hz
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
            FROM   ds.signal_200hz
            WHERE  patient_id = ? AND week = ? AND file = ?
        """
        params = [patient_id, week, night]

        if start_idx is not None and end_idx is not None:
            query += " AND sample_idx BETWEEN ? AND ?"
            params.extend([start_idx, end_idx])

        query += " ORDER BY sample_idx"
        return self.conn.execute(query, params).fetchdf()
