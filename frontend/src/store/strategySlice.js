/**
 * strategySlice.js — current AlphaGenes (active + shadow) and the registry list.
 */

const MAX_SIGNALS = 100

export const createStrategySlice = (set, get) => ({
  activeStrategy: null,         // {id, gene, status, ...}
  shadowStrategy: null,
  strategies: [],               // full list

  setActiveStrategy: (rec) => set({ activeStrategy: rec }),
  setShadowStrategy: (rec) => set({ shadowStrategy: rec }),
  setStrategies: (rows) => set({ strategies: rows }),

  signals: [],                  // last N {ts, action, indicators, strategy_id}
  appendSignal: (signal) =>
    set((state) => ({
      signals: [{ ts: new Date().toISOString(), ...signal }, ...state.signals].slice(0, MAX_SIGNALS),
    })),
})
