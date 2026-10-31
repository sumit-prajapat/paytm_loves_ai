import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NotificationBus:
    """Manages proactive and interactive notifications across Soundbox, WhatsApp-style UI, and Push."""

    def __init__(self) -> None:
        # merchant_id -> list of WebSockets
        self.merchant_connections: dict[str, list[WebSocket]] = {}
        self.console_connections: list[WebSocket] = []

    async def connect_merchant(self, merchant_id: str, websocket: WebSocket) -> None:
        if websocket.client_state.name != "CONNECTED":
            await websocket.accept()
        if merchant_id not in self.merchant_connections:
            self.merchant_connections[merchant_id] = []
        self.merchant_connections[merchant_id].append(websocket)
        logger.info(f"Connected WebSocket for merchant '{merchant_id}'")

    def disconnect_merchant(self, merchant_id: str, websocket: WebSocket) -> None:
        if merchant_id in self.merchant_connections:
            if websocket in self.merchant_connections[merchant_id]:
                self.merchant_connections[merchant_id].remove(websocket)

    async def connect_console(self, websocket: WebSocket) -> None:
        if websocket.client_state.name != "CONNECTED":
            await websocket.accept()
        self.console_connections.append(websocket)
        logger.info("Connected WebSocket for Ops Console")

    def disconnect_console(self, websocket: WebSocket) -> None:
        if websocket in self.console_connections:
            self.console_connections.remove(websocket)

    async def send_notification(
        self,
        recipient_id: str,
        channel: str,  # soundbox | whatsapp_ui | push
        text: str,
        language: str = "hi",
        audio_url: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "type": "notification",
            "recipient_id": recipient_id,
            "channel": channel,
            "text": text,
            "language": language,
            "audio_url": audio_url,
            "extra": extra or {},
        }
        msg_str = json.dumps(payload, default=str)

        # 1. Send to merchant sockets
        if recipient_id in self.merchant_connections:
            for ws in list(self.merchant_connections[recipient_id]):
                try:
                    await ws.send_text(msg_str)
                except Exception:
                    self.disconnect_merchant(recipient_id, ws)

        # 2. Broadcast to Ops console
        for c_ws in list(self.console_connections):
            try:
                await c_ws.send_text(msg_str)
            except Exception:
                self.disconnect_console(c_ws)

        logger.info(f"Notification sent on channel '{channel}' to '{recipient_id}': '{text[:40]}...'")
        return {"status": "delivered", "channel": channel, "recipient_id": recipient_id}


notification_bus = NotificationBus()
