import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventQueue:
    """In-process asynchronous event queue for scheduling and dispatching anomalies."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def put(self, event: dict[str, Any]) -> None:
        await self._queue.put(event)
        logger.info(f"Event enqueued: {event.get('type')}")

    async def get(self) -> dict[str, Any]:
        return await self._queue.get()

    def qsize(self) -> int:
        return self._queue.qsize()


event_queue = EventQueue()
