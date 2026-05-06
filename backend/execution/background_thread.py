"""
background_thread.py — Daemon thread that polls Markov state every 60 seconds.
Triggers re-evolution when the market regime changes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

import pandas as pd

from processing.markov_detector import MarkovDetector

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]
ReEvolutionCallback = Callable[[], Awaitable[None]]


class BackgroundMonitor:
    """
    Continuously polls the Markov regime detector and fires callbacks on regime shifts.

    Runs as an asyncio background task (not a true OS thread) to integrate
    cleanly with the FastAPI event loop.

    Args:
        detector: Fitted MarkovDetector instance.
        get_recent_data: Async function returning recent (price, volume) Series pair.
        poll_interval: Seconds between regime checks.
        event_callback: Async callback for WebSocket regime events.
        re_evolution_callback: Async callback invoked on regime change.
    """

    def __init__(
        self,
        detector: MarkovDetector,
        get_recent_data: Callable[[], Awaitable[tuple[pd.Series, pd.Series]]],
        poll_interval: int = 60,
        event_callback: Optional[EventCallback] = None,
        re_evolution_callback: Optional[ReEvolutionCallback] = None,
    ) -> None:
        self._detector = detector
        self._get_data = get_recent_data
        self._poll_interval = poll_interval
        self._event_cb = event_callback
        self._re_evolution_cb = re_evolution_callback

        self._running = False
        self._current_regime: Optional[str] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background polling loop as an asyncio Task."""
        if self._running:
            logger.warning("BackgroundMonitor already running.")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="background_monitor")
        logger.info("BackgroundMonitor started (interval=%ds).", self._poll_interval)

    async def stop(self) -> None:
        """Gracefully stop the background loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("BackgroundMonitor stopped.")

    async def _loop(self) -> None:
        """Main polling loop: detect regime, compare to last known, fire callbacks."""
        while self._running:
            try:
                await self._check_regime()
            except Exception as exc:
                logger.error("Regime check failed: %s", exc)

            try:
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break

    async def _check_regime(self) -> None:
        """Detect current regime and emit event if it has changed."""
        prices, volumes = await self._get_data()
        new_regime = self._detector.detect(prices, volumes)

        if new_regime != self._current_regime:
            prev = self._current_regime or "unknown"
            logger.info("Regime shift: %s → %s", prev, new_regime)
            self._current_regime = new_regime

            if self._event_cb:
                await self._event_cb({
                    "type": "regime_change",
                    "previous": prev,
                    "current": new_regime,
                })

            if self._re_evolution_cb:
                logger.info("Triggering re-evolution due to regime shift.")
                asyncio.create_task(self._re_evolution_cb())
        else:
            logger.debug("Regime unchanged: %s", new_regime)

    @property
    def current_regime(self) -> Optional[str]:
        """The most recently detected market regime."""
        return self._current_regime


if __name__ == "__main__":
    import yfinance as yf
    logging.basicConfig(level=logging.INFO)

    async def _demo() -> None:
        df = yf.Ticker("BTC-USD").history(period="2y")
        detector = MarkovDetector()
        detector.fit(df["Close"], df["Volume"])

        async def get_data() -> tuple[pd.Series, pd.Series]:
            return df["Close"].tail(60), df["Volume"].tail(60)

        async def on_event(event: dict) -> None:
            print("Event:", event)

        async def on_re_evo() -> None:
            print("Re-evolution triggered!")

        monitor = BackgroundMonitor(
            detector=detector,
            get_recent_data=get_data,
            poll_interval=2,
            event_callback=on_event,
            re_evolution_callback=on_re_evo,
        )
        await monitor.start()
        await asyncio.sleep(6)
        await monitor.stop()

    asyncio.run(_demo())
