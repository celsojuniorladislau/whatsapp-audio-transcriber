from fastapi.testclient import TestClient

from whatsapp_transcriber.app import create_app
from whatsapp_transcriber.config import Settings


def make_settings() -> Settings:
    return Settings(
        evolution_base_url="http://evolution.test",
        evolution_api_key="test-key",
        evolution_instance="personal",
        openai_api_key="test-openai-key",
        webhook_secret="private-hook-secret",
        _env_file=None,
    )


def test_webhook_rejects_missing_or_wrong_secret() -> None:
    client = TestClient(create_app(settings=make_settings()))

    assert client.post("/webhooks/evolution", json={}).status_code == 401
    assert client.post("/webhooks/evolution", headers={"x-webhook-secret": "wrong"}, json={}).status_code == 401


def test_webhook_reports_processing_failure_for_retry() -> None:
    def fail(_: dict) -> None:
        raise RuntimeError("internal secret details")

    client = TestClient(create_app(settings=make_settings(), webhook_handler=fail))
    response = client.post(
        "/webhooks/evolution",
        headers={"x-webhook-secret": "private-hook-secret"},
        json={"event": "messages.upsert"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Webhook processing failed"}


def test_webhook_accepts_correct_secret() -> None:
    received = []
    client = TestClient(create_app(settings=make_settings(), webhook_handler=received.append))

    response = client.post(
        "/webhooks/evolution",
        headers={"x-webhook-secret": "private-hook-secret"},
        json={"event": "messages.upsert"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}
    assert received == [{"event": "messages.upsert"}]
