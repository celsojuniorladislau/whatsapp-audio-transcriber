import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from whatsapp_transcriber.app import create_app
from whatsapp_transcriber.config import Settings
from whatsapp_transcriber.evolution import EvolutionClient
from whatsapp_transcriber.handler import AudioMessageHandler
from whatsapp_transcriber.repository import SQLiteRepository
from whatsapp_transcriber.transcription import FasterWhisperTranscriber

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

settings = Settings()
repository = SQLiteRepository(settings.database_path)
repository.initialize()
evolution = EvolutionClient(
    base_url=settings.normalized_evolution_base_url,
    api_key=settings.evolution_api_key.get_secret_value(),
    instance=settings.evolution_instance,
    max_audio_bytes=settings.max_audio_bytes,
)
transcriber = FasterWhisperTranscriber(
    model_size=settings.whisper_model,
    device=settings.whisper_device,
    compute_type=settings.whisper_compute_type,
    cpu_threads=settings.whisper_cpu_threads,
)
handler = AudioMessageHandler(settings.evolution_instance, repository, evolution, transcriber)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    evolution.close()


app = create_app(
    settings=settings,
    webhook_handler=handler.process,
    repository=repository,
    lifespan=lifespan,
)
