"""Technical indicator computations using the `ta` library."""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from app.utils.logger import get_logger

log = get_logger(__name__)


def candles_to_df(candles: List[Dict[str, Any]]) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame()
    df = pd.DataFrame(candles)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.dropna(subset=["close"])
    return df


def compute_indicators(candles: List[Dict[str, Any]], ma_short: int = 9, ma_long: int = 21) -> Dict[str, Any]:
    """Return latest indicator values given a list of candle dicts."""
    df = candles_to_df(candles)
    if len(df) < max(ma_long, 30):
        return {"rsi": 50.0, "ma_short": 0.0, "ma_long": 0.0, "bb_upper": 0.0, "bb_lower": 0.0, "price": 0.0}

    try:
        import ta
        close = df["close"]
        rsi_series = ta.momentum.RSIIndicator(close, window=14).rsi()
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)

        ma_s = close.rolling(window=ma_short).mean()
        ma_l = close.rolling(window=ma_long).mean()

        return {
            "rsi": float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0,
            "ma_short": float(ma_s.iloc[-1]) if not pd.isna(ma_s.iloc[-1]) else 0.0,
            "ma_long": float(ma_l.iloc[-1]) if not pd.isna(ma_l.iloc[-1]) else 0.0,
            "bb_upper": float(bb.bollinger_hband().iloc[-1]),
            "bb_lower": float(bb.bollinger_lband().iloc[-1]),
            "price": float(close.iloc[-1]),
        }
    except Exception as e:
        log.warning(f"Indicator computation error: {e}")
        return {"rsi": 50.0, "ma_short": 0.0, "ma_long": 0.0, "bb_upper": 0.0, "bb_lower": 0.0, "price": float(df["close"].iloc[-1]) if len(df) else 0.0}


def compute_features_for_hmm(df: pd.DataFrame) -> np.ndarray:
    """4-feature matrix for HMM: log_return, rolling_vol, ma_slope, volume_zscore."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    close = (df["Close"] if "Close" in df.columns else df["close"]).squeeze()
    volume = (df["Volume"] if "Volume" in df.columns else df["volume"]).squeeze()

    log_ret = np.log(close / close.shift(1)).fillna(0)
    rolling_vol = log_ret.rolling(20).std().fillna(0)
    ma20 = close.rolling(20).mean()
    ma_slope = (ma20 - ma20.shift(5)).fillna(0) / (close + 1e-8)
    vol_mean = volume.rolling(20).mean()
    vol_std = volume.rolling(20).std() + 1e-8
    vol_z = ((volume - vol_mean) / vol_std).fillna(0)

    features = np.column_stack([
        log_ret.values,
        rolling_vol.values,
        ma_slope.values,
        vol_z.values,
    ])
    return features
