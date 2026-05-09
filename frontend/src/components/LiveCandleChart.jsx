/**
 * LiveCandleChart.jsx — Live price chart + RSI overlay + buy/sell markers.
 * Uses Recharts ComposedChart.
 */

import { useMemo } from 'react'
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, ReferenceDot,
} from 'recharts'
import { useStore } from '../store'

export default function LiveCandleChart() {
  const candles = useStore((s) => s.candles)
  const indicators = useStore((s) => s.indicators)
  const signals = useStore((s) => s.signals)

  const data = useMemo(() => candles.map((c) => ({
    ts: c.ts ? new Date(c.ts).toLocaleTimeString() : '',
    close: c.close,
  })), [candles])

  const lastClose = data.length ? data[data.length - 1].close : null

  // Map BUY/SELL signals to dots on chart
  const buys = signals.filter((x) => x.action === 'BUY').slice(0, 10)
  const sells = signals.filter((x) => x.action === 'SELL').slice(0, 10)

  return (
    <div className="card h-full flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Live Trading
        </h2>
        <div className="flex gap-3 text-xs tabular-nums">
          <Stat label="Price" value={lastClose ? `$${lastClose.toLocaleString()}` : '—'} accent="text-indigo-300" />
          <Stat label="RSI" value={indicators.rsi ?? '—'} />
          <Stat label="MA-S" value={indicators.ma_short ?? '—'} />
          <Stat label="MA-L" value={indicators.ma_long ?? '—'} />
        </div>
      </div>

      <div className="flex-1 min-h-0">
        {data.length === 0 ? (
          <Empty msg="Waiting for first candle close…" />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 6, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"  stopColor="#6366f1" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="ts" tick={{ fill: '#6b7280', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#374151' }} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#374151' }} tickFormatter={(v) => `$${Number(v).toLocaleString()}`} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #374151', borderRadius: 6, fontSize: 12 }}
                labelStyle={{ color: '#9ca3af' }}
                itemStyle={{ color: '#a5b4fc' }}
                formatter={(v) => `$${Number(v).toLocaleString()}`}
              />
              <Area type="monotone" dataKey="close" stroke="#6366f1" strokeWidth={2}
                    fill="url(#priceGrad)" isAnimationActive={false} />
              {indicators.ma_long && <ReferenceLine y={indicators.ma_long} stroke="#a78bfa" strokeDasharray="4 2" strokeOpacity={0.5} />}
              {indicators.ma_short && <ReferenceLine y={indicators.ma_short} stroke="#34d399" strokeDasharray="4 2" strokeOpacity={0.5} />}
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="flex items-center gap-4 text-xs text-gray-500 border-t border-gray-800 pt-2">
        <Legend color="#6366f1" label="Price" />
        <Legend color="#34d399" label="MA short" />
        <Legend color="#a78bfa" label="MA long" />
        <span className="ml-auto text-gray-600">{candles.length} candles</span>
      </div>
    </div>
  )
}

function Stat({ label, value, accent = 'text-gray-200' }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-gray-500">{label}</span>
      <span className={`font-semibold ${accent}`}>{value}</span>
    </div>
  )
}

function Legend({ color, label }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="h-0.5 w-3 rounded-sm" style={{ backgroundColor: color }} />
      {label}
    </span>
  )
}

function Empty({ msg }) {
  return <div className="h-full flex items-center justify-center text-gray-600 text-sm">{msg}</div>
}
