import sys
import os
import random

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.data.yfinance_loader import fetch_historical_data
from backend.genetic.gene import Gene


def create_random_gene() -> Gene:
    """Create one agent with random gene values within standard trading bounds."""
    return Gene(
        rsi_period=random.randint(5, 30),
        ma_short=random.randint(5, 15),
        ma_long=random.randint(25, 100),
        stop_loss_pct=round(random.uniform(0.02, 0.10), 3),
        take_profit_pct=round(random.uniform(0.05, 0.20), 3),
        position_size_pct=round(random.uniform(0.10, 0.40), 3)
    )


def create_population(size: int = 10) -> list:
    """Create a population of random agents."""
    return [create_random_gene() for _ in range(size)]


if __name__ == "__main__":
    print("=" * 60)
    print("        EVOTRADE - Genetic Algorithm Trading Bot")
    print("         STEP 1: Population Initialization Demo")
    print("=" * 60)

    # Step 1: Fetch data
    print("\n[1/3] Fetching market data...")
    df = fetch_historical_data("BTC-USD", "1y")
    print(f"      Shape: {df.shape} | From {str(df.index[0])[:10]} to {str(df.index[-1])[:10]}")

    # Step 2: Create population
    print("\n[2/3] Creating population of 10 random agents...")
    print()
    print(f"{'Agent':<8} {'RSI':>4} {'MA_S':>5} {'MA_L':>5} {'StopLoss':>9} {'TakeProfit':>11} {'PositionSz':>11}")
    print("-" * 60)

    population = create_population(10)
    for i, gene in enumerate(population):
        g = gene.to_dict()
        print(f"Agent {i+1:<2}  {g['rsi_period']:>4}  {g['ma_short']:>5}  {g['ma_long']:>5}  "
              f"{g['stop_loss_pct']:>8.1%}  {g['take_profit_pct']:>10.1%}  {g['position_size_pct']:>10.1%}")

    # Step 3: Demo mutation
    print("\n[3/3] Demo: Mutating Agent 1...")
    original = population[0].to_dict()
    population[0].mutate()
    mutated = population[0].to_dict()
    
    changes = [k for k in original if original[k] != mutated[k]]
    print(f"      Changed: {changes[0] if changes else 'no change'}")
    if changes:
        print(f"      Before: {original[changes[0]]}")
        print(f"      After:  {mutated[changes[0]]}")

    print()
    print("=" * 60)
    print("  Population created successfully!")
    print(f"  Total agents: {len(population)}")
    print(f"  Data rows available for backtesting: {len(df)}")
    print()
    print("  Next step: Backtest each agent -> Calculate fitness scores")
    print("=" * 60)
