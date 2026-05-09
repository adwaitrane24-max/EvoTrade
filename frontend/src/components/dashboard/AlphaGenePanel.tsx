import React from 'react'
import { Chromosome } from '../../types'

const GENE_META: Record<string, { label: string; tip: string }> = {
  rsi_oversold: { label: 'RSI Oversold', tip: 'Buy signal when RSI drops below this' },
  rsi_overbought: { label: 'RSI Overbought', tip: 'Sell signal when RSI exceeds this' },
  ma_short: { label: 'MA Short', tip: 'Fast moving average window (bars)' },
  ma_long: { label: 'MA Long', tip: 'Slow moving average window (bars)' },
  stop_loss_pct: { label: 'Stop Loss', tip: 'Auto-close position on this % loss' },
  take_profit_pct: { label: 'Take Profit', tip: 'Auto-close position on this % gain' },
  position_size_pct: { label: 'Position Size', tip: 'Fraction of capital deployed per trade' },
  sentiment_weight: { label: 'Sentiment Wt.', tip: 'Weight of sentiment signal in decisions' },
}

function fmtGene(key: string, val: number): string {
  if (key.includes('pct') || key.includes('weight')) return `${(val * 100).toFixed(1)}%`
  if (key.includes('ma_')) return `${Math.round(val)}`
  return val.toFixed(1)
}

export function AlphaGenePanel({ gene }: { gene: Chromosome }) {
  return (
    <div className="h-full flex flex-col">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-text-primary">AlphaGene</h3>
        <p className="text-xs text-text-muted font-mono mt-0.5">
          Gen {gene.generation} · Fitness {(gene.fitness ?? 0).toFixed(4)}
        </p>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto">
        {gene.genes && Object.entries(gene.genes).map(([key, val]) => {
          const meta = GENE_META[key]
          return (
            <div
              key={key}
              className="flex justify-between items-center group"
              title={meta?.tip}
            >
              <span className="text-xs text-text-muted group-hover:text-text-secondary transition-colors">
                {meta?.label ?? key}
              </span>
              <span className="text-xs font-mono text-text-secondary">{fmtGene(key, val as number)}</span>
            </div>
          )
        })}
      </div>
      {gene.backtest && (
        <div className="mt-4 pt-3 border-t border-bg-border space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-text-muted">Sharpe</span>
            <span className="font-mono text-text-secondary">{gene.backtest.sharpe.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-text-muted">Max DD</span>
            <span className="font-mono text-signal-sell">{(gene.backtest.max_drawdown * 100).toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  )
}
