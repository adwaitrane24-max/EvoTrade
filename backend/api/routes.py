"""
routes.py — FastAPI REST endpoint definitions for the EvoTrade backend.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.websocket_handler import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Pydantic request/response models ──────────────────────────────────────────


class OnboardRequest(BaseModel):
    risk_profile: str = Field("medium", pattern="^(low|medium|high)$")
    symbol: str = Field("BTC/USDT")
    initial_capital: float = Field(10_000.0, gt=0)
    exchange_api_key: Optional[str] = Field(None)
    exchange_api_secret: Optional[str] = Field(None)


class StatusResponse(BaseModel):
    running: bool
    paused: bool
    emergency_stopped: bool
    current_regime: Optional[str]
    current_gene: Optional[dict]
    fitness_history: list[float]
    trade_count: int
    portfolio_value: float


# ── Shared runtime state (injected by main.py at startup) ─────────────────────

class AppState:
    """Mutable singleton holding references to all live runtime objects."""

    def __init__(self) -> None:
        self.running: bool = False
        self.paused: bool = False
        self.emergency_stopped: bool = False
        self.current_regime: Optional[str] = None
        self.current_gene: Optional[dict] = None
        self.fitness_history: list[float] = []
        self.trade_count: int = 0
        self.portfolio_value: float = 0.0
        self.risk_profile: str = "medium"
        self.symbol: str = "BTC/USDT"
        self.initial_capital: float = 10_000.0

        # References injected by main.py
        self.trader = None
        self.monitor = None
        self.evolution_task = None


app_state = AppState()


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/onboard", summary="Configure trading parameters")
async def onboard(req: OnboardRequest) -> dict:
    """
    Accept onboarding parameters and store them in app state.
    Does not start trading.
    """
    app_state.risk_profile = req.risk_profile
    app_state.symbol = req.symbol
    app_state.initial_capital = req.initial_capital

    logger.info(
        "Onboarded: symbol=%s, profile=%s, capital=%.2f",
        req.symbol, req.risk_profile, req.initial_capital,
    )

    await ws_manager.broadcast({"type": "onboarded", "symbol": req.symbol})
    return {"status": "ok", "message": "Configuration saved. Call /start to begin."}


@router.post("/start", summary="Begin evolution loop then live execution")
async def start() -> dict:
    """Start the evolution loop and live trading in the background."""
    if app_state.running:
        raise HTTPException(status_code=409, detail="Already running.")
    if app_state.emergency_stopped:
        raise HTTPException(status_code=403, detail="Emergency stop is active. Restart the server.")

    app_state.running = True
    app_state.paused = False

    # Actual launch logic is in main.py to avoid circular imports
    await ws_manager.broadcast({"type": "started"})
    logger.info("Start requested via /start.")
    return {"status": "ok", "message": "Evolution and trading started."}


@router.post("/pause", summary="Pause live trading")
async def pause() -> dict:
    """Pause trade execution. Evolution can continue in background."""
    app_state.paused = True
    if app_state.trader and hasattr(app_state.trader, "safety"):
        app_state.trader.safety.pause()
    await ws_manager.broadcast({"type": "paused"})
    logger.info("Trading paused via /pause.")
    return {"status": "ok", "message": "Trading paused."}


@router.post("/resume", summary="Resume live trading")
async def resume() -> dict:
    """Resume paused trade execution."""
    if app_state.emergency_stopped:
        raise HTTPException(status_code=403, detail="Emergency stop active.")
    app_state.paused = False
    if app_state.trader and hasattr(app_state.trader, "safety"):
        app_state.trader.safety.resume()
    await ws_manager.broadcast({"type": "resumed"})
    return {"status": "ok", "message": "Trading resumed."}


@router.post("/emergency_stop", summary="Immediately halt all activity")
async def emergency_stop() -> dict:
    """Emergency stop: halt trading, cancel all positions (in live mode)."""
    app_state.emergency_stopped = True
    app_state.paused = True
    app_state.running = False

    if app_state.trader and hasattr(app_state.trader, "safety"):
        app_state.trader.safety.emergency_stop()

    if app_state.monitor:
        await app_state.monitor.stop()

    if app_state.evolution_task and not app_state.evolution_task.done():
        app_state.evolution_task.cancel()

    await ws_manager.broadcast({"type": "emergency_stopped"})
    logger.critical("EMERGENCY STOP activated via /emergency_stop.")
    return {"status": "ok", "message": "Emergency stop activated."}


@router.get("/status", response_model=StatusResponse, summary="Current system status")
async def status() -> StatusResponse:
    """Return the current state of the trading system."""
    trade_count = 0
    portfolio_value = app_state.initial_capital

    if app_state.trader:
        trade_count = len(getattr(app_state.trader, "_trade_log", []))
        portfolio_value = getattr(app_state.trader, "portfolio_value", app_state.initial_capital)

    return StatusResponse(
        running=app_state.running,
        paused=app_state.paused,
        emergency_stopped=app_state.emergency_stopped,
        current_regime=app_state.current_regime,
        current_gene=app_state.current_gene,
        fitness_history=app_state.fitness_history,
        trade_count=trade_count,
        portfolio_value=portfolio_value,
    )
