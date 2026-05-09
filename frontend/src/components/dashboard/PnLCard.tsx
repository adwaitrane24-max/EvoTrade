import React from 'react'
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts'

export function PnLCard({ equityCurve, initialCapital }: { equityCurve: number[]; initialCapital: number }) {
  const data = equityCurve.slice(-100).map((v, i) => ({ i, v }))
  const current = equityCurve.length > 0 ? equityCurve[equityCurve.length - 1] : initialCapital
  const pnl = current - initialCapital
  const pnlPct = (pnl / initialCapital) * 100
  const color = pnl >= 0 ? '#10B981' : '#EF4444'

  return (
    <div className="h-full flex flex-col">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-text-primary">Equity Curve</h3>
        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-xl font-mono font-bold text-text-primary">
            ₹{current.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </span>
          <span className={`text-sm font-mono ${pnl >= 0 ? 'text-signal-buy' : 'text-signal-sell'}`}>
            {pnl >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
          </span>
        </div>
      </div>
      <div className="flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.2} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Tooltip
              contentStyle={{ background: '#111114', border: '1px solid #1F1F25', borderRadius: 8, fontSize: 11 }}
              formatter={(v: number) => [`₹${v.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`, 'Equity']}
              labelFormatter={() => ''}
            />
            <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} fill="url(#equityGrad)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
