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

# Ensure both import styles work (backend.* and top-level modules under backend/)
_BACKEND_DIR = Path(__file__).parent
_REPO_ROOT = _BACKEND_DIR.parent
for _path in (str(_REPO_ROOT), str(_BACKEND_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from api.routes import app_state, router
from api.websocket_handler import ws_manager
from config import config
from data.yfinance_loader import YFinanceLoader
from data.binance_ws import BinanceWebSocket
from execution.alpha_gene_store import AlphaGeneStore
from execution.background_thread import BackgroundMonitor
from execution.main_thread import MainTradingThread
from execution.re_evolution_trigger import ReEvolutionTrigger
from execution.safety_controls import SafetyControls
from genetic.evolution_engine import EvolutionEngine
from genetic.gene import Gene
from genetic.fitness import backtest_gene
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
        app_state.portfolio_value = app_state.initial_capital

        # Prime with recent closes so live signal generation starts immediately.
        trader._prices = [float(x) for x in df["Close"].tail(400).tolist()]

        # ── Start paper-trading market feed ───────────────────────────────────
        feed = BinanceWebSocket(symbol_raw)
        feed.add_callback(trader.on_tick)
        app_state.binance_feed = feed
        app_state.binance_feed_task = asyncio.create_task(feed.start(), name="binance_feed")
        await _broadcast({"type": "paper_trading_started", "symbol": app_state.symbol})

        # ── Background regime monitor ─────────────────────────────────────────
        async def get_recent_data():
            fresh = loader.fetch(period_days=90)
            return fresh["Close"].tail(60), fresh["Volume"].tail(60)

        async def on_new_gene(gene: Gene) -> None:
            app_state.current_gene = gene.to_dict()
            if app_state.trader:
                app_state.trader.gene = gene  # hot-swap

        async def get_full_data():
            return loader.fetch(period_days=730)

        re_trigger = ReEvolutionTrigger(
            gene_store=gene_store,
            price_df_getter=get_full_data,
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


async def start_live_adaptation(top_genes: list[Gene]) -> None:
    """
    Live adaptation loop: score Top-3 genes on incoming ticks, pick best, and trade.
    Lightweight per-tick scoring (no full recompute), and a periodic parent-child
    refinement that evaluates 1 child per parent and promotes if better.
    """
    try:
        # Convert incoming representations into Gene objects
        genes: list[Gene] = []
        for g in top_genes:
            if isinstance(g, dict):
                try:
                    gene = Gene(
                        rsi_period=int(g.get("rsi_period", 14)),
                        ma_short=int(g.get("ma_short", 10)),
                        ma_long=int(g.get("ma_long", 50)),
                        stop_loss_pct=float(g.get("stop_loss_pct", 0.05)),
                        take_profit_pct=float(g.get("take_profit_pct", 0.10)),
                        position_size_pct=float(g.get("position_size_pct", 0.20)),
                    )
                    if "fitness" in g:
                        setattr(gene, "fitness", g["fitness"])
                except Exception:
                    continue
            else:
                gene = g
            genes.append(gene)

        if not genes:
            logger.warning("start_live_adaptation: no valid top_genes provided")
            return

        app_state.top_genes = [getattr(g, "to_dict", lambda: g)() if hasattr(g, "to_dict") else g for g in genes]
        app_state.pre_market_done = True
        await _broadcast({"type": "pre_market_complete", "top_genes": app_state.top_genes})

        local_prices: list[float] = []

        def score_gene_sync(gene: Gene, prices: list[float]) -> float:
            # fast heuristic score used per tick
            if len(prices) < gene.ma_long + 1:
                return -1e6
            period = gene.rsi_period
            if len(prices) < period + 1:
                return -1e6
            window = prices[-(period + 1):]
            deltas = [window[i + 1] - window[i] for i in range(period)]
            gains = sum(d for d in deltas if d > 0) / period
            losses = sum(-d for d in deltas if d < 0) / period
            rsi = 100.0 if losses == 0 else 100 - 100 / (1 + gains / (losses + 1e-12))
            ma_s = sum(prices[-gene.ma_short:]) / gene.ma_short
            ma_l = sum(prices[-gene.ma_long:]) / gene.ma_long
            score = 0.0
            if rsi < 30 and prices[-1] > ma_s:
                score += 3.0
            if rsi > 70 and prices[-1] < ma_l:
                score -= 2.0
            score += (gene.take_profit_pct - gene.stop_loss_pct) * 10.0
            score += gene.position_size_pct * 2.0
            return score

        try:
            from data.binance_ws import BinanceWebSocket
            feed = BinanceWebSocket(app_state.symbol.replace("/", ""))
        except Exception as exc:
            logger.error("Binance feed unavailable: %s", exc)
            return

        async def _on_tick(tick: dict) -> None:
            price = float(tick.get("close", 0))
            if price <= 0:
                return
            if app_state.trader:
                await app_state.trader.on_tick(tick)
                prices = app_state.trader._prices
            else:
                local_prices.append(price)
                lookback = max(g.ma_long for g in genes) + 5
                if len(local_prices) > lookback * 2:
                    del local_prices[:-lookback * 2]
                prices = local_prices

            scores = await asyncio.gather(*[asyncio.to_thread(score_gene_sync, g, list(prices)) for g in genes])
            best_idx = max(range(len(scores)), key=lambda i: scores[i])
            best_gene = genes[best_idx]
            if app_state.trader:
                app_state.trader.gene = best_gene
            app_state.active_gene = best_gene.to_dict() if hasattr(best_gene, "to_dict") else best_gene
            await _broadcast({"type": "live_gene_selected", "gene": app_state.active_gene})

        feed.add_callback(_on_tick)
        app_state.binance_feed = feed
        task = asyncio.create_task(feed.start())
        app_state.binance_feed_task = task
        logger.info("Live adaptation started with %d genes", len(genes))

        async def _refinement_loop() -> None:
            # Run light parent-child refinement every X minutes
            while True:
                await asyncio.sleep(60 * 5)
                prices_ref = app_state.trader._prices if app_state.trader else local_prices
                if len(prices_ref) < 50:
                    continue
                import pandas as pd
                df_quick = pd.DataFrame({"Close": prices_ref[-250:]})
                for i, parent in enumerate(genes):
                    child = Gene(**(parent.to_dict() if hasattr(parent, "to_dict") else parent))
                    child.mutate()
                    try:
                        res = backtest_gene(child, df_quick, initial_capital=app_state.initial_capital)
                        child_score = res.get("fitness_score", 0.0)
                    except Exception as exc:
                        logger.debug("Quick eval failed for child: %s", exc)
                        continue
                    weakest_idx = min(range(len(genes)), key=lambda j: getattr(genes[j], "fitness", float("-inf")))
                    weakest_score = getattr(genes[weakest_idx], "fitness", float("-inf"))
                    if child_score > weakest_score:
                        child.fitness = child_score
                        genes[weakest_idx] = child
                        app_state.top_genes = [g.to_dict() if hasattr(g, "to_dict") else g for g in genes]
                        await _broadcast({"type": "child_gene_promoted", "index": weakest_idx, "gene": child.to_dict() if hasattr(child, "to_dict") else child})

        asyncio.create_task(_refinement_loop())

    except Exception as exc:
        logger.exception("start_live_adaptation failed: %s", exc)
        await _broadcast({"type": "error", "message": "live_adaptation_error"})

# ── FastAPI lifecycle ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("EvoTrade backend starting up…")
    yield
    logger.info("EvoTrade backend shutting down…")
    if getattr(app_state, "binance_feed", None):
        await app_state.binance_feed.stop()
    if app_state.binance_feed_task and not app_state.binance_feed_task.done():
        app_state.binance_feed_task.cancel()
        try:
            await app_state.binance_feed_task
        except asyncio.CancelledError:
            pass
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


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.WS_HOST,
        port=config.WS_PORT,
        reload=False,
        log_level="info",
    )
