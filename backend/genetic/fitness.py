"""Backtesting and fitness scoring."""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    import talib  # type: ignore
except Exception:  # pragma: no cover
    talib = None

from .gene import Gene


def _calc_rsi(close: pd.Series, period: int) -> pd.Series:
    if talib is not None:
        try:
            return pd.Series(talib.RSI(close.values, timeperiod=period), index=close.index)
        except Exception:
            pass
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _calc_sma(close: pd.Series, period: int) -> pd.Series:
    if talib is not None:
        try:
            return pd.Series(talib.SMA(close.values, timeperiod=period), index=close.index)
        except Exception:
            pass
    return close.rolling(period, min_periods=period).mean()


def backtest_gene(gene: Gene, df: pd.DataFrame, initial_capital: float = 10000.0) -> dict[str, float | int | list[dict[str, float]]]:
    """
    Run rule-based backtest for one gene and return metrics.

    BUY: RSI < 35 and MA_short > MA_long and not holding.
    SELL: RSI > 65 or MA_short < MA_long or stop loss / take profit hit.
    """
    if df.empty:
        raise ValueError("Input dataframe is empty.")
    if "Close" not in df.columns:
        raise ValueError("Input dataframe must have Close column.")

    data = df.copy()
    data["RSI"] = _calc_rsi(data["Close"], gene.rsi_period)
    data["MA_S"] = _calc_sma(data["Close"], gene.ma_short)
    data["MA_L"] = _calc_sma(data["Close"], gene.ma_long)
    data = data.dropna().copy()
    if data.empty:
        raise ValueError("No rows left after indicator computation.")

    cash = float(initial_capital)
    qty = 0.0
    entry_price = 0.0
    trades: list[dict[str, float]] = []
    equity_curve: list[float] = []
    daily_returns: list[float] = []
    prev_equity = cash

    for idx, row in data.iterrows():
        price = float(row["Close"])
        rsi = float(row["RSI"])
        ma_s = float(row["MA_S"])
        ma_l = float(row["MA_L"])

        holding = qty > 0.0
        if (not holding) and (rsi < 35.0) and (ma_s > ma_l):
            allocation = cash * gene.position_size_pct
            if allocation > 0:
                qty = allocation / price
                cash -= allocation
                entry_price = price
                trades.append({"timestamp": float(pd.Timestamp(idx).timestamp()), "side": 1.0, "price": price})
        elif holding:
            pnl_ratio = (price - entry_price) / entry_price
            stop_hit = pnl_ratio <= -gene.stop_loss_pct
            target_hit = pnl_ratio >= gene.take_profit_pct
            signal_sell = (rsi > 65.0) or (ma_s < ma_l)
            if stop_hit or target_hit or signal_sell:
                cash += qty * price
                trades.append({"timestamp": float(pd.Timestamp(idx).timestamp()), "side": -1.0, "price": price})
                qty = 0.0
                entry_price = 0.0

        equity = cash + (qty * price)
        equity_curve.append(equity)
        if prev_equity > 0:
            daily_returns.append((equity - prev_equity) / prev_equity)
        prev_equity = equity

    if qty > 0.0:
        final_price = float(data["Close"].iloc[-1])
        cash += qty * final_price
        qty = 0.0

    final_capital = float(cash)
    profit_pct = ((final_capital - initial_capital) / initial_capital) * 100.0

    returns_arr = np.array(daily_returns, dtype=float)
    if returns_arr.size >= 2 and np.std(returns_arr) > 0:
        sharpe_ratio = float((np.mean(returns_arr) / np.std(returns_arr)) * np.sqrt(252.0))
    else:
        sharpe_ratio = 0.0

    if equity_curve:
        eq = np.array(equity_curve, dtype=float)
        peaks = np.maximum.accumulate(eq)
        dd = (eq - peaks) / peaks
        max_drawdown = float(abs(np.min(dd)) * 100.0)
    else:
        max_drawdown = 0.0

    completed_trade_returns: list[float] = []
    open_buy: float | None = None
    for t in trades:
        if t["side"] == 1.0:
            open_buy = t["price"]
        elif t["side"] == -1.0 and open_buy is not None:
            completed_trade_returns.append((t["price"] - open_buy) / open_buy)
            open_buy = None

    total_trades = len(completed_trade_returns)
    if total_trades > 0:
        wins = sum(1 for r in completed_trade_returns if r > 0)
        win_rate = (wins / total_trades) * 100.0
    else:
        win_rate = 0.0

    fitness_score = (profit_pct * 0.4) + (sharpe_ratio * 0.3) + (win_rate * 0.2) - (max_drawdown * 0.1)

    return {
        "final_capital": final_capital,
        "profit_pct": float(profit_pct),
        "sharpe_ratio": float(sharpe_ratio),
        "max_drawdown": float(max_drawdown),
        "win_rate": float(win_rate),
        "total_trades": int(total_trades),
        "fitness_score": float(fitness_score),
        "trades": trades,
    }


if __name__ == "__main__":
    try:
        from ..data.yfinance_loader import fetch_historical_data
    except ImportError:
        from data.yfinance_loader import fetch_historical_data

    sample = fetch_historical_data("BTC-USD", "1y")
    gene = Gene()
    result = backtest_gene(gene, sample, 10000.0)
    print(result)
