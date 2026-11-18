import logging
from typing import Any

from whatsapp_transcriber.events import parse_audio_event

logger = logging.getLogger("whatsapp_transcriber")


class ProcessingError(RuntimeError):
    pass


class AudioMessageHandler:
    def __init__(self, instance: str, repository: Any, evolution: Any, transcriber: Any) -> None:
        self.instance = instance
        self.repository = repository
        self.evolution = evolution
        self.transcriber = transcriber

    def process(self, payload: dict[str, Any]) -> bool:
        incoming = parse_audio_event(payload, self.instance)
        if incoming is None:
            logger.info("Ignoring event: not a targeted incoming audio message")
            return False
        status = self.repository.get_status(incoming.message_id)
        if status in {"done", "processing"}:
            logger.info("Message %s already in status '%s', ignoring", incoming.message_id, status)
            return False

        logger.info("Starting processing for audio message %s from %s", incoming.message_id, incoming.number)
        self.repository.mark_message(incoming.message_id, "processing")
        try:
            audio, mime_type = self.evolution.download_audio(incoming.message_payload)
            logger.info("Audio downloaded successfully for %s (%d bytes, %s)", incoming.message_id, len(audio), mime_type)
            filename = "voice.ogg" if "ogg" in mime_type.lower() else "voice.audio"
            transcript = self.transcriber.transcribe(audio, filename, mime_type)
            logger.info("Transcription completed for %s: '%s'", incoming.message_id, transcript)
            self.evolution.send_text(incoming.number, f"Transcrição: {transcript}")
            logger.info("Transcription response sent to %s for message %s", incoming.number, incoming.message_id)
            self.repository.mark_message(incoming.message_id, "done")
            return True
        except Exception as exc:
            logger.error("Processing failed for %s: %s", incoming.message_id, exc, exc_info=True)
            self.repository.mark_message(incoming.message_id, "error", "processing failed")
            raise ProcessingError("audio message processing failed") from exc
