"""WebSocket gateway — single /ws endpoint, broadcasts all event_bus events."""
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.event_bus import event_bus
from app.utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[user_id] = ws
        log.info(f"WS connected: {user_id} (total={len(self._connections)})")

    def disconnect(self, user_id: str):
        self._connections.pop(user_id, None)
        log.info(f"WS disconnected: {user_id} (total={len(self._connections)})")

    async def send(self, user_id: str, message: dict):
        ws = self._connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id)

    async def broadcast(self, message: dict):
        disconnected = []
        for uid, ws in list(self._connections.items()):
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(uid)
        for uid in disconnected:
            self.disconnect(uid)


manager = ConnectionManager()


async def broadcaster():
    """Background task: reads from event_bus and broadcasts to all WS clients."""
    q = event_bus.subscribe()
    log.info("WS broadcaster started")
    try:
        while True:
            event = await q.get()
            msg = {
                "type": event["type"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": event["data"],
            }
            await manager.broadcast(msg)
    finally:
        event_bus.unsubscribe(q)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    user_id = "default"
    try:
        await ws.accept()
        # Wait for AUTH message
        try:
            raw = await asyncio.wait_for(ws.receive_text(), timeout=5.0)
            msg = json.loads(raw)
            if msg.get("type") == "AUTH":
                user_id = msg.get("user_id", "default")
        except asyncio.TimeoutError:
            pass

        # Replace with proper accepted connection tracking
        manager._connections[user_id] = ws
        log.info(f"WS authenticated: {user_id}")

        # Send system status immediately
        await ws.send_json({
            "type": "SYSTEM_STATUS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"status": "connected", "user_id": user_id},
        })

        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                msg = json.loads(raw)
                if msg.get("type") == "PING":
                    await ws.send_json({"type": "PONG", "timestamp": datetime.now(timezone.utc).isoformat()})
            except asyncio.TimeoutError:
                # Send health ping
                try:
                    await ws.send_json({"type": "SYSTEM_STATUS", "timestamp": datetime.now(timezone.utc).isoformat(), "data": {"status": "ok"}})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning(f"WS error for {user_id}: {e}")
    finally:
        manager.disconnect(user_id)
