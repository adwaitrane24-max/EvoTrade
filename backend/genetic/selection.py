"""Selection strategies for GA."""

from __future__ import annotations

import numpy as np

from .gene import Gene


def weighted_selection(population_with_scores: list[tuple[Gene, float]]) -> list[Gene]:
    """Roulette-wheel select up to 3 parents, weighted by fitness."""
    if not population_with_scores:
        return []
    genes = [g for g, _ in population_with_scores]
    scores = np.array([s for _, s in population_with_scores], dtype=float)
    shift = 0.0
    if np.min(scores) <= 0:
        shift = abs(np.min(scores)) + 1e-8
    probs = scores + shift
    if np.sum(probs) == 0:
        probs = np.ones_like(probs) / len(probs)
    else:
        probs = probs / np.sum(probs)

    n_pick = min(3, len(genes))
    idx = np.random.default_rng(2026).choice(len(genes), size=n_pick, replace=False, p=probs)
    return [genes[i] for i in idx]


def elitism_selection(population_with_scores: list[tuple[Gene, float]], elite_count: int = 3) -> list[Gene]:
    """Return top-N genes sorted by fitness descending."""
    sorted_items = sorted(population_with_scores, key=lambda x: x[1], reverse=True)
    return [g for g, _ in sorted_items[:max(0, elite_count)]]


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    sample = [
        (
            Gene(
                rsi_period=int(rng.integers(5, 31)),
                ma_short=int(rng.integers(5, 51)),
                ma_long=int(rng.integers(20, 201)),
                stop_loss_pct=float(rng.uniform(0.01, 0.10)),
                take_profit_pct=float(rng.uniform(0.01, 0.20)),
                position_size_pct=float(rng.uniform(0.01, 0.50)),
            ).validate(),
            float(rng.normal(10, 2)),
        )
        for _ in range(10)
    ]
    parents = weighted_selection(sample)
    elites = elitism_selection(sample, elite_count=3)
    print("Selected parents:", [p.to_dict() for p in parents])
    print("Elite count:", len(elites))
