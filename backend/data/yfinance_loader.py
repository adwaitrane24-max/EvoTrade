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

if __name__ == "__main__":
    df = fetch_historical_data("BTC-USD", "1y")
    print(df.head(3))
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
