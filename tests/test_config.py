import pytest
from pydantic import ValidationError

from whatsapp_transcriber.config import Settings


def test_missing_required_secrets_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "EVOLUTION_BASE_URL",
        "EVOLUTION_API_KEY",
        "EVOLUTION_INSTANCE",
        "OPENAI_API_KEY",
        "WEBHOOK_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_load_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVOLUTION_BASE_URL", "http://localhost:8080")
    monkeypatch.setenv("EVOLUTION_API_KEY", "test-evolution-key")
    monkeypatch.setenv("EVOLUTION_INSTANCE", "personal")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-webhook-secret")

    settings = Settings(_env_file=None)

    assert settings.max_audio_bytes == 20 * 1024 * 1024
    assert settings.openai_model == "whisper-1"
    assert settings.database_path == "./data/messages.sqlite3"
