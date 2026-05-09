"""
run_demo.py — Full EvoTrade demo (backtesting mode, no real trades, no API keys needed).

Usage:
    python scripts/run_demo.py
    python scripts/run_demo.py --symbol ETH/USDT --profile high --generations 20
"""

import argparse
import asyncio
import sys
import os

# Make backend importable from project root
_repo_root = os.path.join(os.path.dirname(__file__), '..')
_backend_dir = os.path.join(_repo_root, 'backend')
for _p in (_repo_root, _backend_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="EvoTrade full pipeline demo")
    p.add_argument("--symbol",      default="BTC/USDT",  help="Trading pair (default: BTC/USDT)")
    p.add_argument("--profile",     default="medium",     choices=["low", "medium", "high"])
    p.add_argument("--generations", default=15,           type=int)
    p.add_argument("--population",  default=10,           type=int)
    p.add_argument("--period-days", default=730,          type=int, dest="period_days")
    return p.parse_args()


def section(title: str) -> None:
    print("\n" + "=" * 64)
    print(f"  {title}")
    print("=" * 64)


async def main() -> None:
    args = parse_args()

    print()
    print("  EvoTrade - Self-Evolving GA Trading Bot  | Demo Mode")
    print(f"  Symbol: {args.symbol}  |  Risk: {args.profile}  |  Max gens: {args.generations}")

    # ── Step 1: Load data ─────────────────────────────────────────────────────
    section("Step 1 / 5 — Loading Historical Market Data")
    from data.yfinance_loader import YFinanceLoader

    loader = YFinanceLoader(args.symbol)
    print(f"  Fetching {args.period_days} days of {args.symbol} OHLCV from Yahoo Finance…")
    df = loader.fetch(period_days=args.period_days)
    print(f"  Loaded {len(df)} bars  |  {df.index[0].date()} -> {df.index[-1].date()}")
    print(f"  Price range: ${df['Close'].min():,.0f} — ${df['Close'].max():,.0f}")

    # ── Step 2: Fit Markov regime detector ────────────────────────────────────
    section("Step 2 / 5 — Fitting Market Regime Detector (HMM)")
    from processing.markov_detector import MarkovDetector

    detector = MarkovDetector()
    print("  Fitting Gaussian HMM with 4 hidden states (bull/bear/sideways/crash)…")
    detector.fit(df["Close"], df["Volume"])
    regime = detector.detect(df["Close"].tail(60), df["Volume"].tail(60))
    print(f"  Current market regime: [{regime.upper()}]")
    print(f"  State→regime mapping : {detector._state_to_regime}")

    # ── Step 3: GA Evolution ──────────────────────────────────────────────────
    section("Step 3 / 5 — Running Genetic Algorithm Evolution")
    from genetic.evolution_engine import EvolutionEngine

    fitness_log: list[float] = []
    generation_log: list[dict] = []

    print(f"  Population: {args.population} agents  |  Max generations: {args.generations}")
    print(f"  Convergence window: 5 gens  |  Risk profile: {args.profile}")
    print()
    print(f"  {'Gen':>4}  {'Best Fitness':>14}  {'Improvement':>12}  {'Status'}")
    print(f"  {'-'*52}")

    async def on_event(event: dict) -> None:
        if event["type"] == "generation_complete":
            gen   = event["generation"]
            best  = event["best_fitness"]
            prev  = fitness_log[-1] if fitness_log else best
            delta = best - prev
            sign  = "+" if delta >= 0 else ""
            status = "converged" if event.get("type") == "converged" else "improving" if delta > 0.001 else "plateau"
            fitness_log.append(best)
            generation_log.append(event)
            print(f"  {gen:>4}  {best:>14.4f}  {sign}{delta:>11.4f}  {status}")

        elif event["type"] == "converged":
            print(f"\n  Convergence detected at generation {event['generation']}.")

    engine = EvolutionEngine(
        price_df=df,
        risk_profile=args.profile,
        population_size=args.population,
        max_generations=args.generations,
        convergence_window=5,
        event_callback=on_event,
    )
    result = await engine.run()
    alpha = result.alpha_gene

    # ── Step 4: Monte Carlo stress test ───────────────────────────────────────
    section("Step 4 / 5 — Monte Carlo Stress Test (scenario-based)")
    from stress_test.monte_carlo import run_monte_carlo

    mc_result = run_monte_carlo(alpha, df, n_runs=5)

    print(f"  Average fitness       : {mc_result['avg_fitness']:.4f}")
    print(f"  Survival rate         : {mc_result['survival_rate']:.2%}")
    print(f"  Robust fitness        : {mc_result['robust_fitness']:.4f}")

    print("\n  --- Scenario breakdown ---")
    for r in mc_result.get('scenario_results', []):
        print(f"  {r.get('scenario','unknown'):<20} fitness={r.get('fitness_score',0):+.4f} profit_pct={r.get('profit_pct',0):+.1%} max_dd={r.get('max_drawdown',0):+.1%}")

    # ── Step 5: Alpha Gene report ─────────────────────────────────────────────
    section("Step 5 / 5 — Alpha Gene Report")
    print(f"  Evolved in {result.generations_run} generation(s)  |  Converged: {result.converged}")
    print()
    gene_dict = alpha.to_dict()
    for k, v in gene_dict.items():
        if k == "fitness":
            continue
        bar_len = 20
        if k in ("stop_loss_pct", "take_profit_pct", "position_size_pct"):
            display = f"{v * 100:.2f}%"
            filled  = int(v / 0.50 * bar_len)
        else:
            display = str(int(v))
            limits  = {"rsi_period": 30, "ma_short": 50, "ma_long": 200}
            filled  = int(v / limits.get(k, 1) * bar_len)
        bar = "#" * filled + "-" * (bar_len - filled)
        print(f"  {k:<22} [{bar}]  {display}")

    print()
    print(f"  Fitness score         : {alpha.fitness:+.4f}")
    print(f"  MC weighted fitness   : {mc_result['robust_fitness']:.4f}")

    if len(fitness_log) > 1:
        print()
        print("  Fitness history per generation:")
        for i, f in enumerate(fitness_log, 1):
            bar = "#" * max(1, int((f - min(fitness_log)) / (max(fitness_log) - min(fitness_log) + 1e-9) * 30))
            print(f"    Gen {i:>3}  {bar}  {f:.4f}")

    print()
    print("  " + "-" * 48)
    print("  DISCLAIMER: Educational/research tool only.")
    print("  This is NOT financial advice. Do NOT use with")
    print("  real funds without independent risk assessment.")
    print("  " + "-" * 48)
    print()


if __name__ == "__main__":
    asyncio.run(main())
