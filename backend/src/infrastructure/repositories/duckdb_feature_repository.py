# backend/src/infrastructure/repositories/duckdb_feature_repository.py
import pandas as pd
from .feature_repository import FeatureRepository
from src.extensions import duckdb_instance


class DuckDbFeatureRepository(FeatureRepository):
    def __init__(self):
        self.conn = duckdb_instance.conn

    # ---------- API ----------
    def load(self, patient_id, week, night):
        q = """SELECT * FROM feat.features
               WHERE patient_id=? AND week=? AND file=?
               ORDER BY window_idx"""
        return self.conn.execute(q, (patient_id, week, night)).fetchdf()

    def save(self, df: pd.DataFrame, patient_id, week, night):
        df = df.copy()
        df.insert(0, "window_idx", range(len(df)))
        df.insert(0, "file", night)
        df.insert(0, "week", week)
        df.insert(0, "patient_id", patient_id)

        # add new columns on the fly
        known = {
            r[1]
            for r in self.conn.execute("PRAGMA table_info('feat.features')").fetchall()
        }
        for col in df.columns:
            if col not in known:
                self.conn.execute(
                    f'ALTER TABLE feat.features ADD COLUMN "{col}" DOUBLE'
                )
                known.add(col)

        self.conn.register("t", df)
        self.conn.execute("INSERT OR REPLACE INTO feat.features SELECT * FROM t")
        self.conn.unregister("t")
