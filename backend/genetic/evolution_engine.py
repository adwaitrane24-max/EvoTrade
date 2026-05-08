import json
import os
import random
from datetime import datetime

from backend.data.yfinance_loader import fetch_historical_data
from backend.genetic.gene import Gene
from backend.genetic.fitness import backtest_gene
from backend.genetic.crossover import create_offspring
from backend.genetic.convergence import ConvergenceChecker
from backend.stress_test.monte_carlo import run_monte_carlo

_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'outputs')
_LOG_FILE = os.path.join(_OUTPUT_DIR, 'evolution_log.json')


def _ensure_output_dir() -> None:
    os.makedirs(_OUTPUT_DIR, exist_ok=True)


def _append_generation_log(entry: dict) -> None:
    _ensure_output_dir()
    existing: list = []
    if os.path.exists(_LOG_FILE):
        try:
            with open(_LOG_FILE, 'r') as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []
    existing.append(entry)
    with open(_LOG_FILE, 'w') as f:
        json.dump(existing, f, indent=2)


def _make_population(size: int) -> list[Gene]:
    """Create a population of random Gene objects using Gene defaults + randomness."""
    population = []
    for _ in range(size):
        gene = Gene(
            rsi_period=random.randint(5, 30),
            ma_short=random.randint(5, 20),
            ma_long=random.randint(21, 100),
            stop_loss_pct=round(random.uniform(0.02, 0.10), 3),
            take_profit_pct=round(random.uniform(0.05, 0.20), 3),
            position_size_pct=round(random.uniform(0.10, 0.40), 3),
        )
        population.append(gene)
    return population


def run_evolution(
    symbol: str = "BTC-USD",
    risk_profile: str = "medium",
    initial_capital: float = 10000.0,
    population_size: int = 10,
    max_generations: int = 100,
    verbose: bool = True,
) -> dict:
    """
    Run the full genetic algorithm evolution loop until convergence or max_generations.

    Returns dict with:
        best_gene          : Gene object
        best_fitness       : float
        generations_run    : int
        fitness_history    : list of floats (best fitness per generation)
        convergence_reason : str
        best_result        : dict from backtest_gene()
    """
    # ── Step 1: Fetch data ────────────────────────────────────────────────────
    df = fetch_historical_data(symbol=symbol, period="2y")

    # ── Step 2: Create initial population ────────────────────────────────────
    population = _make_population(population_size)

    checker = ConvergenceChecker(patience=5, min_improvement=0.005)
    fitness_history: list[float] = []
    best_gene: Gene = population[0]
    best_fitness: float = float("-inf")
    convergence_reason: str = "max_generations_reached"

    if verbose:
        print(f"\n  {'Gen':>4}  {'Best':>9}  {'Avg':>9}  {'Stale':>6}  {'Status'}")
        print(f"  {'-' * 52}")

    # ── Step 3: Evolution loop ────────────────────────────────────────────────
    generation = 0
    while generation < max_generations:
        generation += 1

        # a. Score every gene via Monte Carlo
        scored: list[tuple[Gene, float]] = []
        for gene in population:
            mc = run_monte_carlo(gene, df, n_runs=5)
            score = float(mc["robust_fitness"])
            scored.append((gene, score))

        # b. Sort descending by fitness
        scored.sort(key=lambda x: x[1], reverse=True)

        gen_best_fitness = scored[0][1]
        gen_avg_fitness = sum(s for _, s in scored) / len(scored)

        # Track global best
        if gen_best_fitness > best_fitness:
            best_fitness = gen_best_fitness
            best_gene = scored[0][0]

        fitness_history.append(gen_best_fitness)

        # c. Top 3 survivors (elitism)
        survivors = [gene for gene, _ in scored[:3]]

        # d. Update convergence checker
        converged = checker.update(gen_best_fitness)
        stale = checker._stale_count
        status = checker.get_status()

        # h. Save generation to JSON log
        _append_generation_log({
            "generation": generation,
            "best_fitness": round(gen_best_fitness, 4),
            "avg_fitness": round(gen_avg_fitness, 4),
            "top_gene": survivors[0].to_dict(),
            "population_size": len(population),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        })

        # i. Verbose output
        if verbose:
            print(f"  {generation:>4}  {gen_best_fitness:>9.4f}  {gen_avg_fitness:>9.4f}  {stale:>6}  {status}")

        # e. Convergence check
        if converged:
            convergence_reason = "patience_exhausted"
            if verbose:
                print(f"\n  Converged after {generation} generations (no improvement for {checker.patience} gens).")
            break

        # f. Create offspring to fill population back to target size
        offspring = create_offspring(survivors, target_size=population_size)

        # g. New population = survivors + offspring
        population = (survivors + offspring)[:population_size]

    # ── Step 4: Final backtest of best gene ───────────────────────────────────
    best_result = backtest_gene(best_gene, df, initial_capital=initial_capital)

    return {
        "best_gene": best_gene,
        "best_fitness": round(best_fitness, 4),
        "generations_run": generation,
        "fitness_history": [round(f, 4) for f in fitness_history],
        "convergence_reason": convergence_reason,
        "best_result": best_result,
    }


if __name__ == "__main__":
    result = run_evolution(symbol="BTC-USD", risk_profile="medium", verbose=True, max_generations=20)
    print("\nBest gene:", result["best_gene"].to_dict())
    print("Best fitness:", result["best_fitness"])
    print("Generations run:", result["generations_run"])
    print("Convergence reason:", result["convergence_reason"])
