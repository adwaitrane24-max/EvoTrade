"""Monte Carlo robustness testing."""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from ..genetic.fitness import backtest_gene
    from ..genetic.gene import Gene
    from .scenarios import get_all_scenarios
except ImportError:
    from genetic.fitness import backtest_gene
    from genetic.gene import Gene
    from stress_test.scenarios import get_all_scenarios


def _gbm_path_df(base_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    close = base_df["Close"].astype(float).to_numpy()
    n = len(close)
    if n < 5:
        return base_df.copy()

    log_ret = np.diff(np.log(close))
    mu = float(np.mean(log_ret))
    sigma = float(np.std(log_ret))
    shocks = rng.normal(mu, sigma, size=n - 1)
    sim_close = np.empty(n, dtype=float)
    sim_close[0] = max(close[0], 1e-6)
    sim_close[1:] = sim_close[0] * np.exp(np.cumsum(shocks))

    out = base_df.copy()
    out["Close"] = sim_close
    for c, mult in [("Open", 1.0), ("High", 1.002), ("Low", 0.998)]:
        if c in out.columns:
            out[c] = sim_close * mult
    if "Volume" in out.columns:
        out["Volume"] = out["Volume"].astype(float) * (1.0 + np.abs(rng.normal(0.0, 0.05, size=n)))
    return out


def run_monte_carlo(gene: Gene, df: pd.DataFrame, n_simulations: int = 100) -> dict[str, float | int | list[dict[str, float]]]:
    """
    Evaluate gene robustness across fixed stress scenarios + random GBM paths.
    """
    if n_simulations < 5:
        raise ValueError("n_simulations must be at least 5.")

    scenario_map = get_all_scenarios(df)
    runs: list[dict[str, float]] = []

    for name, scenario_df in scenario_map.items():
        result = backtest_gene(gene, scenario_df)
        runs.append(
            {
                "scenario": float(hash(name) % 10_000),  # numeric for compact transport
                "profit_pct": float(result["profit_pct"]),
                "fitness_score": float(result["fitness_score"]),
            }
        )

    rng = np.random.default_rng(2026)
    extra = n_simulations - len(scenario_map)
    for _ in range(extra):
        sim_df = _gbm_path_df(df, rng)
        result = backtest_gene(gene, sim_df)
        runs.append(
            {
                "scenario": -1.0,
                "profit_pct": float(result["profit_pct"]),
                "fitness_score": float(result["fitness_score"]),
            }
        )

    profits = np.array([r["profit_pct"] for r in runs], dtype=float)
    fitness = np.array([r["fitness_score"] for r in runs], dtype=float)

    avg_fitness = float(np.mean(fitness))
    survival_rate = float(np.mean(profits > 0.0) * 100.0)
    worst_case_loss = float(np.min(profits))
    best_case_gain = float(np.max(profits))
    robust_fitness_score = float(avg_fitness * survival_rate)

    return {
        "n_simulations": int(n_simulations),
        "avg_fitness": avg_fitness,
        "survival_rate": survival_rate,
        "worst_case_loss": worst_case_loss,
        "best_case_gain": best_case_gain,
        "robust_fitness_score": robust_fitness_score,
        "runs": runs,
    }


if __name__ == "__main__":
    try:
        from ..data.yfinance_loader import fetch_historical_data
    except ImportError:
        from data.yfinance_loader import fetch_historical_data

    data = fetch_historical_data("BTC-USD", "1y")
    gene = Gene()
    print(run_monte_carlo(gene, data, n_simulations=100))
