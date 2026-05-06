"""Stress scenario generators."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _pick_window(df: pd.DataFrame, duration_days: int, rng: np.random.Generator) -> tuple[int, int]:
    n = len(df)
    if n <= duration_days + 2:
        return 1, max(2, n - 1)
    start = int(rng.integers(1, n - duration_days))
    end = start + duration_days
    return start, end


def _apply_close_shock(df: pd.DataFrame, start: int, end: int, factors: np.ndarray) -> pd.DataFrame:
    out = df.copy()
    cols = [c for c in ["Open", "High", "Low", "Close"] if c in out.columns]
    out.iloc[start:end, out.columns.get_loc("Close")] *= factors
    if cols:
        for c in cols:
            out.iloc[start:end, out.columns.get_loc(c)] *= factors
    if "Volume" in out.columns:
        out.iloc[start:end, out.columns.get_loc("Volume")] *= np.clip(1.0 + np.abs(factors - 1.0), 1.0, None)
    return out


def simulate_crash(df: pd.DataFrame, crash_pct: float = 0.30, duration_days: int = 10) -> pd.DataFrame:
    """Inject a downward crash window into OHLCV data."""
    if df.empty:
        return df.copy()
    rng = np.random.default_rng(42)
    start, end = _pick_window(df, duration_days, rng)
    factors = np.linspace(1.0, 1.0 - crash_pct, end - start)
    return _apply_close_shock(df, start, end, factors)


def simulate_pump(df: pd.DataFrame, pump_pct: float = 0.30, duration_days: int = 5) -> pd.DataFrame:
    """Inject an upward pump window into OHLCV data."""
    if df.empty:
        return df.copy()
    rng = np.random.default_rng(84)
    start, end = _pick_window(df, duration_days, rng)
    factors = np.linspace(1.0, 1.0 + pump_pct, end - start)
    return _apply_close_shock(df, start, end, factors)


def simulate_sideways(df: pd.DataFrame, duration_days: int = 30) -> pd.DataFrame:
    """Reduce volatility over a window to emulate range-bound market."""
    if df.empty:
        return df.copy()
    out = df.copy()
    rng = np.random.default_rng(126)
    start, end = _pick_window(df, duration_days, rng)
    close = out["Close"].to_numpy(dtype=float)
    base = np.mean(close[max(0, start - 5):start + 1])
    noise = rng.normal(loc=0.0, scale=np.std(close) * 0.05, size=end - start)
    flat = np.maximum(base + noise, 1e-8)
    out.iloc[start:end, out.columns.get_loc("Close")] = flat
    for c in ["Open", "High", "Low"]:
        if c in out.columns:
            out.iloc[start:end, out.columns.get_loc(c)] = flat
    if "Volume" in out.columns:
        out.iloc[start:end, out.columns.get_loc("Volume")] *= 0.8
    return out


def get_all_scenarios(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return standard scenario variants for stress testing."""
    return {
        "normal": df.copy(),
        "small_crash": simulate_crash(df, crash_pct=0.10, duration_days=8),
        "big_crash": simulate_crash(df, crash_pct=0.40, duration_days=12),
        "pump": simulate_pump(df, pump_pct=0.30, duration_days=5),
        "sideways": simulate_sideways(df, duration_days=30),
    }


if __name__ == "__main__":
    try:
        from ..data.yfinance_loader import fetch_historical_data
    except ImportError:
        from data.yfinance_loader import fetch_historical_data

    sample = fetch_historical_data("BTC-USD", "1y")
    scenarios = get_all_scenarios(sample)
    for name, sdf in scenarios.items():
        change = ((sdf["Close"].iloc[-1] - sdf["Close"].iloc[0]) / sdf["Close"].iloc[0]) * 100.0
        print(f"{name:12} rows={len(sdf):4d} change={change:+.2f}%")
