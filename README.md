# EvoTrade — AI Self-Evolving Paper Trading Platform

EvoTrade uses a Genetic Algorithm to evolve custom trading strategies in real time. Watch 5 generations of 10 candidate strategies compete, survive, and mutate — then deploy the winning AlphaGene to paper trade live BTC/USDT data from Binance. **No real money. No broker connection. Paper trading only.**

---

## Quickstart

### Windows
```
start.bat
```
Opens two terminal windows — one for backend, one for frontend.

### Mac / Linux
```bash
chmod +x start.sh && ./start.sh
```

Then open **http://localhost:5173**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        BROWSER (React 18 + Vite)                │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────────────┐  │
│  │   Chat   │ → │  Evolution   │ → │  Live Trading Dashboard │  │
│  │Onboarding│   │Visualization │   │  (BTC/USDT paper trade) │  │
│  └──────────┘   └──────────────┘   └────────────────────────┘  │
│       Zustand stores │ REST (axios) │ WebSocket (native)         │
└──────────────────────┼─────────────┼────────────────────────────┘
                       │             │
┌──────────────────────┼─────────────┼────────────────────────────┐
│             BACKEND (FastAPI + Uvicorn)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  /api/chat/*  /api/evolution/*  /api/trading/*  /ws      │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐  │
│  │ GA Engine│ │HMM Regime│ │Monte Carlo│ │  Paper Trader    │  │
│  │  (DEAP)  │ │(hmmlearn)│ │  (NumPy)  │ │ (no real money!) │  │
│  └──────────┘ └──────────┘ └───────────┘ └──────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Binance Public WebSocket ← BTC/USDT 1m klines (no key) │   │
│  └──────────────────────────────────────────────────────────┘   │
│  SQLite (evotrade.db)                                            │
└──────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, TailwindCSS |
| State | Zustand |
| Charts | Recharts |
| Animation | Framer Motion |
| Backend | FastAPI, Uvicorn, Python 3.10+ |
| GA Engine | DEAP |
| Regime Detection | hmmlearn (4-state GaussianHMM) |
| Stress Testing | NumPy (GBM + jump diffusion) |
| Indicators | `ta` library (RSI, MA, Bollinger) |
| Market Data | Binance public WebSocket |
| Historical Data | yfinance |
| Database | SQLite (Supabase-compatible schema) |
| Real-time | Native WebSocket (FastAPI + asyncio) |

---

## Demo Flow

1. **Chat** (`/`) — Answer 7 questions about your risk profile. The bot extracts name, capital, risk tolerance, experience, asset preference, daily loss limit, and strategy preference.

2. **Evolve** (`/evolution`) — Watch 5 generations × 10 chromosomes evolve. Each chromosome is backtested on 90 days of real BTC price data, stress-tested with 50 Monte Carlo paths, and scored by a 3-agent mock AI council. The top 3 AlphaGenes are shown side-by-side. Select one and confirm.

3. **Trade** (`/dashboard`) — Live BTC/USDT price streams from Binance. The deployed AlphaGene generates BUY/SELL signals from RSI + moving average crossovers, with automatic stop-loss and take-profit. All trades are paper only. Hit Emergency Stop to close all positions instantly.

---

## Notes

- No API keys required for the MVP demo (Binance public stream, no authentication)
- HMM model is trained on startup using 90 days of yfinance data (~30 seconds first run)
- Evolution takes ~2–4 minutes for 5 generations on a typical laptop
- State resets on browser refresh (Zustand in-memory only — by design for MVP)
