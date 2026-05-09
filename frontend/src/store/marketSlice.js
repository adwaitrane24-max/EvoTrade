/**
 * marketSlice.js — live price + indicators + regime.
 */

const MAX_CANDLES = 250

export const createMarketSlice = (set, get) => ({
  symbol: 'BTC-USD',
  setSymbol: (symbol) => set({ symbol }),

  candles: [],          // array of { ts, close, ... }
  appendCandle: (candle) =>
    set((state) => {
      const next = [...state.candles, candle].slice(-MAX_CANDLES)
      return { candles: next }
    }),

  indicators: { rsi: null, ma_short: null, ma_long: null, price: null },
  setIndicators: (indicators) => set({ indicators }),

  // Regime layer
  regime: null,
  regimeConfidence: 0,
  regimePosterior: { bull: 0, sideways: 0, bear: 0, crash: 0 },
  transitionMatrix: [],
  regimeSwitchCount: 0,
  setRegime: ({ regime, confidence, posterior, transition_matrix, switched }) =>
    set((state) => ({
      regime,
      regimeConfidence: confidence ?? state.regimeConfidence,
      regimePosterior: posterior ?? state.regimePosterior,
      transitionMatrix: transition_matrix ?? state.transitionMatrix,
      regimeSwitchCount: switched ? state.regimeSwitchCount + 1 : state.regimeSwitchCount,
    })),
})
