import asyncio
from typing import Any, Callable, Dict, List
from app.utils.logger import get_logger

log = get_logger(__name__)


class EventBus:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._subscribers: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def publish(self, event_type: str, data: Dict[str, Any]):
        event = {"type": event_type, "data": data}
        for q in list(self._subscribers):
            try:
                await q.put(event)
            except Exception as e:
                log.warning(f"EventBus publish error: {e}")


event_bus = EventBus()
