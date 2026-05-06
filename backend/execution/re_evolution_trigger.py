"""
re_evolution_trigger.py — Triggers a background re-evolution run when regime shifts.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

import pandas as pd

from execution.alpha_gene_store import AlphaGeneStore
from genetic.evolution_engine import EvolutionEngine
from genetic.gene import Gene

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


class ReEvolutionTrigger:
    """
    Orchestrates a fresh evolution run when the background monitor detects a regime shift.

    After a new Alpha Gene is found, it is persisted via AlphaGeneStore and
    the active trading thread is hot-swapped to the new gene without interruption.

    Args:
        gene_store: Persistent Alpha Gene store.
        price_df_getter: Async callable that returns the latest historical DataFrame.
        risk_profile: Risk profile for the new population.
        event_callback: Async callback for WebSocket progress events.
        on_new_gene: Async callback invoked when a new Alpha Gene is ready.
    """

    def __init__(
        self,
        gene_store: AlphaGeneStore,
        price_df_getter: Callable[[], Awaitable[pd.DataFrame]],
        risk_profile: str = "medium",
        event_callback: Optional[EventCallback] = None,
        on_new_gene: Optional[Callable[[Gene], Awaitable[None]]] = None,
    ) -> None:
        self._store = gene_store
        self._get_price_df = price_df_getter
        self._risk_profile = risk_profile
        self._event_cb = event_callback
        self._on_new_gene = on_new_gene
        self._running = False

    async def trigger(self) -> None:
        """
        Start a re-evolution run.  If one is already in progress, skip this call.
        """
        if self._running:
            logger.info("Re-evolution already in progress; skipping duplicate trigger.")
            return

        self._running = True
        logger.info("Re-evolution triggered.")

        try:
            if self._event_cb:
                await self._event_cb({"type": "re_evolution_started"})

            price_df = await self._get_price_df()
            engine = EvolutionEngine(
                price_df=price_df,
                risk_profile=self._risk_profile,
                max_generations=30,
                event_callback=self._event_cb,
            )
            result = await engine.run()
            new_gene = result.alpha_gene

            self._store.save(new_gene)
            logger.info(
                "Re-evolution complete. New Alpha Gene fitness=%.4f (converged=%s)",
                new_gene.fitness,
                result.converged,
            )

            if self._on_new_gene:
                await self._on_new_gene(new_gene)

            if self._event_cb:
                await self._event_cb({
                    "type": "re_evolution_complete",
                    "new_gene": new_gene.to_dict(),
                    "fitness": new_gene.fitness,
                    "converged": result.converged,
                })

        except Exception as exc:
            logger.error("Re-evolution failed: %s", exc)
            if self._event_cb:
                await self._event_cb({"type": "re_evolution_error", "error": str(exc)})
        finally:
            self._running = False

    @property
    def is_running(self) -> bool:
        """True if a re-evolution is currently in progress."""
        return self._running


if __name__ == "__main__":
    import yfinance as yf
    logging.basicConfig(level=logging.INFO)

    async def _demo() -> None:
        store = AlphaGeneStore()
        df = yf.Ticker("BTC-USD").history(period="1y")

        async def get_df() -> pd.DataFrame:
            return df

        async def on_event(event: dict) -> None:
            if event.get("type") in ("re_evolution_complete", "generation_complete"):
                print(event)

        async def on_new_gene(gene: Gene) -> None:
            print("Hot-swap to gene:", gene.to_dict())

        trigger = ReEvolutionTrigger(
            gene_store=store,
            price_df_getter=get_df,
            event_callback=on_event,
            on_new_gene=on_new_gene,
        )
        await trigger.trigger()

    asyncio.run(_demo())
