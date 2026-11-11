from io import BytesIO
from typing import Any


class TranscriptionError(RuntimeError):
    pass


class FasterWhisperTranscriber:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 2,
        model: Any = None,
    ) -> None:
        if model is None:
            from faster_whisper import WhisperModel

            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                cpu_threads=cpu_threads,
                num_workers=1,
            )
        self.model = model

    def transcribe(self, audio: bytes, filename: str, mime_type: str) -> str:
        del filename, mime_type  # The decoder detects the audio format from the bytes.
        if not audio:
            raise TranscriptionError("empty audio")
        try:
            segments, _info = self.model.transcribe(
                BytesIO(audio),
                language="pt",
                beam_size=5,
                vad_filter=True,
            )
            text = "".join(segment.text for segment in segments).strip()
        except Exception as exc:
            raise TranscriptionError("local transcription failed") from exc
        if not text:
            raise TranscriptionError("empty transcription")
        return text
