import yfinance as yf
import pandas as pd


def fetch_historical_data(symbol="BTC-USD", period="1y") -> pd.DataFrame:
    """Fetch historical OHLCV data from Yahoo Finance."""
    print(f"Fetching {symbol} data...")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
    df.dropna(inplace=True)
    print(f"Data loaded successfully: {df.shape[0]} rows, {df.shape[1]} columns")
    return df


class YFinanceLoader:
    """Class-based wrapper around fetch_historical_data for use in main.py."""

    # Map ccxt-style symbols to yfinance tickers
    _SYMBOL_MAP = {
        "BTC/USDT": "BTC-USD",
        "ETH/USDT": "ETH-USD",
        "SOL/USDT": "SOL-USD",
        "BNB/USDT": "BNB-USD",
    }

    def __init__(self, symbol: str = "BTC/USDT") -> None:
        self.symbol = symbol
        self._yf_symbol = self._SYMBOL_MAP.get(symbol, symbol.replace("/", "-"))

    def fetch(self, period_days: int = 365) -> pd.DataFrame:
        if period_days <= 30:
            period = "1mo"
        elif period_days <= 90:
            period = "3mo"
        elif period_days <= 180:
            period = "6mo"
        elif period_days <= 365:
            period = "1y"
        elif period_days <= 730:
            period = "2y"
        else:
            period = "5y"
        return fetch_historical_data(self._yf_symbol, period)

if __name__ == "__main__":
    df = fetch_historical_data("BTC-USD", "1y")
    print(df.head(3))
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
