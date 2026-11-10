from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IncomingAudio:
    message_id: str
    remote_jid: str
    number: str
    from_me: bool
    mime_type: str
    audio_message: dict[str, Any]
    key: dict[str, Any]
    message_payload: dict[str, Any]


def parse_audio_event(payload: Any, expected_instance: str) -> IncomingAudio | None:
    if not isinstance(payload, dict):
        return None
    event = str(payload.get("event", "")).replace("_", ".").lower()
    if event != "messages.upsert" or payload.get("instance") != expected_instance:
        return None

    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    key = data.get("key")
    message = data.get("message")
    if not isinstance(key, dict) or not isinstance(message, dict):
        return None

    remote_jid = key.get("remoteJid")
    message_id = key.get("id")
    from_me = key.get("fromMe")
    if not isinstance(remote_jid, str) or not isinstance(message_id, str) or not message_id:
        return None
    if from_me is not False or remote_jid.endswith("@g.us"):
        return None
    number = remote_jid.split("@", 1)[0].split(":", 1)[0]
    if not number.isdigit():
        return None

    audio = message.get("audioMessage")
    if not isinstance(audio, dict):
        return None
    mime_type = audio.get("mimetype")
    if not isinstance(mime_type, str) or not mime_type.lower().startswith("audio/"):
        return None

    return IncomingAudio(
        message_id=message_id,
        remote_jid=remote_jid,
        number=number,
        from_me=False,
        mime_type=mime_type,
        audio_message=audio,
        key=key,
        message_payload=data,
    )
