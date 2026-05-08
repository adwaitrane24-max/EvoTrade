import pandas as pd
import numpy as np
from backend.genetic.gene import Gene
from backend.genetic.fitness import backtest_gene
from backend.stress_test.scenarios import get_all_scenarios


def run_monte_carlo(gene: Gene, df: pd.DataFrame, n_runs: int = 5) -> dict:
    """
    Test one agent across multiple market scenarios.
    Returns average fitness and survival rate.
    n_runs kept small (5) for speed - enough for demo.
    """
    scenarios = get_all_scenarios(df)
    results = []
    
    for scenario_name, scenario_df in scenarios.items():
        try:
            result = backtest_gene(gene, scenario_df)
            result['scenario'] = scenario_name
            results.append(result)
        except Exception as e:
            print(f"  Warning: scenario {scenario_name} failed: {e}")
            continue
    
    if not results:
        return {
            'avg_fitness': 0.0,
            'survival_rate': 0.0,
            'robust_fitness': 0.0,
            'scenario_results': []
        }
    
    fitness_scores = [r['fitness_score'] for r in results]
    profitable = [r for r in results if r['profit_pct'] > 0]
    
    avg_fitness = float(np.mean(fitness_scores))
    survival_rate = len(profitable) / len(results)
    robust_fitness = avg_fitness * survival_rate
    
    return {
        'avg_fitness': round(avg_fitness, 4),
        'survival_rate': round(survival_rate, 2),
        'robust_fitness': round(robust_fitness, 4),
        'best_scenario': max(results, key=lambda x: x['fitness_score'])['scenario'],
        'worst_scenario': min(results, key=lambda x: x['fitness_score'])['scenario'],
        'scenario_results': results
    }


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from backend.data.yfinance_loader import fetch_historical_data
    
    df = fetch_historical_data("BTC-USD", "1y")
    gene = Gene()
    result = run_monte_carlo(gene, df)
    print(f"Monte Carlo Result:")
    print(f"  Avg Fitness:    {result['avg_fitness']}")
    print(f"  Survival Rate:  {result['survival_rate']}")
    print(f"  Robust Fitness: {result['robust_fitness']}")
    print(f"  Best Scenario:  {result['best_scenario']}")
    print(f"  Worst Scenario: {result['worst_scenario']}")