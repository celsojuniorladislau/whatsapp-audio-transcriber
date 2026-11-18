from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from whatsapp_transcriber.app import create_app


def test_health_returns_ok() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_executes_lifespan_cleanup() -> None:
    cleaned = False

    @asynccontextmanager
    async def sample_lifespan(_):
        nonlocal cleaned
        yield
        cleaned = True

    app = create_app(lifespan=sample_lifespan)
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert cleaned is False

    assert cleaned is True
