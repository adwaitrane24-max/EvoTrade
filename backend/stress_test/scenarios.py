import pandas as pd
import numpy as np
import random


def simulate_crash(df: pd.DataFrame, crash_pct: float = 0.30) -> pd.DataFrame:
    """Inject a sudden price crash into the data."""
    crashed = df.copy()
    crash_point = random.randint(50, len(df) - 50)
    duration = random.randint(5, 15)
    for i in range(duration):
        if crash_point + i < len(crashed):
            factor = 1 - (crash_pct * (i + 1) / duration)
            crashed.iloc[crash_point + i, crashed.columns.get_loc('Close')] *= factor
    return crashed


def simulate_pump(df: pd.DataFrame, pump_pct: float = 0.30) -> pd.DataFrame:
    """Inject a sudden price pump into the data."""
    pumped = df.copy()
    pump_point = random.randint(50, len(df) - 50)
    duration = random.randint(3, 8)
    for i in range(duration):
        if pump_point + i < len(pumped):
            factor = 1 + (pump_pct * (i + 1) / duration)
            pumped.iloc[pump_point + i, pumped.columns.get_loc('Close')] *= factor
    return pumped


def simulate_sideways(df: pd.DataFrame) -> pd.DataFrame:
    """Make market flat - reduce volatility for a period."""
    sideways = df.copy()
    start = random.randint(30, len(df) - 60)
    duration = random.randint(20, 40)
    avg_price = float(sideways['Close'].iloc[start])
    for i in range(duration):
        if start + i < len(sideways):
            noise = avg_price * random.uniform(-0.005, 0.005)
            sideways.iloc[start + i, sideways.columns.get_loc('Close')] = avg_price + noise
    return sideways


def get_all_scenarios(df: pd.DataFrame) -> dict:
    """Return all 5 test scenarios."""
    return {
        'normal': df,
        'small_crash': simulate_crash(df, crash_pct=0.10),
        'big_crash': simulate_crash(df, crash_pct=0.40),
        'pump': simulate_pump(df, pump_pct=0.30),
        'sideways': simulate_sideways(df)
    }


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from backend.data.yfinance_loader import fetch_historical_data
    df = fetch_historical_data("BTC-USD", "1y")
    scenarios = get_all_scenarios(df)
    print("Scenarios created:")
    for name, data in scenarios.items():
        print(f"  {name}: {len(data)} rows")