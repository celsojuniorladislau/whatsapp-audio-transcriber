from whatsapp_transcriber.app import create_app
from whatsapp_transcriber.config import Settings
from whatsapp_transcriber.evolution import EvolutionClient
from whatsapp_transcriber.handler import AudioMessageHandler
from whatsapp_transcriber.repository import SQLiteRepository
from whatsapp_transcriber.transcription import OpenAITranscriber

settings = Settings()
repository = SQLiteRepository(settings.database_path)
repository.initialize()
evolution = EvolutionClient(
    base_url=settings.normalized_evolution_base_url,
    api_key=settings.evolution_api_key.get_secret_value(),
    instance=settings.evolution_instance,
    max_audio_bytes=settings.max_audio_bytes,
)
transcriber = OpenAITranscriber(
    api_key=settings.openai_api_key.get_secret_value(),
    model=settings.openai_model,
)
handler = AudioMessageHandler(settings.evolution_instance, repository, evolution, transcriber)
app = create_app(settings=settings, webhook_handler=handler.process, repository=repository)
