import pandas as pd
import numpy as np
from backend.genetic.gene import Gene


def calculate_rsi(prices: pd.Series, period: int) -> pd.Series:
    """Calculate RSI indicator using pandas."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def backtest_gene(gene: Gene, df: pd.DataFrame, initial_capital: float = 10000.0) -> dict:
    """
    Simulate trading using gene parameters on historical data.
    No real money involved - pure simulation.
    
    Returns dict with:
    - final_capital: how much money after simulation
    - profit_pct: percentage profit/loss
    - total_trades: how many trades were made
    - win_rate: percentage of profitable trades
    - max_drawdown: biggest loss from peak
    - sharpe_ratio: risk-adjusted return
    - fitness_score: final combined score
    """
    # Calculate indicators
    close = df['Close'].copy()
    rsi = calculate_rsi(close, gene.rsi_period)
    ma_short = close.rolling(window=gene.ma_short).mean()
    ma_long = close.rolling(window=gene.ma_long).mean()
    
    # Drop NaN rows
    valid_start = max(gene.rsi_period, gene.ma_long)
    
    # Trading simulation variables
    capital = initial_capital
    holding = False
    buy_price = 0.0
    trades = []
    peak_capital = initial_capital
    max_drawdown = 0.0
    
    # Loop through each day
    for i in range(valid_start, len(df)):
        price = float(close.iloc[i])
        rsi_val = float(rsi.iloc[i])
        ma_s = float(ma_short.iloc[i])
        ma_l = float(ma_long.iloc[i])
        
        if pd.isna(rsi_val) or pd.isna(ma_s) or pd.isna(ma_l):
            continue
        
        # BUY condition: RSI below threshold AND short MA above long MA
        if not holding:
            if rsi_val < (100 - gene.rsi_period * 2) and ma_s > ma_l:
                buy_price = price
                holding = True
        
        # SELL condition: RSI high OR MA cross OR stop loss OR take profit
        elif holding:
            price_change = (price - buy_price) / buy_price
            
            stop_loss_hit = price_change < -gene.stop_loss_pct
            take_profit_hit = price_change > gene.take_profit_pct
            ma_cross_down = ma_s < ma_l
            rsi_overbought = rsi_val > 70
            
            if stop_loss_hit or take_profit_hit or ma_cross_down or rsi_overbought:
                # Calculate profit for this trade
                trade_profit = price_change * gene.position_size_pct
                capital = capital * (1 + trade_profit)
                
                trades.append({
                    'profit_pct': price_change,
                    'profitable': price_change > 0
                })
                
                holding = False
                buy_price = 0.0
        
        # Track drawdown
        if capital > peak_capital:
            peak_capital = capital
        drawdown = (peak_capital - capital) / peak_capital
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # Calculate final metrics
    profit_pct = (capital - initial_capital) / initial_capital
    total_trades = len(trades)
    win_rate = sum(1 for t in trades if t['profitable']) / max(total_trades, 1)
    
    # Calculate Sharpe ratio (simplified)
    if total_trades > 1:
        trade_returns = [t['profit_pct'] for t in trades]
        avg_return = np.mean(trade_returns)
        std_return = np.std(trade_returns) + 1e-10
        sharpe_ratio = avg_return / std_return
    else:
        sharpe_ratio = 0.0
    
    # Final fitness score formula
    # Weighted combination of profit, sharpe, win_rate, drawdown penalty
    fitness_score = (
        (profit_pct * 0.4) +
        (sharpe_ratio * 0.3) +
        (win_rate * 0.2) -
        (max_drawdown * 0.1)
    )
    
    return {
        'final_capital': round(capital, 2),
        'profit_pct': round(profit_pct * 100, 2),
        'total_trades': total_trades,
        'win_rate': round(win_rate * 100, 2),
        'max_drawdown': round(max_drawdown * 100, 2),
        'sharpe_ratio': round(sharpe_ratio, 3),
        'fitness_score': round(fitness_score, 4)
    }


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from backend.data.yfinance_loader import fetch_historical_data
    
    df = fetch_historical_data("BTC-USD", "1y")
    gene = Gene(rsi_period=14, ma_short=10, ma_long=50,
                stop_loss_pct=0.05, take_profit_pct=0.10,
                position_size_pct=0.20)
    
    result = backtest_gene(gene, df)
    print("Single agent backtest result:")
    for k, v in result.items():
        print(f"  {k}: {v}")