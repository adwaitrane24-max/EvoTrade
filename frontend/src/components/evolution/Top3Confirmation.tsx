import React, { useState } from 'react'
import { Chromosome } from '../../types'
import { Button } from '../common/Button'

interface Props {
  top3: Chromosome[]
  onConfirm: (selected: Chromosome) => void
  onCancel: () => void
}

function geneLabel(key: string): string {
  const map: Record<string, string> = {
    rsi_oversold: 'RSI Oversold',
    rsi_overbought: 'RSI Overbought',
    ma_short: 'MA Short',
    ma_long: 'MA Long',
    stop_loss_pct: 'Stop Loss',
    take_profit_pct: 'Take Profit',
    position_size_pct: 'Position Size',
    sentiment_weight: 'Sentiment Weight',
  }
  return map[key] ?? key
}

function fmtGene(key: string, val: number): string {
  if (key.includes('pct') || key.includes('weight')) return `${(val * 100).toFixed(1)}%`
  if (key.includes('ma_')) return `${Math.round(val)} bars`
  return val.toFixed(1)
}

function geneSummary(c: Chromosome): string {
  const g = c.genes
  const sl = g ? `${(g.stop_loss_pct * 100).toFixed(1)}%` : '?'
  const tp = g ? `${(g.take_profit_pct * 100).toFixed(1)}%` : '?'
  const rsi = g ? `RSI < ${g.rsi_oversold.toFixed(0)}` : ''
  const bt = c.backtest
  const survival = c.council?.forecaster?.score
    ? `${(c.council.forecaster.score * 100).toFixed(0)}%`
    : '?'
  return `Buys on ${rsi} signal. Stop-loss ${sl}, take-profit ${tp}. Win rate: ${bt ? (bt.win_rate * 100).toFixed(0) : '?'}%.`
}

export function Top3Confirmation({ top3, onConfirm, onCancel }: Props) {
  const [selected, setSelected] = useState(0)
  const sorted = [...top3].sort((a, b) => (b.fitness ?? 0) - (a.fitness ?? 0))

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-text-primary">Top 3 AlphaGenes Ready</h2>
        <p className="text-sm text-text-secondary mt-1">Select the strategy to deploy for paper trading.</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {sorted.map((chrom, idx) => (
          <div
            key={chrom.id ?? idx}
            onClick={() => setSelected(idx)}
            className={`rounded-xl border p-5 cursor-pointer transition-all duration-200 ${
              selected === idx
                ? 'bg-accent-primary/8 border-accent-primary shadow-[0_0_16px_rgba(59,130,246,0.2)]'
                : 'bg-bg-surface border-bg-border hover:border-accent-primary/30'
            }`}
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="text-xs text-text-muted font-mono mb-1">AlphaGene #{idx + 1}</div>
                <div className="text-2xl font-mono font-bold text-text-primary">
                  {(chrom.fitness ?? 0).toFixed(4)}
                </div>
                <div className="text-xs text-text-muted mt-0.5">fitness score</div>
              </div>
              <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-1 ${
                selected === idx ? 'border-accent-primary bg-accent-primary' : 'border-bg-border'
              }`}>
                {selected === idx && <div className="w-2 h-2 rounded-full bg-white" />}
              </div>
            </div>

            {chrom.genes && (
              <div className="space-y-1 mb-4">
                {Object.entries(chrom.genes).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span className="text-text-muted">{geneLabel(k)}</span>
                    <span className="font-mono text-text-secondary">{fmtGene(k, v as number)}</span>
                  </div>
                ))}
              </div>
            )}

            {chrom.backtest && (
              <div className="pt-3 border-t border-bg-border space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-text-muted">Sharpe</span>
                  <span className="font-mono text-text-secondary">{chrom.backtest.sharpe.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-text-muted">Max Drawdown</span>
                  <span className="font-mono text-signal-sell">{(chrom.backtest.max_drawdown * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-text-muted">Win Rate</span>
                  <span className="font-mono text-signal-buy">{(chrom.backtest.win_rate * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-text-muted">Trades (90d)</span>
                  <span className="font-mono text-text-secondary">{chrom.backtest.n_trades}</span>
                </div>
              </div>
            )}

            <p className="text-xs text-text-muted mt-3 leading-relaxed">{geneSummary(chrom)}</p>
          </div>
        ))}
      </div>

      <div className="border-t border-bg-border pt-5">
        <p className="text-sm text-text-secondary mb-4">
          Are you ready to deploy this AlphaGene to live paper trading?
        </p>
        <div className="flex gap-3">
          <Button onClick={() => onConfirm(sorted[selected])} size="lg">
            Yes, Start Trading →
          </Button>
          <Button variant="ghost" onClick={onCancel} size="lg">
            Let me think
          </Button>
        </div>
      </div>
    </div>
  )
}
