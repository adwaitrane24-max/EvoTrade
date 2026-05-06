"""
mutation.py — Mutation operators for genetic algorithm diversity maintenance.
"""

from __future__ import annotations

import logging
import random
from typing import Optional

from genetic.gene import Gene

logger = logging.getLogger(__name__)


def gaussian_mutate(
    gene: Gene,
    mutation_rate: float = 0.15,
    sigma_fraction: float = 0.10,
) -> Gene:
    """
    Apply Gaussian perturbation to each float parameter with probability mutation_rate.
    Integer parameters use uniform ±offset.

    Args:
        gene: Source Gene to mutate.
        mutation_rate: Per-parameter mutation probability.
        sigma_fraction: Standard deviation as a fraction of the parameter's valid range.

    Returns:
        New mutated Gene (source is not modified).
    """
    return gene.mutate(mutation_rate=mutation_rate)


def boundary_mutate(gene: Gene) -> Gene:
    """
    Reset one randomly chosen parameter to a boundary (min or max) value.
    Useful for escaping local optima by pushing toward extreme configurations.

    Args:
        gene: Source Gene.

    Returns:
        New Gene with one parameter at its boundary.
    """
    d = gene.to_dict()
    bounds = {
        "rsi_period":        (5,    30,   True),
        "ma_short":          (5,    50,   True),
        "ma_long":           (20,  200,   True),
        "stop_loss_pct":     (0.01, 0.10, False),
        "take_profit_pct":   (0.01, 0.20, False),
        "position_size_pct": (0.01, 0.50, False),
    }
    key = random.choice(list(bounds.keys()))
    lo, hi, is_int = bounds[key]
    d[key] = (lo if random.random() < 0.5 else hi)
    if is_int:
        d[key] = int(d[key])
    return Gene.from_dict(d)


def adaptive_mutate(
    gene: Gene,
    generation: int,
    max_generations: int,
    base_rate: float = 0.20,
    min_rate: float = 0.05,
) -> Gene:
    """
    Reduce mutation rate as evolution progresses (exploitation > exploration).

    Args:
        gene: Gene to mutate.
        generation: Current generation index (0-based).
        max_generations: Total planned generations.
        base_rate: Starting mutation rate.
        min_rate: Floor mutation rate.

    Returns:
        Mutated Gene.
    """
    decay = (max_generations - generation) / max_generations
    rate = max(min_rate, base_rate * decay)
    logger.debug("Generation %d: adaptive mutation rate = %.3f", generation, rate)
    return gene.mutate(mutation_rate=rate)


def apply_mutations(
    offspring: list[Gene],
    mutation_rate: float = 0.15,
    generation: Optional[int] = None,
    max_generations: Optional[int] = None,
) -> list[Gene]:
    """
    Apply mutations to an entire offspring list.

    Uses adaptive mutation if generation info is provided, otherwise gaussian.

    Args:
        offspring: List of child Genes produced by crossover.
        mutation_rate: Base per-parameter mutation rate.
        generation: Current generation (enables adaptive mode).
        max_generations: Total generations (enables adaptive mode).

    Returns:
        New list of mutated Genes.
    """
    mutated: list[Gene] = []
    for gene in offspring:
        if generation is not None and max_generations is not None:
            m = adaptive_mutate(gene, generation, max_generations, base_rate=mutation_rate)
        else:
            m = gaussian_mutate(gene, mutation_rate=mutation_rate)
        mutated.append(m)
    return mutated


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    g = Gene.random()
    print("Original:", g.to_dict())
    print("Gaussian mutated:", gaussian_mutate(g).to_dict())
    print("Boundary mutated:", boundary_mutate(g).to_dict())
    print("Adaptive (gen 5/50):", adaptive_mutate(g, 5, 50).to_dict())
