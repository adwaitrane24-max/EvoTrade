"""
Live market data service.
- Connects to Binance public WebSocket for BTC/USDT 1m klines (no API key needed)
- Maintains a rolling 500-candle buffer
- Broadcasts MARKET_TICK events via event_bus on each closed candle
- PAPER TRADING ONLY — no real money involved
"""
import asyncio
import json
import websockets
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, Any, Optional
import yfinance as yf
import pandas as pd

from app.config import BINANCE_WS_URL, CANDLE_BUFFER_SIZE, SYMBOL_YFINANCE
from app.utils.logger import get_logger

log = get_logger(__name__)


class MarketDataService:
    def __init__(self):
        self.candles: Deque[Dict[str, Any]] = deque(maxlen=CANDLE_BUFFER_SIZE)
        self.last_price: float = 0.0
        self.running: bool = False
        self._task: Optional[asyncio.Task] = None

    def get_candles(self, n: int = 200) -> list:
        return list(self.candles)[-n:]

    def get_last_price(self) -> float:
        return self.last_price

    async def load_historical(self):
        """Seed the buffer with yfinance historical data for cold-start indicators."""
        try:
            log.info("Loading historical BTC-USD data from yfinance...")
            df = yf.download(SYMBOL_YFINANCE, period="7d", interval="1m", progress=False, auto_adjust=True)
            if df.empty:
                log.warning("yfinance returned empty data, skipping historical seed")
                return
            # Flatten MultiIndex columns (yfinance >= 0.2.38 returns (field, ticker) tuples)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            for ts, row in df.iterrows():
                candle = {
                    "timestamp": int(ts.timestamp() * 1000),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                    "closed": True,
                }
                self.candles.append(candle)
            if self.candles:
                self.last_price = self.candles[-1]["close"]
            log.info(f"Seeded {len(self.candles)} historical candles")
        except Exception as e:
            log.warning(f"Historical data load failed: {e}")

    def load_historical_df(self, days: int = 90) -> pd.DataFrame:
        """Return OHLCV DataFrame for the specified number of days (1d interval)."""
        try:
            df = yf.download(SYMBOL_YFINANCE, period=f"{days}d", interval="1d", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except Exception as e:
            log.warning(f"yfinance download failed: {e}")
            return pd.DataFrame()

    async def start(self, event_bus):
        await self.load_historical()
        self.running = True
        self._task = asyncio.create_task(self._connect_loop(event_bus))
        log.info("MarketDataService started")

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()

    async def _connect_loop(self, event_bus):
        backoff = 1
        while self.running:
            try:
                await self._run_ws(event_bus)
                backoff = 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.warning(f"Binance WS error: {e}. Reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    async def _run_ws(self, event_bus):
        log.info(f"Connecting to Binance WS: {BINANCE_WS_URL}")
        async with websockets.connect(BINANCE_WS_URL, ping_interval=20, ping_timeout=10) as ws:
            backoff = 1
            async for raw in ws:
                if not self.running:
                    break
                try:
                    msg = json.loads(raw)
                    kline = msg.get("k", {})
                    candle = {
                        "timestamp": kline.get("t"),
                        "open": float(kline.get("o", 0)),
                        "high": float(kline.get("h", 0)),
                        "low": float(kline.get("l", 0)),
                        "close": float(kline.get("c", 0)),
                        "volume": float(kline.get("v", 0)),
                        "closed": kline.get("x", False),
                    }
                    self.last_price = candle["close"]

                    if candle["closed"]:
                        self.candles.append(candle)
                        await event_bus.publish("MARKET_TICK", candle)
                        log.info(f"MARKET_TICK BTC/USDT close={candle['close']:.2f}")
                except Exception as e:
                    log.warning(f"WS parse error: {e}")


market_data_service = MarketDataService()
