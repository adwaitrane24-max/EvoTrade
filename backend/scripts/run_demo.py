import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.data.yfinance_loader import fetch_historical_data
from backend.genetic.gene import Gene
from backend.stress_test.monte_carlo import run_monte_carlo


def create_random_gene() -> Gene:
    return Gene(
        rsi_period=random.randint(5, 30),
        ma_short=random.randint(5, 15),
        ma_long=random.randint(25, 100),
        stop_loss_pct=round(random.uniform(0.02, 0.10), 3),
        take_profit_pct=round(random.uniform(0.05, 0.20), 3),
        position_size_pct=round(random.uniform(0.10, 0.40), 3)
    )


if __name__ == "__main__":
    print("=" * 65)
    print("        EVOTRADE - Genetic Algorithm Trading Bot")
    print("         STEP 2: Fitness Evaluation Demo")
    print("=" * 65)

    print("\n[1/3] Fetching BTC-USD market data...")
    df = fetch_historical_data("BTC-USD", "1y")
    print(f"      {len(df)} days loaded")

    print("\n[2/3] Creating 10 agents and scoring each one...")
    print()
    print(f"{'Agent':<10} {'RSI':>4} {'MA':>7} {'Fitness':>8} {'Return':>8} {'Trades':>7} {'WinRate':>8} {'Survival':>9}")
    print("-" * 65)

    population = []
    for i in range(10):
        gene = create_random_gene()
        mc_result = run_monte_carlo(gene, df, n_runs=5)

        g = gene.to_dict()
        population.append({
            'gene': gene,
            'fitness': mc_result['robust_fitness'],
            'mc_result': mc_result
        })

        scenario_results = mc_result['scenario_results']
        normal_result = next((r for r in scenario_results if r['scenario'] == 'normal'), {})

        print(f"Agent {i+1:<4}  {g['rsi_period']:>4}  "
              f"{g['ma_short']:>2}/{g['ma_long']:<3}  "
              f"{mc_result['robust_fitness']:>8.4f}  "
              f"{normal_result.get('profit_pct', 0):>+7.1f}%  "
              f"{normal_result.get('total_trades', 0):>7}  "
              f"{normal_result.get('win_rate', 0):>7.1f}%  "
              f"{mc_result['survival_rate']:>8.0%}")

    print("-" * 65)

    print("\n[3/3] Ranking agents by fitness score...")
    population.sort(key=lambda x: x['fitness'], reverse=True)

    print()
    print("  SURVIVORS (Top 3):")
    for i, agent in enumerate(population[:3]):
        g = agent['gene'].to_dict()
        print(f"  #{i+1} Agent | Fitness: {agent['fitness']:.4f} | "
              f"RSI:{g['rsi_period']} MA:{g['ma_short']}/{g['ma_long']} | "
              f"Best in: {agent['mc_result']['best_scenario']}")

    print()
    print("  ELIMINATED (Bottom 7):")
    for agent in population[3:]:
        g = agent['gene'].to_dict()
        print(f"  ✗ Fitness: {agent['fitness']:.4f} | "
              f"Worst in: {agent['mc_result']['worst_scenario']}")

    print()
    print("=" * 65)
    print(f"  Best Agent Fitness Score: {population[0]['fitness']:.4f}")
    print(f"  Best Agent Genes: {population[0]['gene'].to_dict()}")
    print()
    print("  Next step: Crossover + Mutation -> Evolution Loop")
    print("=" * 65)
