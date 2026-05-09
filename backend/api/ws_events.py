"""
ws_events.py — Canonical WebSocket event-type constants per PRD §21.1.

All backend modules emit events with these exact names so the frontend
Zustand store can route them deterministically.
"""

# ── Market layer ──────────────────────────────────────────────────────────────
MARKET_TICK             = "market.tick"
MARKET_CANDLE_CLOSE     = "market.candle_close"

# ── Strategy / signal layer ───────────────────────────────────────────────────
STRATEGY_SIGNAL         = "strategy.signal"
STRATEGY_ACTIVATED      = "strategy.activated"      # extension: hot-swap notification
STRATEGY_SHADOW_UPDATE  = "strategy.shadow_update"  # extension: shadow tick

# ── Execution layer ───────────────────────────────────────────────────────────
EXECUTION_ORDER_SUBMITTED = "execution.order_submitted"
EXECUTION_ORDER_FILLED    = "execution.order_filled"
EXECUTION_ORDER_REJECTED  = "execution.order_rejected"

# ── Risk layer ────────────────────────────────────────────────────────────────
RISK_LIMIT_TRIGGERED    = "risk.limit_triggered"
RISK_KILL_SWITCH        = "risk.kill_switch"

# ── Evolution layer ───────────────────────────────────────────────────────────
EVOLUTION_RUN_STARTED      = "evolution.run_started"
EVOLUTION_GEN_STARTED      = "evolution.generation_started"
EVOLUTION_GEN_SCORED       = "evolution.generation_scored"
EVOLUTION_TOP3_SELECTED    = "evolution.top3_selected"
EVOLUTION_RUN_COMPLETED    = "evolution.run_completed"

# ── Regime layer ──────────────────────────────────────────────────────────────
REGIME_DETECTED         = "regime.detected"
REGIME_SWITCHED         = "regime.switched"

# ── AI layer ──────────────────────────────────────────────────────────────────
AI_REASONING_READY      = "ai.reasoning_ready"

# ── System layer ──────────────────────────────────────────────────────────────
SYSTEM_HEALTH           = "system.health"
SYSTEM_ERROR            = "system.error"


ALL_EVENTS = {
    "market":    [MARKET_TICK, MARKET_CANDLE_CLOSE],
    "strategy":  [STRATEGY_SIGNAL, STRATEGY_ACTIVATED, STRATEGY_SHADOW_UPDATE],
    "execution": [EXECUTION_ORDER_SUBMITTED, EXECUTION_ORDER_FILLED,
                  EXECUTION_ORDER_REJECTED],
    "risk":      [RISK_LIMIT_TRIGGERED, RISK_KILL_SWITCH],
    "evolution": [EVOLUTION_RUN_STARTED, EVOLUTION_GEN_STARTED,
                  EVOLUTION_GEN_SCORED, EVOLUTION_TOP3_SELECTED,
                  EVOLUTION_RUN_COMPLETED],
    "regime":    [REGIME_DETECTED, REGIME_SWITCHED],
    "ai":        [AI_REASONING_READY],
    "system":    [SYSTEM_HEALTH, SYSTEM_ERROR],
}
