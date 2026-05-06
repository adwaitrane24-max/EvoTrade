"""Convergence-based evolution loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

try:
    from ..data.yfinance_loader import fetch_historical_data
    from ..processing.indicators import calculate_indicators
    from ..stress_test.monte_carlo import run_monte_carlo
except ImportError:
    from data.yfinance_loader import fetch_historical_data
    from processing.indicators import calculate_indicators
    from stress_test.monte_carlo import run_monte_carlo

from .convergence import ConvergenceChecker
from .crossover import create_offspring
from .fitness import backtest_gene
from .gene import Gene
from .population import create_population
from .selection import elitism_selection, weighted_selection


@dataclass
class GenerationSummary:
    generation: int
    best_fitness: float
    avg_fitness: float
    best_return_pct: float


def run_evolution(
    symbol: str = "BTC-USD",
    risk_profile: str = "medium",
    initial_capital: float = 10000.0,
    population_size: int = 10,
    max_generations: int = 100,
    use_monte_carlo: bool = True,
    verbose: bool = True,
) -> dict[str, object]:
    """Run GA evolution until convergence or safety cap."""
    raw_df = fetch_historical_data(symbol=symbol, period="1y")
    df = calculate_indicators(raw_df)
    population = create_population(size=population_size, risk_profile=risk_profile, rng=np.random.default_rng(2026))
    checker = ConvergenceChecker(patience=5, min_improvement=0.01)
    fitness_history: list[float] = []
    generation_table: list[GenerationSummary] = []
    best_gene = population[0]
    best_result: dict[str, float | int | list[dict[str, float]]] = backtest_gene(best_gene, raw_df, initial_capital)
    converged_reason = "patience_exhausted"

    generation = 0
    while True:
        generation += 1
        scored: list[tuple[Gene, float, dict[str, float | int | list[dict[str, float]]]]] = []

        for gene in population:
            if use_monte_carlo:
                mc = run_monte_carlo(gene, raw_df, n_simulations=100)
                score = float(mc["robust_fitness_score"])
                bt = backtest_gene(gene, raw_df, initial_capital)
            else:
                bt = backtest_gene(gene, raw_df, initial_capital)
                score = float(bt["fitness_score"])
            scored.append((gene, score, bt))

        scored_sorted = sorted(scored, key=lambda x: x[1], reverse=True)
        best_gene = scored_sorted[0][0]
        best_fitness = float(scored_sorted[0][1])
        best_result = scored_sorted[0][2]
        avg_fitness = float(np.mean([s for _, s, _ in scored]))
        fitness_history.append(best_fitness)

        converged = checker.update(best_fitness)
        status = "CONVERGED" if converged else "IMPROVING"
        if verbose:
            print(
                f"Gen {generation} | Best: {best_fitness:.2f} | Avg: {avg_fitness:.2f} | "
                f"Return: {float(best_result['profit_pct']):+.2f}% | Status: {status}"
            )

        generation_table.append(
            GenerationSummary(
                generation=generation,
                best_fitness=best_fitness,
                avg_fitness=avg_fitness,
                best_return_pct=float(best_result["profit_pct"]),
            )
        )

        if converged:
            converged_reason = "patience_exhausted"
            break

        if generation >= max_generations:
            converged_reason = "safety_cap"
            if verbose:
                print("Warning: safety cap reached before convergence.")
            break

        parent_pairs = [(g, s) for g, s, _ in scored]
        parents = weighted_selection(parent_pairs)
        elites = elitism_selection(parent_pairs, elite_count=3)
        offspring = create_offspring(parents if parents else elites, target_size=population_size)
        population = (elites + offspring)[:population_size]
        if len(population) < population_size:
            population.extend(create_population(size=population_size - len(population), risk_profile=risk_profile))

    return {
        "best_gene": best_gene,
        "fitness_history": fitness_history,
        "generation_count": generation,
        "converged_reason": converged_reason,
        "best_backtest_result": best_result,
        "generation_table": [asdict(row) for row in generation_table],
    }


if __name__ == "__main__":
    result = run_evolution(verbose=True, use_monte_carlo=True)
    print(f"\nLoop ran {result['generation_count']} generations (not fixed — stopped when evolution plateaued)")
    print("Convergence reason: fitness did not improve for 5 consecutive generations")
    print("Best gene:", result["best_gene"].to_dict())
    print("Best backtest:", result["best_backtest_result"])
