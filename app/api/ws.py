import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.adapters.notify.in_app import notification_bus
from app.core.security import decode_token
from app.trace.bus import trace_bus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSockets"])


async def authenticate_websocket(websocket: WebSocket, required_roles: list[str] | None = None) -> dict | None:
    """Authenticates WebSocket connection via query param `?token=` or initial JSON message.

    Closes connection with 4001 (unauthenticated) or 4003 (forbidden) if invalid.
    """
    token = websocket.query_params.get("token")
    if not token:
        # Check if first message sends auth token
        await websocket.accept()
        try:
            msg = await asyncio.wait_for(websocket.receive_json(), timeout=2.0)
            token = msg.get("token") if isinstance(msg, dict) else None
        except Exception:
            token = None

        if not token:
            await websocket.close(code=4001, reason="Missing authentication token")
            return None

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid or expired access token")
        return None

    role = payload.get("role")
    if required_roles and role not in required_roles:
        await websocket.close(code=4003, reason=f"Forbidden: Role '{role}' not authorized")
        return None

    return payload


@router.websocket("/ws/trace")
async def websocket_trace_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming of multi-agent traces to Glass-box Console (Admin & Ops only)."""
    user = await authenticate_websocket(websocket, required_roles=["admin", "ops_agent"])
    if not user:
        return

    await trace_bus.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        trace_bus.disconnect(websocket)
    except asyncio.CancelledError:
        trace_bus.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket trace exception: {e}")
        trace_bus.disconnect(websocket)


@router.websocket("/ws/merchant/{merchant_id}")
async def websocket_merchant_endpoint(websocket: WebSocket, merchant_id: str):
    """WebSocket endpoint streaming Soundbox chimes and merchant chat notifications (IDOR protected)."""
    user = await authenticate_websocket(websocket)
    if not user:
        return

    role = user.get("role")
    user_merchant = user.get("merchant_id")
    if role == "merchant" and user_merchant != merchant_id:
        await websocket.close(code=4003, reason=f"IDOR Violation: Cannot subscribe to merchant '{merchant_id}'")
        return
    elif role not in ["merchant", "ops_agent", "admin"]:
        await websocket.close(code=4003, reason="Forbidden")
        return

    await notification_bus.connect_merchant(merchant_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        notification_bus.disconnect_merchant(merchant_id, websocket)
    except asyncio.CancelledError:
        notification_bus.disconnect_merchant(merchant_id, websocket)
    except Exception as e:
        logger.warning(f"Merchant WebSocket exception: {e}")
        notification_bus.disconnect_merchant(merchant_id, websocket)


@router.websocket("/ws/console")
async def websocket_console_endpoint(websocket: WebSocket):
    """WebSocket endpoint streaming human escalation queue and metrics updates to Ops Console (Ops & Admin only)."""
    user = await authenticate_websocket(websocket, required_roles=["admin", "ops_agent"])
    if not user:
        return

    await notification_bus.connect_console(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        notification_bus.disconnect_console(websocket)
    except asyncio.CancelledError:
        notification_bus.disconnect_console(websocket)
    except Exception as e:
        logger.warning(f"Console WebSocket exception: {e}")
        notification_bus.disconnect_console(websocket)
