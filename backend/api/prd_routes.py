"""
prd_routes.py — PRD §20 REST endpoints layered alongside the legacy routes.

This router is mounted at the FastAPI app root and offers the canonical
PRD endpoint surface:
    GET  /state
    POST /control/start
    POST /control/stop
    POST /control/kill-switch
    GET  /strategies
    GET  /strategies/{id}
    POST /broker/connect
    POST /evolution/run

The legacy `routes.py` router (/onboard, /pre_market_run, /live_start,
/start, /pause, /resume, /emergency_stop, /status) remains unchanged.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.ws_events import (
    EVOLUTION_RUN_STARTED,
    RISK_KILL_SWITCH,
    SYSTEM_HEALTH,
    STRATEGY_ACTIVATED,
)
from api.websocket_handler import ws_manager
from api.routes import app_state

logger = logging.getLogger(__name__)

prd_router = APIRouter(tags=["prd"])


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────────────────────────────────────

class StateResponse(BaseModel):
    running: bool
    paused: bool
    emergency_stopped: bool
    kill_switch_active: bool
    current_regime: Optional[str]
    regime_confidence: Optional[float]
    active_strategy_id: Optional[str]
    shadow_strategy_id: Optional[str]
    portfolio_value: float
    initial_capital: float
    pnl_pct: float


class StartRequest(BaseModel):
    risk_profile: str = Field("medium", pattern="^(low|medium|high)$")
    symbol: str = Field("BTC/USDT")
    initial_capital: float = Field(10_000.0, gt=0)


class KillSwitchRequest(BaseModel):
    enable: bool = Field(True)
    reason: str = Field("user_initiated")


class BrokerConnectRequest(BaseModel):
    broker: str = Field("paper", pattern="^(paper|binance)$")
    api_key: Optional[str] = None
    api_secret: Optional[str] = None


class EvolutionRunRequest(BaseModel):
    symbol: str = Field("BTC-USD")
    risk_profile: str = Field("medium", pattern="^(low|medium|high)$")
    initial_capital: float = Field(10_000.0, gt=0)
    n_generations: int = Field(5, ge=1, le=10)
    population_size: int = Field(10, ge=4, le=30)
    use_ai_council: bool = Field(True)


# ──────────────────────────────────────────────────────────────────────────────
# State + lifecycle
# ──────────────────────────────────────────────────────────────────────────────

@prd_router.get("/state", response_model=StateResponse)
async def get_state() -> StateResponse:
    """Returns the canonical system snapshot used by the dashboard."""
    pv = float(getattr(app_state, "portfolio_value", 0.0) or 0.0)
    ic = float(getattr(app_state, "initial_capital", 10_000.0))
    pnl = ((pv - ic) / ic * 100.0) if ic > 0 and pv > 0 else 0.0

    sx = getattr(app_state, "secure_exec", None)
    reg = getattr(app_state, "strategy_registry", None)

    return StateResponse(
        running=getattr(app_state, "running", False),
        paused=getattr(app_state, "paused", False),
        emergency_stopped=getattr(app_state, "emergency_stopped", False),
        kill_switch_active=bool(sx.kill_switch_active) if sx else False,
        current_regime=getattr(app_state, "current_regime", None),
        regime_confidence=getattr(app_state, "regime_confidence", None),
        active_strategy_id=reg.active_strategy_id if reg else None,
        shadow_strategy_id=reg.shadow_strategy_id if reg else None,
        portfolio_value=pv,
        initial_capital=ic,
        pnl_pct=round(pnl, 2),
    )


@prd_router.post("/control/start")
async def control_start(req: StartRequest) -> dict:
    """Start orchestrator (delegates to pipeline/orchestrator.start_pipeline)."""
    if getattr(app_state, "running", False):
        raise HTTPException(status_code=409, detail="Already running")

    app_state.symbol = req.symbol
    app_state.risk_profile = req.risk_profile
    app_state.initial_capital = req.initial_capital
    app_state.running = True

    try:
        from pipeline.orchestrator import start_pipeline
        task = asyncio.create_task(start_pipeline())
        app_state.evolution_task = task
    except Exception as exc:
        logger.exception("Failed to start pipeline: %s", exc)
        app_state.running = False
        raise HTTPException(status_code=500, detail="pipeline_start_failed")

    await ws_manager.broadcast({"type": SYSTEM_HEALTH,
                                 "data": {"status": "starting"}})
    return {"status": "ok", "message": "pipeline started"}


@prd_router.post("/control/stop")
async def control_stop() -> dict:
    """Gracefully stop the pipeline (kept distinct from emergency stop)."""
    app_state.running = False
    app_state.paused = True

    if getattr(app_state, "monitor", None):
        try:
            await app_state.monitor.stop()
        except Exception:
            pass

    task = getattr(app_state, "evolution_task", None)
    if task and not task.done():
        task.cancel()

    await ws_manager.broadcast({"type": SYSTEM_HEALTH,
                                 "data": {"status": "stopped"}})
    return {"status": "ok", "message": "pipeline stopped"}


@prd_router.post("/control/kill-switch")
async def control_kill_switch(req: KillSwitchRequest) -> dict:
    """Server-side enforcement: hits the SecureExecutionLayer kill switch."""
    sx = getattr(app_state, "secure_exec", None)
    if not sx:
        raise HTTPException(status_code=503, detail="secure_exec_unavailable")

    if req.enable:
        await sx.trigger_kill_switch(req.reason)
        app_state.emergency_stopped = True
    else:
        await sx.clear_kill_switch(req.reason)
        app_state.emergency_stopped = False

    await ws_manager.broadcast({"type": RISK_KILL_SWITCH,
                                 "data": {"active": req.enable,
                                          "reason": req.reason}})
    return {"status": "ok", "kill_switch_active": req.enable}


# ──────────────────────────────────────────────────────────────────────────────
# Strategies
# ──────────────────────────────────────────────────────────────────────────────

@prd_router.get("/strategies")
async def list_strategies() -> dict:
    reg = getattr(app_state, "strategy_registry", None)
    if not reg:
        return {"strategies": [], "active_strategy_id": None,
                "shadow_strategy_id": None}
    return {
        "strategies": [r.to_dict() for r in reg.list_all()],
        "active_strategy_id": reg.active_strategy_id,
        "shadow_strategy_id": reg.shadow_strategy_id,
    }


@prd_router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str) -> dict:
    reg = getattr(app_state, "strategy_registry", None)
    if not reg:
        raise HTTPException(status_code=404, detail="registry_not_initialized")
    rec = reg.get(strategy_id)
    if not rec:
        raise HTTPException(status_code=404, detail="strategy_not_found")
    return rec.to_dict()


@prd_router.post("/strategies/{strategy_id}/promote-shadow")
async def promote_shadow(strategy_id: str) -> dict:
    reg = getattr(app_state, "strategy_registry", None)
    if not reg:
        raise HTTPException(status_code=503, detail="registry_unavailable")
    try:
        rec = await reg.promote_to_shadow(strategy_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await ws_manager.broadcast({"type": STRATEGY_ACTIVATED,
                                 "data": {"strategy_id": rec.id, "status": "shadow"}})
    return {"status": "ok", "strategy_id": rec.id}


@prd_router.post("/strategies/{strategy_id}/hot-swap")
async def hot_swap(strategy_id: str, force: bool = False) -> dict:
    reg = getattr(app_state, "strategy_registry", None)
    if not reg:
        raise HTTPException(status_code=503, detail="registry_unavailable")
    result = await reg.hot_swap_to(strategy_id, force=force)
    if result.get("status") == "ok":
        await ws_manager.broadcast({"type": STRATEGY_ACTIVATED,
                                     "data": {"strategy_id": strategy_id,
                                              "status": "live"}})
    return result


@prd_router.post("/strategies/rollback")
async def rollback_strategy() -> dict:
    reg = getattr(app_state, "strategy_registry", None)
    if not reg:
        raise HTTPException(status_code=503, detail="registry_unavailable")
    return await reg.rollback(reason="manual")


# ──────────────────────────────────────────────────────────────────────────────
# Broker
# ──────────────────────────────────────────────────────────────────────────────

@prd_router.post("/broker/connect")
async def broker_connect(req: BrokerConnectRequest) -> dict:
    """
    Store broker credentials encrypted via SecureExecutionLayer.
    Plaintext is never persisted; we return only the metadata of the
    encrypted envelope so the UI can confirm storage.
    """
    sx = getattr(app_state, "secure_exec", None)
    if not sx:
        raise HTTPException(status_code=503, detail="secure_exec_unavailable")

    user_id = "default"  # MVP single-tenant
    if req.broker == "paper":
        # No keys needed; mark broker as configured
        app_state.broker_kind = "paper"
        return {"status": "ok", "broker": "paper",
                "configured": True, "encrypted": False}

    if not req.api_key or not req.api_secret:
        raise HTTPException(status_code=400, detail="api_key/secret required")

    envelope = sx.store_credentials(user_id=user_id,
                                     api_key=req.api_key,
                                     api_secret=req.api_secret)
    # Persist envelope reference, NOT plaintext
    app_state.broker_kind = req.broker
    app_state.broker_envelope = envelope
    return {"status": "ok", "broker": req.broker, "configured": True,
            "encrypted": True,
            "envelope_meta": {k: envelope.get(k) for k in ("alg", "v")}}


# ──────────────────────────────────────────────────────────────────────────────
# Evolution
# ──────────────────────────────────────────────────────────────────────────────

@prd_router.post("/evolution/run")
async def evolution_run(req: EvolutionRunRequest) -> dict:
    """Trigger the PRD §11 fixed-N-generation evolution run as a background task."""
    from genetic.evolution_engine import run_fixed_5gen_evolution
    from agents.ollama_council import OllamaCouncil

    if getattr(app_state, "evolution_running", False):
        raise HTTPException(status_code=409, detail="evolution_already_running")

    app_state.evolution_running = True

    council = OllamaCouncil() if req.use_ai_council else None

    async def _run() -> None:
        try:
            await ws_manager.broadcast({"type": EVOLUTION_RUN_STARTED,
                                         "data": {"symbol": req.symbol,
                                                  "n_generations": req.n_generations}})

            async def _broadcast(event: dict) -> None:
                # event already shaped {"type": "...", ...} from the engine
                await ws_manager.broadcast(event)

            await run_fixed_5gen_evolution(
                symbol=req.symbol,
                risk_profile=req.risk_profile,
                initial_capital=req.initial_capital,
                population_size=req.population_size,
                n_generations=req.n_generations,
                ai_council=council,
                on_event=_broadcast,
                verbose=False,
            )
        except Exception as exc:
            logger.exception("Evolution run failed: %s", exc)
            await ws_manager.broadcast({"type": "system.error",
                                         "data": {"error": str(exc)}})
        finally:
            app_state.evolution_running = False

    asyncio.create_task(_run())
    return {"status": "ok", "message": "evolution scheduled"}
