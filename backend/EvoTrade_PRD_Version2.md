# EvoTrade — Product Requirements Document (PRD)
**“Not Your Ordinary AI Trading Bot”**  
**Document Type:** Production-grade FinTech PRD (Architecture + Implementation Spec)  
**Target:** Hackathon-feasible MVP (48–72 hours) with a credible path to institutional-grade production  
**Current Date:** 2026-05-08  
**Author:** (Generated)  
**Version:** 1.0

---

## Title Page

### Product
**EvoTrade** — AI-powered autonomous live trading **web application** that continuously evolves strategies under strict security and latency constraints.

### Core Thesis
EvoTrade is designed around an explicit separation of:
- **FAST SYSTEMS (Deterministic Execution Layer)** — ultra-low latency, purely deterministic, never blocks on AI.
- **SMART SYSTEMS (AI Reasoning Layer)** — asynchronous, local DeepSeek-R1 reasoning for evaluation, critique, explainability, and strategy guidance.

### Non-Negotiable Security Principle
> **AI SHOULD NEVER HAVE DIRECT ACCESS TO MONEY.**  
The AI layer cannot access secrets, cannot decrypt credentials, and cannot place trades.

---

## Executive Summary

EvoTrade is a self-evolving live trading platform that:
- trades using an **ultra-low latency deterministic engine** (FastAPI + asyncio + websockets + numpy/pandas),
- evolves strategies in a **background genetic evolution pipeline** (DEAP + backtesting + Monte Carlo stress testing),
- uses **HMM-based market regime detection** to adapt behavior and control re-evolution frequency,
- leverages **DeepSeek-R1 7B locally via Ollama** to provide strategic critique, risk commentary, overfitting analysis, and explainability,
- enforces strict security boundaries with a **TEE-inspired secure execution layer** that alone can access broker APIs and decrypt credentials.

**MVP Outcome:** A polished web app that demonstrates live/paper trading, evolving strategies across 5 generations, regime-aware adaptation, and AI-driven explanation cards — without ever coupling AI inference to execution latency.

---

## Table of Contents

1. Goals, Non-Goals, and Success Metrics  
2. Users, Personas, and Primary Use Cases  
3. System Overview & High-Level Architecture  
4. Key Architecture Decision: FAST vs SMART Systems  
5. Thread/Service Model (3-thread architecture)  
6. Market Data Layer  
7. Live Trading Engine (FAST)  
8. Secure Execution Layer (TEE-inspired)  
9. Background Evolution Engine (FAST compute + SMART reasoning)  
10. Genetic Algorithm Design (AlphaGene)  
11. Generation Workflow (Gen1 → Gen5)  
12. Backtesting & Fitness Scoring  
13. Monte Carlo Stress Testing (MVP-optimized)  
14. HMM Regime Detection  
15. DeepSeek-R1 Local AI Architecture (Ollama)  
16. AI Council Simulation (single-call, structured)  
17. Strategy Deployment: Shadow Mode + Hot Swap + Rollback  
18. Data Model & Supabase Schema  
19. Supabase Auth + Realtime + RLS Policies  
20. API Specifications (FastAPI)  
21. WebSockets & Dashboard Streaming  
22. Frontend Architecture (React/Vite/Zustand/Recharts/Tailwind)  
23. UX Requirements & Dashboard Modules  
24. Security, Data Minimization, Zero-Trust Design  
25. Performance, Latency, and Scalability Plan  
26. Observability & Monitoring  
27. Hackathon MVP Scope vs Mocking Plan  
28. Future Roadmap (Production-grade confidential computing)  
29. Investor Positioning  
30. Conclusion

---

## 1) Goals, Non-Goals, and Success Metrics

### 1.1 Goals
**G1 — Latency-safe autonomous trading**
- Live trading loop remains deterministic and independent from AI reasoning.
- Target decision-to-order latency: **~200ms to 1s** (non-HFT).

**G2 — Continuous strategy evolution**
- Strategy families evolve across **5 generations**.
- Each generation produces **10 strategies**, top **3** survive for AI reasoning.
- Output: one AlphaGene per generation + final best AlphaGene.

**G3 — Regime-aware adaptation**
- HMM identifies regime (bull/bear/crash/sideways) with confidence.
- Re-evolution triggers only when confidence thresholds and cooldown are met.

**G4 — Secure execution boundary**
- Credentials encrypted at rest.
- Only Secure Execution Layer can decrypt (memory-only) and hit broker API.

**G5 — Premium, beginner-friendly web UI**
- Clean “Stripe/Vercel/Robinhood-like” dashboard: modern, elegant, non-terminal.

