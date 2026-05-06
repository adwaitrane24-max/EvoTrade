"""
markov_detector.py — Hidden Markov Model market regime classifier.
Uses hmmlearn GaussianHMM with 4 hidden states mapped to bull/bear/sideways/crash.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from hmmlearn import hmm

logger = logging.getLogger(__name__)

# Ordered from most-bullish to most-bearish expected return per state
_REGIME_LABELS = ["bull", "sideways", "bear", "crash"]


class MarkovDetector:
    """
    Trains a Gaussian HMM on rolling price+volume features and infers
    the current market regime.

    The 4 hidden states are mapped to human-readable labels by sorting
    on mean log-return: highest return → "bull", lowest → "crash".

    Attributes:
        n_components: Number of HMM hidden states (always 4).
        model: Fitted hmmlearn GaussianHMM instance.
    """

    def __init__(self, n_components: int = 4, random_state: int = 42) -> None:
        self.n_components = n_components
        self.random_state = random_state
        self.model: Optional[hmm.GaussianHMM] = None
        self._state_to_regime: dict[int, str] = {}

    def _build_features(
        self,
        price_series: pd.Series,
        volume_series: pd.Series,
        window: int = 30,
    ) -> np.ndarray:
        """
        Construct a (T, 3) feature matrix: [log_return, rolling_vol, norm_volume].

        Args:
            price_series: Close prices indexed by datetime.
            volume_series: Volume indexed by datetime.
            window: Rolling window for volatility calculation.

        Returns:
            2-D numpy array of shape (T, 3), no NaN rows.
        """
        log_ret = np.log(price_series / price_series.shift(1))
        rolling_vol = log_ret.rolling(window).std()
        norm_vol = (volume_series - volume_series.mean()) / (volume_series.std() + 1e-9)

        features = pd.DataFrame(
            {"log_return": log_ret, "volatility": rolling_vol, "norm_volume": norm_vol}
        )
        features.dropna(inplace=True)
        return features.values

    def fit(
        self,
        price_series: pd.Series,
        volume_series: pd.Series,
        n_iter: int = 100,
    ) -> "MarkovDetector":
        """
        Fit the HMM on historical data.

        Args:
            price_series: Historical close prices.
            volume_series: Historical volume.
            n_iter: EM iterations for HMM training.

        Returns:
            self (for chaining).
        """
        X = self._build_features(price_series, volume_series)

        self.model = hmm.GaussianHMM(
            n_components=self.n_components,
            covariance_type="full",
            n_iter=n_iter,
            random_state=self.random_state,
        )
        self.model.fit(X)

        # Map hidden states to regime labels by mean log-return (descending)
        mean_returns = self.model.means_[:, 0]  # first feature = log_return
        sorted_states = np.argsort(mean_returns)[::-1]  # highest first

        self._state_to_regime = {}
        for rank, state_idx in enumerate(sorted_states):
            label = _REGIME_LABELS[rank] if rank < len(_REGIME_LABELS) else f"state_{rank}"
            self._state_to_regime[int(state_idx)] = label

        logger.info("HMM fitted. State→regime map: %s", self._state_to_regime)
        return self

    def detect(
        self,
        price_series: pd.Series,
        volume_series: pd.Series,
    ) -> str:
        """
        Infer the current market regime from recent price/volume data.

        Args:
            price_series: Recent close prices (minimum ~35 rows recommended).
            volume_series: Corresponding volume data.

        Returns:
            One of: "bull", "bear", "sideways", "crash".

        Raises:
            RuntimeError: If fit() has not been called.
        """
        if self.model is None:
            raise RuntimeError("Call fit() before detect().")

        X = self._build_features(price_series, volume_series)
        if len(X) == 0:
            logger.warning("Not enough data to detect regime; defaulting to 'sideways'.")
            return "sideways"

        hidden_states = self.model.predict(X)
        current_state = int(hidden_states[-1])
        regime = self._state_to_regime.get(current_state, "sideways")
        logger.debug("Current hidden state %d → regime '%s'", current_state, regime)
        return regime

    def detect_sequence(
        self,
        price_series: pd.Series,
        volume_series: pd.Series,
    ) -> list[str]:
        """Return regime label for every time step (useful for visualization)."""
        if self.model is None:
            raise RuntimeError("Call fit() before detect_sequence().")
        X = self._build_features(price_series, volume_series)
        hidden_states = self.model.predict(X)
        return [self._state_to_regime.get(int(s), "sideways") for s in hidden_states]


if __name__ == "__main__":
    import yfinance as yf

    logging.basicConfig(level=logging.INFO)
    df = yf.Ticker("BTC-USD").history(period="2y")
    detector = MarkovDetector()
    detector.fit(df["Close"], df["Volume"])
    regime = detector.detect(df["Close"].tail(60), df["Volume"].tail(60))
    print(f"Current regime: {regime}")
