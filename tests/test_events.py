import pytest

from whatsapp_transcriber.events import parse_audio_event


@pytest.fixture
def audio_payload() -> dict:
    return {
        "event": "messages.upsert",
        "instance": "personal",
        "data": {
            "key": {"id": "wamid-123", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
            "message": {"audioMessage": {"mimetype": "audio/ogg; codecs=opus", "ptt": True}},
            "messageType": "audioMessage",
        },
    }


def test_parses_incoming_audio_event(audio_payload: dict) -> None:
    message = parse_audio_event(audio_payload, "personal")

    assert message is not None
    assert message.message_id == "wamid-123"
    assert message.remote_jid == "5511999999999@s.whatsapp.net"
    assert message.number == "5511999999999"
    assert message.from_me is False
    assert message.mime_type == "audio/ogg; codecs=opus"


def test_ignores_other_event(audio_payload: dict) -> None:
    audio_payload["event"] = "messages.delete"
    assert parse_audio_event(audio_payload, "personal") is None


def test_ignores_other_instance(audio_payload: dict) -> None:
    assert parse_audio_event(audio_payload, "another") is None


def test_ignores_own_messages(audio_payload: dict) -> None:
    audio_payload["data"]["key"]["fromMe"] = True
    assert parse_audio_event(audio_payload, "personal") is None


def test_ignores_group_messages(audio_payload: dict) -> None:
    audio_payload["data"]["key"]["remoteJid"] = "12345@g.us"
    assert parse_audio_event(audio_payload, "personal") is None


def test_ignores_non_audio_and_malformed_messages(audio_payload: dict) -> None:
    audio_payload["data"]["message"] = {"conversation": "hello"}
    assert parse_audio_event(audio_payload, "personal") is None
    assert parse_audio_event({"event": "messages.upsert"}, "personal") is None


def test_parses_evolution_go_conventions() -> None:
    payload = {
        "event": "messages_upsert",
        "instanceName": "personal",
        "data": {
            "key": {
                "id": "wamid-go-123",
                "remoteJID": "5511988887777@s.whatsapp.net",
                "from_me": False,
            },
            "message": {
                "audioMessage": {
                    "mimeType": "audio/ogg; codecs=opus",
                    "ptt": True,
                }
            },
        },
    }

    message = parse_audio_event(payload, "personal")

    assert message is not None
    assert message.message_id == "wamid-go-123"
    assert message.remote_jid == "5511988887777@s.whatsapp.net"
    assert message.number == "5511988887777"
    assert message.from_me is False
    assert message.mime_type == "audio/ogg; codecs=opus"


def test_parses_evolution_go_whatsmeow_message_event() -> None:
    payload = {
        "event": "Message",
        "instanceName": "personal",
        "data": {
            "Info": {
                "ID": "A5250E3CE0F575BE07F2B9024B65976A",
                "Chat": "5527992665692@s.whatsapp.net",
                "Sender": "125198296715452@lid",
                "SenderAlt": "5527992665692@s.whatsapp.net",
                "IsFromMe": False,
                "IsGroup": False,
                "Type": "media",
            },
            "Message": {
                "audioMessage": {
                    "mimetype": "audio/ogg; codecs=opus",
                    "ptt": True,
                },
                "base64": "inline-audio-base64",
            },
        },
    }

    message = parse_audio_event(payload, "personal")

    assert message is not None
    assert message.message_id == "A5250E3CE0F575BE07F2B9024B65976A"
    assert message.remote_jid == "5527992665692@s.whatsapp.net"
    assert message.number == "5527992665692"
    assert message.from_me is False
    assert message.mime_type == "audio/ogg; codecs=opus"


