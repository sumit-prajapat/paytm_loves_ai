import datetime
import json
import logging
import uuid
from typing import Any

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentRun
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


class TraceBus:
    """Central event and observability bus for streaming agent execution steps

    to WebSocket subscribers (Glass-box Console) and persisting them to the database.
    """

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        if websocket.client_state.name != "CONNECTED":
            await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "WebSocket client connected to /ws/trace",
            extra={"total_clients": len(self.active_connections)},
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                "WebSocket client disconnected from /ws/trace",
                extra={"total_clients": len(self.active_connections)},
            )

    async def broadcast_json(self, message: dict[str, Any]) -> None:
        """Broadcasts a JSON-serializable message to all connected clients."""
        payload = json.dumps(message, default=str)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning(f"Error streaming to WebSocket: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

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
    ) -> str:
        """Persists agent step to agent_runs and broadcasts to /ws/trace."""
        if not run_id:
            run_id = f"run_{uuid.uuid4().hex[:12]}"

        now = datetime.datetime.now(datetime.timezone.utc)

        # Step payload for streaming
        step_payload = {
            "type": "agent_step",
            "run_id": run_id,
            "case_id": case_id,
            "agent": agent,
            "tool": tool,
            "input": input_data,
            "output": output_data,
            "confidence": confidence,
            "ts": now.isoformat(),
        }

        # 1. Broadcast to WebSockets
        await self.broadcast_json(step_payload)

        # 2. Persist to agent_runs table
        agent_run = AgentRun(
            run_id=run_id,
            case_id=case_id,
            agent=agent,
            tool=tool,
            input=input_data if isinstance(input_data, (dict, list)) else {"raw": input_data},
            output=output_data if isinstance(output_data, (dict, list)) else {"raw": output_data},
            confidence=confidence,
            ts=now,
        )

        if db:
            db.add(agent_run)
            await db.commit()
        else:
            async with AsyncSessionLocal() as session:
                session.add(agent_run)
                await session.commit()

        logger.info(
            f"Step published for agent '{agent}' in case '{case_id}'",
            extra={"run_id": run_id, "confidence": confidence, "tool": tool},
        )
        return run_id


# Global Trace Bus singleton
trace_bus = TraceBus()
