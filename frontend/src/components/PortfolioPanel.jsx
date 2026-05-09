/**
 * PortfolioPanel.jsx — equity curve + cash/exposure breakdown.
 */

import { useMemo } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { motion } from 'framer-motion'
import { useStore } from '../store'

export default function PortfolioPanel() {
  const { equityCurve, portfolioValue, initialCapital, pnlPct, cashUsdt, positions, highWaterMark } =
    useStore((s) => ({
      equityCurve: s.equityCurve,
      portfolioValue: s.portfolioValue,
      initialCapital: s.initialCapital,
      pnlPct: s.pnlPct,
      cashUsdt: s.cashUsdt,
      positions: s.positions,
      highWaterMark: s.highWaterMark,
    }))

  const data = useMemo(
    () => equityCurve.map((p) => ({ ts: p.ts ? new Date(p.ts).toLocaleTimeString() : '', equity: p.equity })),
    [equityCurve]
  )

  const drawdown = highWaterMark > 0
    ? Math.max(0, (highWaterMark - portfolioValue) / highWaterMark * 100)
    : 0
  const exposure = portfolioValue > 0 ? Math.max(0, 100 - (cashUsdt / portfolioValue * 100)) : 0
  const positionCount = Object.keys(positions || {}).length

  return (
    <div className="card flex flex-col gap-3 h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Portfolio</h2>
        <motion.span
          key={Math.round(pnlPct * 10)}
          initial={{ scale: 0.85 }}
          animate={{ scale: 1 }}
          className={`text-xs font-bold tabular-nums ${pnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
        >
          {pnlPct >= 0 ? '+' : ''}{Number(pnlPct).toFixed(2)}%
        </motion.span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <Stat label="Equity" value={`$${Number(portfolioValue || initialCapital).toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
        <Stat label="Cash" value={`$${Number(cashUsdt || initialCapital).toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
        <Stat label="Open" value={positionCount} />
      </div>

      <div className="flex-1 min-h-32">
        {data.length === 0 ? (
          <Empty msg="Equity curve will start once first trade fills." />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
              <defs>
                <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"  stopColor="#34d399" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="ts" tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#374151' }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#374151' }} domain={['auto', 'auto']} />
              <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #374151', borderRadius: 6, fontSize: 12 }} formatter={(v) => `$${Number(v).toFixed(2)}`} />
              <ReferenceLine y={initialCapital} stroke="#374151" strokeDasharray="4 2" />
              <Area type="monotone" dataKey="equity" stroke="#34d399" strokeWidth={2}
                    fill="url(#eqGrad)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="border-t border-gray-800 pt-2 grid grid-cols-2 gap-3">
        <Gauge label="Exposure" value={exposure} color="#a78bfa" suffix="%" />
        <Gauge label="Drawdown" value={drawdown} color="#f87171" suffix="%" />
      </div>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="bg-gray-900/40 border border-gray-800 rounded-md py-1.5 px-2">
      <div className="text-[9px] uppercase tracking-wider text-gray-500">{label}</div>
      <div className="text-sm font-semibold tabular-nums text-gray-200">{value}</div>
    </div>
  )
}

function Gauge({ label, value, color, suffix = '%' }) {
  return (
    <div>
      <div className="flex justify-between text-[10px] mb-1">
        <span className="text-gray-500 uppercase tracking-wider">{label}</span>
        <span className="tabular-nums" style={{ color }}>{Number(value).toFixed(1)}{suffix}</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(0, Math.min(100, value))}%` }}
          transition={{ duration: 0.4 }}
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
    </div>
  )
}

function Empty({ msg }) {
  return <div className="h-full flex items-center justify-center text-gray-600 text-xs">{msg}</div>
}
