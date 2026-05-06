"""
normalizer.py — Data cleaning and feature normalization for ML pipeline inputs.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

logger = logging.getLogger(__name__)


class Normalizer:
    """
    Cleans OHLCV DataFrames and normalizes feature columns for HMM / ML models.

    Supports MinMax (0–1 range) and Standard (zero mean, unit variance) scaling.
    Fitted scalers are preserved so they can be applied to new streaming data.
    """

    def __init__(self, method: str = "standard") -> None:
        """
        Args:
            method: "standard" for StandardScaler, "minmax" for MinMaxScaler.
        """
        if method not in ("standard", "minmax"):
            raise ValueError("method must be 'standard' or 'minmax'")
        self.method = method
        self._scaler: StandardScaler | MinMaxScaler | None = None
        self._fitted_columns: list[str] = []

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove rows with nulls, infinite values, and duplicate timestamps.

        Args:
            df: Raw OHLCV DataFrame.

        Returns:
            Cleaned copy of the DataFrame.
        """
        original_len = len(df)
        df = df.copy()

        # Drop duplicate index entries
        df = df[~df.index.duplicated(keep="first")]

        # Replace infinities with NaN then drop
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        removed = original_len - len(df)
        if removed:
            logger.debug("Removed %d rows during cleaning.", removed)

        return df

    def fit_transform(self, df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """
        Fit the scaler on the given columns and return the normalized DataFrame.

        Args:
            df: Cleaned DataFrame.
            columns: Column names to normalize.

        Returns:
            DataFrame with specified columns replaced by normalized values.
        """
        df = df.copy()
        self._fitted_columns = columns

        if self.method == "standard":
            self._scaler = StandardScaler()
        else:
            self._scaler = MinMaxScaler()

        df[columns] = self._scaler.fit_transform(df[columns].values)
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply previously fitted scaler to new data.

        Raises:
            RuntimeError: If fit_transform has not been called yet.
        """
        if self._scaler is None:
            raise RuntimeError("Call fit_transform() before transform().")
        df = df.copy()
        df[self._fitted_columns] = self._scaler.transform(df[self._fitted_columns].values)
        return df

    def add_returns(self, df: pd.DataFrame, window: int = 1) -> pd.DataFrame:
        """
        Add log-return column derived from Close price.

        Args:
            df: DataFrame with 'Close' column.
            window: Lag for return calculation.

        Returns:
            DataFrame with 'log_return' column appended.
        """
        df = df.copy()
        df["log_return"] = np.log(df["Close"] / df["Close"].shift(window))
        df.dropna(inplace=True)
        return df

    def add_volatility(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """Add rolling volatility (std of log returns) column."""
        df = df.copy()
        if "log_return" not in df.columns:
            df = self.add_returns(df)
        df["volatility"] = df["log_return"].rolling(window).std()
        df.dropna(inplace=True)
        return df


if __name__ == "__main__":
    import yfinance as yf

    logging.basicConfig(level=logging.INFO)
    raw = yf.Ticker("BTC-USD").history(period="1y")

    norm = Normalizer(method="standard")
    cleaned = norm.clean(raw)
    with_returns = norm.add_returns(cleaned)
    with_vol = norm.add_volatility(with_returns)
    scaled = norm.fit_transform(with_vol, columns=["log_return", "volatility", "Volume"])

    print(scaled[["Close", "log_return", "volatility", "Volume"]].tail())
