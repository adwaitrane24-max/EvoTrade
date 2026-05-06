"""Population creation utilities."""

from __future__ import annotations

from typing import Literal

import numpy as np

from .gene import Gene

GENE_BOUNDS: dict[str, tuple[float, float]] = {
    "rsi_period": (5, 30),
    "ma_short": (5, 50),
    "ma_long": (20, 200),
    "stop_loss_pct": (0.01, 0.10),
    "take_profit_pct": (0.01, 0.20),
    "position_size_pct": (0.01, 0.50),
}

RiskProfile = Literal["low", "medium", "high"]


def _sample_gene(bounds: dict[str, tuple[float, float]], rng: np.random.Generator) -> Gene:
    gene = Gene(
        rsi_period=int(rng.integers(bounds["rsi_period"][0], bounds["rsi_period"][1] + 1)),
        ma_short=int(rng.integers(bounds["ma_short"][0], bounds["ma_short"][1] + 1)),
        ma_long=int(rng.integers(bounds["ma_long"][0], bounds["ma_long"][1] + 1)),
        stop_loss_pct=float(rng.uniform(*bounds["stop_loss_pct"])),
        take_profit_pct=float(rng.uniform(*bounds["take_profit_pct"])),
        position_size_pct=float(rng.uniform(*bounds["position_size_pct"])),
    )
    return gene.validate()


def create_random_gene(rng: np.random.Generator | None = None) -> Gene:
    """Create one random gene within standard bounds."""
    local_rng = rng or np.random.default_rng()
    return _sample_gene(GENE_BOUNDS, local_rng)


def create_population(
    size: int = 10,
    risk_profile: RiskProfile = "medium",
    rng: np.random.Generator | None = None,
) -> list[Gene]:
    """Create a population using bounds tuned by risk profile."""
    local_rng = rng or np.random.default_rng(42)

    bounds = {k: (v[0], v[1]) for k, v in GENE_BOUNDS.items()}
    if risk_profile == "low":
        bounds["position_size_pct"] = (0.01, 0.15)
        bounds["stop_loss_pct"] = (0.01, 0.05)
        bounds["take_profit_pct"] = (0.02, 0.12)
    elif risk_profile == "high":
        bounds["position_size_pct"] = (0.20, 0.50)
        bounds["stop_loss_pct"] = (0.05, 0.10)
        bounds["take_profit_pct"] = (0.08, 0.20)

    return [_sample_gene(bounds, local_rng) for _ in range(size)]


if __name__ == "__main__":
    pop = create_population(size=10, risk_profile="medium", rng=np.random.default_rng(99))
    for idx, g in enumerate(pop, start=1):
        print(f"Agent {idx:02d}: {g.to_dict()}")
