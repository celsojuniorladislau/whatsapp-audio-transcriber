import base64

import httpx
import pytest
import respx

from whatsapp_transcriber.evolution import EvolutionClient, EvolutionError

BASE_URL = "http://evolution.test"


@respx.mock
@pytest.mark.parametrize("encoded", [base64.b64encode(b"voice note").decode(), "data:audio/ogg;base64," + base64.b64encode(b"voice note").decode()])
def test_downloads_audio_using_message_data(encoded: str) -> None:
    route = respx.post(f"{BASE_URL}/chat/getBase64FromMediaMessage/personal").mock(
        return_value=httpx.Response(200, json={"base64": encoded, "mimetype": "audio/ogg"})
    )
    client = EvolutionClient(BASE_URL, "secret", "personal", max_audio_bytes=100)

    audio, mime_type = client.download_audio({"key": {"id": "m1"}, "message": {"audioMessage": {}}})

    assert audio == b"voice note"
    assert mime_type == "audio/ogg"
    assert route.calls[0].request.headers["apikey"] == "secret"
    assert route.calls[0].request.content == b'{"message":{"key":{"id":"m1"},"message":{"audioMessage":{}}}}'


@respx.mock
def test_send_text_uses_evolution_v2_contract() -> None:
    route = respx.post(f"{BASE_URL}/message/sendText/personal").mock(
        return_value=httpx.Response(201, json={"key": {"id": "reply-1"}})
    )
    client = EvolutionClient(BASE_URL, "secret", "personal")

    client.send_text("5511999999999", "Transcrição: olá")

    assert route.called
    assert route.calls[0].request.headers["apikey"] == "secret"
    assert route.calls[0].request.read() == b'{"number":"5511999999999","text":"Transcri\xc3\xa7\xc3\xa3o: ol\xc3\xa1"}'


@respx.mock
def test_send_text_uses_evolution_go_contract() -> None:
    respx.get(f"{BASE_URL}/instance/all").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"name": "personal", "token": "token-go-abc"}]},
        )
    )
    route = respx.post(f"{BASE_URL}/send/text").mock(
        return_value=httpx.Response(200, json={"message": "success"})
    )
    client = EvolutionClient(BASE_URL, "secret", "personal")

    client.send_text("5511999999999", "Transcrição: olá")

    assert route.called
    assert route.calls[0].request.headers["apikey"] == "token-go-abc"
    assert route.calls[0].request.read() == b'{"number":"5511999999999","text":"Transcri\xc3\xa7\xc3\xa3o: ol\xc3\xa1"}'


@respx.mock
def test_rejects_audio_over_limit() -> None:
    encoded = base64.b64encode(b"too long").decode()
    respx.post(f"{BASE_URL}/chat/getBase64FromMediaMessage/personal").mock(
        return_value=httpx.Response(200, json={"base64": encoded, "mimetype": "audio/ogg"})
    )
    client = EvolutionClient(BASE_URL, "secret", "personal", max_audio_bytes=3)

    with pytest.raises(EvolutionError, match="exceeds configured limit"):
        client.download_audio({"key": {"id": "m1"}})


@respx.mock
def test_rejects_malformed_media_response() -> None:
    respx.post(f"{BASE_URL}/chat/getBase64FromMediaMessage/personal").mock(
        return_value=httpx.Response(200, json={"base64": "not base64"})
    )
    client = EvolutionClient(BASE_URL, "secret", "personal")

    with pytest.raises(EvolutionError, match="invalid media response"):
        client.download_audio({"key": {"id": "m1"}})


@respx.mock
def test_wraps_http_errors_without_exposing_secret(caplog) -> None:
    respx.post(f"{BASE_URL}/message/sendText/personal").mock(return_value=httpx.Response(500))
    client = EvolutionClient(BASE_URL, "top-secret", "personal")

    with pytest.raises(EvolutionError, match="Evolution API request failed"):
        client.send_text("5511999999999", "text")

    assert "top-secret" not in caplog.text


@respx.mock
def test_downloads_audio_from_embedded_base64_without_http_call() -> None:
    route = respx.post(f"{BASE_URL}/chat/getBase64FromMediaMessage/personal").mock(
        return_value=httpx.Response(500)
    )
    client = EvolutionClient(BASE_URL, "secret", "personal")
    encoded = base64.b64encode(b"inline voice bytes").decode()

    # Embedded in audioMessage with mimeType (Evolution Go convention)
    payload = {
        "key": {"id": "m1"},
        "audioMessage": {
            "base64": encoded,
            "mimeType": "audio/ogg; codecs=opus",
        },
    }

    audio, mime_type = client.download_audio(payload)

    assert audio == b"inline voice bytes"
    assert mime_type == "audio/ogg; codecs=opus"
    assert not route.called


@respx.mock
def test_downloads_audio_using_nested_data_response() -> None:
    encoded = base64.b64encode(b"nested voice note").decode()
    route = respx.post(f"{BASE_URL}/chat/getBase64FromMediaMessage/personal").mock(
        return_value=httpx.Response(
            200,
            json={"data": {"base64": encoded, "mimeType": "audio/ogg"}},
        )
    )
    client = EvolutionClient(BASE_URL, "secret", "personal")

    audio, mime_type = client.download_audio({"key": {"id": "m2"}, "message": {"audioMessage": {}}})

    assert audio == b"nested voice note"
    assert mime_type == "audio/ogg"
    assert route.called


def test_client_close_closes_http_session() -> None:
    client = EvolutionClient(BASE_URL, "secret", "personal")
    assert not client.http.is_closed
    client.close()
    assert client.http.is_closed

