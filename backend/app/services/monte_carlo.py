"""
Monte Carlo stress testing via GBM + Poisson jump diffusion.
Vectorized with NumPy — generates all paths in one operation.
PAPER TRADING ONLY — no real money simulation.
"""
import numpy as np
from typing import Dict, Any, List
from app.config import MC_PATHS, MC_STEPS, MC_SURVIVAL_THRESHOLD
from app.utils.logger import get_logger

log = get_logger(__name__)


def run_monte_carlo(
    genes: Dict[str, float],
    initial_price: float = 60000.0,
    regime: str = "SIDEWAYS",
    n_paths: int = MC_PATHS,
    n_steps: int = MC_STEPS,
    initial_capital: float = 50000.0,
) -> Dict[str, Any]:
    """
    Simulate n_paths price trajectories using GBM + jump diffusion.
    For each path, apply the gene's simple trading logic and record outcomes.
    Returns survival_rate and other aggregate stats.
    """
    rng = np.random.default_rng(42)

    # Regime-adjusted GBM parameters
    regime_params = {
        "BULL":     {"mu": 0.0008,  "sigma": 0.018, "jump_intensity": 0.02, "jump_mean": 0.01},
        "SIDEWAYS": {"mu": 0.0001,  "sigma": 0.022, "jump_intensity": 0.03, "jump_mean": -0.005},
        "BEAR":     {"mu": -0.0005, "sigma": 0.028, "jump_intensity": 0.05, "jump_mean": -0.02},
        "CRASH":    {"mu": -0.002,  "sigma": 0.050, "jump_intensity": 0.10, "jump_mean": -0.05},
    }
    p = regime_params.get(regime, regime_params["SIDEWAYS"])
    mu, sigma = p["mu"], p["sigma"]
    jump_intensity, jump_mean = p["jump_intensity"], p["jump_mean"]

    dt = 1.0

    # GBM paths: shape (n_paths, n_steps)
    z = rng.standard_normal((n_paths, n_steps))
    # Jump component
    jumps = rng.poisson(jump_intensity * dt, (n_paths, n_steps))
    jump_sizes = rng.normal(jump_mean, abs(jump_mean) * 0.5, (n_paths, n_steps))
    jump_returns = jumps * jump_sizes

    log_returns = (mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z + jump_returns
    prices = initial_price * np.exp(np.cumsum(log_returns, axis=1))  # (n_paths, n_steps)

    # Simple trading simulation per gene
    stop_loss = genes.get("stop_loss_pct", 0.02)
    take_profit = genes.get("take_profit_pct", 0.04)
    position_size = genes.get("position_size_pct", 0.20)
    rsi_oversold = genes.get("rsi_oversold", 30)

    final_values = []
    for path in prices:
        capital = initial_capital
        position_qty = 0.0
        entry_price = 0.0
        for i, price in enumerate(path):
            if position_qty == 0:
                # Simple entry: buy at the start of each 20-step cycle
                if i % 20 == 0 and capital > 0:
                    invest = capital * position_size
                    position_qty = invest / price
                    entry_price = price
            else:
                pct_change = (price - entry_price) / entry_price
                if pct_change <= -stop_loss:
                    capital += position_qty * price
                    position_qty = 0.0
                elif pct_change >= take_profit:
                    capital += position_qty * price
                    position_qty = 0.0
        # Close any open position at end
        if position_qty > 0:
            capital += position_qty * path[-1]
        final_values.append(capital)

    final_values = np.array(final_values)
    threshold = initial_capital * MC_SURVIVAL_THRESHOLD
    survival_rate = float(np.mean(final_values >= threshold))
    mean_return = float(np.mean((final_values - initial_capital) / initial_capital))
    worst_case = float(np.percentile(final_values, 5))

    result = {
        "survival_rate": survival_rate,
        "mean_return": mean_return,
        "worst_case_pct": (worst_case - initial_capital) / initial_capital,
        "n_paths": n_paths,
        "regime": regime,
    }
    log.info(f"Monte Carlo: survival={survival_rate:.2%} mean_ret={mean_return:.2%}")
    return result
