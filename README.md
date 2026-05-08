# EvoTrade

EvoTrade is a self-evolving AI trading bot that uses a Genetic Algorithm (DEAP) to breed optimal trading strategies, validates them through Monte Carlo stress testing, and filters decisions through a Multi-Agent Council of three specialist Claude AI agents — all streaming live to a React + Recharts dashboard. It is designed for educational and research purposes only and does not constitute financial advice.

---

## Quick Start (Demo — no API keys required)

```bash
# 1. Install Python dependencies
cd backend
pip install -r requirements.txt

# 2. Run the full pipeline demo (uses free Yahoo Finance data)
cd ..
python scripts/run_demo.py
```

**Optional flags:**
```bash
python scripts/run_demo.py --symbol ETH/USDT --profile high --generations 20
```

**Quick GA sanity check:**
```bash
python scripts/test_evolution.py
```

---

## Full Setup (Live backend + frontend)

### Backend

```bash
cd backend

# Copy and fill in your API keys
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY, BINANCE_API_KEY, etc.

pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Layer 1 — Data Ingestion                           │
│  yFinance (historical) · Binance WS (live) · NewsAPI│
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│  Layer 2 — Processing                               │
│  TA-Lib indicators · Normalizer · HMM Regime (4-state)│
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│  Layer 3 — Genetic Algorithm (DEAP)                 │
│  Gene (6 params) · Population · Fitness (Sharpe)    │
│  Selection · Crossover · Mutation · Convergence      │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│  Layer 4 — Stress Testing                           │
│  Monte Carlo GBM (1000 paths) · Scenario simulator  │
│  Backtrader backtesting engine                      │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│  Layer 5 — Multi-Agent Council (Claude API)         │
│  The Critic (overfitting) · The Guardian (VaR/risk) │
│  The Forecaster (macro/sentiment) → fitness delta   │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│  Layer 6 — Execution Engine                         │
│  Alpha Gene store · Main trading thread             │
│  Background regime monitor · Re-evolution trigger   │
│  Safety controls (daily loss cap, emergency stop)   │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│  Layer 7 — API + Frontend                           │
│  FastAPI REST + WebSocket · React + Recharts        │
│  Real-time evolution graph · Live trade log         │
│  Regime badge · Gene display · Safety controls      │
└─────────────────────────────────────────────────────┘
```

---

## REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/onboard` | Set symbol, risk profile, capital |
| `POST` | `/start` | Begin evolution + live trading |
| `POST` | `/pause` | Pause trading |
| `POST` | `/resume` | Resume trading |
| `POST` | `/emergency_stop` | Halt everything immediately |
| `GET`  | `/status` | Current gene, regime, fitness history |
| `WS`   | `/ws` | Real-time event stream |

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key (required for agent council) |
| `BINANCE_API_KEY` | Binance API key (required for live trading) |
| `BINANCE_API_SECRET` | Binance API secret |
| `NEWS_API_KEY` | NewsAPI key (for sentiment agent) |
| `DEFAULT_SYMBOL` | e.g. `BTC/USDT` |
| `DEFAULT_RISK_PROFILE` | `low` / `medium` / `high` |

---

## Gene Parameters

Each evolved trading strategy is encoded as 6 parameters:

| Parameter | Range | Description |
|-----------|-------|-------------|
| `rsi_period` | 5–30 bars | RSI lookback window |
| `ma_short` | 5–50 bars | Short moving average |
| `ma_long` | 20–200 bars | Long moving average |
| `stop_loss_pct` | 1–10 % | Stop-loss threshold |
| `take_profit_pct` | 1–20 % | Take-profit threshold |
| `position_size_pct` | 1–50 % | Capital per trade |

**BUY signal:** RSI < 30 AND price > MA_short  
**SELL signal:** RSI > 70 AND price < MA_long (or stop/take-profit hit)

---

## Disclaimer

This software is provided for **educational and research purposes only**. It is not financial advice. Cryptocurrency trading involves substantial risk of loss. Never use this system with real funds without thorough independent testing and risk assessment. The authors accept no liability for trading losses.
