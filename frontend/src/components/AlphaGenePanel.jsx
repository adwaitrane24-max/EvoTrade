/**
 * AlphaGenePanel.jsx — read-only sliders showing the active strategy's gene values.
 */

import { motion } from 'framer-motion'
import { useStore } from '../store'

const PARAMS = [
  { key: 'rsi_period',        label: 'RSI period',        unit: 'bars',  min: 5,    max: 30 },
  { key: 'ma_short',          label: 'MA short',          unit: 'bars',  min: 5,    max: 50 },
  { key: 'ma_long',           label: 'MA long',           unit: 'bars',  min: 20,   max: 200 },
  { key: 'stop_loss_pct',     label: 'Stop loss',         unit: '%',     min: 0.003, max: 0.05, pct: true },
  { key: 'take_profit_pct',   label: 'Take profit',       unit: '%',     min: 0.003, max: 0.10, pct: true },
  { key: 'position_size_pct', label: 'Position size',     unit: '%',     min: 0.01, max: 0.30, pct: true },
]

export default function AlphaGenePanel() {
  const { active, shadow } = useStore((s) => ({
    active: s.activeStrategy,
    shadow: s.shadowStrategy,
  }))

  const gene = active?.gene
  return (
    <div className="card h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          AlphaGene
        </h2>
        <div className="flex items-center gap-2">
          {active && (
            <span className="badge bg-emerald-900/60 text-emerald-300 border border-emerald-800">
              live · {active.origin}
            </span>
          )}
          {shadow && (
            <span className="badge bg-indigo-900/60 text-indigo-300 border border-indigo-800">
              shadow · {shadow.origin}
            </span>
          )}
        </div>
      </div>

      {!gene ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 text-gray-600 text-sm">
          <span className="text-3xl">🧬</span>
          Awaiting first AlphaGene…
        </div>
      ) : (
        <div className="flex flex-col gap-3 flex-1">
          {PARAMS.map((p) => (
            <GeneBar key={p.key} param={p} value={gene[p.key]} />
          ))}
        </div>
      )}

      {active?.fitness_at_creation != null && (
        <div className="border-t border-gray-800 pt-3 text-xs text-gray-500 flex justify-between">
          <span>Fitness at creation</span>
          <span className="text-indigo-300 font-semibold tabular-nums">
            {Number(active.fitness_at_creation).toFixed(4)}
          </span>
        </div>
      )}
    </div>
  )
}

function GeneBar({ param, value }) {
  const numVal = value ?? 0
  const display = param.pct ? `${(numVal * 100).toFixed(2)}%` : numVal
  const fillPct = ((numVal - param.min) / (param.max - param.min)) * 100
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-400">{param.label}</span>
        <span className="text-indigo-300 font-semibold tabular-nums">{display}</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(2, Math.min(100, fillPct))}%` }}
          transition={{ duration: 0.55, ease: 'easeOut' }}
          className="h-full bg-gradient-to-r from-indigo-500 to-purple-400 rounded-full"
        />
      </div>
    </div>
  )
}
