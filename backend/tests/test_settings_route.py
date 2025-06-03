import pytest
from src.app import create_app
from src.extensions import db


@pytest.fixture
def client():
    app = create_app()
    app.config.update({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
    with app.test_client() as client:
        yield client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_settings_get_empty(client):
    response = client.get("/settings")
    assert response.status_code == 200
    assert response.get_json() == {}
