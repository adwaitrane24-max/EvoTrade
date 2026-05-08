"""
routes.py — FastAPI REST endpoint definitions for the EvoTrade backend.
"""

from __future__ import annotations

import logging
import asyncio
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


class PreMarketRequest(BaseModel):
    symbol: str = Field("BTC/USDT")
    risk_profile: str = Field("medium", pattern="^(low|medium|high)$")
    initial_capital: float = Field(10_000.0, gt=0)
    lookback_days: int = Field(180, gt=0)
    expected_return: float = Field(0.15, gt=0)
    max_drawdown: float = Field(0.20, gt=0)
    target_asset: str = Field("crypto")
    ready_to_join: bool = Field(False)


class LiveStartRequest(BaseModel):
    ready_to_join: bool = Field(True)


class StatusResponse(BaseModel):
    running: bool
    paused: bool
    emergency_stopped: bool
    current_regime: Optional[str]
    current_gene: Optional[dict]
    fitness_history: list[float]
    trade_count: int
    portfolio_value: float

    # New fields
    pre_market_done: bool = False
    top_genes: list = []
    ready_to_join: bool = False
    active_gene: Optional[dict] = None


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


@router.post("/pre_market_run", summary="Run exhaustive pre-market combinations")
async def pre_market_run(req: PreMarketRequest) -> dict:
    """Run a fast exhaustive combination search on historical data and persist Top-3."""
    await ws_manager.broadcast({"type": "pre_market_started", "symbol": req.symbol})
    logger.info("Pre-market run requested: %s", req.symbol)

    # Run the full combinations loop in a thread to avoid blocking the event loop
    try:
        from genetic.combo_search import run_full_combinations
        top_genes = await asyncio.to_thread(
            run_full_combinations,
            req.symbol,
            req.lookback_days,
            req.risk_profile,
            req.initial_capital,
            req.expected_return,
            req.max_drawdown,
        )
    except Exception as exc:
        logger.exception("Pre-market combination search failed: %s", exc)
        raise HTTPException(status_code=500, detail="Pre-market run failed")

    # Persist Top-3
    try:
        from execution.alpha_gene_store import AlphaGeneStore
        store = AlphaGeneStore()
        store.save_top_genes(top_genes)
    except Exception:
        logger.exception("Failed to persist top_genes")

    app_state.pre_market_done = True
    app_state.top_genes = [g.to_dict() if hasattr(g, "to_dict") else g for g in top_genes]
    await ws_manager.broadcast({"type": "top_genes_selected", "top_genes": app_state.top_genes})

    return {"status": "ok", "message": "Pre-market run complete", "top_genes": app_state.top_genes}


@router.post("/live_start", summary="Start live adaptation with Top-3 genes")
async def live_start(req: LiveStartRequest) -> dict:
    app_state.ready_to_join = req.ready_to_join
    await ws_manager.broadcast({"type": "live_start", "ready_to_join": req.ready_to_join})
    logger.info("Live start requested (ready_to_join=%s)", req.ready_to_join)

    if req.ready_to_join:
        try:
            # Import here to avoid circular module imports at startup
            from main import start_live_adaptation
            asyncio.create_task(start_live_adaptation(app_state.top_genes))
        except Exception as exc:
            logger.exception("Failed to start live adaptation: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to start live adaptation")

    return {"status": "ok", "message": "Live trading started"}


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
        pre_market_done=getattr(app_state, "pre_market_done", False),
        top_genes=getattr(app_state, "top_genes", []),
        ready_to_join=getattr(app_state, "ready_to_join", False),
        active_gene=getattr(app_state, "active_gene", None),
    )