### 1.2 Non-Goals (MVP)
- HFT microsecond-level execution.
- Multi-venue smart order routing.
- Full portfolio optimization across many assets.
- Complex derivatives margin modeling.
- Institutional-grade compliance (SOC2, ISO27001) — but we design toward it.

### 1.3 Success Metrics (MVP)
- Deterministic engine remains stable under continuous websocket load.
- Evolution engine produces non-trivial parameter diversity and measurable fitness ranking.
- AI explanations are coherent, role-structured, and consistent with provided metrics.
- Shadow-mode deployment prevents strategy regressions.
- Demo stability: 30+ minutes continuous run without crashes.

---

## 2) Users, Personas, and Primary Use Cases

### 2.1 Personas
1. **Beginner Retail User**
   - Wants “autopilot” with guardrails.
   - Values clear explanations and safety controls (kill switch).
2. **Power Trader**
   - Wants regime view, backtest results, parameter controls, logs.
3. **Builder / Hacker**
   - Wants strategy introspection, evolution charts, reproducible runs.
4. **Investor / Judge**
   - Wants believable architecture, security boundaries, and operational realism.

### 2.2 Primary Use Cases
- Connect broker (paper first), start trading, observe dashboard.
- System evolves strategies in background and proposes new AlphaGene.
- User sees AI rationale for strategy ranking and risks.
- System shadow-tests and then hot-swaps strategy (or rolls back).

---

## 3) System Overview & High-Level Architecture

### 3.1 Final Optimized Architecture (Required)

**Layers / Components**
1. **Frontend Layer** (React/Vite)
2. **FastAPI Orchestrator** (API + WebSockets)
3. **Secure Execution Layer** (TEE-inspired compartment)
4. **Live Trading Engine** (deterministic)
5. **Background Evolution Engine** (compute + asynchronous AI)
6. **DeepSeek AI Reasoning Layer** (local via Ollama)
7. **Supabase Backend Infrastructure** (Auth, Postgres, Realtime, Storage)
8. **Market Data Layer** (exchange websockets / broker feeds)

### 3.2 Architecture Diagram (Logical)

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                                  Frontend                                  │
│ React + Vite + Tailwind + Recharts + Zustand                                │
│  - Live Dashboard                                                           │
│  - AI Reasoning Cards                                                       │
│  - Evolution Graphs                                                         │
│  - Kill Switch                                                              │
└───────────────────────────────▲────────────────────────────────────────────┘
                                │ WebSockets (dashboard stream)
                                │ REST (control/config)
┌───────────────────────────────┴────────────────────────────────────────────┐
│                           FastAPI Orchestrator                              │
│  - REST endpoints (auth/session/state)                                      │
│  - WS aggregator for UI                                                     │
│  - Task coordinator (asyncio)                                               │
│  - Writes to Supabase                                                       │
└───────────────▲───────────────────────────▲─────────────────────────────────┘
                │                           │
                │                           │ async jobs/events
                │                           │
┌───────────────┴──────────────┐     ┌──────┴───────────────────────────────┐
│   Live Trading Engine (FAST)  │     │ Background Evolution Engine (FAST)    │
│   - Websocket market feed     │     │ - GA (DEAP)                           │
│   - Indicators (TA-Lib)       │     │ - Backtests (Backtrader)              │
│   - HMM regime detection      │     │ - Monte Carlo (50–100 paths)          │
│   - Signal gen (AlphaGene)    │     │ - Fitness scoring                      │
│   - Order intent ->           │     │ - Select Top3 -> AI reasoning          │
│     Secure Exec Layer         │     └───────────────▲───────────────────────┘
└───────────────▲──────────────┘                     │
                │ order requests                       │ local inference only
                │                                      │
┌───────────────┴──────────────┐            ┌─────────┴──────────────────────┐
│ Secure Execution Layer (TEE*) │            │ DeepSeek-R1 via Ollama (SMART) │
│ - decrypt in memory only      │            │ - AI council simulation         │
│ - broker API calls            │            │ - explanations & critique        │
│ - risk checks & limits        │            │ - NO secrets / NO money access   │
│ - audit logs                  │            └────────────────────────────────┘
└───────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                            Supabase (Auth + Postgres + Realtime)            │
│  - user accounts, strategies, runs, logs, portfolio snapshots               │
│  - RLS for multi-user isolation                                             │
└────────────────────────────────────────────────────────────────────────────┘

