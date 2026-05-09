"""
DEAP-based Genetic Algorithm engine.
5 generations × 10 chromosomes.
Emits real-time WS events as evolution progresses.
PAPER TRADING ONLY.
"""
import asyncio
import json
import random
import uuid
from typing import Any, Callable, Dict, List, Optional
import numpy as np
import pandas as pd

from deap import base, creator, tools, algorithms

from app.config import GA_POPULATION, GA_GENERATIONS, GA_CXPB, GA_MUTPB_START, GA_MUTPB_DECAY
from app.services.ai_council import evaluate as council_evaluate
from app.services.monte_carlo import run_monte_carlo
from app.utils.logger import get_logger

log = get_logger(__name__)

# DEAP setup — safe to call multiple times
try:
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMax)
except Exception:
    pass  # Already created in this process


GENE_BOUNDS = [
    (15.0, 45.0),   # rsi_oversold
    (55.0, 85.0),   # rsi_overbought
    (5.0,  30.0),   # ma_short
    (30.0, 200.0),  # ma_long
    (0.005, 0.05),  # stop_loss_pct
    (0.005, 0.10),  # take_profit_pct
    (0.05,  0.40),  # position_size_pct
    (0.0,   1.0),   # sentiment_weight
]

GENE_KEYS = [
    "rsi_oversold", "rsi_overbought", "ma_short", "ma_long",
    "stop_loss_pct", "take_profit_pct", "position_size_pct", "sentiment_weight"
]


def clamp_individual(ind: list, risk_level: str = "moderate") -> list:
    """Apply risk-profile constraints and hard bounds."""
    for i, (lo, hi) in enumerate(GENE_BOUNDS):
        ind[i] = max(lo, min(hi, ind[i]))

    # ma_long must be > ma_short
    if ind[3] <= ind[2]:
        ind[3] = ind[2] + 10

    # Conservative risk caps
    if risk_level == "conservative":
        ind[4] = min(ind[4], 0.02)   # stop_loss_pct max 2%
        ind[6] = min(ind[6], 0.15)   # position_size_pct max 15%
    return ind


def genes_to_dict(individual: list) -> Dict[str, float]:
    d = {k: individual[i] for i, k in enumerate(GENE_KEYS)}
    d["ma_short"] = int(d["ma_short"])
    d["ma_long"] = int(d["ma_long"])
    return d


def run_simple_backtest(genes: Dict[str, float], df: pd.DataFrame) -> Dict[str, Any]:
    """Vectorised backtest on daily OHLCV DataFrame."""
    if df is None or len(df) < 30:
        return {"sharpe": 0.0, "max_drawdown": 0.30, "win_rate": 0.0, "n_trades": 0}

    try:
        import ta
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = df.columns.get_level_values(0)
        close = (df["Close"] if "Close" in df.columns else df["close"]).squeeze()
        close = close.dropna().reset_index(drop=True)
        ma_s = int(genes["ma_short"])
        ma_l = int(genes["ma_long"])
        rsi_os = genes["rsi_oversold"]
        rsi_ob = genes["rsi_overbought"]
        sl = genes["stop_loss_pct"]
        tp = genes["take_profit_pct"]
        pos_size = genes["position_size_pct"]

        rsi = ta.momentum.RSIIndicator(close, window=14).rsi().fillna(50)
        ma_short_s = close.rolling(ma_s).mean().fillna(close)
        ma_long_s = close.rolling(ma_l).mean().fillna(close)

        capital = 100.0
        position = 0.0
        entry_price = 0.0
        trades = []
        equity = [capital]

        for i in range(max(ma_l, 15), len(close)):
            price = float(close.iloc[i])
            rsi_val = float(rsi.iloc[i])
            ma_s_val = float(ma_short_s.iloc[i])
            ma_l_val = float(ma_long_s.iloc[i])

            if position == 0:
                if rsi_val < rsi_os and ma_s_val > ma_l_val:
                    invest = capital * pos_size
                    position = invest / price
                    entry_price = price
            else:
                pct = (price - entry_price) / entry_price
                if pct <= -sl:
                    pnl = position * price - position * entry_price
                    capital += position * price
                    trades.append({"pnl": pnl, "type": "stop_loss"})
                    position = 0.0
                elif pct >= tp:
                    pnl = position * price - position * entry_price
                    capital += position * price
                    trades.append({"pnl": pnl, "type": "take_profit"})
                    position = 0.0
                elif rsi_val > rsi_ob:
                    pnl = position * price - position * entry_price
                    capital += position * price
                    trades.append({"pnl": pnl, "type": "rsi_overbought"})
                    position = 0.0
            equity.append(capital + position * price if position else capital)

        # Close final position
        if position > 0:
            capital += position * float(close.iloc[-1])

        equity_arr = np.array(equity)
        returns = np.diff(equity_arr) / (equity_arr[:-1] + 1e-8)
        sharpe = float(np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)) if len(returns) > 1 else 0.0
        peak = np.maximum.accumulate(equity_arr)
        dd = (peak - equity_arr) / (peak + 1e-8)
        max_dd = float(np.max(dd))
        wins = [t for t in trades if t["pnl"] > 0]
        win_rate = len(wins) / max(len(trades), 1)
        return {
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "n_trades": len(trades),
        }
    except Exception as e:
        log.warning(f"Backtest error: {e}")
        return {"sharpe": 0.0, "max_drawdown": 0.30, "win_rate": 0.0, "n_trades": 0}


