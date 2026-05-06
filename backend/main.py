"""
main.py — FastAPI application entry point and lifecycle manager.

Wires together evolution engine, trading thread, background monitor,
and WebSocket broadcaster into a single cohesive async application.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend package is importable when run directly
sys.path.insert(0, str(Path(__file__).parent))

from api.routes import app_state, router
from api.websocket_handler import ws_manager
from config import config
from data.yfinance_loader import YFinanceLoader
from execution.alpha_gene_store import AlphaGeneStore
from execution.background_thread import BackgroundMonitor
from execution.main_thread import MainTradingThread
from execution.re_evolution_trigger import ReEvolutionTrigger
from execution.safety_controls import SafetyControls
from genetic.evolution_engine import EvolutionEngine
from genetic.gene import Gene
from processing.markov_detector import MarkovDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("evotrade.main")

# ── Module-level singletons ───────────────────────────────────────────────────

gene_store = AlphaGeneStore()
safety = SafetyControls(
    max_daily_loss_pct=config.MAX_DAILY_LOSS_PCT,
    max_position_size_pct=config.MAX_POSITION_SIZE_PCT,
)


# ── Event broadcaster helper ──────────────────────────────────────────────────

async def _broadcast(event: dict) -> None:
    await ws_manager.broadcast(event)
    # Mirror certain events into app_state for /status endpoint
    if event.get("type") == "generation_complete":
        app_state.fitness_history.append(event["best_fitness"])
        app_state.current_gene = event.get("best_gene")
    elif event.get("type") == "regime_change":
        app_state.current_regime = event.get("current")
    elif event.get("type") == "re_evolution_complete":
        app_state.current_gene = event.get("new_gene")


# ── Evolution + execution launcher ────────────────────────────────────────────

async def _launch_evolution_and_trading() -> None:
    """
    Full pipeline:
    1. Load historical data.
    2. Fit Markov detector.
    3. Run GA evolution.
    4. Start live trading thread.
    5. Start background regime monitor.
    """
    try:
        loader = YFinanceLoader(app_state.symbol)
        df = loader.fetch(period_days=730)
        logger.info("Loaded %d bars for %s", len(df), app_state.symbol)

        # ── Fit Markov detector ───────────────────────────────────────────────
        detector = MarkovDetector()
        detector.fit(df["Close"], df["Volume"])
        app_state.current_regime = detector.detect(df["Close"].tail(60), df["Volume"].tail(60))
        await _broadcast({"type": "regime_detected", "regime": app_state.current_regime})

        # ── Run initial evolution ─────────────────────────────────────────────
        await _broadcast({"type": "evolution_started"})
        engine = EvolutionEngine(
            price_df=df,
            risk_profile=app_state.risk_profile,
            max_generations=config.GA_MAX_GENERATIONS,
            convergence_window=config.GA_CONVERGENCE_WINDOW,
            event_callback=_broadcast,
        )
        result = await engine.run()
        alpha_gene = result.alpha_gene
        gene_store.save(alpha_gene)
        app_state.current_gene = alpha_gene.to_dict()

        await _broadcast({
            "type": "evolution_complete",
            "gene": alpha_gene.to_dict(),
            "fitness": alpha_gene.fitness,
        })

        # ── Start trading thread ──────────────────────────────────────────────
        binance_key    = getattr(config, "BINANCE_API_KEY", "")
        binance_secret = getattr(config, "BINANCE_API_SECRET", "")
        symbol_raw = app_state.symbol.replace("/", "")

        trader = MainTradingThread(
            api_key=binance_key,
            api_secret=binance_secret,
            symbol=symbol_raw,
            gene=alpha_gene,
            safety=safety,
            initial_capital=app_state.initial_capital,
            dry_run=True,  # switch to False only with real credentials
            event_callback=_broadcast,
        )
        app_state.trader = trader

        # ── Background regime monitor ─────────────────────────────────────────
        async def get_recent_data():
            fresh = loader.fetch(period_days=90)
            return fresh["Close"].tail(60), fresh["Volume"].tail(60)

        async def on_new_gene(gene: Gene) -> None:
            app_state.current_gene = gene.to_dict()
            if app_state.trader:
                app_state.trader.gene = gene  # hot-swap

        re_trigger = ReEvolutionTrigger(
            gene_store=gene_store,
            price_df_getter=lambda: asyncio.coroutine(lambda: loader.fetch(period_days=730))(),
            risk_profile=app_state.risk_profile,
            event_callback=_broadcast,
            on_new_gene=on_new_gene,
        )

        monitor = BackgroundMonitor(
            detector=detector,
            get_recent_data=get_recent_data,
            poll_interval=60,
            event_callback=_broadcast,
            re_evolution_callback=re_trigger.trigger,
        )
        app_state.monitor = monitor
        await monitor.start()

    except Exception as exc:
        logger.exception("Evolution/trading pipeline failed: %s", exc)
        await _broadcast({"type": "error", "message": str(exc)})
        app_state.running = False


# ── FastAPI lifecycle ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("EvoTrade backend starting up…")
    yield
    logger.info("EvoTrade backend shutting down…")
    if app_state.monitor:
        await app_state.monitor.stop()


app = FastAPI(
    title="EvoTrade API",
    description="Genetic Algorithm trading bot with Multi-Agent Council",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Stream real-time events to connected frontend clients."""
    await ws_manager.handle_client(ws)


# Override /start to actually launch the pipeline
@app.post("/start", include_in_schema=False)
async def _start_override() -> dict:
    from api.routes import app_state as _state
    if _state.running:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Already running.")
    _state.running = True
    task = asyncio.create_task(_launch_evolution_and_trading())
    _state.evolution_task = task
    return {"status": "ok", "message": "Evolution and trading started."}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.WS_HOST,
        port=config.WS_PORT,
        reload=False,
        log_level="info",
    )
