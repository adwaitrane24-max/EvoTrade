/**
 * TopBar.jsx — header with brand, system status, regime pill, and global controls.
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useStore } from '../store'
import { api } from '../api/websocket'
import RegimeIndicator from './RegimeIndicator'
import EmergencyStop from './EmergencyStop'

export default function TopBar() {
  const { connected, systemStatus, regime, regimeConfidence, pnlPct, evolutionRunning } =
    useStore((s) => ({
      connected: s.connected,
      systemStatus: s.systemStatus,
      regime: s.regime,
      regimeConfidence: s.regimeConfidence,
      pnlPct: s.pnlPct,
      evolutionRunning: s.evolutionRunning,
    }))

  const [starting, setStarting] = useState(false)
  const [evolving, setEvolving] = useState(false)

  async function handleStart() {
    setStarting(true)
    try { await api.controlStart({ symbol: 'BTC/USDT', risk_profile: 'medium', initial_capital: 10000 }) }
    catch (e) { console.error(e) }
    finally  { setStarting(false) }
  }

  async function handleEvolution() {
    setEvolving(true)
    try { await api.evolutionRun({ symbol: 'BTC-USD', risk_profile: 'medium', n_generations: 5, population_size: 10 }) }
    catch (e) { console.error(e) }
    finally  { setEvolving(false) }
  }

  return (
    <header className="border-b border-gray-800 px-6 py-3 flex items-center justify-between shrink-0 bg-gray-950/95 backdrop-blur sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <motion.div
          className="flex items-center gap-2"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <span className="text-2xl">🧬</span>
          <span className="text-lg font-bold tracking-tight text-white">EvoTrade</span>
          <span className="hidden sm:inline text-[10px] text-gray-600 font-mono uppercase tracking-widest border border-gray-800 rounded px-1.5 py-0.5">PRD v2</span>
        </motion.div>

        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-gray-600'}`} />
          <span className="text-xs text-gray-500 hidden md:block">
            {connected ? `${systemStatus}` : 'connecting…'}
          </span>
        </div>

        <RegimeIndicator regime={regime} confidence={regimeConfidence} />
      </div>

      <div className="flex items-center gap-3">
        {pnlPct !== 0 && (
          <span className={`text-sm font-semibold tabular-nums ${pnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {pnlPct >= 0 ? '+' : ''}{Number(pnlPct).toFixed(2)}%
          </span>
        )}

        <button className="btn-ghost text-xs" onClick={handleEvolution} disabled={evolving || evolutionRunning}>
          {evolving || evolutionRunning ? 'Evolving…' : 'Run Evolution'}
        </button>

        {systemStatus !== 'running' && (
          <button className="btn-primary text-xs" onClick={handleStart} disabled={starting}>
            {starting ? 'Starting…' : 'Start Trading'}
          </button>
        )}

        <EmergencyStop />
      </div>
    </header>
  )
}
