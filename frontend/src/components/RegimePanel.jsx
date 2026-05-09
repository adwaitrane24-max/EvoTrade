/**
 * RegimePanel.jsx — current regime + posterior bars + transition matrix mini-grid.
 */

import { motion } from 'framer-motion'
import { useStore } from '../store'

const ORDER = ['bull', 'sideways', 'bear', 'crash']
const COLOR = {
  bull: '#34d399', sideways: '#fbbf24', bear: '#f87171', crash: '#fb7185',
}

export default function RegimePanel() {
  const { regime, regimeConfidence, regimePosterior, transitionMatrix, regimeSwitchCount } =
    useStore((s) => ({
      regime: s.regime,
      regimeConfidence: s.regimeConfidence,
      regimePosterior: s.regimePosterior,
      transitionMatrix: s.transitionMatrix,
      regimeSwitchCount: s.regimeSwitchCount,
    }))

  return (
    <div className="card flex flex-col gap-3 h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Market Regime
        </h2>
        <span className="text-xs text-gray-500">{regimeSwitchCount} shifts</span>
      </div>

      {/* Big confidence pill */}
      <div className="flex items-baseline gap-3 px-1">
        <motion.span
          key={regime}
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-3xl font-bold capitalize"
          style={{ color: COLOR[regime] || '#6b7280' }}
        >
          {regime || '—'}
        </motion.span>
        {regimeConfidence > 0 && (
          <span className="text-sm text-gray-500 tabular-nums">
            {Math.round(regimeConfidence * 100)}% confidence
          </span>
        )}
      </div>

      {/* Posterior probability distribution */}
      <div className="space-y-2">
        <div className="text-[10px] uppercase tracking-wider text-gray-500">Posterior P(regime | data)</div>
        {ORDER.map((label) => {
          const p = regimePosterior?.[label] ?? 0
          return (
            <div key={label}>
              <div className="flex justify-between text-xs mb-0.5">
                <span className="capitalize text-gray-400">{label}</span>
                <span className="tabular-nums" style={{ color: COLOR[label] }}>
                  {(p * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: COLOR[label] }}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.max(0, Math.min(100, p * 100))}%` }}
                  transition={{ duration: 0.4 }}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* Transition matrix mini-grid */}
      {transitionMatrix?.length > 0 && (
        <div className="border-t border-gray-800 pt-3">
          <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-2">Transition matrix</div>
          <div className="grid grid-cols-5 gap-1 text-[10px] tabular-nums">
            <div></div>
            {ORDER.map((l) => <div key={l} className="text-center text-gray-500 capitalize">{l[0].toUpperCase()}</div>)}
            {transitionMatrix.slice(0, 4).map((row, i) => (
              <RowOfMatrix key={i} from={ORDER[i]} row={row} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function RowOfMatrix({ from, row }) {
  return (
    <>
      <div className="text-gray-500 capitalize text-right pr-1">{from?.[0]?.toUpperCase()}</div>
      {row.slice(0, 4).map((p, j) => {
        const intensity = Math.min(1, Math.max(0, p))
        return (
          <div
            key={j}
            className="aspect-square rounded flex items-center justify-center text-[9px]"
            style={{
              backgroundColor: `rgba(99, 102, 241, ${intensity * 0.85 + 0.05})`,
              color: intensity > 0.5 ? '#fff' : '#9ca3af',
            }}
          >
            {(p * 100).toFixed(0)}
          </div>
        )
      })}
    </>
  )
}
