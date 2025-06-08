# backend/src/infrastructure/repositories/raw_signal_repository.py
import os
import pandas as pd
from abc import ABC, abstractmethod


class RawSignalRepository(ABC):
    @abstractmethod
    def load(self, patient_id: int, week: str, night: str) -> pd.DataFrame:
        """Return the downsampled CSV as a Pandas DataFrame."""
        raise NotImplementedError


class CsvRawSignalRepository(RawSignalRepository):
    def __init__(self, base_path: str):
        self.base_path = base_path

    def load(self, patient_id: int, week: str, night: str) -> pd.DataFrame:
        file_name = night[:-8] + "200Hz.parquet"
        file_path = os.path.join(self.base_path, f"p{patient_id}_wk{week}", file_name)
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"No raw signal file at {file_path}")
        return pd.read_parquet(file_path)
