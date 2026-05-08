"""combo_search.py — Exhaustive combinations helper for fast pre-market search.

Produces Top-3 genes by running quick backtests over fixed parameter ranges.
"""

from __future__ import annotations

import logging
from typing import List

import pandas as pd

from genetic.gene import Gene
from genetic.fitness import backtest_gene

logger = logging.getLogger(__name__)


def _normalize_symbol_for_yf(symbol: str) -> str:
    s = symbol.replace("/", "-")
    # prefer USD instead of USDT for Yahoo tickers
    if s.endswith("USDT"):
        s = s[:-4] + "USD"
    return s


def _load_price_df(symbol: str, lookback_days: int) -> pd.DataFrame:
    try:
        # data.yfinance_loader provides a simple fetch_historical_data helper
        from data.yfinance_loader import fetch_historical_data
        yf_sym = _normalize_symbol_for_yf(symbol)
        period = f"{lookback_days}d"
        df = fetch_historical_data(yf_sym, period)
        return df
    except Exception:
        # If a YFinanceLoader class exists, try it
        try:
            from data.yfinance_loader import YFinanceLoader
            loader = YFinanceLoader(symbol)
            return loader.fetch(period_days=lookback_days)
        except Exception as exc:
            logger.error("Failed to load price data for %s: %s", symbol, exc)
            raise


def run_full_combinations(
    symbol: str,
    lookback_days: int,
    risk_profile: str,
    initial_capital: float,
    expected_return: float,
    max_drawdown: float,
) -> List[Gene]:
    """
    Exhaustive loop over fixed gene parameter ranges.
    Evaluate fitness with backtest + simple penalties.
    Return Top-3 genes.
    """
    df = _load_price_df(symbol, lookback_days)
    if df is None or df.empty:
        raise ValueError("No historical data available for symbol: %s" % symbol)

    ranges = {
        "rsi_period": [7, 14, 21],
        "ma_short": [10, 20],
        "ma_long": [50, 100],
        "stop_loss_pct": [0.02, 0.05, 0.08],
        "take_profit_pct": [0.05, 0.1, 0.15],
        "position_size_pct": [0.1, 0.2, 0.3],
    }

    scored: List[tuple[float, Gene]] = []
    for rsi in ranges["rsi_period"]:
        for ma_s in ranges["ma_short"]:
            for ma_l in ranges["ma_long"]:
                if ma_s >= ma_l:
                    continue
                for sl in ranges["stop_loss_pct"]:
                    for tp in ranges["take_profit_pct"]:
                        for pos in ranges["position_size_pct"]:
                            gene = Gene(
                                rsi_period=rsi,
                                ma_short=ma_s,
                                ma_long=ma_l,
                                stop_loss_pct=sl,
                                take_profit_pct=tp,
                                position_size_pct=pos,
                            )
                            try:
                                res = backtest_gene(gene, df, initial_capital=initial_capital)
                                fitness = float(res.get("fitness_score", 0.0))
                            except Exception as exc:
                                logger.debug("Backtest failed for gene %s: %s", gene.to_dict(), exc)
                                continue
                            # penalty for drawdown beyond user limit (res stores percent)
                            dd = float(res.get("max_drawdown", 0.0))
                            if dd > max_drawdown * 100:
                                fitness -= (dd - max_drawdown * 100) * 0.01
                            gene.fitness = fitness
                            scored.append((fitness, gene))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_genes = [g for _, g in scored[:3]]
    return top_genes
