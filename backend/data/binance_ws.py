"""
binance_ws.py — Binance WebSocket live price feed.
Streams real-time ticker updates and calls registered callbacks.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Optional

import websockets

logger = logging.getLogger(__name__)

# Binance public stream endpoint (no auth required for market data)
_WS_BASE = "wss://stream.binance.com:9443/ws"


class BinanceWebSocket:
    """
    Subscribes to a Binance mini-ticker stream and emits price ticks.

    Usage::

        feed = BinanceWebSocket("BTCUSDT")
        feed.add_callback(my_handler)
        await feed.start()
    """

    def __init__(self, symbol: str) -> None:
        """
        Args:
            symbol: Binance symbol WITHOUT slash, e.g. "BTCUSDT".
        """
        self.symbol = symbol.upper().replace("/", "")
        self._callbacks: list[Callable[[dict], None]] = []
        self._running = False
        self._ws: Optional[websockets.WebSocketClientProtocol] = None

    def add_callback(self, fn: Callable[[dict], None]) -> None:
        """Register a function to be called on each price tick."""
        self._callbacks.append(fn)

    async def start(self) -> None:
        """Open the WebSocket and begin streaming. Reconnects on disconnect."""
        self._running = True
        stream = f"{_WS_BASE}/{self.symbol.lower()}@miniTicker"
        logger.info("Connecting to Binance stream: %s", stream)

        while self._running:
            try:
                async with websockets.connect(stream) as ws:
                    self._ws = ws
                    logger.info("Binance WebSocket connected for %s", self.symbol)
                    async for raw in ws:
                        if not self._running:
                            break
                        await self._handle_message(raw)
            except (websockets.ConnectionClosed, OSError) as exc:
                if self._running:
                    logger.warning("WebSocket disconnected (%s). Reconnecting in 3s…", exc)
                    await asyncio.sleep(3)

    async def stop(self) -> None:
        """Gracefully close the stream."""
        self._running = False
        if self._ws:
            await self._ws.close()

    async def _handle_message(self, raw: str) -> None:
        """Parse incoming JSON and invoke registered callbacks."""
        try:
            data = json.loads(raw)
            tick = {
                "symbol": data.get("s"),
                "close": float(data.get("c", 0)),
                "open": float(data.get("o", 0)),
                "high": float(data.get("h", 0)),
                "low": float(data.get("l", 0)),
                "volume": float(data.get("v", 0)),
                "timestamp": data.get("E"),  # event time ms
            }
            for cb in self._callbacks:
                if asyncio.iscoroutinefunction(cb):
                    await cb(tick)
                else:
                    cb(tick)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.error("Failed to parse tick: %s — %s", raw[:120], exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def _demo() -> None:
        feed = BinanceWebSocket("BTCUSDT")

        async def printer(tick: dict) -> None:
            print(f"BTC price: ${tick['close']:,.2f}")

        feed.add_callback(printer)
        try:
            await asyncio.wait_for(feed.start(), timeout=10)
        except asyncio.TimeoutError:
            await feed.stop()
            print("Demo complete.")

    asyncio.run(_demo())
