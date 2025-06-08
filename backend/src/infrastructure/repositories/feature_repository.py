# backend/src/infrastructure/repositories/feature_repository.py
import os
import pandas as pd
from abc import ABC, abstractmethod


class FeatureRepository(ABC):
    @abstractmethod
    def load(self, patient_id: int, week: str, night: str) -> pd.DataFrame:
        """Load the 43-column features CSV or raise FileNotFoundError."""
        raise NotImplementedError

    @abstractmethod
    def save(self, df: pd.DataFrame, patient_id: int, week: str, night: str) -> None:
        """Persist the features DataFrame to CSV."""
        raise NotImplementedError


class CsvFeatureRepository(FeatureRepository):
    def __init__(self, base_path: str):
        self.base_path = base_path

    def _path(self, patient_id, week, night):
        name = night[:-8] + "200Hz_features.parquet"
        return os.path.join(self.base_path, f"p{patient_id}_wk{week}", name)

    def load(self, patient_id, week, night) -> pd.DataFrame:
        fp = self._path(patient_id, week, night)
        if not os.path.isfile(fp):
            raise FileNotFoundError(f"No feature file at {fp}")
        return pd.read_parquet(fp)

    def save(self, df: pd.DataFrame, patient_id: int, week: str, night: str) -> None:
        fp = self._path(patient_id, week, night)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        df.to_parquet(fp, index=False)
