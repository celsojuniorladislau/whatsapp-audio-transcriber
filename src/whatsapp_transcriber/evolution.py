import base64
import binascii
from typing import Any

import httpx


class EvolutionError(RuntimeError):
    pass


class EvolutionClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        instance: str,
        http_client: Any = None,
        max_audio_bytes: int = 20 * 1024 * 1024,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.instance = instance
        self.max_audio_bytes = max_audio_bytes
        self.http = http_client or httpx.Client(
            base_url=self.base_url,
            headers={"apikey": api_key},
            timeout=30.0,
        )
        self._api_key = api_key

    def download_audio(self, message_payload: dict[str, Any]) -> tuple[bytes, str]:
        try:
            response = self.http.post(
                f"{self.base_url}/chat/getBase64FromMediaMessage/{self.instance}",
                headers={"apikey": self._api_key},
                json={"message": message_payload},
            )
            response.raise_for_status()
            data = response.json()
            encoded = data.get("base64")
            mime_type = data.get("mimetype") or data.get("mimeType") or "audio/ogg"
            if not isinstance(encoded, str):
                raise TypeError("missing base64 field")
            if encoded.startswith("data:"):
                encoded = encoded.split(",", 1)[-1]
            audio = base64.b64decode(encoded, validate=True)
            if not audio:
                raise ValueError("empty audio")
            if len(audio) > self.max_audio_bytes:
                raise EvolutionError("audio exceeds configured limit")
            if not isinstance(mime_type, str) or not mime_type.startswith("audio/"):
                raise ValueError("invalid MIME type")
            return audio, mime_type
        except EvolutionError:
            raise
        except (httpx.HTTPError, ValueError, TypeError, binascii.Error) as exc:
            raise EvolutionError("invalid media response or Evolution API request failed") from exc

    def send_text(self, number: str, text: str) -> None:
        try:
            response = self.http.post(
                f"{self.base_url}/message/sendText/{self.instance}",
                headers={"apikey": self._api_key},
                json={"number": number, "text": text},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EvolutionError("Evolution API request failed") from exc

    def close(self) -> None:
        close = getattr(self.http, "close", None)
        if close:
            close()
