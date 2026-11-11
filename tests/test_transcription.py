from types import SimpleNamespace

import pytest

from whatsapp_transcriber.transcription import FasterWhisperTranscriber, TranscriptionError


class FakeWhisperModel:
    def __init__(self, segments=None, error=None):
        self.segments = segments or []
        self.error = error
        self.audio_bytes = None
        self.options = None

    def transcribe(self, audio, **options):
        self.audio_bytes = audio.read()
        self.options = options
        if self.error:
            raise self.error
        return iter(self.segments), SimpleNamespace(language="pt")


def test_transcriber_returns_trimmed_portuguese_text_from_local_model() -> None:
    model = FakeWhisperModel([SimpleNamespace(text=" olá"), SimpleNamespace(text=", tudo bem? ")])
    transcriber = FasterWhisperTranscriber(model=model)

    assert transcriber.transcribe(b"audio bytes", "voice.ogg", "audio/ogg") == "olá, tudo bem?"
    assert model.audio_bytes == b"audio bytes"
    assert model.options["language"] == "pt"
    assert model.options["beam_size"] == 5


def test_transcriber_rejects_empty_audio() -> None:
    transcriber = FasterWhisperTranscriber(model=FakeWhisperModel())

    with pytest.raises(TranscriptionError, match="empty audio"):
        transcriber.transcribe(b"", "voice.ogg", "audio/ogg")


def test_transcriber_rejects_blank_result() -> None:
    model = FakeWhisperModel([SimpleNamespace(text="  ")])
    transcriber = FasterWhisperTranscriber(model=model)

    with pytest.raises(TranscriptionError, match="empty transcription"):
        transcriber.transcribe(b"audio", "voice.ogg", "audio/ogg")


def test_transcriber_wraps_local_model_errors() -> None:
    model = FakeWhisperModel(error=RuntimeError("model failed"))
    transcriber = FasterWhisperTranscriber(model=model)

    with pytest.raises(TranscriptionError, match="local transcription failed"):
        transcriber.transcribe(b"audio", "voice.ogg", "audio/ogg")
