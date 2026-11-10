import hmac
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Header, HTTPException

from whatsapp_transcriber.config import Settings

WebhookHandler = Callable[[dict[str, Any]], None]


def create_app(
    settings: Settings | None = None,
    webhook_handler: WebhookHandler | None = None,
    repository: Any = None,
) -> FastAPI:
    app = FastAPI(title="WhatsApp Audio Transcriber")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict[str, str]:
        if repository is None or not repository.is_ready():
            raise HTTPException(status_code=503, detail="Database unavailable")
        return {"status": "ready"}

    @app.post("/webhooks/evolution")
    def evolution_webhook(
        payload: dict[str, Any],
        x_webhook_secret: str | None = Header(default=None),
    ) -> dict[str, str]:
        if settings is None:
            raise HTTPException(status_code=503, detail="Webhook configuration unavailable")
        expected = settings.webhook_secret.get_secret_value()
        if x_webhook_secret is None or not hmac.compare_digest(x_webhook_secret, expected):
            raise HTTPException(status_code=401, detail="Unauthorized")
        if webhook_handler is not None:
            try:
                webhook_handler(payload)
            except Exception as exc:
                raise HTTPException(status_code=500, detail="Webhook processing failed") from exc
        return {"status": "accepted"}

    return app
