import pytest

from app.app import app


@pytest.fixture()
def client():
    app.config.update(TESTING=True)

    with app.test_client() as test_client:
        yield test_client


def test_home_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200

    assert response.get_json() == {
        "application": "Python AWS Automation Demo",
        "status": "running",
        "message": "Python application is running successfully",
    }


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200

    assert response.get_json() == {
        "status": "healthy"
    }


def test_data_endpoint(client):
    response = client.get("/api/data")

    payload = response.get_json()

    assert response.status_code == 200

    assert len(payload["data"]) == 4

    assert payload["data"][0] == {
        "id": 1,
        "name": "DevOps"
    }


def test_unknown_endpoint_returns_404(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404

    assert response.get_json() == {
        "error": "Endpoint not found"
    }