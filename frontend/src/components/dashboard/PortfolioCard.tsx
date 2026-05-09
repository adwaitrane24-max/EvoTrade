import React from 'react'
import { Portfolio } from '../../types'

function MetricCard({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="bg-bg-surface border border-bg-border rounded-xl p-4">
      <p className="text-xs text-text-muted uppercase tracking-wider mb-2">{label}</p>
      <div className="font-mono text-lg font-semibold text-text-primary">{value}</div>
      {sub && <p className="text-xs text-text-muted mt-1 font-mono">{sub}</p>}
    </div>
  )
}

function pnlColor(val: number) {
  return val > 0 ? 'text-signal-buy' : val < 0 ? 'text-signal-sell' : 'text-text-secondary'
}

function fmtPnl(val: number): string {
  const sign = val >= 0 ? '+' : ''
  return `${sign}₹${Math.abs(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function PortfolioCard({ portfolio, initialCapital }: { portfolio: Portfolio; initialCapital: number }) {
  return (
    <div className="grid grid-cols-4 gap-3">
      <MetricCard
        label="Capital"
        value={`₹${(portfolio.cash).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
        sub={`Initial: ₹${initialCapital.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
      />
      <MetricCard
        label="P&L Today"
        value={
          <span className={pnlColor(portfolio.daily_pnl)}>{fmtPnl(portfolio.daily_pnl)}</span>
        }
      />
      <MetricCard
        label="Total P&L"
        value={
          <span className={pnlColor(portfolio.total_pnl)}>{fmtPnl(portfolio.total_pnl)}</span>
        }
      />
      <MetricCard
        label="Win Rate"
        value={
          <span className={portfolio.win_rate > 0.5 ? 'text-signal-buy' : 'text-signal-sell'}>
            {(portfolio.win_rate * 100).toFixed(0)}%
          </span>
        }
        sub={`${portfolio.wins}/${portfolio.total_closed} trades`}
      />
    </div>
  )
}
