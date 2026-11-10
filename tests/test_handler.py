import pytest

from whatsapp_transcriber.handler import AudioMessageHandler, ProcessingError
from whatsapp_transcriber.repository import SQLiteRepository

PAYLOAD = {
    "event": "messages.upsert",
    "instance": "personal",
    "data": {
        "key": {"id": "msg-1", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
        "message": {"audioMessage": {"mimetype": "audio/ogg; codecs=opus", "ptt": True}},
        "messageType": "audioMessage",
    },
}


class FakeEvolution:
    def __init__(self, failure: str | None = None):
        self.calls = []
        self.failure = failure

    def download_audio(self, message_payload):
        self.calls.append(("download", message_payload))
        if self.failure == "download":
            self.failure = None
            raise RuntimeError("download failure")
        return b"voice bytes", "audio/ogg"

    def send_text(self, number, text):
        self.calls.append(("send", number, text))
        if self.failure == "send":
            self.failure = None
            raise RuntimeError("send failure")


class FakeTranscriber:
    def __init__(self, failure: bool = False):
        self.calls = []
        self.failure = failure

    def transcribe(self, audio, filename, mime_type):
        self.calls.append((audio, filename, mime_type))
        if self.failure:
            self.failure = False
            raise RuntimeError("transcription failure")
        return "bom dia"


def test_processes_audio_once_and_retries_completed_duplicate(tmp_path) -> None:
    repository = SQLiteRepository(str(tmp_path / "db.sqlite3"))
    repository.initialize()
    evolution = FakeEvolution()
    transcriber = FakeTranscriber()
    handler = AudioMessageHandler("personal", repository, evolution, transcriber)

    assert handler.process(PAYLOAD) is True
    assert handler.process(PAYLOAD) is False
    assert [call[0] for call in evolution.calls] == ["download", "send"]
    assert evolution.calls[1] == ("send", "5511999999999", "Transcrição: bom dia")
    assert repository.get_status("msg-1") == "done"


def test_ignores_non_audio_event(tmp_path) -> None:
    repository = SQLiteRepository(str(tmp_path / "db.sqlite3"))
    repository.initialize()
    evolution = FakeEvolution()
    handler = AudioMessageHandler("personal", repository, evolution, FakeTranscriber())

    assert handler.process({"event": "messages.delete"}) is False
    assert evolution.calls == []


@pytest.mark.parametrize("failure", ["download", "transcription", "send"])
def test_records_failure_and_allows_safe_retry(tmp_path, failure) -> None:
    repository = SQLiteRepository(str(tmp_path / "db.sqlite3"))
    repository.initialize()
    evolution = FakeEvolution(failure if failure != "transcription" else None)
    transcriber = FakeTranscriber(failure=failure == "transcription")
    handler = AudioMessageHandler("personal", repository, evolution, transcriber)

    with pytest.raises(ProcessingError):
        handler.process(PAYLOAD)

    assert repository.get_status("msg-1") == "error"
    assert handler.process(PAYLOAD) is True
    assert repository.get_status("msg-1") == "done"