def normalize_sharpe(sharpe: float) -> float:
    return max(0.0, min(1.0, (sharpe + 1.0) / 4.0))


async def run_evolution(
    evolution_id: str,
    profile: Dict[str, Any],
    historical_df: pd.DataFrame,
    regime: str,
    publish: Callable,
    initial_price: float = 60000.0,
) -> Dict[str, Any]:
    """Main GA loop. Publishes WS events as it runs. Returns final_top_3 + best_alpha_gene."""
    capital = float(profile.get("capital", 50000))
    risk_level = profile.get("risk_level", "moderate").lower()

    toolbox = base.Toolbox()

    def init_individual():
        ind = [random.uniform(lo, hi) for lo, hi in GENE_BOUNDS]
        return creator.Individual(clamp_individual(ind, risk_level))

    toolbox.register("individual", init_individual)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate", tools.cxOnePoint)
    toolbox.register("select", tools.selTournament, tournsize=3)

    def mutate_individual(ind, sigma=0.1):
        for i in range(len(ind)):
            if random.random() < 0.3:
                lo, hi = GENE_BOUNDS[i]
                rng = hi - lo
                ind[i] += random.gauss(0, sigma * rng)
        return clamp_individual(ind, risk_level),

    toolbox.register("mutate", mutate_individual)

    population = toolbox.population(n=GA_POPULATION)
    all_generations_data = []
    top_3_global = []

    for gen in range(1, GA_GENERATIONS + 1):
        mutpb = max(0.05, GA_MUTPB_START - GA_MUTPB_DECAY * (gen - 1))
        await publish("GEN_STARTED", {"generation": gen, "evolution_id": evolution_id})

        # Emit chromosome creation events
        for idx, ind in enumerate(population):
            chrom_id = f"g{gen}_c{idx}"
            genes_dict = genes_to_dict(list(ind))
            await publish("CHROMOSOME_CREATED", {
                "generation": gen,
                "chromosome_id": chrom_id,
                "genes": genes_dict,
                "evolution_id": evolution_id,
            })
            await asyncio.sleep(0.08)

        # Monte Carlo
        await publish("MONTE_CARLO_STARTED", {"generation": gen, "evolution_id": evolution_id})

        # Evaluate fitness for all individuals
        fitnesses = []
        for ind in population:
            genes_dict = genes_to_dict(list(ind))
            bt = run_simple_backtest(genes_dict, historical_df)
            mc = run_monte_carlo(genes_dict, initial_price=initial_price, regime=regime,
                                 n_paths=50, initial_capital=capital)
            council = council_evaluate(genes_dict, bt, mc, regime)

            fitness_val = (
                0.30 * normalize_sharpe(bt["sharpe"])
                + 0.25 * max(0, 1 - bt["max_drawdown"])
                + 0.20 * mc["survival_rate"]
                + 0.15 * council["composite_score"]
                + 0.10 * bt["win_rate"]
            )
            if bt["n_trades"] < 5:
                fitness_val *= 0.3

            ind.fitness.values = (fitness_val,)
            fitnesses.append({
                "genes": genes_dict,
                "fitness": fitness_val,
                "backtest": bt,
                "mc": mc,
                "council": council,
            })

        await publish("MONTE_CARLO_DONE", {"generation": gen, "evolution_id": evolution_id,
                                           "results": [f["mc"] for f in fitnesses]})
        await publish("AI_COUNCIL_STARTED", {"generation": gen, "evolution_id": evolution_id})
        await asyncio.sleep(0.1)
        await publish("AI_COUNCIL_DONE", {"generation": gen, "evolution_id": evolution_id,
                                          "scores": [f["council"] for f in fitnesses]})

        # Rank
        ranked = sorted(fitnesses, key=lambda x: x["fitness"], reverse=True)
        ranked_payload = [
            {"id": f"g{gen}_c{i}", "fitness": r["fitness"], "genes": r["genes"]}
            for i, r in enumerate(ranked)
        ]
        await publish("FITNESS_SCORED", {"generation": gen, "ranked": ranked_payload,
                                          "evolution_id": evolution_id})

        top_3 = ranked[:3]
        top_3_payload = [
            {
                "id": f"g{gen}_c{i}",
                "fitness": r["fitness"],
                "genes": r["genes"],
                "backtest": r["backtest"],
                "council": r["council"],
                "generation": gen,
            }
            for i, r in enumerate(top_3)
        ]
        await publish("TOP_3_SELECTED", {"generation": gen, "top3": top_3_payload,
                                          "evolution_id": evolution_id})

        best_gene = top_3[0]["genes"]
        await publish("GEN_COMPLETED", {
            "generation": gen,
            "best_alpha_gene": best_gene,
            "evolution_id": evolution_id,
        })

        all_generations_data.append({"generation": gen, "ranked": ranked_payload, "top3": top_3_payload})

        # Evolve next population (keep top 3, fill rest via crossover/mutation)
        offspring = toolbox.select(population, k=GA_POPULATION - 3)
        offspring = list(map(toolbox.clone, offspring))
        # Crossover
        for c1, c2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < GA_CXPB:
                toolbox.mate(c1, c2)
                del c1.fitness.values
                del c2.fitness.values
        # Mutation
        for mut in offspring:
            if random.random() < mutpb:
                toolbox.mutate(mut)
                del mut.fitness.values

        elites = [creator.Individual(clamp_individual(list(r["genes"].values()), risk_level))
                  for r in top_3]
        population = elites + offspring

        top_3_global = top_3_payload  # keep last generation's top 3

    # Final best
    best_alpha = max(top_3_global, key=lambda x: x["fitness"]) if top_3_global else {}
    best_alpha_id = str(uuid.uuid4())
    if best_alpha:
        best_alpha["alpha_gene_id"] = best_alpha_id
    for item in top_3_global:
        item["alpha_gene_id"] = str(uuid.uuid4())

    await publish("EVOLUTION_COMPLETE", {
        "evolution_id": evolution_id,
        "final_top_3": top_3_global,
        "best_alpha_gene": best_alpha,
    })

    log.info(f"Evolution {evolution_id} complete. Best fitness: {best_alpha.get('fitness', 0):.4f}")
    return {"final_top_3": top_3_global, "best_alpha_gene": best_alpha}
