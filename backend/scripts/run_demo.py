import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.genetic.evolution_engine import run_evolution

if __name__ == "__main__":
    print("=" * 65)
    print("        EVOTRADE - Full Evolution Demo")
    print("        Loop runs until convergence automatically")
    print("=" * 65)

    result = run_evolution(
        symbol="BTC-USD",
        risk_profile="medium",
        initial_capital=10000.0,
        population_size=10,
        verbose=True
    )

    print()
    print("=" * 65)
    print("  EVOLUTION COMPLETE")
    print("=" * 65)
    print(f"  Generations Run    : {result['generations_run']}")
    print(f"  Convergence Reason : {result['convergence_reason']}")
    print(f"  Best Fitness Score : {result['best_fitness']:.4f}")
    print(f"  Best Gene Found    :")
    for k, v in result['best_gene'].to_dict().items():
        print(f"    {k}: {v}")
    print(f"  Final Capital      : ${result['best_result']['final_capital']}")
    print(f"  Total Return       : {result['best_result']['profit_pct']}%")
    print(f"  Win Rate           : {result['best_result']['win_rate']}%")
    print(f"  Sharpe Ratio       : {result['best_result']['sharpe_ratio']}")
    print()
    print("  Evolution log saved to: outputs/evolution_log.json")
    print("=" * 65)
