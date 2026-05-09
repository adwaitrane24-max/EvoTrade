import React from 'react'
import { RadialBarChart, RadialBar, ResponsiveContainer } from 'recharts'
import { Regime } from '../../types'

const REGIME_COLOR: Record<Regime, string> = {
  BULL: '#10B981',
  BEAR: '#EF4444',
  SIDEWAYS: '#F59E0B',
  CRASH: '#DC2626',
}

const REGIME_DESC: Record<Regime, string> = {
  BULL: 'Upward momentum dominant',
  BEAR: 'Downward pressure detected',
  SIDEWAYS: 'Range-bound price action',
  CRASH: 'High volatility crash regime',
}

export function RegimeIndicator({ regime, confidence }: { regime: Regime; confidence: number }) {
  const color = REGIME_COLOR[regime]
  const data = [{ value: confidence * 100, fill: color }]

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-36 h-36">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%" cy="50%"
            innerRadius="65%" outerRadius="90%"
            startAngle={90} endAngle={-270}
            data={[{ value: 100, fill: '#1F1F25' }, ...data]}
            barSize={10}
          >
            <RadialBar dataKey="value" cornerRadius={5} background={false} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs font-mono font-bold" style={{ color }}>{regime}</span>
          <span className="text-lg font-mono font-semibold text-text-primary mt-0.5">
            {(confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      <p className="text-xs text-text-muted text-center mt-2 max-w-[140px]">{REGIME_DESC[regime]}</p>
    </div>
  )
}
