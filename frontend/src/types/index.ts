// ── Chat ────────────────────────────────────────────────────────────────────
export interface ChatMessage {
  id: string
  role: 'bot' | 'user'
  text: string
  timestamp: number
  quickReplies?: string[]
}

export interface UserProfile {
  name?: string
  capital?: number
  risk_level?: string
  experience?: string
  asset_pref?: string
  daily_loss_limit?: number
  strategy_pref?: string
}

export interface ChatResponse {
  bot_message: string
  step: number
  total_steps: number
  profile_so_far: UserProfile
  is_complete: boolean
  quick_replies?: string[]
}

// ── Evolution ────────────────────────────────────────────────────────────────
export interface GeneVector {
  rsi_oversold: number
  rsi_overbought: number
  ma_short: number
  ma_long: number
  stop_loss_pct: number
  take_profit_pct: number
  position_size_pct: number
  sentiment_weight: number
}

export interface BacktestResult {
  sharpe: number
  max_drawdown: number
  win_rate: number
  n_trades: number
}

export interface CouncilResult {
  critic: { score: number; verdict: string; note: string }
  guardian: { score: number; note: string }
  forecaster: { score: number; note: string }
  composite_score: number
}

export interface Chromosome {
  id: string
  generation: number
  genes: GeneVector
  fitness: number
  survived?: boolean
  backtest?: BacktestResult
  council?: CouncilResult
  alpha_gene_id?: string
}

export interface GenerationData {
  generation: number
  ranked: Chromosome[]
  top3: Chromosome[]
}

// ── Trading ──────────────────────────────────────────────────────────────────
export type Signal = 'BUY' | 'SELL' | 'HOLD'
export type Regime = 'BULL' | 'BEAR' | 'SIDEWAYS' | 'CRASH'

export interface Candle {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  closed: boolean
}

export interface Trade {
  id: string
  timestamp: string
  side: 'BUY' | 'SELL'
  qty: number
  price: number
  pnl: number | null
  reason: string
}

export interface Position {
  qty: number
  entry_price: number
}

export interface Portfolio {
  cash: number
  position: Position | null
  trades: Trade[]
  equity_curve: number[]
  total_pnl: number
  daily_pnl: number
  win_rate: number
  wins: number
  total_closed: number
  equity?: number
}

// ── WebSocket events ──────────────────────────────────────────────────────────
export interface WsEvent {
  type: string
  timestamp: string
  data: Record<string, unknown>
}
