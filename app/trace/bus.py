import datetime
import json
import logging
import uuid
from typing import Any

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import enforce_tool_allowed, mask_pii
from app.core.turn import current_turn
from app.db.models import AgentRun
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


def _mask(value: Any) -> Any:
    """Mask phone/Aadhaar/card/PIN patterns before anything is persisted or streamed."""
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, dict):
        return {k: _mask(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_mask(v) for v in value]
    return value


class TraceBus:
    """Glass-box trace: every agent step goes to agent_runs and to /ws/trace subscribers (R4)."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        if websocket.client_state.name != "CONNECTED":
            await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message, default=str, ensure_ascii=False)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception as exc:  # dropped client: remove and keep going
                logger.warning("Dropping trace WebSocket: %s", type(exc).__name__)
                self.disconnect(connection)

    async def publish_step(
        self,
        case_id: str,
        agent: str,
        tool: str | None = None,
        input_data: Any = None,
        output_data: Any = None,
        confidence: float = 1.0,
        run_id: str | None = None,
        db: AsyncSession | None = None,
        tier: int = 0,
        tokens: int = 0,
        cost_inr: float = 0.0,
        latency_ms: float = 0.0,
        event_type: str = "agent_step",
    ) -> str:
        """Persist one agent step and stream it. Raises ToolNotAllowed for denied tools (R3)."""
        enforce_tool_allowed(agent, tool)
        ctx = current_turn()
        if ctx is not None and agent != "llm_gateway":
            ctx.count_tool_call()
        run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now(datetime.timezone.utc)
        input_data, output_data = _mask(input_data), _mask(output_data)

        await self.broadcast_json({
            "type": event_type,
            "run_id": run_id,
            "case_id": case_id,
            "agent": agent,
            "tool": tool,
            "input": input_data,
            "output": output_data,
            "confidence": confidence,
            "cost_tier": tier,
            "tokens": tokens,
            "cost_inr": cost_inr,
            "latency_ms": round(latency_ms, 2),
            "ts": now.isoformat(),
        })

        agent_run = AgentRun(
            run_id=run_id,
            case_id=case_id,
            agent=agent,
            tool=tool,
            input=input_data if isinstance(input_data, (dict, list)) else {"raw": input_data},
            output=output_data if isinstance(output_data, (dict, list)) else {"raw": output_data},
            confidence=confidence,
            tier=tier,
            tokens=tokens,
            cost_inr=cost_inr,
            latency_ms=latency_ms,
            ts=now,
        )
        if db is not None:
            db.add(agent_run)
            await db.flush()  # caller owns the transaction; never commit it from here
        else:
            async with AsyncSessionLocal() as session:
                session.add(agent_run)
                await session.commit()
        return run_id


trace_bus = TraceBus()
