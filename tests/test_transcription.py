from types import SimpleNamespace

import pytest

from whatsapp_transcriber.transcription import OpenAITranscriber, TranscriptionError


class FakeAudioTranscriptions:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.result


def test_transcriber_returns_trimmed_portuguese_text() -> None:
    audio = FakeAudioTranscriptions(SimpleNamespace(text="  olá, tudo bem?  "))
    transcriber = OpenAITranscriber(client=SimpleNamespace(audio=SimpleNamespace(transcriptions=audio)))

    assert transcriber.transcribe(b"audio", "voice.ogg", "audio/ogg") == "olá, tudo bem?"
    assert audio.kwargs["language"] == "pt"
    assert audio.kwargs["model"] == "whisper-1"


def test_transcriber_rejects_empty_audio() -> None:
    transcriber = OpenAITranscriber(client=SimpleNamespace())

    with pytest.raises(TranscriptionError, match="empty audio"):
        transcriber.transcribe(b"", "voice.ogg", "audio/ogg")


def test_transcriber_rejects_blank_result() -> None:
    audio = FakeAudioTranscriptions(SimpleNamespace(text="  "))
    transcriber = OpenAITranscriber(client=SimpleNamespace(audio=SimpleNamespace(transcriptions=audio)))

    with pytest.raises(TranscriptionError, match="empty transcription"):
        transcriber.transcribe(b"audio", "voice.ogg", "audio/ogg")


def test_transcriber_wraps_provider_errors() -> None:
    audio = FakeAudioTranscriptions(error=RuntimeError("provider down"))
    transcriber = OpenAITranscriber(client=SimpleNamespace(audio=SimpleNamespace(transcriptions=audio)))

    with pytest.raises(TranscriptionError, match="transcription provider failed"):
        transcriber.transcribe(b"audio", "voice.ogg", "audio/ogg")
