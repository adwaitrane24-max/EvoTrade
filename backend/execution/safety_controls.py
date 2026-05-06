"""
safety_controls.py — Runtime safety guardrails: daily loss limits, position caps, emergency stop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class SafetyState:
    """Mutable safety state updated on each trade event."""

    paused: bool = False
    emergency_stopped: bool = False
    daily_loss_pct: float = 0.0
    current_date: date = field(default_factory=date.today)
    trade_count_today: int = 0


class SafetyControls:
    """
    Enforces runtime trading safety rules.

    Checks:
    - Daily loss limit: halt trading if drawdown exceeds threshold.
    - Maximum position size: reject oversized orders.
    - Pause / emergency stop flags: honour manual overrides from the UI.

    Args:
        max_daily_loss_pct: Maximum tolerated daily loss as a fraction (e.g. 0.05 = 5 %).
        max_position_size_pct: Maximum single-trade position as fraction of capital.
    """

    def __init__(
        self,
        max_daily_loss_pct: float = 0.05,
        max_position_size_pct: float = 0.20,
    ) -> None:
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_position_size_pct = max_position_size_pct
        self._state = SafetyState()
        self._start_of_day_capital: float = 0.0

    def initialize(self, capital: float) -> None:
        """Record the starting capital for daily loss tracking."""
        self._start_of_day_capital = capital
        self._state.current_date = date.today()
        logger.info("Safety controls initialised. Capital: $%.2f", capital)

    def record_trade_result(self, current_capital: float) -> None:
        """
        Update daily loss tracking after each completed trade.

        Args:
            current_capital: Portfolio value after the trade.
        """
        today = date.today()
        if today != self._state.current_date:
            # New day: reset daily counters
            self._state.daily_loss_pct = 0.0
            self._state.trade_count_today = 0
            self._state.current_date = today
            self._start_of_day_capital = current_capital

        if self._start_of_day_capital > 0:
            loss = (self._start_of_day_capital - current_capital) / self._start_of_day_capital
            self._state.daily_loss_pct = max(0.0, loss)

        self._state.trade_count_today += 1

        if self._state.daily_loss_pct >= self.max_daily_loss_pct:
            logger.warning(
                "Daily loss limit reached (%.2f%%). Trading halted for today.",
                self._state.daily_loss_pct * 100,
            )
            self._state.paused = True

    def can_trade(self) -> tuple[bool, str]:
        """
        Return (allowed, reason) indicating whether a new trade is permissible.

        Returns:
            Tuple of (bool, explanation string).
        """
        if self._state.emergency_stopped:
            return False, "EMERGENCY STOP active"
        if self._state.paused:
            return False, f"Trading paused (daily loss = {self._state.daily_loss_pct:.1%})"
        return True, "OK"

    def validate_position_size(self, size_pct: float) -> float:
        """
        Clamp position size to the configured maximum.

        Args:
            size_pct: Requested position size as fraction of capital.

        Returns:
            Approved (possibly clamped) position size.
        """
        if size_pct > self.max_position_size_pct:
            logger.warning(
                "Position size %.1f%% exceeds max %.1f%%; clamping.",
                size_pct * 100, self.max_position_size_pct * 100,
            )
            return self.max_position_size_pct
        return size_pct

    def pause(self) -> None:
        """Pause live trading (can be resumed)."""
        self._state.paused = True
        logger.info("Trading paused by user.")

    def resume(self) -> None:
        """Resume live trading if not emergency-stopped."""
        if self._state.emergency_stopped:
            logger.warning("Cannot resume: emergency stop is active.")
            return
        self._state.paused = False
        logger.info("Trading resumed.")

    def emergency_stop(self) -> None:
        """Immediately halt all trading activity. Cannot be auto-resumed."""
        self._state.emergency_stopped = True
        self._state.paused = True
        logger.critical("EMERGENCY STOP triggered. All trading halted.")

    @property
    def state(self) -> SafetyState:
        return self._state


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sc = SafetyControls(max_daily_loss_pct=0.05)
    sc.initialize(capital=10_000)
    print("Can trade:", sc.can_trade())
    sc.record_trade_result(current_capital=9_400)  # 6 % loss → triggers pause
    print("Can trade after 6% loss:", sc.can_trade())
    sc.resume()
    print("After resume attempt:", sc.can_trade())
    sc.emergency_stop()
    print("After emergency stop:", sc.can_trade())
