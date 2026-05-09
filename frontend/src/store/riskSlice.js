/**
 * riskSlice.js — risk limits, kill switch, recent risk events.
 */

const MAX_RISK_EVENTS = 50

export const createRiskSlice = (set, get) => ({
  killSwitchActive: false,
  paused: false,

  riskLimits: {
    max_daily_loss_pct: 5.0,
    max_position_size_pct: 0.30,
    max_open_positions: 5,
    max_orders_per_minute: 30,
  },

  riskEvents: [],

  setKillSwitch: (active) => set({ killSwitchActive: active }),
  setPaused: (paused) => set({ paused }),
  setRiskLimits: (limits) => set({ riskLimits: { ...get().riskLimits, ...limits } }),
  appendRiskEvent: (event) =>
    set((state) => ({
      riskEvents: [{ ts: new Date().toISOString(), ...event }, ...state.riskEvents].slice(0, MAX_RISK_EVENTS),
    })),
})
