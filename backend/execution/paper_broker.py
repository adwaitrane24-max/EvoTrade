"""
paper_broker.py — Deterministic paper-trading simulator.

Conforms to the BrokerCallable interface required by SecureExecutionLayer:

    async def broker(intent: OrderIntent) -> dict

Models:
  • Maker/taker fees (bps)
  • Slippage envelope per the OrderIntent.risk.max_slippage_bps cap
  • Tracks balances + open positions in-memory (persisted to disk between runs)

Used in MVP and as the default for any environment without real broker keys.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.execution.secure_exec import OrderIntent

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Position:
    symbol: str
    qty: float                   # signed: + long, - short (MVP: long-only)
    avg_price: float
    opened_at: str
    last_update: str

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "avg_price": self.avg_price,
            "opened_at": self.opened_at,
            "last_update": self.last_update,
        }


@dataclass
class PortfolioState:
    cash_usdt: float = 10_000.0
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl_usdt: float = 0.0
    high_water_mark: float = 10_000.0
    fills: list[dict] = field(default_factory=list)

    def equity(self, mark_prices: dict[str, float]) -> float:
        eq = self.cash_usdt
        for sym, pos in self.positions.items():
            mp = mark_prices.get(sym, pos.avg_price)
            eq += pos.qty * mp
        return eq

    def to_dict(self) -> dict:
        return {
            "cash_usdt": self.cash_usdt,
            "positions": {s: p.to_dict() for s, p in self.positions.items()},
            "realized_pnl_usdt": self.realized_pnl_usdt,
            "high_water_mark": self.high_water_mark,
            "fills": self.fills[-100:],  # last 100
        }


# ──────────────────────────────────────────────────────────────────────────────
# Broker
# ──────────────────────────────────────────────────────────────────────────────

_STATE_FILE = Path(__file__).parent.parent.parent / "outputs" / "paper_broker_state.json"


class PaperBroker:
    """
    Synchronous-style paper broker exposed as an async callable.

    Slippage:
      - We simulate price impact within `intent.risk.max_slippage_bps` (default 10 bps).
      - BUY fills slightly above mark, SELL slightly below — to mimic taker.
    Fees:
      - taker_bps = 10 (0.10%); maker_bps = 5 (kept for future LIMIT orders).
    """

    def __init__(
        self,
        starting_cash: float = 10_000.0,
        taker_bps: int = 10,
        maker_bps: int = 5,
        state_path: Path = _STATE_FILE,
    ) -> None:
        self.taker_bps = taker_bps
        self.maker_bps = maker_bps
        self.state_path = state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self.state: PortfolioState = self._load_state(starting_cash)

    # ── persistence ──────────────────────────────────────────────────────────

    def _load_state(self, starting_cash: float) -> PortfolioState:
        if not self.state_path.exists():
            return PortfolioState(cash_usdt=starting_cash, high_water_mark=starting_cash)
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            positions = {
                s: Position(**p) for s, p in (data.get("positions") or {}).items()
            }
            return PortfolioState(
                cash_usdt=float(data.get("cash_usdt", starting_cash)),
                positions=positions,
                realized_pnl_usdt=float(data.get("realized_pnl_usdt", 0.0)),
                high_water_mark=float(data.get("high_water_mark", starting_cash)),
                fills=list(data.get("fills") or []),
            )
        except Exception as exc:
            logger.warning("PaperBroker state load failed: %s — starting fresh", exc)
            return PortfolioState(cash_usdt=starting_cash, high_water_mark=starting_cash)

    def _persist(self) -> None:
        self.state_path.write_text(
            json.dumps(self.state.to_dict(), indent=2), encoding="utf-8"
        )

    # ── core entry point ─────────────────────────────────────────────────────

    async def __call__(self, intent: OrderIntent) -> dict:
        return await self.place_order(intent)

    async def place_order(self, intent: OrderIntent) -> dict:
        """
        Execute a paper order. Returns a fill dict shaped like a real broker.
        """
        async with self._lock:
            mark = float(intent.metadata.get("price") or 0.0)
            if mark <= 0:
                return {"status": "rejected", "reason": "missing_mark_price"}

            fee_rate = self.taker_bps / 10_000.0
            slip_cap = float(intent.risk.get("max_slippage_bps") or 10) / 10_000.0
            slip_dir = +1 if intent.side == "BUY" else -1
            slip_used = slip_cap * 0.5  # use half the budget on average
            fill_price = mark * (1.0 + slip_dir * slip_used)

            qty = float(intent.qty)
            if qty <= 0:
                return {"status": "rejected", "reason": "non_positive_qty"}

            notional = qty * fill_price
            fee = notional * fee_rate

            sym = intent.symbol
            pos = self.state.positions.get(sym)

            # ── BUY ──────────────────────────────────────────────────────────
            if intent.side == "BUY":
                cost = notional + fee
                if cost > self.state.cash_usdt:
                    return {"status": "rejected", "reason": "insufficient_cash",
                            "needed": round(cost, 4),
                            "available": round(self.state.cash_usdt, 4)}
                self.state.cash_usdt -= cost

                if pos and pos.qty > 0:
                    new_qty = pos.qty + qty
                    pos.avg_price = (pos.avg_price * pos.qty + fill_price * qty) / new_qty
                    pos.qty = new_qty
                    pos.last_update = datetime.now(timezone.utc).isoformat()
                else:
                    self.state.positions[sym] = Position(
                        symbol=sym, qty=qty, avg_price=fill_price,
                        opened_at=datetime.now(timezone.utc).isoformat(),
                        last_update=datetime.now(timezone.utc).isoformat(),
                    )

            # ── SELL ─────────────────────────────────────────────────────────
            elif intent.side == "SELL":
                if not pos or pos.qty <= 0:
                    return {"status": "rejected", "reason": "no_long_position"}
                close_qty = min(qty, pos.qty)
                gross = close_qty * fill_price
                trade_pnl = (fill_price - pos.avg_price) * close_qty - fee
                self.state.cash_usdt += gross - fee
                self.state.realized_pnl_usdt += trade_pnl
                pos.qty -= close_qty
                pos.last_update = datetime.now(timezone.utc).isoformat()
                if pos.qty <= 1e-12:
                    del self.state.positions[sym]
            else:
                return {"status": "rejected", "reason": f"bad_side:{intent.side}"}

            equity = self.state.cash_usdt + sum(
                p.qty * fill_price for p in self.state.positions.values()
            )
            if equity > self.state.high_water_mark:
                self.state.high_water_mark = equity

            fill = {
                "broker_order_id": f"paper-{uuid.uuid4()}",
                "status": "filled",
                "ts": datetime.now(timezone.utc).isoformat(),
                "symbol": sym,
                "side": intent.side,
                "type": intent.type,
                "qty": round(qty, 8),
                "fill_price": round(fill_price, 4),
                "mark_price": round(mark, 4),
                "fee_usdt": round(fee, 4),
                "slip_bps_used": round(slip_used * 10_000, 2),
                "cash_usdt": round(self.state.cash_usdt, 4),
                "equity_usdt": round(equity, 4),
                "realized_pnl_usdt": round(self.state.realized_pnl_usdt, 4),
                "strategy_id": intent.metadata.get("strategy_id"),
                "regime": intent.metadata.get("regime"),
            }
            self.state.fills.append(fill)
            self._persist()

            # Supabase mirror (best-effort)
            try:
                from persistence.supabase_client import supabase
                strategy_id = fill.get("strategy_id")
                asyncio.create_task(supabase().insert_trade(
                    fill=fill, strategy_id=strategy_id,
                ))
                if sym in self.state.positions:
                    pos = self.state.positions[sym]
                    asyncio.create_task(supabase().upsert_position(
                        symbol=sym, qty=float(pos.qty),
                        avg_price=float(pos.avg_price), is_paper=True,
                    ))
            except Exception:
                pass
            return fill

    # ── read API ─────────────────────────────────────────────────────────────

    def get_portfolio(self) -> dict:
        return self.state.to_dict()

    def get_equity(self, last_prices: Optional[dict[str, float]] = None) -> float:
        prices = last_prices or {s: p.avg_price for s, p in self.state.positions.items()}
        return self.state.equity(prices)

    def reset(self, starting_cash: float = 10_000.0) -> None:
        self.state = PortfolioState(cash_usdt=starting_cash, high_water_mark=starting_cash)
        self._persist()


# ──────────────────────────────────────────────────────────────────────────────
# CLI smoke
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def _demo():
        broker = PaperBroker(starting_cash=10_000.0)
        broker.reset(10_000.0)
        intents = [
            OrderIntent(user_id="u1", symbol="BTCUSDT", side="BUY", type="MARKET",
                         qty=0.05, risk={"max_slippage_bps": 10},
                         metadata={"price": 50_000, "strategy_id": "demo"}),
            OrderIntent(user_id="u1", symbol="BTCUSDT", side="SELL", type="MARKET",
                         qty=0.02, risk={"max_slippage_bps": 10},
                         metadata={"price": 51_000, "strategy_id": "demo"}),
        ]
        for it in intents:
            r = await broker.place_order(it)
            print(r)
        print("\nPortfolio:", json.dumps(broker.get_portfolio(), indent=2))

    asyncio.run(_demo())
