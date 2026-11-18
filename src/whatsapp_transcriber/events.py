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
    raw_event = str(payload.get("event") or payload.get("eventType") or "")
    event = raw_event.replace("_", ".").lower()
    valid_events = {
        "messages.upsert",
        "messages_upsert",
        "message",
        "messages",
        "message.upsert",
    }
    if event not in valid_events:
        return None

    instance = (
        payload.get("instance")
        or payload.get("instanceName")
        or payload.get("instance_name")
    )
    if instance and instance != expected_instance:
        return None

    data = payload.get("data")
    if not isinstance(data, dict):
        return None

    info = data.get("Info") or data.get("info")
    key = data.get("key") or (info if isinstance(info, dict) else {})

    message_id = None
    if isinstance(key, dict):
        message_id = key.get("id") or key.get("ID")
    if not message_id and isinstance(info, dict):
        message_id = info.get("ID") or info.get("id")
    if not isinstance(message_id, str) or not message_id:
        return None

    from_me = None
    if isinstance(key, dict):
        if "fromMe" in key:
            from_me = key["fromMe"]
        elif "from_me" in key:
            from_me = key["from_me"]
        elif "IsFromMe" in key:
            from_me = key["IsFromMe"]
        elif "isFromMe" in key:
            from_me = key["isFromMe"]
    if from_me is None and isinstance(info, dict):
        from_me = info.get("IsFromMe", info.get("isFromMe", False))
    if from_me is not False:
        return None

    is_group = False
    if isinstance(info, dict):
        is_group = bool(info.get("IsGroup") or info.get("isGroup"))
    if is_group:
        return None

    remote_jid = None
    if isinstance(key, dict):
        remote_jid = (
            key.get("remoteJid")
            or key.get("remoteJID")
            or key.get("remoteJidAlt")
            or key.get("remoteJIDAlt")
            or key.get("Chat")
            or key.get("chat")
            or key.get("Sender")
            or key.get("sender")
        )
    if not remote_jid and isinstance(info, dict):
        remote_jid = (
            info.get("Chat")
            or info.get("chat")
            or info.get("SenderAlt")
            or info.get("senderAlt")
            or info.get("Sender")
            or info.get("sender")
        )
    if not isinstance(remote_jid, str) or not remote_jid:
        return None

    if remote_jid.endswith("@g.us"):
        return None

    # Handle @lid mapping if SenderAlt or alternative non-lid JID is present
    if remote_jid.endswith("@lid"):
        alt_jid = None
        if isinstance(key, dict):
            alt_jid = key.get("remoteJidAlt") or key.get("remoteJIDAlt") or key.get("SenderAlt")
        if not alt_jid and isinstance(info, dict):
            alt_jid = info.get("SenderAlt") or info.get("senderAlt") or info.get("Chat")
        if isinstance(alt_jid, str) and not alt_jid.endswith("@lid"):
            remote_jid = alt_jid

    number = remote_jid.split("@", 1)[0].split(":", 1)[0]
    if not number.isdigit():
        return None

    message = data.get("message") or data.get("Message")
    if not isinstance(message, dict):
        return None

    audio = message.get("audioMessage") or message.get("AudioMessage")
    if not isinstance(audio, dict):
        if "base64" in message or "base64" in data:
            m = (
                message.get("mimetype")
                or message.get("mimeType")
                or data.get("mimetype")
                or data.get("mimeType")
                or ""
            )
            if isinstance(m, str) and m.lower().startswith("audio/"):
                audio = message

    if not isinstance(audio, dict):
        return None

    mime_type = (
        audio.get("mimetype")
        or audio.get("mimeType")
        or audio.get("Mimetype")
        or audio.get("MimeType")
        or message.get("mimetype")
        or message.get("mimeType")
        or "audio/ogg"
    )
    if not isinstance(mime_type, str) or not mime_type.lower().startswith("audio/"):
        return None

    return IncomingAudio(
        message_id=message_id,
        remote_jid=remote_jid,
        number=number,
        from_me=False,
        mime_type=mime_type,
        audio_message=audio,
        key=key if isinstance(key, dict) else {},
        message_payload=data,
    )
