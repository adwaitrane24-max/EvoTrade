"""
test_evolution.py — Quick sanity-check for the GA loop.
Runs 5 generations on 6 months of BTC data and prints results.
No API keys required.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import numpy as np
from data.yfinance_loader import YFinanceLoader
from genetic.gene import Gene
from genetic.population import initialize_population
from genetic.fitness import FitnessEvaluator
from genetic.crossover import single_point_crossover
from genetic.mutation import apply_mutations
from genetic.selection import select_parents
from genetic.convergence import ConvergenceChecker


def main() -> None:
    print("=" * 60)
    print("EvoTrade — Quick GA Evolution Test")
    print("=" * 60)

    print("\n[1/4] Fetching 6 months of BTC-USD data…")
    loader = YFinanceLoader("BTC/USDT")
    df = loader.fetch(period_days=180)
    print(f"      Loaded {len(df)} daily bars.")

    print("\n[2/4] Initialising population (medium risk, 6 agents)…")
    population = initialize_population(risk_profile="medium", size=6)

    evaluator = FitnessEvaluator()
    checker = ConvergenceChecker(window=3, min_delta=0.001)

    print("\n[3/4] Running 5 generations…")
    print(f"{'Gen':>4}  {'Best':>8}  {'Avg':>8}  {'Status'}")
    print("-" * 40)

    for gen in range(1, 6):
        for gene in population:
            gene.fitness = evaluator.evaluate(gene, df)

        fitnesses = [g.fitness for g in population]
        best_f = max(fitnesses)
        avg_f  = sum(fitnesses) / len(fitnesses)
        checker.update(best_f)
        status = "CONVERGED" if checker.has_converged() else "evolving"
        print(f"{gen:>4}  {best_f:>8.4f}  {avg_f:>8.4f}  {status}")

        if checker.has_converged():
            break

        parents, elites = select_parents(population, n_parents=2, elite_count=1)
        offspring = list(elites)
        while len(offspring) < 6:
            import random
            p1, p2 = random.sample(parents + elites, k=2) if len(parents + elites) >= 2 else (parents[0], elites[0])
            c1, c2 = single_point_crossover(p1, p2)
            offspring.extend([c1, c2])
        population = apply_mutations(offspring[:6])

    best_gene = max(population, key=lambda g: g.fitness)
    print("\n[4/4] Best gene found:")
    for k, v in best_gene.to_dict().items():
        print(f"      {k:<22} {v}")

    print("\n✓ Test complete — GA loop is functional.")


if __name__ == "__main__":
    main()
