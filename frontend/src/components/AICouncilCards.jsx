/**
 * AICouncilCards.jsx — 3 role cards + consensus card per PRD §16.
 */

import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../store'

const RISK_COLOR = {
  low:    'text-emerald-400 bg-emerald-900/30 border-emerald-800',
  medium: 'text-yellow-400 bg-yellow-900/30 border-yellow-800',
  high:   'text-red-400 bg-red-900/30 border-red-800',
}

export default function AICouncilCards() {
  const cards = useStore((s) => s.aiCards)
  const latest = cards[0]
  const r = latest?.reasoning

  return (
    <div className="card flex flex-col gap-3 h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          AI Council
        </h2>
        <span className="text-[10px] text-gray-500 font-mono">
          {r?._meta?.source === 'ollama' ? 'DeepSeek-R1' : r?._meta?.source || 'fallback'}
        </span>
      </div>

      {!r ? (
        <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">
          Run evolution to receive AI council reasoning…
        </div>
      ) : (
        <AnimatePresence mode="wait">
          <motion.div
            key={latest.ts}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex flex-col gap-3 flex-1 overflow-auto pr-1"
          >
            <RoleCard
              title="The Critic"
              subtitle="Backtesting"
              tag={r.backtesting_critic?.overfitting_risk}
              tagLabel={`overfitting · ${r.backtesting_critic?.overfitting_risk || '—'}`}
              summary={r.backtesting_critic?.summary}
              notes={r.backtesting_critic?.notes}
            />
            <RoleCard
              title="The Guardian"
              subtitle="Risk"
              tag={r.risk_guardian?.risk_level}
              tagLabel={`risk · ${r.risk_guardian?.risk_level || '—'}`}
              summary={r.risk_guardian?.summary}
              extra={r.risk_guardian?.recommended_limits && (
                <div className="text-[11px] text-gray-500 mt-1.5 flex gap-3">
                  <span>max pos: {((r.risk_guardian.recommended_limits.max_position_size_pct ?? 0) * 100).toFixed(0)}%</span>
                  <span>max daily loss: {(r.risk_guardian.recommended_limits.max_daily_loss_pct ?? 0).toFixed(1)}%</span>
                </div>
              )}
            />
            <RoleCard
              title="The Forecaster"
              subtitle="Sentiment"
              tag="medium"
              tagLabel={`regime · ${r.sentiment_forecaster?.regime_sensitivity || '—'}`}
              summary={r.sentiment_forecaster?.summary}
            />

            {/* Consensus */}
            <div className={`rounded-md border p-3 ${
              r.consensus?.approve_for_shadow
                ? 'border-emerald-800 bg-emerald-900/20'
                : 'border-red-800 bg-red-900/20'
            }`}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-300">
                  Consensus
                </span>
                <span className={`badge text-[10px] ${
                  r.consensus?.approve_for_shadow
                    ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700'
                    : 'bg-red-900/60 text-red-300 border border-red-700'
                }`}>
                  {r.consensus?.approve_for_shadow ? 'approve · shadow' : 'reject'}
                </span>
              </div>
              <ul className="text-[11px] text-gray-300 list-disc list-inside space-y-1">
                {(r.consensus?.key_reasoning || []).slice(0, 3).map((x, i) => <li key={i}>{x}</li>)}
              </ul>
              {r.consensus?.watchouts?.length > 0 && (
                <div className="mt-2 text-[10px] text-amber-400">
                  ⚠ {r.consensus.watchouts.slice(0, 2).join(' · ')}
                </div>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  )
}

function RoleCard({ title, subtitle, tag, tagLabel, summary, notes, extra }) {
  return (
    <div className="bg-gray-900/40 border border-gray-800 rounded-md p-3">
      <div className="flex items-center justify-between mb-1">
        <div>
          <div className="text-xs font-semibold text-gray-200">{title}</div>
          <div className="text-[10px] text-gray-600 uppercase tracking-wider">{subtitle}</div>
        </div>
        <span className={`badge text-[10px] border ${RISK_COLOR[tag] || 'bg-gray-800 text-gray-400 border-gray-700'}`}>
          {tagLabel}
        </span>
      </div>
      {summary && <div className="text-[12px] text-gray-300 leading-relaxed">{summary}</div>}
      {notes?.length > 0 && (
        <ul className="mt-1.5 text-[11px] text-gray-500 list-disc list-inside space-y-0.5">
          {notes.slice(0, 3).map((n, i) => <li key={i}>{n}</li>)}
        </ul>
      )}
      {extra}
    </div>
  )
}