*TEE-inspired in MVP = software isolation + strict interfaces + secret vaulting
```

---

## 4) Key Architecture Decision: FAST vs SMART Systems

### 4.1 FAST SYSTEMS (Deterministic Execution Layer)
Handles:
- market data ingestion
- websocket loops
- indicator computations
- AlphaGene signal generation
- HMM regime detection
- risk validation (pre-trade intent checks)
- order management + execution pipeline (through Secure Exec Layer)

**Hard Requirements**
- MUST NOT block on AI.
- MUST be deterministic: same inputs -> same outputs.
- MUST be async / event-driven.
- MUST degrade safely (drop non-critical updates, not execution correctness).

### 4.2 SMART SYSTEMS (AI Reasoning Layer)
Handles:
- critique of top strategies (overfitting risk, regime fragility)
- narrative explanation for UI
- “AI Council” multi-role simulation
- guidance signals (NOT execution signals)

**Soft Requirements**
- 2–10 seconds latency acceptable.
- Must run locally and asynchronously.
- Only receives summarized metrics.

### 4.3 Why this separation is scalable and realistic
- AI inference is nondeterministic and variable-latency.
- Coupling AI to the live loop creates tail latency spikes and unstable behavior.
- Regulations and security best practices favor deterministic, auditable execution paths.

---

## 5) Thread/Service Model (3-thread architecture)

> Implementation note: “thread” here may mean **async tasks**, **processes**, or **separate services**.  
For MVP: keep it as separate asyncio task groups + optional multiprocessing for CPU-heavy backtests.

### 5.1 THREAD 1 — LIVE TRADING THREAD (FAST)
Responsibilities:
- subscribe to market websocket feeds
- update rolling candles/orderbook snapshots
- compute indicators per tick/candle close
- run HMM update
- run AlphaGene signal logic
- produce order intents (BUY/SELL/HOLD + parameters)
- call Secure Execution Layer for approval + placement

Guarantee:
- never calls DeepSeek
- never waits for evolution thread
- can continue trading on last known AlphaGene

### 5.2 THREAD 2 — BACKGROUND EVOLUTION THREAD (FAST + SMART)
Responsibilities:
- generate strategy candidates (10 per generation)
- backtest each candidate
- Monte Carlo stress testing (50–100 paths)
- compute fitness
- select top 3
- send only top 3 summaries to DeepSeek
- extract AI council output
- select generation AlphaGene
- propose deployment via shadow-mode

### 5.3 THREAD 3 — DASHBOARD STREAM THREAD
Responsibilities:
- publish high-frequency updates to UI via websocket:
  - latest price, indicators, regime state
  - open positions (sanitized)
  - PnL (paper/live)
  - evolution progress
  - AI reasoning cards
  - logs and alerts

Design rule:
- dashboard updates must be droppable/throttled
- execution events must be durable (DB/audit logs)

---

## 6) Market Data Layer

### 6.1 Data Sources (MVP options)
- Crypto exchange websocket (e.g., Binance/Bybit) OR broker paper feed.
- For hackathon: choose one asset (e.g., BTC/USDT) to reduce complexity.

### 6.2 Market Data Requirements
- Latency: sub-second is fine.
- Correctness > micro-latency.
- Must handle reconnects, heartbeats, and data gaps.

### 6.3 Data Normalization
Represent unified tick/candle events:

```json
{
  "ts": "2026-05-08T12:00:01.123Z",
  "symbol": "BTCUSDT",
  "event_type": "candle_close",
  "timeframe": "1m",
  "o": 62000.1,
  "h": 62120.4,
  "l": 61980.7,
  "c": 62090.2,
  "v": 120.53
}
```

---

## 7) Live Trading Engine (FAST)

### 7.1 Responsibilities
- Maintain rolling OHLCV window (e.g., last 500 candles).
- Compute indicators:
  - RSI(period)
  - MA short, MA long
- Apply AlphaGene:
  - define signal logic using RSI + MA crossover + risk parameters
- Validate with risk manager (pre-trade checks)
- Convert to order intent for Secure Execution Layer

### 7.2 Indicator Computation Strategy
- Pre-allocate arrays / use numpy vector operations where possible.
- Only compute on candle close for MVP (reduces noise & load).
- Keep indicator compute in-memory; persist periodic snapshots to DB.

### 7.3 AlphaGene Signal Logic (Deterministic)
AlphaGene genes:
- `rsi_period`
- `ma_short_window`
- `ma_long_window`
- `stop_loss_pct`
- `take_profit_pct`
- `position_size_pct`

Example deterministic logic (illustrative):

- Trend filter: if `MA_short > MA_long`, bias long; if `<`, bias short/flat.
- RSI trigger: oversold/overbought thresholds (fixed or derived).
- Risk wrapper: stop-loss/take-profit and position sizing strictly enforced.

### 7.4 Pseudocode (Live Loop)

```python
async def live_trading_loop():
    while True:
        event = await market_feed.next_event()  # websocket -> candle_close
        state.update_market(event)

        if event.event_type != "candle_close":
            continue

        indicators = indicator_engine.compute(state.ohlcv)
        regime = hmm_engine.update(indicators, state.returns)

        alphagene = strategy_registry.get_active()
        signal = alphagene.generate_signal(indicators, regime)

        intent = risk_engine.build_order_intent(signal, alphagene, state)

        if not intent:
            continue

        # Critical: secure execution call is bounded & deterministic
        result = await secure_exec.place_order(intent)

        # publish events
        event_bus.publish("execution_event", result)
