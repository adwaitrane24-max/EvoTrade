"""
websocket_handler.py — WebSocket connection manager: broadcasts events to all connected clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages a pool of active WebSocket connections.

    All connected clients receive every broadcast event.
    Stale connections are cleaned up on send failure.
    """

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        """Accept a new client WebSocket connection."""
        await ws.accept()
        self._connections.append(ws)
        logger.info("WebSocket client connected. Total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a client WebSocket from the pool."""
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("WebSocket client disconnected. Total: %d", len(self._connections))

    async def broadcast(self, event: dict[str, Any]) -> None:
        """
        Send an event to all connected clients.  Dead connections are pruned.

        Args:
            event: JSON-serializable dict with at least a 'type' key.
        """
        if not self._connections:
            return

        payload = json.dumps(event)
        dead: list[WebSocket] = []

        for ws in list(self._connections):
            try:
                await ws.send_text(payload)
            except Exception as exc:
                logger.debug("Failed to send to client: %s", exc)
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    async def handle_client(self, ws: WebSocket) -> None:
        """
        Accept and maintain a single client connection.
        Reads (and discards) any client-sent messages to keep the pipe alive.

        Args:
            ws: The FastAPI WebSocket instance for this client.
        """
        await self.connect(ws)
        try:
            while True:
                # Keep connection alive; ignore inbound messages
                await ws.receive_text()
        except WebSocketDisconnect:
            self.disconnect(ws)
        except Exception as exc:
            logger.warning("WebSocket client error: %s", exc)
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Singleton shared across all routers
ws_manager = WebSocketManager()
