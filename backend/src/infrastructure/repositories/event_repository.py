# backend/src/infrastructure/repositories/event_repository.py
from abc import ABC, abstractmethod
from typing import List
from src.models.event_prediction import EventPrediction
from src.extensions import db


class EventRepository(ABC):
    @abstractmethod
    def list(self, patient_id: int, week: str, night: str) -> List[EventPrediction]:
        """Return all EventPrediction rows for this night."""
        raise NotImplementedError

    @abstractmethod
    def save_all(self, events: List[EventPrediction]) -> None:
        """Bulk‐save a list of EventPrediction instances."""
        raise NotImplementedError


class SqlAlchemyEventRepository(EventRepository):
    def list(self, patient_id: int, week: str, night: str) -> List[EventPrediction]:
        return EventPrediction.query.filter_by(
            patient_id=patient_id, week=week, file=night
        ).all()

    def save_all(self, events: List[EventPrediction]) -> None:
        for ev in events:
            db.session.add(ev)
        db.session.commit()