```

---

## 8) Secure Execution Layer (TEE-inspired)

### 8.1 Purpose
A software-isolated component that is the **only** module allowed to:
- decrypt broker API credentials,
- sign requests,
- place orders,
- enforce absolute risk limits,
- write immutable audit logs.

### 8.2 Threat Model (MVP)
Protect against:
- AI prompt injection exfiltration attempts (AI never sees secrets)
- compromised UI trying to place unauthorized trades
- lateral movement within backend services
- accidental leakage of credentials in logs

Does not fully protect against:
- root-level server compromise (future: SGX/confidential computing)

### 8.3 Key Rule
**All trade placement must go through Secure Execution Layer.**

### 8.4 Secure Interfaces
- Input: order intent (sanitized, no secrets needed)
- Output: execution result + audit id

Order Intent schema:

```json
{
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "qty": 0.002,
  "risk": {
    "stop_loss_pct": 0.012,
    "take_profit_pct": 0.021,
    "max_slippage_bps": 15
  },
  "metadata": {
    "strategy_id": "uuid",
    "regime": "bull",
    "confidence": 0.83
  }
}
```

### 8.5 Secrets Handling
- Store encrypted secrets in DB (Supabase Postgres) or server-side vault file.
- Encryption: AES-256-GCM (recommended).
- Decrypt:
  - only inside secure exec process,
  - only in memory,
  - zeroize buffers when possible,
  - never log plaintext.

### 8.6 Risk Limits (Hard Guards)
- daily loss limit
- max leverage cap
- max position size cap
- max number of open positions
- max orders per minute (rate safety)
- slippage thresholds

### 8.7 Emergency Kill Switch
- UI button triggers server-side flag in DB.
- Secure exec checks kill switch before every placement.
- Hard-stop cancels outstanding orders (where supported) and blocks new orders.

---

## 9) Background Evolution Engine (FAST compute + SMART reasoning)

### 9.1 Purpose
Continuously evolve AlphaGene strategies without affecting live trading loop.

### 9.2 Execution Mode
- Runs periodically or regime-triggered.
- Uses historical window (e.g., last 7–30 days) for backtests in MVP.
- Produces candidate strategies and ranks them.

### 9.3 Compute Isolation
- Use multiprocessing for heavy backtests to avoid blocking asyncio loop.
- Each candidate backtest is a job; results are aggregated.

---

## 10) Genetic Algorithm Design (AlphaGene)

### 10.1 Why these genes (required explanation)

**RSI period**
- Lower period → faster reaction, more noise sensitivity.
- Higher period → smoother, slower, fewer trades.

**MA short window / MA long window**
- Determines trend confirmation horizon.
- Large long window → stable trend filter; small long window → more whipsaws.
- Short vs long spacing affects crossover frequency.

**Stop loss / take profit**
- Tight stop loss → protects capital but can stop out often.
- Wider stop loss → tolerates volatility but increases drawdown risk.
- Take profit influences expectancy and trade duration.

**Position size**
- Primary risk lever.
- Higher sizing increases variance, drawdown probability, and tail risk.

These genes together create distinct “strategy personalities”:
- **Aggressive:** low RSI, short MAs, wider TP, high position size.
- **Conservative:** higher RSI, longer MAs, tighter SL, smaller size.

### 10.2 Genome Representation
Example gene vector:

```text
[rsi_period, ma_short, ma_long, stop_loss_pct, take_profit_pct, position_size_pct]
```

Constraints:
- `rsi_period`: 5–30
- `ma_short`: 5–50
- `ma_long`: 20–200 (must be > ma_short)
- `stop_loss_pct`: 0.3%–5%
- `take_profit_pct`: 0.3%–10% (often > stop_loss)
- `position_size_pct`: 1%–30%

### 10.3 Mutation & Crossover
- Mutation: random jitter within bounds (or resample).
- Crossover: combine segments of two strong parents.

**Example**
- Parent A: `[7, 10, 60, 0.8%, 1.6%, 12%]`
- Parent B: `[14, 20, 120, 1.2%, 2.4%, 8%]`
- Child:    `[7, 20, 120, 1.2%, 1.6%, 8%]`

---

## 11) Generation Workflow (Gen1 → Gen5)

### 11.1 Fixed MVP Evolution Plan
- **5 generations**
- **10 strategies per generation**
- Per generation output: **Top 3** survive + **1 AlphaGene winner**

### 11.2 Per-Generation Steps (Required)
1. Generate 10 strategies
2. Python backtesting
3. Monte Carlo stress testing
4. Python fitness scoring
5. Top 3 survive
6. Only top 3 sent to DeepSeek

### 11.3 Why Python filters first (required)
- Minimizes AI workload and cost (even local inference is compute-heavy).
- Reduces latency and keeps system responsive.
- AI should reason on *high-quality candidates*, not random noise.
- Deterministic numeric filtering is more reproducible and auditable.

---

## 12) Backtesting & Fitness Scoring

### 12.1 Backtesting Engine
- Use Backtrader for MVP for credible trading simulation.
- Inputs: OHLCV candles.
- Output metrics:
  - total return
  - Sharpe ratio (approx)
  - max drawdown
  - win rate
  - avg trade duration
  - # trades
  - profit factor

### 12.2 Fitness Function (Deterministic)
Multi-objective can be simplified to scalar score for MVP.

Example:

```text
fitness =
  + 0.35 * normalized_sharpe
  + 0.25 * normalized_return
  - 0.20 * normalized_drawdown
  + 0.10 * normalized_win_rate
  - 0.10 * normalized_overtrade_penalty
