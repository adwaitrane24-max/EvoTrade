"""
Rule-based market regime detector using rolling statistics.
Pure NumPy — no compiled extensions required.
Classifies price series into BULL / BEAR / SIDEWAYS / CRASH.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from app.utils.logger import get_logger

log = get_logger(__name__)

REGIMES = ["BULL", "BEAR", "SIDEWAYS", "CRASH"]


class HMMRegimeDetector:
    """
    Lightweight rule-based regime detector.
    Uses rolling 20-bar momentum, volatility, and trend to assign regime labels.
    Compatible API with the hmmlearn-based version so routers don't change.
    """

    def __init__(self):
        self.trained: bool = False
        self.current_regime: str = "SIDEWAYS"
        self.current_confidence: float = 0.70
        # Thresholds calibrated on typical BTC daily volatility
        self._vol_crash_threshold: float = 0.05     # >5% daily vol → CRASH regime
        self._vol_bear_threshold: float = 0.025     # >2.5% daily vol + neg trend → BEAR
        self._mom_bull_threshold: float = 0.02      # >2% 20-bar momentum → BULL
        self._mom_bear_threshold: float = -0.02     # <-2% 20-bar momentum → BEAR

    def load(self) -> bool:
        # No model file needed — pure rules
        self.trained = True
        return True

    def train(self, df: pd.DataFrame):
        """Analyse the historical DF to set adaptive thresholds."""
        try:
            # Flatten MultiIndex columns (yfinance >= 0.2.38)
            if isinstance(df.columns, pd.MultiIndex):
                df = df.copy()
                df.columns = df.columns.get_level_values(0)
            close = df["Close"] if "Close" in df.columns else df["close"]
            close = close.squeeze()  # ensure 1-D Series if multi-column edge case
            log_ret = np.log(close / close.shift(1)).dropna()
            self._vol_crash_threshold = float(log_ret.abs().quantile(0.95))
            self._vol_bear_threshold = float(log_ret.abs().quantile(0.75))
            self._mom_bull_threshold = float(log_ret.rolling(20).mean().quantile(0.70))
            self._mom_bear_threshold = float(log_ret.rolling(20).mean().quantile(0.30))
            self.trained = True
            log.info(
                f"Regime detector calibrated: crash_vol>={self._vol_crash_threshold:.3f}, "
                f"bull_mom>={self._mom_bull_threshold:.4f}"
            )
        except Exception as e:
            log.warning(f"Regime calibration failed: {e}")
            self.trained = True  # Use defaults

    def predict_current_regime(self, candles: list) -> Dict[str, Any]:
        if len(candles) < 25:
            return {"regime": self.current_regime, "confidence": self.current_confidence}
        try:
            closes = np.array([c["close"] for c in candles[-50:]], dtype=float)
            log_rets = np.diff(np.log(closes + 1e-8))

            vol_20 = float(np.std(log_rets[-20:]))
            mom_20 = float(np.mean(log_rets[-20:]))
            vol_5 = float(np.std(log_rets[-5:]))

            # Regime classification rules
            if vol_5 >= self._vol_crash_threshold or vol_5 >= 0.05:
                regime = "CRASH"
                confidence = min(0.95, 0.6 + (vol_5 - 0.04) * 10)
            elif mom_20 >= self._mom_bull_threshold and vol_20 < 0.03:
                regime = "BULL"
                confidence = min(0.92, 0.65 + mom_20 * 5)
            elif mom_20 <= self._mom_bear_threshold and vol_20 >= self._vol_bear_threshold:
                regime = "BEAR"
                confidence = min(0.90, 0.60 + abs(mom_20) * 5)
            else:
                regime = "SIDEWAYS"
                confidence = max(0.55, 0.80 - vol_20 * 5)

            self.current_regime = regime
            self.current_confidence = float(np.clip(confidence, 0.5, 0.95))
            return {"regime": regime, "confidence": self.current_confidence}
        except Exception as e:
            log.warning(f"Regime prediction error: {e}")
            return {"regime": self.current_regime, "confidence": self.current_confidence}


hmm_detector = HMMRegimeDetector()
