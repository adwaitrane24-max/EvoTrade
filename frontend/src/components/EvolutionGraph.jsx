/**
 * EvolutionGraph.jsx — Live Recharts line chart of generation vs. fitness score.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const val = payload[0].value
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-400">Generation {label}</p>
      <p className="text-indigo-300 font-semibold">
        Fitness: {val >= 0 ? '+' : ''}{Number(val).toFixed(4)}
      </p>
    </div>
  )
}

export default function EvolutionGraph({ fitnessHistory, currentGene, generation }) {
  const data = fitnessHistory.map((fitness, i) => ({ gen: i + 1, fitness }))
  const latest = data[data.length - 1]
  const best = data.reduce((b, d) => (d.fitness > (b?.fitness ?? -Infinity) ? d : b), null)

  return (
    <div className="card h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Evolution Progress
        </h2>
        <div className="flex items-center gap-3 text-xs">
          {generation > 0 && (
            <span className="text-gray-500">Gen {generation}</span>
          )}
          {latest && (
            <span className={`font-semibold tabular-nums ${latest.fitness >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {latest.fitness >= 0 ? '+' : ''}{latest.fitness.toFixed(4)}
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 min-h-0">
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-600 text-sm">
            Waiting for first generation…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="gen"
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: '#374151' }}
                label={{ value: 'Generation', position: 'insideBottom', offset: -2, fill: '#4b5563', fontSize: 11 }}
              />
              <YAxis
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: '#374151' }}
                tickFormatter={(v) => v.toFixed(2)}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={0} stroke="#374151" strokeDasharray="4 2" />
              {best && (
                <ReferenceLine
                  y={best.fitness}
                  stroke="#6366f1"
                  strokeDasharray="4 2"
                  strokeOpacity={0.4}
                />
              )}
              <Line
                type="monotone"
                dataKey="fitness"
                stroke="#6366f1"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#818cf8', strokeWidth: 0 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {currentGene && (
        <div className="border-t border-gray-800 pt-3 grid grid-cols-3 gap-3 text-xs text-center">
          <Stat label="RSI period" value={currentGene.rsi_period} />
          <Stat label="MA short/long" value={`${currentGene.ma_short}/${currentGene.ma_long}`} />
          <Stat label="Stop / TP" value={`${((currentGene.stop_loss_pct ?? 0) * 100).toFixed(1)}% / ${((currentGene.take_profit_pct ?? 0) * 100).toFixed(1)}%`} />
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div>
      <p className="text-gray-500">{label}</p>
      <p className="text-gray-300 font-semibold tabular-nums mt-0.5">{value}</p>
    </div>
  )
}
