from fastapi.testclient import TestClient

from app import __version__
from app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert set(body) == {"status", "app", "version", "environment"}


def test_request_id_is_generated_and_echoed() -> None:
    client = TestClient(create_app())

    generated = client.get("/health").headers["x-request-id"]
    assert len(generated) == 32

    echoed = client.get("/health", headers={"x-request-id": "abc-123"}).headers["x-request-id"]
    assert echoed == "abc-123"
