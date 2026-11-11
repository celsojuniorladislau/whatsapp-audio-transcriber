from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    evolution_base_url: str
    evolution_api_key: SecretStr
    evolution_instance: str
    webhook_secret: SecretStr
    database_path: str = "./data/messages.sqlite3"
    max_audio_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_cpu_threads: int = Field(default=2, gt=0)

    @property
    def normalized_evolution_base_url(self) -> str:
        return self.evolution_base_url.rstrip("/")
