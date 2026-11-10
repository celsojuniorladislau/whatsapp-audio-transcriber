from typing import Any

from whatsapp_transcriber.events import parse_audio_event


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
            return False
        status = self.repository.get_status(incoming.message_id)
        if status in {"done", "processing"}:
            return False

        self.repository.mark_message(incoming.message_id, "processing")
        try:
            audio, mime_type = self.evolution.download_audio(incoming.message_payload)
            filename = "voice.ogg" if "ogg" in mime_type.lower() else "voice.audio"
            transcript = self.transcriber.transcribe(audio, filename, mime_type)
            self.evolution.send_text(incoming.number, f"Transcrição: {transcript}")
            self.repository.mark_message(incoming.message_id, "done")
            return True
        except Exception as exc:
            self.repository.mark_message(incoming.message_id, "error", "processing failed")
            raise ProcessingError("audio message processing failed") from exc
