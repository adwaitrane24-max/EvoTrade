import React, { useMemo } from 'react'
import {
  ComposedChart, Line, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceDot,
} from 'recharts'
import { Candle, Trade } from '../../types'

interface Props {
  candles: Candle[]
  trades: Trade[]
}

export function PriceChart({ candles, trades }: Props) {
  const data = useMemo(() => {
    return candles.map((c) => {
      const ts = new Date(c.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      const trade = trades.find((t) => {
        const tTs = new Date(t.timestamp).getTime()
        return Math.abs(tTs - c.timestamp) < 65000
      })
      return {
        time: ts,
        price: c.close,
        trade,
      }
    })
  }, [candles, trades])

  const prices = candles.map((c) => c.close)
  const minPrice = Math.min(...prices) * 0.9995
  const maxPrice = Math.max(...prices) * 1.0005

  const buyDots = data.filter((d) => d.trade?.side === 'BUY')
  const sellDots = data.filter((d) => d.trade?.side === 'SELL')

  return (
    <div className="h-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="time"
            tick={{ fill: '#5A5A63', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[minPrice, maxPrice]}
            tick={{ fill: '#5A5A63', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `$${v.toLocaleString()}`}
            width={70}
          />
          <Tooltip
            contentStyle={{ background: '#111114', border: '1px solid #1F1F25', borderRadius: 8, fontSize: 12 }}
            formatter={(val: number) => [`$${val.toLocaleString()}`, 'Price']}
            labelStyle={{ color: '#5A5A63' }}
          />
          <Area type="monotone" dataKey="price" stroke="none" fill="url(#priceGrad)" />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#E8E8EC"
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3, fill: '#3B82F6' }}
          />
          {buyDots.map((d, i) => (
            <ReferenceDot
              key={`buy-${i}`}
              x={d.time}
              y={d.price}
              r={5}
              fill="#10B981"
              stroke="#0A0A0B"
              strokeWidth={1.5}
              label={{ value: '▲', position: 'top', fill: '#10B981', fontSize: 10 }}
            />
          ))}
          {sellDots.map((d, i) => (
            <ReferenceDot
              key={`sell-${i}`}
              x={d.time}
              y={d.price}
              r={5}
              fill="#EF4444"
              stroke="#0A0A0B"
              strokeWidth={1.5}
              label={{ value: '▼', position: 'bottom', fill: '#EF4444', fontSize: 10 }}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
