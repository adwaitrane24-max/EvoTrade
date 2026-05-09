/**
 * EvolutionPanel.jsx — best-fitness-per-generation line + Top-3 distribution per gen.
 */

import { useMemo } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../store'

export default function EvolutionPanel() {
  const { fitnessHistory, generations, currentGeneration, evolutionRunning } =
    useStore((s) => ({
      fitnessHistory: s.fitnessHistory,
      generations: s.generations,
      currentGeneration: s.currentGeneration,
      evolutionRunning: s.evolutionRunning,
    }))

  const lineData = useMemo(
    () => fitnessHistory.map((f, i) => ({ gen: i + 1, fitness: f })),
    [fitnessHistory]
  )

  const lastGen = generations[generations.length - 1]
  const distData = useMemo(() => {
    if (!lastGen) return []
    return (lastGen.top_3 || []).map((c, i) => ({
      rank: `#${i + 1}`,
      fitness: Number(c.fitness ?? 0),
    }))
  }, [lastGen])

  return (
    <div className="card h-full flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Evolution Progress
        </h2>
        <div className="flex items-center gap-2 text-xs">
          {evolutionRunning && (
            <motion.span
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ repeat: Infinity, duration: 1.6 }}
              className="text-indigo-400 font-mono"
            >
              evolving…
            </motion.span>
          )}
          <span className="text-gray-500">Gen {currentGeneration || '-'}/5</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 flex-1 min-h-0">
        {/* Best fitness across generations */}
        <div className="md:col-span-2 min-h-48">
          {lineData.length === 0 ? (
            <Empty msg="No generations yet — click Run Evolution." />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={lineData} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="gen" tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#374151' }} label={{ value: 'Generation', position: 'insideBottom', offset: -2, fill: '#4b5563', fontSize: 10 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#374151' }} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #374151', borderRadius: 6, fontSize: 12 }} />
                <ReferenceLine y={0} stroke="#374151" strokeDasharray="4 2" />
                <Line
                  type="monotone"
                  dataKey="fitness"
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#818cf8' }}
                  activeDot={{ r: 5 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top-3 distribution */}
        <div className="min-h-48">
          <div className="text-xs text-gray-500 mb-1 px-1">
            {lastGen ? `Top-3 (gen ${lastGen.generation})` : 'Top-3 distribution'}
          </div>
          {distData.length === 0 ? (
            <Empty msg="—" />
          ) : (
            <ResponsiveContainer width="100%" height="92%">
              <BarChart data={distData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="rank" tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#374151' }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#374151' }} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #374151', borderRadius: 6, fontSize: 12 }} />
                <Bar dataKey="fitness" fill="#a78bfa" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Top-3 mini-cards */}
      <AnimatePresence>
        {lastGen && (
          <motion.div
            key={lastGen.generation}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="border-t border-gray-800 pt-2 grid grid-cols-3 gap-2"
          >
            {(lastGen.top_3 || []).map((c, i) => (
              <div key={i} className="bg-gray-900/50 border border-gray-800 rounded-md p-2 text-[11px]">
                <div className="flex justify-between text-gray-400">
                  <span>#{i + 1}</span>
                  <span className="text-indigo-300 font-semibold">{Number(c.fitness ?? 0).toFixed(3)}</span>
                </div>
                <div className="mt-1 text-gray-500">
                  RSI {c.genes?.rsi_period} · MA {c.genes?.ma_short}/{c.genes?.ma_long}
                </div>
                {c.metrics && (
                  <div className="text-gray-600 mt-0.5">
                    DD {Number(c.metrics.max_drawdown_pct ?? 0).toFixed(1)}% · WR {Number(c.metrics.win_rate ?? 0).toFixed(0)}%
                  </div>
                )}
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Empty({ msg }) {
  return <div className="h-full flex items-center justify-center text-gray-600 text-sm">{msg}</div>
}
