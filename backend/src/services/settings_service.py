from src.models.settings import Settings
from src.extensions import db


def get_settings():
    """Return the first Settings row."""
    return Settings.query.first()


def save_settings(data: dict) -> None:
    Settings.query.delete()
    settings = Settings(**data)
    db.session.add(settings)
    db.session.commit()
