import hmac
import ipaddress
import logging
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request

from whatsapp_transcriber.config import Settings

logger = logging.getLogger("whatsapp_transcriber")

WebhookHandler = Callable[[dict[str, Any]], None]


def create_app(
    settings: Settings | None = None,
    webhook_handler: WebhookHandler | None = None,
    repository: Any = None,
    lifespan: Any = None,
) -> FastAPI:
    app = FastAPI(title="WhatsApp Audio Transcriber", lifespan=lifespan)

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
        request: Request,
        x_webhook_secret: str | None = Header(default=None),
        token: str | None = Query(default=None),
        secret: str | None = Query(default=None),
    ) -> dict[str, str]:
        if settings is None:
            raise HTTPException(status_code=503, detail="Webhook configuration unavailable")
        expected = settings.webhook_secret.get_secret_value()
        provided = x_webhook_secret or token or secret
        if provided is not None:
            if not hmac.compare_digest(provided, expected):
                raise HTTPException(status_code=401, detail="Unauthorized")
        elif expected:
            # When caller does not send a secret, allow if request originates from trusted local/private network
            client_host = request.client.host if request.client else None
            is_internal = False
            if client_host:
                try:
                    is_internal = ipaddress.ip_address(client_host).is_private
                except ValueError:
                    is_internal = False
            if not is_internal:
                raise HTTPException(status_code=401, detail="Unauthorized")
        if webhook_handler is not None:
            logger.info(
                "Webhook received: event=%s instance=%s",
                payload.get("event") or payload.get("eventType"),
                payload.get("instanceName") or payload.get("instance"),
            )
            try:
                webhook_handler(payload)
            except Exception as exc:
                logger.error("Webhook handler raised error: %s", exc, exc_info=True)
                raise HTTPException(status_code=500, detail="Webhook processing failed") from exc
        return {"status": "accepted"}

    return app