```

Overtrade penalty example:
- if trades > threshold, penalize (reduces noise strategies)

### 12.3 Edge Cases
- Too few trades → unreliable metrics → penalize.
- No trades → fitness = very low.
- Extreme leverage/position size candidates → rejected before backtest.

---

## 13) Monte Carlo Stress Testing (MVP-optimized)

### 13.1 MVP Approach (Required)
- **50–100** simulated paths (not 1000+).
- Purpose: detect fragility, not to be statistically perfect.

### 13.2 What we simulate
- Return perturbations (bootstrap resampling)
- Slippage variation within bounds
- Random execution delay jitter
- Spread widening events

### 13.3 Output metrics for fitness augmentation
- survivability score: % of paths not blowing past drawdown threshold
- tail drawdown (95th percentile)
- worst-case return across paths

### 13.4 Why simplified Monte Carlo is sufficient for hackathon
- Demonstrates robust-thinking architecture.
- Finds obvious overfit strategies quickly.
- Keeps compute bounded and demo reliable.

---

## 14) HMM Regime Detection

### 14.1 Regimes
- **bull**
- **bear**
- **crash**
- **sideways**

### 14.2 Observations / Features (MVP)
- rolling returns
- rolling volatility
- MA slope or trend strength
- drawdown velocity proxy

### 14.3 HMM Outputs
- regime state at time `t`
- transition probabilities matrix
- confidence score (posterior probability)

### 14.4 Stabilization: thresholds + cooldowns (Required)
To avoid constant re-evolution:
- Confidence threshold: trigger only if `P(regime) > 0.80`
- Sustained window: must persist for N candles/minutes
- Cooldown: minimum time between regime-triggered re-evolutions

Example rule:
- “Switch to crash regime only if confidence > 0.80 for 5 consecutive minutes.”

---

## 15) DeepSeek-R1 Local AI Architecture (Ollama)

### 15.1 Why DeepSeek-R1 7B locally (Required)
**Zero API costs**
- Continuous evaluation would be expensive with cloud models.

**Privacy**
- No sensitive trading data leaves the machine.
- Supports data minimization and compliance posture.

**TEE integration**
- Local-only reasoning fits a secure enclave / compartment approach.
- Easier to ensure strict boundaries than with external calls.

**Offline capability**
- Works in restricted environments.

**Reduced operational risk**
- No vendor rate limits, outages, or policy shifts.

**Latency predictability**
- Still variable, but controlled locally and isolated from live loop.

### 15.2 What DeepSeek is NOT allowed to do (Required)
DeepSeek must not be used for:
- real-time trade execution
- websocket loops
- candle processing
- broker access
- direct trade placement

DeepSeek only does:
- strategy reasoning
- risk analysis commentary
- AI council simulation
- explainability
- qualitative critique of top strategies

### 15.3 Inference Interface
- Call Ollama locally via HTTP.
- Enforce timeouts and concurrency limits.
- Store prompts + responses for audit (sanitized).

---

## 16) AI Council Simulation (single-call, structured)

### 16.1 Goal
Simulate three roles using one model call:
- Backtesting Critic
- Risk Guardian
- Sentiment Forecaster

### 16.2 Data Minimization Input (Required)
Only send summarized metrics:

```json
{
  "strategy_id": "uuid",
  "genes": {
    "rsi_period": 9,
    "ma_short": 18,
    "ma_long": 96,
    "stop_loss_pct": 0.011,
    "take_profit_pct": 0.024,
    "position_size_pct": 0.10
  },
  "metrics": {
    "win_rate": 61,
    "max_drawdown_pct": 7.0,
    "sharpe_ratio": 1.8,
    "profit_factor": 1.35,
    "trades": 120
  },
  "regime_breakdown": {
    "bull": {"sharpe": 2.1, "dd": 5.2},
    "bear": {"sharpe": 0.6, "dd": 9.8},
    "sideways": {"sharpe": 1.1, "dd": 7.5},
    "crash": {"sharpe": -0.2, "dd": 14.0}
  },
  "monte_carlo": {
    "paths": 80,
    "survivability_pct": 92,
    "tail_dd_95_pct": 11.5,
    "worst_case_return_pct": -6.2
  }
}
```

### 16.3 Prompt Contract (Structured Output)
Require JSON output:

```json
{
  "backtesting_critic": {
    "summary": "...",
    "overfitting_risk": "low|medium|high",
    "notes": ["..."]
  },
  "risk_guardian": {
    "summary": "...",
    "risk_level": "low|medium|high",
    "recommended_limits": {
      "max_position_size_pct": 0.08,
      "max_daily_loss_pct": 2.0
    }
  },
  "sentiment_forecaster": {
    "summary": "...",
    "regime_sensitivity": "..."
  },
  "consensus": {
    "approve_for_shadow": true,
    "key_reasoning": ["..."],
    "watchouts": ["..."]
  }
}
```

### 16.4 Guardrails
- If model output is not valid JSON, discard and retry once with stricter system prompt; if fails, fall back to deterministic selection without AI.
- Never allow AI output to modify live risk limits directly; AI can only recommend.

---

## 17) Strategy Deployment: Shadow Mode + Hot Swap + Rollback

### 17.1 Safe Deployment Flow (Required)
1. New AlphaGene generated
2. Shadow-tested briefly (paper or “shadow decisions”)
3. Performance validated
4. Hot-swapped into live engine
5. Rollback available instantly

### 17.2 Shadow Mode Options
- **Paper trading**: place paper orders with realistic fees/slippage.
- **Shadow signals**: generate signals but do not place orders; compare against live strategy.

### 17.3 Hot-Swapping Mechanism
- Strategy registry supports atomic swap:
  - `active_strategy_id` pointer updated
  - live loop reads pointer at candle close boundary

### 17.4 Rollback
- Keep last N strategies with metadata.
- If live drawdown exceeds threshold after swap, auto-rollback.

---

## 18) Data Model & Supabase Schema

### 18.1 Core Entities
- users
- broker_connections
- strategies (AlphaGenes)
- evolution_runs
- generation_results
- backtest_results
- monte_carlo_results
- ai_reasoning_cards
- trades (paper/live)
- positions
- risk_events
- audit_logs
- dashboard_events (optional)

### 18.2 Example Tables (Simplified)

#### `strategies`
- id (uuid, pk)
- user_id (uuid, fk)
- genes (jsonb)
- created_at (timestamptz)
- status (text: candidate/shadow/live/retired)
- origin (text: gen1..gen5, manual, etc.)

#### `backtest_results`
- id
- strategy_id
- sharpe
- max_drawdown_pct
- win_rate
- trades
- profit_factor
- created_at

#### `ai_reasoning_cards`
- id
- strategy_id
- generation
- reasoning_json (jsonb)
- model (text)
- created_at

#### `audit_logs`
- id
- user_id
- event_type
- event_payload (jsonb)
- created_at
- hash (text)  (optional: tamper-evidence)

---

## 19) Supabase Auth + Realtime + RLS Policies

### 19.1 Auth
- Email/password for MVP.
- Optional OAuth for demo polish.

### 19.2 RLS (Row-Level Security)
Policies:
- users can read/write only their own strategies and runs.
- trades and audit logs isolated by `user_id`.
- server-side service role for Secure Exec layer writes.

### 19.3 Realtime
- Use Supabase Realtime or FastAPI WS (choose one primary).
- Recommended for MVP: FastAPI WS for high-frequency UI events; Supabase Realtime for durable state changes.

---

## 20) API Specifications (FastAPI)

### 20.1 REST Endpoints (MVP)
- `POST /auth/login` (optional if using Supabase directly)
- `GET /state` → current regime, active strategy id, kill switch state
- `POST /control/start` → start engines
- `POST /control/stop` → stop engines
- `POST /control/kill-switch` → enable/disable (server-side enforcement)
- `GET /strategies` → list strategies
- `GET /strategies/{id}` → details + metrics + reasoning
- `POST /broker/connect` → store encrypted creds (server-only)
- `POST /evolution/run` → trigger evolution (manual for demo)

### 20.2 WebSocket
- `WS /ws/dashboard`
  - server pushes:
    - price updates (throttled)
    - regime state
    - active strategy summary
    - evolution progress
    - latest AI reasoning cards
    - execution logs

---

## 21) WebSockets & Dashboard Streaming

### 21.1 Event Types
- `market.tick`
- `market.candle_close`
- `strategy.signal`
- `execution.order_submitted`
- `execution.order_filled`
- `risk.limit_triggered`
- `evolution.generation_started`
- `evolution.generation_scored`
- `evolution.top3_selected`
- `ai.reasoning_ready`
- `system.health`

### 21.2 Throttling Rules
- Price updates: max 5–10 per second to UI.
- Logs: batch per second.
- Execution events: immediate.

---

## 22) Frontend Architecture (React/Vite/Zustand/Recharts/Tailwind)

### 22.1 Tech Stack (Required)
- React + Vite
- TailwindCSS
- Zustand (state)
- Recharts (charts)
- Framer Motion (animations/microinteractions)

### 22.2 State Model (Zustand)
Slices:
- `sessionSlice` (user/auth)
- `marketSlice` (price, candles, indicators)
- `strategySlice` (active strategy genes, metrics, regime breakdown)
- `evolutionSlice` (gen progress, fitness graph, winners)
- `riskSlice` (limits, alerts, kill switch)
- `logsSlice` (execution + system logs)
- `aiSlice` (reasoning cards)

### 22.3 UI Principles
- “Apple-like simplicity” + “Stripe cleanliness”
- Minimal knobs by default; advanced panel collapsible
- Explainability everywhere: tooltips and AI cards

---

## 23) UX Requirements & Dashboard Modules

### 23.1 Required Dashboard Modules
1. **Live Trading Dashboard**
   - price chart (candles)
   - indicators overlay
   - signal marker (buy/sell)
2. **AlphaGene Visualization**
   - genes displayed as clean cards/sliders (read-only by default)
3. **Evolution Charts**
   - generation timeline
   - best fitness per generation
   - distribution of fitness among 10 candidates
4. **Regime Indicator**
   - current regime + confidence
   - transition probability mini-matrix
5. **AI Reasoning Cards**
   - Backtesting Critic, Risk Guardian, Sentiment Forecaster
   - consensus approval + watchouts
6. **Portfolio Analytics**
   - equity curve (paper/live)
   - exposure gauges
7. **Risk Exposure Indicators**
   - daily loss used, leverage, position size
8. **Emergency Stop Button**
   - prominent, two-step confirmation
9. **Live Execution Logs**
   - order intents, approvals, fills
10. **Confidence Indicators**
   - regime confidence, strategy confidence (derived deterministic metric)

### 23.2 Recharts Visualizations
- Line chart: equity curve
- Area chart: drawdown curve
- Bar chart: generation fitness distribution
- Scatter: risk vs return for top candidates
- Small multiples: regime performance breakdown
- Monte Carlo: fan chart / percentile bands

---

## 24) Security, Data Minimization, Zero-Trust Design

### 24.1 Data Minimization Principle (Required)
DeepSeek never receives:
- API keys
- user passwords
- broker credentials
- wallet balances
- full portfolio
- PII financial data

DeepSeek only receives:
- summarized strategy metrics
- normalized performance figures
- regime breakdown summaries
- Monte Carlo aggregates

### 24.2 Zero-Trust Boundaries
- UI is untrusted: cannot trigger direct broker calls.
- AI layer is untrusted: cannot access secrets or execution.
- Secure exec is trusted but minimal: smallest interface surface.

### 24.3 Logging & Privacy
- Redact sensitive fields.
- Separate audit logs (secure) from UI logs (sanitized).

---

## 25) Performance, Latency, and Scalability Plan

### 25.1 Latency Targets (Required)
- Live trading: **200ms–1s**
- AI reasoning: **2–10s acceptable**, async only

### 25.2 Performance Optimizations
- Candle-close processing (not tick-by-tick for everything)
- vectorized indicator computation
- backtests in multiprocessing pool
- AI inference concurrency limit (e.g., 1 at a time)

### 25.3 Scalability
MVP: 1–10 users on one host  
Production path:
- isolate secure exec per user
- separate evolution workers
- use queue (Redis/RQ/Celery) for evolution jobs
- horizontal scale WS gateways

---

## 26) Observability & Monitoring

### 26.1 Metrics
- live loop latency histogram
- websocket reconnect counts
- order placement success rate
- strategy swap count + rollback count
- evolution runtime per generation
- AI inference duration + failures
- kill switch activations

### 26.2 Logs
- structured JSON logs
- correlation id per evolution run and per order intent

### 26.3 Alerts (MVP)
- daily loss limit triggered
- repeated broker auth failures
- data feed downtime
- AI output invalid JSON (degraded mode)

---

## 27) Hackathon MVP Scope vs Mocking Plan (48–72 hours)

### 27.1 Must Be Fully Functional
- Web UI with live streaming
- Candle ingestion (real feed)
- Deterministic strategy execution (paper trading acceptable)
- Genetic evolution pipeline (5 gens, 10 per gen)
- Backtesting + basic fitness scoring
- HMM regime detection (simplified)
- Local DeepSeek via Ollama generating reasoning cards
- Shadow-mode validation + hot swap + rollback logic (simple)

### 27.2 Can Be Mocked / Simplified
- Broker integration: paper trading engine if real broker is too risky
- “TEE”: implement as separate process/module with strict API + encryption, not hardware enclave
- Monte Carlo: 50 paths, coarse modeling
- Sentiment: optional; can be a deterministic proxy (e.g., volatility regime narrative)

### 27.3 Demo Script (Recommended)
1. Start system, show regime detection.
2. Show current AlphaGene and signals.
3. Trigger evolution run.
4. Watch generation fitness charts update.
5. Show top 3 candidates + AI council critique.
6. Shadow-test winner, then hot swap.
7. Show kill switch and audit log entry.

---

## 28) Future Roadmap (Production-grade)

### 28.1 Security & Confidential Computing
- SGX / confidential VM enclaves for secure exec
- remote attestation for trust verification
- hardware-backed key sealing

### 28.2 Trading Sophistication
- multi-asset allocation
- portfolio-level risk parity constraints
- execution algorithms (TWAP/VWAP)
- adaptive slippage models

### 28.3 Research Platform
- strategy versioning
- reproducible experiment registry
- walk-forward testing at scale
- explainability dashboards and drift detection

---

## 29) Investor Positioning

### 29.1 Differentiation
- **Self-evolving** strategy engine with visible, interpretable outputs.
- **Local AI**: privacy + cost + control.
- **Security-first execution boundary**: AI cannot touch money.

### 29.2 Why now
- Local inference has become practical (7B-class models on consumer GPUs/CPUs).
- Retail demand for explainable automation with guardrails.
- Rising sensitivity to data privacy and API cost structures.

---

## 30) Conclusion

EvoTrade is designed as a credible, production-inspired trading system that is still hackathon-buildable:
- deterministic execution for safety and latency,
- evolutionary optimization for adaptivity,
- local DeepSeek reasoning for explainability and critique,
- strict secure execution boundaries to prevent AI from accessing money or secrets,
- modern UI that makes sophisticated systems approachable.

---

## Appendix A — Example Sequence Diagrams

### A1) Live Trading Candle Close → Order Placement

```text
Market WS -> Live Engine -> Risk Engine -> Secure Exec -> Broker -> Secure Exec -> WS/UI
     |            |             |             |           |            |          |
 candle_close     compute        validate      decrypt     place        audit     render
                 indicators      limits        keys        order        log       update
```

### A2) Evolution Run (Gen N)

```text
Evolution Engine -> Generate 10 -> Backtest -> MonteCarlo -> Fitness -> Top3 -> DeepSeek -> AlphaGene
                          |           |           |            |        |         |         |
                          +-----------+-----------+------------+--------+---------+---------+
```

---

## Appendix B — AI Failure Modes & Safe Defaults

- If AI is down: evolution still ranks strategies deterministically.
- If AI output invalid: discard and proceed with deterministic winner.
- If regime detector unstable: enforce cooldown and minimum-hold time.
- If data feed gaps: pause trading and alert UI.

---

## Appendix C — Example “Consensus to Deploy” Rule

Deploy candidate only if:
- deterministic fitness improvement > X%
- Monte Carlo survivability > 90%
- AI consensus approves for shadow
- shadow mode PnL not worse than baseline after N trades (or N minutes)

---

**End of PRD**