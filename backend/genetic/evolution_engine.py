import asyncio
import json
import logging
import os
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional

try:
    from data.yfinance_loader import fetch_historical_data
    from genetic.convergence import ConvergenceChecker
    from genetic.crossover import create_offspring
    from genetic.fitness import backtest_gene
    from genetic.gene import Gene
    from stress_test.monte_carlo import run_monte_carlo
except ModuleNotFoundError:
    pass

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]

_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "outputs")
_LOG_FILE = os.path.join(_OUTPUT_DIR, "evolution_log.json")


def _ensure_output_dir() -> None:
    os.makedirs(_OUTPUT_DIR, exist_ok=True)


def _append_generation_log(entry: dict[str, Any]) -> None:
    _ensure_output_dir()
    existing: list[dict[str, Any]] = []
    if os.path.exists(_LOG_FILE):
        try:
            with open(_LOG_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []
    existing.append(entry)
    with open(_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def _normalize_symbol(symbol: str) -> str:
    return symbol.replace("/", "-").upper()


def _make_population(size: int) -> list[Gene]:
    population: list[Gene] = []
    for _ in range(size):
        population.append(
            Gene(
                rsi_period=random.randint(5, 30),
                ma_short=random.randint(5, 20),
                ma_long=random.randint(21, 100),
                stop_loss_pct=round(random.uniform(0.02, 0.10), 3),
                take_profit_pct=round(random.uniform(0.05, 0.20), 3),
                position_size_pct=round(random.uniform(0.10, 0.40), 3),
            )
        )
    return population


@dataclass
class EvolutionResult:
    alpha_gene: Gene
    best_fitness: float
    generations_run: int
    fitness_history: list[float]
    converged: bool
    convergence_reason: str
    best_result: dict[str, Any]


class EvolutionEngine:
    def __init__(
        self,
        price_df=None,
        symbol: str = "BTC-USD",
        risk_profile: str = "medium",
        initial_capital: float = 10000.0,
        population_size: int = 10,
        max_generations: int = 50,
        convergence_window: int = 5,
        min_improvement: float = 0.005,
        event_callback: Optional[EventCallback] = None,
    ) -> None:
        self.price_df = price_df
        self.symbol = _normalize_symbol(symbol)
        self.risk_profile = risk_profile
        self.initial_capital = initial_capital
        self.population_size = max(2, population_size)
        self.max_generations = max(1, max_generations)
        self.convergence_window = max(1, convergence_window)
        self.min_improvement = min_improvement
        self.event_callback = event_callback

    async def _emit(self, event: dict[str, Any]) -> None:
        if self.event_callback:
            await self.event_callback(event)

    async def run(self) -> EvolutionResult:
        df = self.price_df
        if df is None:
            df = fetch_historical_data(symbol=self.symbol, period="2y")

        population = _make_population(self.population_size)
        checker = ConvergenceChecker(
            patience=self.convergence_window,
            min_improvement=self.min_improvement,
        )

        fitness_history: list[float] = []
        best_gene = population[0]
        best_fitness = float("-inf")
        convergence_reason = "max_generations_reached"
        converged = False
        generation = 0

        for generation in range(1, self.max_generations + 1):
            scored: list[tuple[Gene, float]] = []
            for gene in population:
                mc = run_monte_carlo(gene, df, n_runs=5)
                score = float(mc.get("robust_fitness", 0.0))
                gene.fitness = score
                scored.append((gene, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            gen_best_gene, gen_best_fitness = scored[0]
            gen_avg_fitness = sum(score for _, score in scored) / len(scored)

            if gen_best_fitness > best_fitness:
                best_fitness = gen_best_fitness
                best_gene = gen_best_gene
                best_gene.fitness = gen_best_fitness

            fitness_history.append(round(gen_best_fitness, 4))

            _append_generation_log(
                {
                    "generation": generation,
                    "best_fitness": round(gen_best_fitness, 4),
                    "avg_fitness": round(gen_avg_fitness, 4),
                    "top_gene": gen_best_gene.to_dict(),
                    "population_size": len(population),
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                }
            )

            await self._emit(
                {
                    "type": "generation_complete",
                    "generation": generation,
                    "best_fitness": round(gen_best_fitness, 4),
                    "avg_fitness": round(gen_avg_fitness, 4),
                    "best_gene": gen_best_gene.to_dict(),
                    "fitness_history": fitness_history.copy(),
                }
            )

            if checker.update(gen_best_fitness):
                converged = True
                convergence_reason = "patience_exhausted"
                await self._emit(
                    {
                        "type": "converged",
                        "generation": generation,
                        "best_fitness": round(gen_best_fitness, 4),
                    }
                )
                break

            survivors = [gene for gene, _ in scored[:3]]
            offspring = create_offspring(survivors, target_size=self.population_size)
            population = (survivors + offspring)[: self.population_size]

        best_result = backtest_gene(best_gene, df, initial_capital=self.initial_capital)
        best_gene.fitness = round(best_fitness, 4)

        return EvolutionResult(
            alpha_gene=best_gene,
            best_fitness=round(best_fitness, 4),
            generations_run=generation,
            fitness_history=fitness_history,
            converged=converged,
            convergence_reason=convergence_reason,
            best_result=best_result,
        )


def run_evolution(
    symbol: str = "BTC-USD",
    risk_profile: str = "medium",
    initial_capital: float = 10000.0,
    population_size: int = 10,
    max_generations: int = 100,
    verbose: bool = True,
) -> dict[str, Any]:
    engine = EvolutionEngine(
        symbol=symbol,
        risk_profile=risk_profile,
        initial_capital=initial_capital,
        population_size=population_size,
        max_generations=max_generations,
    )
    result = asyncio.run(engine.run())

    if verbose:
        logger.info(
            "Evolution completed in %d generations (best_fitness=%.4f).",
            result.generations_run,
            result.best_fitness,
        )

    return {
        "best_gene": result.alpha_gene,
        "best_fitness": result.best_fitness,
        "generations_run": result.generations_run,
        "fitness_history": result.fitness_history,
        "convergence_reason": result.convergence_reason,
        "best_result": result.best_result,
    }


async def run_fixed_5gen_evolution(
    symbol: str = "BTC-USD",
    risk_profile: str = "medium",
    initial_capital: float = 10000.0,
    population_size: int = 10,
    n_generations: int = 5,
    ai_council: Any = None,
    on_event: Optional[EventCallback] = None,
    verbose: bool = False,
) -> dict[str, Any]:
    del ai_council  # hook for future AI-council scoring extension

    alpha_gene_per_gen: list[dict[str, Any]] = []
    fitness_history: list[float] = []

    async def _bridge(event: dict[str, Any]) -> None:
        if event.get("type") == "generation_complete":
            best_gene = event.get("best_gene")
            best_fitness = event.get("best_fitness")
            if isinstance(best_gene, dict):
                alpha_gene_per_gen.append(best_gene)
            if best_fitness is not None:
                fitness_history.append(float(best_fitness))
        if on_event:
            await on_event(event)

    engine = EvolutionEngine(
        symbol=symbol,
        risk_profile=risk_profile,
        initial_capital=initial_capital,
        population_size=population_size,
        max_generations=n_generations,
        convergence_window=max(n_generations + 1, 10),  # force fixed-N runs
        event_callback=_bridge,
    )
    result = await engine.run()

    if verbose:
        logger.info(
            "Fixed evolution completed (%d generations, best_fitness=%.4f).",
            result.generations_run,
            result.best_fitness,
        )

    return {
        "alpha_gene": result.alpha_gene.to_dict(),
        "alpha_gene_per_gen": alpha_gene_per_gen,
        "fitness_history": fitness_history or result.fitness_history,
        "best_fitness": result.best_fitness,
        "generations_run": result.generations_run,
        "converged": result.converged,
        "convergence_reason": result.convergence_reason,
        "best_result": result.best_result,
    }


if __name__ == "__main__":
    out = run_evolution(symbol="BTC-USD", risk_profile="medium", verbose=True, max_generations=20)
    print("\nBest gene:", out["best_gene"].to_dict())
    print("Best fitness:", out["best_fitness"])
    print("Generations run:", out["generations_run"])
    print("Convergence reason:", out["convergence_reason"])
