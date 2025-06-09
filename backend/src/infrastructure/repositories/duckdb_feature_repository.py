from abc import ABC, abstractmethod
import pandas as pd
from src.extensions import duckdb_instance


class FeatureRepository(ABC):
    @abstractmethod
    def load(self, patient_id: int, week: str, night: str) -> pd.DataFrame:
        """Load the 43-column features CSV or raise FileNotFoundError."""
        raise NotImplementedError

    @abstractmethod
    def save(self, df: pd.DataFrame, patient_id: int, week: str, night: str) -> None:
        """Persist the features DataFrame to CSV."""
        raise NotImplementedError


class DuckDbFeatureRepository(FeatureRepository):
    def __init__(self):
        self.conn = duckdb_instance.conn

    # ---------- API ----------
    def load(self, patient_id, week, night):
        q = """SELECT * FROM features.feature_windows
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
            for r in self.conn.execute(
                "PRAGMA table_info('features.feature_windows')"
            ).fetchall()
        }
        for col in df.columns:
            if col not in known:
                self.conn.execute(
                    f'ALTER TABLE features.feature_windows ADD COLUMN "{col}" DOUBLE'
                )
                known.add(col)

        self.conn.register("t", df)
        self.conn.execute(
            "INSERT OR REPLACE INTO features.feature_windows SELECT * FROM t"
        )
        self.conn.unregister("t")

    def get_event_metrics(
        self,
        patient_id: int,
        week: str,
        file: str,
        start_s: float,
        end_s: float,
    ) -> dict[str, float]:
        """
        Load all feature windows for this night, filter to those overlapping
        [start_s, end_s], then return the mean of each numeric feature.
        """
        # 1) grab everything
        df = self.load(patient_id, week, file)

        # 2) mask out only windows that overlap the event
        mask = ((df["start_time"] >= start_s) | (df["end_time"] > start_s)) & (
            (df["end_time"] <= end_s) | (df["start_time"] < end_s)
        )
        ev = df.loc[mask]

        # 3) if no overlap, return empty dict (or you could fill with zeros)
        if ev.empty:
            return {}

        # 4) compute mean on *all* the feature columns
        #    pandas will ignore non-numeric cols by default in .mean()
        means = ev.mean(numeric_only=True)

        return means.to_dict()
