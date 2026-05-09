import { create } from 'zustand'
import { Candle, Trade, Portfolio, Regime, Chromosome } from '../types'

interface TradingState {
  candles: Candle[]
  trades: Trade[]
  portfolio: Portfolio | null
  currentPrice: number
  regime: Regime
  regimeConfidence: number
  alphaGene: Chromosome | null
  isRunning: boolean
  sessionId: string

  appendCandle: (c: Candle) => void
  addTrade: (t: Trade) => void
  setPortfolio: (p: Portfolio) => void
  setCurrentPrice: (p: number) => void
  setRegime: (r: Regime, confidence: number) => void
  setAlphaGene: (g: Chromosome) => void
  setRunning: (v: boolean) => void
  setSessionId: (id: string) => void
  reset: () => void
}

const defaultPortfolio: Portfolio = {
  cash: 0,
  position: null,
  trades: [],
  equity_curve: [],
  total_pnl: 0,
  daily_pnl: 0,
  win_rate: 0,
  wins: 0,
  total_closed: 0,
}

export const useTradingStore = create<TradingState>((set) => ({
  candles: [],
  trades: [],
  portfolio: null,
  currentPrice: 0,
  regime: 'SIDEWAYS',
  regimeConfidence: 0.70,
  alphaGene: null,
  isRunning: false,
  sessionId: '',

  appendCandle: (c) =>
    set((s) => ({
      candles: [...s.candles.slice(-199), c],
      currentPrice: c.close,
    })),
  addTrade: (t) => set((s) => ({ trades: [t, ...s.trades].slice(0, 50) })),
  setPortfolio: (p) => set({ portfolio: p }),
  setCurrentPrice: (p) => set({ currentPrice: p }),
  setRegime: (regime, regimeConfidence) => set({ regime, regimeConfidence }),
  setAlphaGene: (g) => set({ alphaGene: g }),
  setRunning: (v) => set({ isRunning: v }),
  setSessionId: (id) => set({ sessionId: id }),
  reset: () => set({
    candles: [], trades: [], portfolio: null, currentPrice: 0,
    regime: 'SIDEWAYS', regimeConfidence: 0.70, alphaGene: null,
    isRunning: false, sessionId: '',
  }),
}))
