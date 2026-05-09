/**
 * RiskPanel.jsx — daily loss used, position size cap, recent risk events.
 */

import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../store'

export default function RiskPanel() {
  const { riskLimits, riskEvents, killSwitchActive, pnlPct, positions, initialCapital, portfolioValue } =
    useStore((s) => ({
      riskLimits: s.riskLimits,
      riskEvents: s.riskEvents,
      killSwitchActive: s.killSwitchActive,
      pnlPct: s.pnlPct,
      positions: s.positions,
      initialCapital: s.initialCapital,
      portfolioValue: s.portfolioValue,
    }))

  const dailyLossUsedPct = pnlPct < 0 ? Math.abs(pnlPct) : 0
  const dailyLossLimit = riskLimits.max_daily_loss_pct || 5
  const dailyLossUsage = (dailyLossUsedPct / dailyLossLimit) * 100

  const totalNotional = Object.values(positions || {}).reduce(
    (acc, p) => acc + Math.abs((p?.qty ?? 0) * (p?.avg_price ?? 0)),
    0,
  )
  const exposurePct = portfolioValue > 0 ? (totalNotional / portfolioValue) * 100 : 0
  const positionLimit = (riskLimits.max_position_size_pct ?? 0.30) * 100
  const positionUsage = exposurePct / positionLimit * 100

  return (
    <div className="card flex flex-col gap-3 h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Risk</h2>
        {killSwitchActive && (
          <span className="badge bg-red-900/60 text-red-300 border border-red-700 animate-pulse">kill switch</span>
        )}
      </div>

      <Bar label="Daily loss used" used={dailyLossUsedPct} cap={dailyLossLimit} suffix="%" colorOk="#34d399" colorWarn="#f87171" />
      <Bar label="Position size" used={exposurePct} cap={positionLimit} suffix="%" colorOk="#a78bfa" colorWarn="#fb923c" />

      <div className="border-t border-gray-800 pt-2">
        <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-1.5">Recent risk events</div>
        <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
          <AnimatePresence>
            {riskEvents.length === 0 ? (
              <div className="text-xs text-gray-600">No risk events.</div>
            ) : (
              riskEvents.slice(0, 8).map((e, i) => (
                <motion.div
                  key={`${e.ts}-${i}`}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-center gap-2 text-[11px] bg-gray-900/40 border border-gray-800 rounded px-2 py-1"
                >
                  <span className="text-gray-500 w-16 truncate">{new Date(e.ts).toLocaleTimeString()}</span>
                  <span className="text-amber-400 font-medium">{e.kind || e.event_type || 'risk'}</span>
                  <span className="text-gray-400 truncate">{e.reason}</span>
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

function Bar({ label, used, cap, suffix = '%', colorOk = '#34d399', colorWarn = '#f87171' }) {
  const pct = Math.max(0, Math.min(100, (used / cap) * 100))
  const color = pct > 80 ? colorWarn : colorOk
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="tabular-nums text-gray-300">
          <span style={{ color }}>{Number(used).toFixed(1)}{suffix}</span>
          <span className="text-gray-600"> / {Number(cap).toFixed(0)}{suffix}</span>
        </span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4 }}
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
    </div>
  )
}
