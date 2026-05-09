"""
Paper trading engine.
Executes trades against live Binance price data.
PAPER TRADING ONLY — no real money, no broker connection.
"""
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.utils.logger import get_logger
from app.services.indicators import compute_indicators

log = get_logger(__name__)


class PaperTrader:
    def __init__(self):
        self.running: bool = False
        self.paused: bool = False
        self.alpha_gene: Optional[Dict[str, float]] = None
        self.capital: float = 50000.0
        self.initial_capital: float = 50000.0
        self.daily_start_capital: float = 50000.0
        self.position: Optional[Dict[str, Any]] = None
        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[float] = []
        self._task: Optional[asyncio.Task] = None
        self.session_id: str = ""

    def get_portfolio(self) -> Dict[str, Any]:
        closed_trades = [t for t in self.trades if t.get("pnl") is not None]
        wins = [t for t in closed_trades if t["pnl"] > 0]
        total_pnl = sum(t["pnl"] for t in closed_trades)
        daily_pnl = self.capital - self.daily_start_capital + (
            self.position["qty"] * self._last_price - self.position["qty"] * self.position["entry_price"]
            if self.position else 0
        )
        equity = self.capital + (
            self.position["qty"] * self._last_price if self.position else 0
        )
        win_rate = len(wins) / max(len(closed_trades), 1)
        return {
            "cash": self.capital,
            "position": self.position,
            "trades": self.trades[-50:],
            "equity_curve": self.equity_curve[-200:],
            "total_pnl": total_pnl,
            "daily_pnl": daily_pnl,
            "win_rate": win_rate,
            "wins": len(wins),
            "total_closed": len(closed_trades),
            "equity": equity,
        }

    def start(self, alpha_gene: Dict[str, float], capital: float, session_id: str, event_bus, market_service):
        self.alpha_gene = alpha_gene
        self.capital = capital
        self.initial_capital = capital
        self.daily_start_capital = capital
        self.session_id = session_id
        self._last_price = 0.0
        self.running = True
        self.paused = False
        self._event_bus = event_bus
        self._market = market_service
        self._task = asyncio.create_task(self._trading_loop())
        log.info(f"PaperTrader started — session {session_id}, capital={capital}")

    def pause(self):
        self.paused = True
        log.info("PaperTrader paused")

    def resume(self):
        self.paused = False
        log.info("PaperTrader resumed")

    async def emergency_stop(self):
        """Close all open positions at last known price."""
        if self.position and self._last_price > 0:
            pnl = (self._last_price - self.position["entry_price"]) * self.position["qty"]
            self.capital += self.position["qty"] * self._last_price
            trade = self._make_trade("SELL", self.position["qty"], self._last_price, pnl, "emergency_stop")
            self.trades.append(trade)
            self.position = None
            await self._event_bus.publish("TRADE_EXECUTED", trade)
        self.running = False
        if self._task:
            self._task.cancel()
        log.info("PaperTrader emergency stop executed")

    async def _trading_loop(self):
        # Subscribe to market ticks
        q = self._event_bus.subscribe()
        try:
            portfolio_tick = 0
            while self.running:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Emit portfolio update every ~5 seconds even if no tick
                    await self._event_bus.publish("PORTFOLIO_UPDATE", self.get_portfolio())
                    continue

                if event["type"] != "MARKET_TICK":
                    continue
                if self.paused:
                    continue

                candle = event["data"]
                price = float(candle["close"])
                self._last_price = price
                self.equity_curve.append(self.capital + (self.position["qty"] * price if self.position else 0))

                # Compute indicators
                candles = self._market.get_candles(250)
                g = self.alpha_gene
                indicators = compute_indicators(
                    candles,
                    ma_short=int(g.get("ma_short", 9)),
                    ma_long=int(g.get("ma_long", 21)),
                )

                signal = self._generate_signal(indicators, price)

                if signal == "BUY" and self.position is None:
                    invest = self.capital * g.get("position_size_pct", 0.20)
                    qty = invest / price
                    self.capital -= invest
                    self.position = {"qty": qty, "entry_price": price}
                    trade = self._make_trade("BUY", qty, price, None, "rsi_oversold")
                    self.trades.append(trade)
                    await self._event_bus.publish("TRADE_EXECUTED", trade)
                    log.info(f"BUY {qty:.6f} BTC @ {price:.2f}")

                elif self.position is not None:
                    pct = (price - self.position["entry_price"]) / self.position["entry_price"]
                    reason = None
                    if pct <= -g.get("stop_loss_pct", 0.02):
                        reason = "stop_loss"
                    elif pct >= g.get("take_profit_pct", 0.04):
                        reason = "take_profit"
                    elif signal == "SELL":
                        reason = "rsi_overbought"

                    if reason:
                        pnl = (price - self.position["entry_price"]) * self.position["qty"]
                        self.capital += self.position["qty"] * price
                        trade = self._make_trade("SELL", self.position["qty"], price, pnl, reason)
                        self.trades.append(trade)
                        self.position = None
                        await self._event_bus.publish("TRADE_EXECUTED", trade)
                        log.info(f"SELL @ {price:.2f} pnl={pnl:.2f} reason={reason}")

                # Portfolio broadcast every 5 ticks
                portfolio_tick += 1
                if portfolio_tick >= 5:
                    portfolio_tick = 0
                    await self._event_bus.publish("PORTFOLIO_UPDATE", self.get_portfolio())

        finally:
            self._event_bus.unsubscribe(q)

    def _generate_signal(self, indicators: Dict[str, Any], price: float) -> str:
        g = self.alpha_gene
        rsi = indicators.get("rsi", 50)
        ma_s = indicators.get("ma_short", 0)
        ma_l = indicators.get("ma_long", 0)

        rsi_os = g.get("rsi_oversold", 30)
        rsi_ob = g.get("rsi_overbought", 70)

        if rsi < rsi_os and (ma_s == 0 or ma_l == 0 or ma_s > ma_l):
            return "BUY"
        if rsi > rsi_ob and (ma_s == 0 or ma_l == 0 or ma_s < ma_l):
            return "SELL"
        return "HOLD"

    def _make_trade(self, side: str, qty: float, price: float, pnl: Optional[float], reason: str) -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "side": side,
            "qty": round(qty, 6),
            "price": round(price, 2),
            "pnl": round(pnl, 4) if pnl is not None else None,
            "reason": reason,
        }


paper_trader = PaperTrader()
