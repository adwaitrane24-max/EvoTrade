"""
backtest_runner.py — Backtrader-based backtesting engine wrapper.
Runs a Gene's strategy against historical data and returns performance metrics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import backtrader as bt
import pandas as pd

from genetic.gene import Gene

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Backtest performance metrics for a single Gene."""

    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    num_trades: int
    win_rate: float
    profit_factor: float
    final_value: float
    initial_value: float


class GeneStrategy(bt.Strategy):
    """
    Backtrader Strategy implementation of a Gene's RSI + dual-MA logic.

    Buys when RSI < 30 and Close > short MA.
    Sells when RSI > 70 and Close < long MA, or stop/take-profit hit.
    """

    params = (
        ("rsi_period",        14),
        ("ma_short",          20),
        ("ma_long",           50),
        ("stop_loss_pct",     0.03),
        ("take_profit_pct",   0.06),
        ("position_size_pct", 0.10),
    )

    def __init__(self) -> None:
        self.rsi   = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.sma_s = bt.indicators.SMA(self.data.close, period=self.p.ma_short)
        self.sma_l = bt.indicators.SMA(self.data.close, period=self.p.ma_long)
        self.entry_price: Optional[float] = None
        self.trades: list[dict] = []
        self._wins = 0
        self._losses = 0
        self._gross_profit = 0.0
        self._gross_loss = 0.0

    def next(self) -> None:
        price = self.data.close[0]

        if not self.position:
            if self.rsi[0] < 30 and price > self.sma_s[0]:
                size = (self.broker.cash * self.p.position_size_pct) / price
                self.buy(size=size)
                self.entry_price = price
        else:
            pnl_pct = (price - self.entry_price) / self.entry_price  # type: ignore[operator]
            take = pnl_pct >= self.p.take_profit_pct
            stop = pnl_pct <= -self.p.stop_loss_pct
            sell_sig = self.rsi[0] > 70 and price < self.sma_l[0]

            if take or stop or sell_sig:
                self.close()

    def notify_trade(self, trade: bt.Trade) -> None:
        if trade.isclosed:
            pnl = trade.pnlcomm
            if pnl > 0:
                self._wins += 1
                self._gross_profit += pnl
            else:
                self._losses += 1
                self._gross_loss += abs(pnl)


class BacktestRunner:
    """
    Wraps Backtrader to run a Gene strategy on a historical OHLCV DataFrame.

    Args:
        initial_capital: Starting portfolio value in USD.
        commission: Per-trade commission fraction.
    """

    def __init__(self, initial_capital: float = 10_000.0, commission: float = 0.001) -> None:
        self.initial_capital = initial_capital
        self.commission = commission

    def run(self, gene: Gene, price_df: pd.DataFrame) -> BacktestResult:
        """
        Execute the backtest.

        Args:
            gene: Strategy parameters.
            price_df: OHLCV DataFrame (must contain Open, High, Low, Close, Volume).

        Returns:
            BacktestResult with performance metrics.
        """
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=self.commission)

        # Convert DataFrame to Backtrader feed
        data_feed = bt.feeds.PandasData(dataname=self._prepare_df(price_df))
        cerebro.adddata(data_feed)

        cerebro.addstrategy(
            GeneStrategy,
            rsi_period=gene.rsi_period,
            ma_short=gene.ma_short,
            ma_long=gene.ma_long,
            stop_loss_pct=gene.stop_loss_pct,
            take_profit_pct=gene.take_profit_pct,
            position_size_pct=gene.position_size_pct,
        )

        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.04)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

        results = cerebro.run()
        strat = results[0]

        final_value = cerebro.broker.getvalue()
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100

        sharpe_data = strat.analyzers.sharpe.get_analysis()
        sharpe = sharpe_data.get("sharperatio") or 0.0

        dd_data = strat.analyzers.drawdown.get_analysis()
        max_dd = dd_data.get("max", {}).get("drawdown", 0.0)

        trade_data = strat.analyzers.trades.get_analysis()
        total_trades = trade_data.get("total", {}).get("closed", 0)
        wins = strat._wins
        losses = strat._losses
        win_rate = wins / max(wins + losses, 1)
        profit_factor = strat._gross_profit / max(strat._gross_loss, 1e-9)

        return BacktestResult(
            total_return_pct=float(total_return),
            sharpe_ratio=float(sharpe),
            max_drawdown_pct=float(max_dd),
            num_trades=int(total_trades),
            win_rate=float(win_rate),
            profit_factor=float(profit_factor),
            final_value=float(final_value),
            initial_value=self.initial_capital,
        )

    @staticmethod
    def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
        """Ensure the DataFrame is compatible with Backtrader's PandasData feed."""
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns for Backtrader feed: {missing}")
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        return df


if __name__ == "__main__":
    import yfinance as yf
    logging.basicConfig(level=logging.INFO)

    df = yf.Ticker("BTC-USD").history(period="1y")
    gene = Gene(rsi_period=14, ma_short=20, ma_long=50, stop_loss_pct=0.03,
                take_profit_pct=0.06, position_size_pct=0.10)
    runner = BacktestRunner(initial_capital=10_000)
    result = runner.run(gene, df)

    print(f"Total return    : {result.total_return_pct:.2f}%")
    print(f"Sharpe ratio    : {result.sharpe_ratio:.3f}")
    print(f"Max drawdown    : {result.max_drawdown_pct:.2f}%")
    print(f"Trades          : {result.num_trades}")
    print(f"Win rate        : {result.win_rate:.1%}")
    print(f"Profit factor   : {result.profit_factor:.2f}")
    print(f"Final value     : ${result.final_value:,.2f}")
