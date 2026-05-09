import React, { useState } from 'react'
import api from '../../lib/api'

export function EmergencyStop({ onStopped }: { onStopped?: () => void }) {
  const [confirming, setConfirming] = useState(false)
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const handleClick = async () => {
    if (!confirming) {
      setConfirming(true)
      return
    }
    setLoading(true)
    try {
      await api.post('/api/trading/emergency-stop')
      setDone(true)
      onStopped?.()
    } catch (e) {
      console.error('Emergency stop failed', e)
    } finally {
      setLoading(false)
      setConfirming(false)
    }
  }

  return (
    <div className="bg-signal-sell/5 border border-signal-sell/20 rounded-xl p-4 flex items-center justify-between">
      <div>
        <p className="text-sm font-semibold text-signal-sell">Emergency Stop</p>
        <p className="text-xs text-text-muted mt-0.5">
          {done
            ? 'All positions closed. Trading halted.'
            : confirming
            ? 'Click again to confirm — all open positions will close at last price.'
            : 'Instantly close all open positions and halt trading.'}
        </p>
      </div>
      {!done && (
        <button
          onClick={handleClick}
          disabled={loading}
          className={`px-4 py-2 rounded-lg border font-medium text-sm transition-all duration-150 disabled:opacity-40 ${
            confirming
              ? 'bg-signal-sell text-white border-signal-sell hover:bg-signal-sell/90'
              : 'bg-signal-sell/10 text-signal-sell border-signal-sell/30 hover:bg-signal-sell/20'
          }`}
        >
          {loading ? 'Stopping...' : confirming ? '⚠ Confirm Stop' : '🛑 Emergency Stop'}
        </button>
      )}
    </div>
  )
}
