/**
 * systemSlice.js — wiring layer (connection state, portfolio, system status).
 */

export const createSystemSlice = (set, get) => ({
  connected: false,
  systemStatus: 'idle',         // 'idle' | 'starting' | 'running' | 'stopped' | 'error'
  setConnected: (b) => set({ connected: b }),
  setSystemStatus: (s) => set({ systemStatus: s }),

  // Portfolio
  portfolioValue: 0,
  initialCapital: 10000,
  pnlPct: 0,
  cashUsdt: 10000,
  positions: {},
  highWaterMark: 10000,

  setPortfolio: ({ portfolio_value, initial_capital, pnl_pct, cash_usdt,
                   positions, high_water_mark }) =>
    set((s) => ({
      portfolioValue: portfolio_value ?? s.portfolioValue,
      initialCapital: initial_capital ?? s.initialCapital,
      pnlPct: pnl_pct ?? s.pnlPct,
      cashUsdt: cash_usdt ?? s.cashUsdt,
      positions: positions ?? s.positions,
      highWaterMark: high_water_mark ?? s.highWaterMark,
    })),

  // Equity curve (sampled from broadcasts / status polls)
  equityCurve: [],
  appendEquityPoint: (point) =>
    set((state) => ({
      equityCurve: [...state.equityCurve, point].slice(-500),
    })),
})
