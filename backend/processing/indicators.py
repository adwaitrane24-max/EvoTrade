"""Indicator calculation helpers for EvoTrade."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import talib  # type: ignore
except Exception:  # pragma: no cover - runtime availability
    talib = None


def _rsi_fallback(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add core indicators to an OHLCV dataframe.

    Adds: RSI_14, MA_short, MA_long, MA_20, BB_upper, BB_lower.
    """
    if "Close" not in df.columns:
        raise ValueError("Input dataframe must contain 'Close' column.")

    out = df.copy()
    close = out["Close"].astype(float)

    try:
        if talib is None:
            raise RuntimeError("TA-Lib not available")
        out["RSI_14"] = talib.RSI(close.values, timeperiod=14)
        out["MA_short"] = talib.SMA(close.values, timeperiod=10)
        out["MA_long"] = talib.SMA(close.values, timeperiod=50)
        out["MA_20"] = talib.SMA(close.values, timeperiod=20)
        bb_upper, _bb_mid, bb_lower = talib.BBANDS(
            close.values,
            timeperiod=20,
            nbdevup=2.0,
            nbdevdn=2.0,
            matype=0,
        )
        out["BB_upper"] = bb_upper
        out["BB_lower"] = bb_lower
    except Exception as exc:
        logger.warning("TA-Lib indicator calculation failed; using pandas fallback: %s", exc)
        out["RSI_14"] = _rsi_fallback(close, 14)
        out["MA_short"] = close.rolling(10, min_periods=10).mean()
        out["MA_long"] = close.rolling(50, min_periods=50).mean()
        out["MA_20"] = close.rolling(20, min_periods=20).mean()
        std20 = close.rolling(20, min_periods=20).std(ddof=0)
        out["BB_upper"] = out["MA_20"] + (2.0 * std20)
        out["BB_lower"] = out["MA_20"] - (2.0 * std20)

    out = out.dropna().copy()
    return out


if __name__ == "__main__":
    try:
        from ..data.yfinance_loader import fetch_historical_data
    except ImportError:
        from data.yfinance_loader import fetch_historical_data

    sample = fetch_historical_data("BTC-USD", "1y")
    with_indicators = calculate_indicators(sample)
    print(with_indicators[["Close", "RSI_14", "MA_short", "MA_long", "BB_upper", "BB_lower"]].head(5))
