/**
 * EmergencyStop.jsx — two-step kill-switch button (PRD §23.1.8).
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useStore } from '../store'
import { api } from '../api/websocket'

export default function EmergencyStop() {
  const killSwitchActive = useStore((s) => s.killSwitchActive)
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)

  async function handleClick() {
    if (killSwitchActive) {
      setBusy(true)
      try { await api.killSwitch(false, 'manual_clear') }
      catch (e) { console.error(e) }
      finally  { setBusy(false) }
      return
    }
    if (!confirming) {
      setConfirming(true)
      setTimeout(() => setConfirming(false), 4000)
      return
    }
    setBusy(true)
    setConfirming(false)
    try { await api.killSwitch(true, 'user_initiated') }
    catch (e) { console.error(e) }
    finally  { setBusy(false) }
  }

  if (killSwitchActive) {
    return (
      <motion.button
        initial={{ scale: 0.9 }}
        animate={{ scale: [1, 1.04, 1] }}
        transition={{ repeat: Infinity, duration: 2.6 }}
        className="btn bg-red-600 text-white border border-red-400 ring-2 ring-red-500/40"
        onClick={handleClick} disabled={busy}
      >
        {busy ? 'Clearing…' : 'Resume Trading'}
      </motion.button>
    )
  }

  return (
    <button
      className={`btn text-xs transition-all ${
        confirming
          ? 'bg-red-600 hover:bg-red-500 text-white ring-2 ring-red-400 ring-offset-2 ring-offset-gray-950'
          : 'bg-gray-800 hover:bg-red-900/50 text-red-400 border border-red-900/60'
      }`}
      onClick={handleClick}
      disabled={busy}
    >
      {busy ? 'Triggering…' : confirming ? 'Confirm Stop!' : 'Emergency Stop'}
    </button>
  )
}
