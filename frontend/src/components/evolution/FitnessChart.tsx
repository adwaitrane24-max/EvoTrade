import React from 'react'
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Chromosome } from '../../types'

interface Props {
  chromosomes: Chromosome[]
  top3Ids: Set<string>
}

export function FitnessChart({ chromosomes, top3Ids }: Props) {
  const data = chromosomes.map((c) => ({
    x: c.generation,
    y: c.fitness ?? 0,
    id: c.id,
    isTop: top3Ids.has(c.id),
  }))

  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
          <XAxis
            dataKey="x"
            type="number"
            domain={[1, 5]}
            ticks={[1, 2, 3, 4, 5]}
            tick={{ fill: '#5A5A63', fontSize: 11, fontFamily: 'JetBrains Mono' }}
            label={{ value: 'Generation', position: 'insideBottom', fill: '#5A5A63', fontSize: 11, dy: 8 }}
          />
          <YAxis
            dataKey="y"
            type="number"
            domain={[0, 1]}
            tick={{ fill: '#5A5A63', fontSize: 11, fontFamily: 'JetBrains Mono' }}
          />
          <Tooltip
            contentStyle={{ background: '#111114', border: '1px solid #1F1F25', borderRadius: 8, fontSize: 12 }}
            formatter={(val: number) => [val.toFixed(4), 'Fitness']}
            labelFormatter={(label) => `Gen ${label}`}
          />
          <Scatter data={data}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.isTop ? '#3B82F6' : '#5A5A63'}
                fillOpacity={entry.isTop ? 0.9 : 0.5}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
