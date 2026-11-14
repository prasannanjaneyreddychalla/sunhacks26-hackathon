from fastapi.testclient import TestClient

from app.main import app


def test_health_contract():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "platform-api"}


def test_unknown_api_route_is_not_a_successful_health_check():
    with TestClient(app) as client:
        assert client.get("/api/not-implemented").status_code == 404
