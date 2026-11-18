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
        self._instance_token: str | None = None

    @staticmethod
    def _find_base64(obj: Any) -> str | None:
        if isinstance(obj, dict):
            for k in ("base64", "Base64"):
                val = obj.get(k)
                if isinstance(val, str) and len(val) > 0:
                    return val
            for v in obj.values():
                res = EvolutionClient._find_base64(v)
                if res:
                    return res
        return None

    @staticmethod
    def _find_mime_type(obj: Any) -> str:
        if isinstance(obj, dict):
            for k in ("mimetype", "mimeType", "Mimetype", "MimeType"):
                val = obj.get(k)
                if isinstance(val, str) and val.lower().startswith("audio/"):
                    return val
            for v in obj.values():
                res = EvolutionClient._find_mime_type(v)
                if res != "audio/ogg":
                    return res
        return "audio/ogg"

    def _get_instance_token(self) -> str:
        if self._instance_token:
            return self._instance_token
        try:
            res = self.http.get(f"{self.base_url}/instance/all", headers={"apikey": self._api_key})
            if res.status_code == 200:
                data = res.json().get("data", [])
                for inst in data:
                    if inst.get("name") == self.instance or inst.get("id") == self.instance:
                        self._instance_token = inst.get("token")
                        return self._instance_token
        except Exception:
            pass
        return self._api_key

    def download_audio(self, message_payload: dict[str, Any]) -> tuple[bytes, str]:
        try:
            encoded = self._find_base64(message_payload)
            mime_type = self._find_mime_type(message_payload)

            if not encoded:
                response = self.http.post(
                    f"{self.base_url}/chat/getBase64FromMediaMessage/{self.instance}",
                    headers={"apikey": self._api_key},
                    json={"message": message_payload},
                )
                response.raise_for_status()
                data = response.json()
                encoded = self._find_base64(data)
                mime_type = self._find_mime_type(data) or mime_type

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
            token = self._get_instance_token()
            try:
                response = self.http.post(
                    f"{self.base_url}/send/text",
                    headers={"apikey": token},
                    json={"number": number, "text": text},
                )
                if response.status_code != 404:
                    response.raise_for_status()
                    return
            except Exception as exc:
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code != 404:
                    raise

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
