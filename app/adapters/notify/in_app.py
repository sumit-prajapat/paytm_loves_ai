"""In-app WebSocket fan-out (merchant channel + ops console).

R11: messages are only ever sent as the RESPONSE to a user trigger (a check-up, a Soundbox
button press, a chat turn) or to an ops action. There is no public push endpoint.
"""
import datetime
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NotificationBus:
    def __init__(self) -> None:
        self.merchant_connections: dict[str, list[WebSocket]] = {}
        self.console_connections: list[WebSocket] = []

    async def connect_merchant(self, merchant_id: str, websocket: WebSocket) -> None:
        if websocket.client_state.name != "CONNECTED":
            await websocket.accept()
        self.merchant_connections.setdefault(merchant_id, []).append(websocket)

    def disconnect_merchant(self, merchant_id: str, websocket: WebSocket) -> None:
        conns = self.merchant_connections.get(merchant_id, [])
        if websocket in conns:
            conns.remove(websocket)

    async def connect_console(self, websocket: WebSocket) -> None:
        if websocket.client_state.name != "CONNECTED":
            await websocket.accept()
        self.console_connections.append(websocket)

    def disconnect_console(self, websocket: WebSocket) -> None:
        if websocket in self.console_connections:
            self.console_connections.remove(websocket)

    @staticmethod
    def _envelope(event_type: str, payload: dict[str, Any]) -> str:
        return json.dumps(
            {"type": event_type, "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(), **payload},
            default=str,
            ensure_ascii=False,
        )

    async def push_merchant(self, merchant_id: str, event_type: str, payload: dict[str, Any]) -> int:
        """Send to the merchant's own sockets only. Returns number of sockets reached."""
        msg = self._envelope(event_type, {"merchant_id": merchant_id, **payload})
        sent = 0
        for ws in list(self.merchant_connections.get(merchant_id, [])):
            try:
                await ws.send_text(msg)
                sent += 1
            except Exception:
                self.disconnect_merchant(merchant_id, ws)
        return sent

    async def push_console(self, event_type: str, payload: dict[str, Any]) -> int:
        msg = self._envelope(event_type, payload)
        sent = 0
        for ws in list(self.console_connections):
            try:
                await ws.send_text(msg)
                sent += 1
            except Exception:
                self.disconnect_console(ws)
        return sent


notification_bus = NotificationBus()
