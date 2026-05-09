"""
EvoTrade Backend — FastAPI entry point.
PAPER TRADING ONLY — no real money, no broker connections.
"""
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, HMM_MODEL_PATH
from app.db import init_db
from app.routers import chat, evolution, trading, ws as ws_router
from app.utils.logger import get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────
    log.info("EvoTrade backend starting up...")
    await init_db()

    # Start market data feed
    from app.services.market_data import market_data_service
    from app.services.event_bus import event_bus
    await market_data_service.start(event_bus)

    # Calibrate regime detector
    from app.services.hmm_regime import hmm_detector
    hmm_detector.load()
    log.info("Calibrating regime detector on historical data...")
    df = market_data_service.load_historical_df(days=90)
    if not df.empty:
        hmm_detector.train(df)
    else:
        log.warning("No historical data — regime detector using built-in defaults")

    # Start WS broadcaster
    broadcaster_task = asyncio.create_task(ws_router.broadcaster())

    # Periodic portfolio + regime update task
    async def periodic_updates():
        while True:
            await asyncio.sleep(5)
            try:
                from app.services.paper_trader import paper_trader
                if paper_trader.running:
                    candles = market_data_service.get_candles(100)
                    regime_info = hmm_detector.predict_current_regime(candles)
                    await event_bus.publish("REGIME_CHANGED", regime_info)
            except Exception as e:
                log.warning(f"Periodic update error: {e}")

    regime_task = asyncio.create_task(periodic_updates())

    log.info("EvoTrade backend ready")
    yield

    # ── Shutdown ─────────────────────────────────────────────────────
    log.info("EvoTrade backend shutting down...")
    await market_data_service.stop()
    broadcaster_task.cancel()
    regime_task.cancel()


app = FastAPI(
    title="EvoTrade API",
    description="AI-powered self-evolving paper trading platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(evolution.router)
app.include_router(trading.router)
app.include_router(ws_router.router)


@app.get("/api/health")
async def health():
    from app.services.market_data import market_data_service
    from app.services.paper_trader import paper_trader
    return {
        "status": "ok",
        "services": {
            "market_feed": "running" if market_data_service.running else "stopped",
            "paper_trader": "running" if paper_trader.running else "stopped",
            "evolution": "ready",
        },
        "last_price": market_data_service.get_last_price(),
    }
