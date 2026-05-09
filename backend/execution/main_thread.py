"""
main_thread.py — Fast trade execution loop.
Loads the Alpha Gene, connects to Binance, and executes BUY/SELL/HOLD on each tick.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional

try:
    from binance.client import Client as BinanceClient  # type: ignore
except ImportError:
    BinanceClient = None  # type: ignore

from execution.alpha_gene_store import AlphaGeneStore
from execution.safety_controls import SafetyControls
from genetic.gene import Gene

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


class TradeRecord:
    """Immutable log entry for a completed trade action."""

    __slots__ = ("timestamp", "action", "price", "quantity", "reason")

    def __init__(self, action: str, price: float, quantity: float, reason: str) -> None:
        self.timestamp = datetime.utcnow().isoformat()
        self.action = action
        self.price = price
        self.quantity = quantity
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "price": self.price,
            "quantity": self.quantity,
            "reason": self.reason,
        }


class MainTradingThread:
    """
    Executes trades based on the Alpha Gene strategy.

    Subscribes to price ticks via the data feed, computes RSI + MA signals
    using the current gene parameters, and places orders through the Binance client.
    In demo mode (dry_run=True), orders are logged but not submitted.

    Args:
        api_key: Binance API key.
        api_secret: Binance API secret.
        symbol: Trading pair, e.g. "BTCUSDT".
        gene: Alpha Gene strategy parameters.
        safety: SafetyControls instance.
        initial_capital: Starting capital in USDT.
        dry_run: If True, simulate trades without real orders.
        event_callback: Async callback for streaming trade events to frontend.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        symbol: str,
        gene: Gene,
        safety: SafetyControls,
        initial_capital: float = 10_000.0,
        dry_run: bool = True,
        event_callback: Optional[EventCallback] = None,
    ) -> None:
        self.symbol = symbol.upper().replace("/", "")
        self.gene = gene
        self.safety = safety
        self.dry_run = dry_run
        self.event_callback = event_callback
        self.initial_capital = initial_capital

        self._client = None
        if not dry_run and BinanceClient is not None:
            self._client = BinanceClient(api_key, api_secret)

        self._prices: list[float] = []
        self._position: float = 0.0
        self._entry_price: float = 0.0
        self._capital: float = initial_capital
        self._trade_log: list[TradeRecord] = []

        self.safety.initialize(initial_capital)

    async def on_tick(self, tick: dict[str, Any]) -> None:
        """
        Process a single price tick from the data feed.

        Args:
            tick: Dict with at least 'close' (float) price.
        """
        price = float(tick.get("close", 0))
        if price <= 0:
            return

        self._prices.append(price)
        lookback = max(self.gene.ma_long + 5, self.gene.rsi_period + 5)
        if len(self._prices) > lookback * 2:
            self._prices = self._prices[-lookback * 2:]

        if len(self._prices) < self.gene.ma_long:
            return  # not enough history yet

        rsi = self._compute_rsi()
        ma_short = sum(self._prices[-self.gene.ma_short:]) / self.gene.ma_short
        ma_long  = sum(self._prices[-self.gene.ma_long:])  / self.gene.ma_long

        allowed, reason = self.safety.can_trade()
        if not allowed:
            logger.debug("Trade blocked: %s", reason)
            return

        action = self._decide(price, rsi, ma_short, ma_long)
        if action != "HOLD":
            await self._execute(action, price, rsi)

    def _decide(self, price: float, rsi: float, ma_short: float, ma_long: float) -> str:
        """Apply gene logic to determine BUY / SELL / HOLD."""
        if self._position == 0 and rsi < 30 and price > ma_short:
            return "BUY"
        if self._position > 0:
            pnl = (price - self._entry_price) / self._entry_price
            if rsi > 70 and price < ma_long:
                return "SELL"
            if pnl >= self.gene.take_profit_pct:
                return "SELL"
            if pnl <= -self.gene.stop_loss_pct:
                return "SELL"
        return "HOLD"

    async def _execute(self, action: str, price: float, rsi: float) -> None:
        """Submit (or simulate) a trade order."""
        size_pct = self.safety.validate_position_size(self.gene.position_size_pct)
        invest = self._capital * size_pct
        quantity = invest / price

        if action == "BUY":
            self._position = quantity
            self._entry_price = price
            self._capital -= invest
            reason = f"RSI={rsi:.1f}<30 price>MA_short"
        else:  # SELL
            pnl = (price - self._entry_price) * self._position
            self._capital += self._position * price
            reason = f"RSI={rsi:.1f} pnl={pnl:.2f}"
            self._position = 0.0
            self._entry_price = 0.0
            self.safety.record_trade_result(self._capital)

        record = TradeRecord(action, price, quantity, reason)
        self._trade_log.append(record)

        if not self.dry_run and self._client:
            try:
                if action == "BUY":
                    self._client.create_order(
                        symbol=self.symbol,
                        side="BUY",
                        type="MARKET",
                        quantity=round(quantity, 6),
                    )
                else:
                    self._client.create_order(
                        symbol=self.symbol,
                        side="SELL",
                        type="MARKET",
                        quantity=round(quantity, 6),
                    )
            except Exception as exc:
                logger.error("Binance order failed: %s", exc)
                return

        logger.info("[%s] %s %.6f @ $%.2f | %s", self.symbol, action, quantity, price, reason)

        if self.event_callback:
            await self.event_callback({
                "type": "trade",
                "data": record.to_dict(),
            })

    def _compute_rsi(self) -> float:
        """Compute RSI from internal price buffer."""
        period = self.gene.rsi_period
        if len(self._prices) < period + 1:
            return 50.0
        window = self._prices[-(period + 1):]
        deltas = [window[i + 1] - window[i] for i in range(period)]
        gains  = sum(d for d in deltas if d > 0) / period
        losses = sum(-d for d in deltas if d < 0) / period
        if losses == 0:
            return 100.0
        rs = gains / losses
        return 100 - 100 / (1 + rs)

    @property
    def trade_log(self) -> list[dict]:
        return [t.to_dict() for t in self._trade_log[-100:]]

    @property
    def portfolio_value(self) -> float:
        last_price = self._prices[-1] if self._prices else 0
        return self._capital + self._position * last_price


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def _demo() -> None:
        gene = Gene(rsi_period=14, ma_short=20, ma_long=50,
                    stop_loss_pct=0.03, take_profit_pct=0.06, position_size_pct=0.10)
        safety = SafetyControls()
        trader = MainTradingThread(
            api_key="", api_secret="", symbol="BTCUSDT",
            gene=gene, safety=safety, dry_run=True,
        )

        import random
        price = 50_000.0
        for _ in range(200):
            price *= (1 + random.gauss(0, 0.01))
            await trader.on_tick({"close": price})

        print(f"Final portfolio: ${trader.portfolio_value:,.2f}")
        print(f"Trades: {len(trader.trade_log)}")
        for t in trader.trade_log[-5:]:
            print(t)

    asyncio.run(_demo())
