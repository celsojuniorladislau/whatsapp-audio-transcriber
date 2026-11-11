from fastapi.testclient import TestClient

from whatsapp_transcriber.app import create_app
from whatsapp_transcriber.config import Settings
from whatsapp_transcriber.repository import SQLiteRepository


def test_ready_reports_database_availability(tmp_path) -> None:
    settings = Settings(
        evolution_base_url="http://evolution.test",
        evolution_api_key="test-key",
        evolution_instance="personal",
        webhook_secret="private-hook-secret",
        _env_file=None,
    )
    repository = SQLiteRepository(str(tmp_path / "messages.sqlite3"))
    repository.initialize()

    response = TestClient(create_app(settings=settings, repository=repository)).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
