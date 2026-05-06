"""Crossover and offspring generation."""

from __future__ import annotations

import numpy as np

from .gene import Gene

_PARAM_KEYS = [
    "rsi_period",
    "ma_short",
    "ma_long",
    "stop_loss_pct",
    "take_profit_pct",
    "position_size_pct",
]


def single_point_crossover(parent1: Gene, parent2: Gene) -> Gene:
    """Create one child by single-point crossover of parent parameters."""
    rng = np.random.default_rng()
    point = int(rng.integers(1, len(_PARAM_KEYS)))
    p1 = parent1.to_dict()
    p2 = parent2.to_dict()
    child_dict: dict[str, float | int] = {}
    for i, k in enumerate(_PARAM_KEYS):
        child_dict[k] = p1[k] if i < point else p2[k]
    return Gene.from_dict(child_dict)


def create_offspring(parents: list[Gene], target_size: int = 10) -> list[Gene]:
    """Create mutated children until population reaches target size."""
    if not parents:
        return []
    rng = np.random.default_rng(2026)
    children_needed = max(0, target_size - len(parents))
    offspring: list[Gene] = []

    for _ in range(children_needed):
        if len(parents) == 1:
            p1 = p2 = parents[0]
        else:
            i, j = rng.choice(len(parents), size=2, replace=False)
            p1, p2 = parents[int(i)], parents[int(j)]
        child = single_point_crossover(p1, p2).mutate(mutation_rate=0.1, rng=rng)
        offspring.append(child)
    return offspring


if __name__ == "__main__":
    p1 = Gene()
    p2 = Gene(rsi_period=21, ma_short=18, ma_long=120, stop_loss_pct=0.03, take_profit_pct=0.15, position_size_pct=0.35)
    child = single_point_crossover(p1, p2)
    print("Parent1:", p1.to_dict())
    print("Parent2:", p2.to_dict())
    print("Child  :", child.to_dict())
    print("Offspring sample size:", len(create_offspring([p1, p2], target_size=10)))
