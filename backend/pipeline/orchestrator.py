"""
orchestrator.py — Wires SecureExec, PaperBroker, StrategyRegistry,
                  MarkovDetector, OllamaCouncil, and the EvolutionEngine
                  together as the PRD §5 three-thread runtime.

Thread model (asyncio tasks):
  • LiveTradingTask   (FAST) — candle loop, signal gen, order intents.
  • EvolutionTask     (FAST + SMART) — periodic GA + AI council.
  • DashboardTask     — passive; broadcasts already happen at event sites.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from agents.ollama_council import OllamaCouncil
from api.routes import app_state
from api.websocket_handler import ws_manager
from api.ws_events import (
    AI_REASONING_READY,
    EXECUTION_ORDER_FILLED,
    EXECUTION_ORDER_REJECTED,
    EXECUTION_ORDER_SUBMITTED,
    MARKET_CANDLE_CLOSE,
    REGIME_DETECTED,
    REGIME_SWITCHED,
    RISK_LIMIT_TRIGGERED,
    STRATEGY_ACTIVATED,
    STRATEGY_SIGNAL,
    SYSTEM_ERROR,
    SYSTEM_HEALTH,
)
from data.yfinance_loader import fetch_historical_data
from execution.paper_broker import PaperBroker
from execution.secure_exec import OrderIntent, SecureExecutionLayer
from execution.strategy_registry import StrategyRegistry
from genetic.gene import Gene
from processing.markov_detector import MarkovDetector

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Singletons (lazy-initialized)
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_singletons() -> None:
    """Build secure exec, broker, registry, council on first use."""
    if not getattr(app_state, "secure_exec", None):
        sx = SecureExecutionLayer()
        broker = PaperBroker(starting_cash=float(getattr(app_state, "initial_capital", 10_000.0)))
        sx.set_broker(broker)
        sx.set_initial_capital(float(getattr(app_state, "initial_capital", 10_000.0)))
        app_state.secure_exec = sx
        app_state.paper_broker = broker

    if not getattr(app_state, "strategy_registry", None):
        app_state.strategy_registry = StrategyRegistry()

    if not getattr(app_state, "ollama_council", None):
        app_state.ollama_council = OllamaCouncil()

    if not getattr(app_state, "markov_detector", None):
        app_state.markov_detector = MarkovDetector(
            confidence_threshold=0.80, sustained_window=5, cooldown_seconds=300
        )


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _yf_symbol(symbol: str) -> str:
    """Convert "BTC/USDT" → "BTC-USD" for yfinance."""
    s = symbol.replace("/", "-")
    if s.endswith("USDT"):
        s = s[:-4] + "USD"
    return s


def _pick_best_top3_summary(top_genes: list[dict]) -> Optional[dict]:
    """Pick the highest-fitness candidate dict."""
    if not top_genes:
        return None
    return max(top_genes, key=lambda g: float(g.get("fitness", 0.0)))


# ──────────────────────────────────────────────────────────────────────────────
# Live trading loop (PRD §7.4)
# ──────────────────────────────────────────────────────────────────────────────

async def live_trading_task() -> None:
    """
    Polls historical data as a stand-in for a websocket feed in MVP demo mode.
    On each "candle close" we run RSI+MA on the active strategy, then route the
    intent through SecureExec → PaperBroker.
    """
    _ensure_singletons()

    sx: SecureExecutionLayer = app_state.secure_exec
    reg: StrategyRegistry = app_state.strategy_registry
    detector: MarkovDetector = app_state.markov_detector
    symbol: str = getattr(app_state, "symbol", "BTC/USDT")

    yf_sym = _yf_symbol(symbol)

    # Bootstrap historical data + fit HMM
    try:
        df = fetch_historical_data(yf_sym, "1y")
        detector.fit(df["Close"], df["Volume"])
    except Exception as exc:
        logger.warning("Live task warmup failed: %s", exc)
        await ws_manager.broadcast({"type": SYSTEM_ERROR, "data": {"error": str(exc)}})
        return

    poll_interval_s = float(getattr(app_state, "live_poll_s", 30.0))

    last_close: Optional[float] = None
    while getattr(app_state, "running", False):
        if getattr(app_state, "paused", False) or sx.kill_switch_active:
            await asyncio.sleep(1.0)
            continue

        try:
            df = fetch_historical_data(yf_sym, "1y")
            if df is None or df.empty:
                await asyncio.sleep(poll_interval_s)
                continue

            close = float(df["Close"].iloc[-1])
            if last_close is not None and abs(close - last_close) < 1e-9:
                await asyncio.sleep(poll_interval_s)
                continue
            last_close = close

            await ws_manager.broadcast({"type": MARKET_CANDLE_CLOSE,
                                         "data": {"symbol": symbol, "close": close,
                                                  "ts": datetime.now(timezone.utc).isoformat()}})

            # Update regime (with stabilization)
            regime_snap = detector.update_stable_regime(df["Close"], df["Volume"])
            app_state.current_regime = regime_snap["stable_regime"]
            app_state.regime_confidence = regime_snap["confidence"]
            if regime_snap["switched"]:
                await ws_manager.broadcast({"type": REGIME_SWITCHED,
                                             "data": {"regime": regime_snap["stable_regime"],
                                                      "confidence": regime_snap["confidence"]}})
            else:
                await ws_manager.broadcast({"type": REGIME_DETECTED,
                                             "data": {"regime": regime_snap["stable_regime"],
                                                      "confidence": regime_snap["confidence"],
                                                      "posterior": regime_snap["posterior"]}})

            # Generate signal from active strategy
            active = reg.active()
            if not active:
                await asyncio.sleep(poll_interval_s)
                continue
            gene = active.gene

            signal = _generate_signal(gene, df)
            if signal["action"] == "HOLD":
                await ws_manager.broadcast({"type": STRATEGY_SIGNAL,
                                             "data": {"strategy_id": active.id,
                                                      "action": "HOLD",
                                                      "indicators": signal["indicators"]}})
                await asyncio.sleep(poll_interval_s)
                continue

            await ws_manager.broadcast({"type": STRATEGY_SIGNAL,
                                         "data": {"strategy_id": active.id,
                                                  **signal}})

            qty = max(0.0, (sx._initial_capital * gene.position_size_pct) / close)
            intent = OrderIntent(
                user_id="default",
                symbol=symbol.replace("/", ""),
                side=signal["action"],
                type="MARKET",
                qty=qty,
                risk={
                    "stop_loss_pct": float(gene.stop_loss_pct),
                    "take_profit_pct": float(gene.take_profit_pct),
                    "max_slippage_bps": 15,
                },
                metadata={
                    "strategy_id": active.id,
                    "regime": regime_snap["stable_regime"],
                    "confidence": regime_snap["confidence"],
                    "price": close,
                },
            )

            await ws_manager.broadcast({"type": EXECUTION_ORDER_SUBMITTED,
                                         "data": intent.sanitized()})

            result = await sx.place_order(intent)
            if result.get("status") == "filled":
                await ws_manager.broadcast({"type": EXECUTION_ORDER_FILLED,
                                             "data": result})
                # Update portfolio and registry live metrics
                broker: PaperBroker = app_state.paper_broker
                equity = broker.get_equity({intent.symbol: close})
                app_state.portfolio_value = equity
                pnl_pct = (equity - sx._initial_capital) / sx._initial_capital * 100.0
                dd = max(0.0, (broker.state.high_water_mark - equity)
                              / broker.state.high_water_mark * 100.0)
                rb = await reg.update_live_metrics(active.id, pnl_pct=pnl_pct, max_dd_pct=dd)
                await sx.update_pnl(equity)
                if rb and rb.get("status") in ("rolled_back", "ok"):
                    await ws_manager.broadcast({"type": STRATEGY_ACTIVATED,
                                                 "data": {"strategy_id": rb.get("to") or rb.get("active_strategy_id"),
                                                          "status": "live", "reason": "auto_rollback"}})
            else:
                await ws_manager.broadcast({"type": EXECUTION_ORDER_REJECTED,
                                             "data": result})
                if result.get("reason"):
                    await ws_manager.broadcast({"type": RISK_LIMIT_TRIGGERED,
                                                 "data": {"reason": result["reason"]}})
                    try:
                        from persistence.supabase_client import supabase
                        asyncio.create_task(supabase().insert_risk_event(
                            event_type="order_rejected",
                            reason=result["reason"],
                            payload={"intent": intent.sanitized()},
                        ))
                    except Exception:
                        pass
        except Exception as exc:
            logger.exception("Live task iteration failed: %s", exc)
            await ws_manager.broadcast({"type": SYSTEM_ERROR, "data": {"error": str(exc)}})

        await asyncio.sleep(poll_interval_s)


def _generate_signal(gene: Gene, df: pd.DataFrame) -> dict:
    """RSI + dual-MA signal logic per PRD §7.3."""
    import numpy as np
    close = df["Close"].astype(float)
    if len(close) < gene.ma_long + 5:
        return {"action": "HOLD", "indicators": {}}

    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(gene.rsi_period).mean().iloc[-1]
    avg_loss = loss.rolling(gene.rsi_period).mean().iloc[-1] + 1e-10
    rs = avg_gain / avg_loss
    rsi = float(100 - (100 / (1 + rs)))
    ma_s = float(close.rolling(gene.ma_short).mean().iloc[-1])
    ma_l = float(close.rolling(gene.ma_long).mean().iloc[-1])
    price = float(close.iloc[-1])

    indicators = {"rsi": round(rsi, 2), "ma_short": round(ma_s, 2),
                  "ma_long": round(ma_l, 2), "price": round(price, 2)}

    if rsi < (100 - gene.rsi_period * 2) and ma_s > ma_l:
        return {"action": "BUY", "indicators": indicators}
    if rsi > 70 or ma_s < ma_l:
        return {"action": "SELL", "indicators": indicators}
    return {"action": "HOLD", "indicators": indicators}


# ──────────────────────────────────────────────────────────────────────────────
# Periodic 5-gen evolution task (PRD §11)
# ──────────────────────────────────────────────────────────────────────────────

async def evolution_task() -> None:
    """
    Run the fixed 5-gen evolution at startup (one cycle for MVP demo).
    The first AlphaGene is force-promoted to LIVE; subsequent winners go to SHADOW
    and are subject to deployment policy gates.
    """
    _ensure_singletons()

    from genetic.evolution_engine import run_fixed_5gen_evolution
    from persistence.supabase_client import supabase

    council: OllamaCouncil = app_state.ollama_council
    reg: StrategyRegistry = app_state.strategy_registry

    symbol = _yf_symbol(getattr(app_state, "symbol", "BTC/USDT"))

    # Open a Supabase evolution_run row up front (no-op if Supabase disabled)
    run_row = await supabase().insert_evolution_run(
        symbol=symbol,
        risk_profile=getattr(app_state, "risk_profile", "medium"),
        n_generations=5, population_size=10,
    )
    run_id: Optional[str] = (run_row or {}).get("id")
    app_state.current_run_id = run_id

    async def _on_event(event: dict) -> None:
        await ws_manager.broadcast(event)
        # Persist the heavy payloads to Supabase (best-effort)
        try:
            etype = event.get("type")
            if etype == "evolution.generation_scored" and run_id:
                # Per-generation summary persisted on top3_selected (richer payload).
                pass
            elif etype == "evolution.top3_selected" and run_id:
                top_3 = event.get("top_3") or event.get("data", {}).get("top_3") or []
                gen = event.get("generation") or event.get("data", {}).get("generation")
                if gen is not None:
                    alpha_gene = (top_3[0].get("genes") if top_3 else {}) or {}
                    asyncio.create_task(supabase().insert_generation_result(
                        run_id=run_id, generation=int(gen),
                        candidates=top_3,            # we only have top3 in this event
                        top_3=top_3, alpha_gene=alpha_gene,
                        best_fitness=float(top_3[0].get("fitness", 0.0)) if top_3 else 0.0,
                        avg_fitness=sum(float(c.get("fitness", 0.0)) for c in top_3) / max(len(top_3), 1),
                    ))
            elif etype == "ai.reasoning_ready" and run_id:
                gen = event.get("generation")
                reasoning = event.get("reasoning") or {}
                asyncio.create_task(supabase().insert_ai_card(
                    run_id=run_id, generation=gen,
                    strategy_id=None, reasoning=reasoning,
                ))
        except Exception:
            pass

    try:
        result = await run_fixed_5gen_evolution(
            symbol=symbol,
            risk_profile=getattr(app_state, "risk_profile", "medium"),
            initial_capital=float(getattr(app_state, "initial_capital", 10_000.0)),
            population_size=10,
            n_generations=5,
            ai_council=council,
            on_event=_on_event,
            verbose=False,
        )
    except Exception as exc:
        logger.exception("Evolution task failed: %s", exc)
        await ws_manager.broadcast({"type": SYSTEM_ERROR, "data": {"error": str(exc)}})
        return

    # Register every generation's AlphaGene
    last_rec = None
    for gi, gene_dict in enumerate(result["alpha_gene_per_gen"], start=1):
        gene = Gene(
            rsi_period=int(gene_dict["rsi_period"]),
            ma_short=int(gene_dict["ma_short"]),
            ma_long=int(gene_dict["ma_long"]),
            stop_loss_pct=float(gene_dict["stop_loss_pct"]),
            take_profit_pct=float(gene_dict["take_profit_pct"]),
            position_size_pct=float(gene_dict["position_size_pct"]),
        )
        last_rec = await reg.register_candidate(
            gene, origin=f"gen{gi}",
            fitness=float(result["fitness_history"][gi - 1]) if gi - 1 < len(result["fitness_history"]) else None,
        )

    if last_rec:
        if reg.active_strategy_id is None:
            # First-ever deploy: force-swap.
            res = await reg.hot_swap_to(last_rec.id, force=True)
            await ws_manager.broadcast({"type": STRATEGY_ACTIVATED,
                                         "data": {"strategy_id": last_rec.id,
                                                  "status": "live", "force": True}})
        else:
            # Promote to shadow for normal workflow
            await reg.promote_to_shadow(last_rec.id)
            await ws_manager.broadcast({"type": STRATEGY_ACTIVATED,
                                         "data": {"strategy_id": last_rec.id,
                                                  "status": "shadow"}})

    # Mark the evolution run as completed in Supabase
    if run_id:
        try:
            await supabase().complete_evolution_run(
                run_id, final_alpha_gene_id=last_rec.id if last_rec else None,
                fitness_history=[float(f) for f in result["fitness_history"]],
            )
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline entry
# ──────────────────────────────────────────────────────────────────────────────

async def start_pipeline() -> None:
    """Start (or restart) all three async tasks."""
    _ensure_singletons()
    await ws_manager.broadcast({"type": SYSTEM_HEALTH,
                                 "data": {"status": "pipeline_starting",
                                          "ts": datetime.now(timezone.utc).isoformat()}})

    # Run evolution first; then start the live loop using whatever was deployed.
    try:
        await evolution_task()
    except Exception as exc:
        logger.exception("Evolution preflight failed: %s", exc)

    asyncio.create_task(live_trading_task(), name="live_trading_task")

    await ws_manager.broadcast({"type": SYSTEM_HEALTH,
                                 "data": {"status": "pipeline_running"}})
