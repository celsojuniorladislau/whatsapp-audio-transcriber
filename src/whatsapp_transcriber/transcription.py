from typing import Any

from openai import OpenAI


class TranscriptionError(RuntimeError):
    pass


class OpenAITranscriber:
    def __init__(self, api_key: str | None = None, model: str = "whisper-1", client: Any = None) -> None:
        self.client = client or OpenAI(api_key=api_key, timeout=45.0, max_retries=1)
        self.model = model

    def transcribe(self, audio: bytes, filename: str, mime_type: str) -> str:
        if not audio:
            raise TranscriptionError("empty audio")
        try:
            result = self.client.audio.transcriptions.create(
                model=self.model,
                file=(filename, audio, mime_type),
                language="pt",
            )
        except Exception as exc:
            raise TranscriptionError("transcription provider failed") from exc
        text = getattr(result, "text", "").strip()
        if not text:
            raise TranscriptionError("empty transcription")
        return text
