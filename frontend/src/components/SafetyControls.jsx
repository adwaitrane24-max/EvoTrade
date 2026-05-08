/**
 * SafetyControls.jsx — Pause and emergency stop buttons with confirmation guard.
 */

import { useState } from 'react'
import { api } from '../api/websocket'

export default function SafetyControls({ paused, emergencyStopped, running }) {
  const [confirmStop, setConfirmStop] = useState(false)
  const [loading, setLoading] = useState(null)

  async function handlePause() {
    setLoading('pause')
    try {
      await api.pause()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(null)
    }
  }

  async function handleResume() {
    setLoading('resume')
    try {
      await api.resume()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(null)
    }
  }

  async function handleEmergencyStop() {
    if (!confirmStop) {
      setConfirmStop(true)
      setTimeout(() => setConfirmStop(false), 4000)
      return
    }
    setLoading('stop')
    setConfirmStop(false)
    try {
      await api.emergencyStop()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(null)
    }
  }

  if (emergencyStopped) {
    return (
      <div className="flex items-center gap-2">
        <span className="badge bg-red-900/60 text-red-300 border border-red-700 animate-pulse">
          Emergency Stopped
        </span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      {running && (
        paused ? (
          <button
            className="btn-primary text-xs"
            onClick={handleResume}
            disabled={!!loading}
          >
            {loading === 'resume' ? 'Resuming…' : 'Resume'}
          </button>
        ) : (
          <button
            className="btn-ghost text-xs"
            onClick={handlePause}
            disabled={!!loading}
          >
            {loading === 'pause' ? 'Pausing…' : 'Pause'}
          </button>
        )
      )}

      <button
        className={`btn text-xs transition-all ${
          confirmStop
            ? 'bg-red-600 hover:bg-red-500 text-white ring-2 ring-red-400 ring-offset-2 ring-offset-gray-950'
            : 'bg-gray-800 hover:bg-red-900/50 text-red-400 border border-red-900'
        }`}
        onClick={handleEmergencyStop}
        disabled={!!loading}
      >
        {loading === 'stop'
          ? 'Stopping…'
          : confirmStop
          ? 'Confirm Stop!'
          : 'Emergency Stop'}
      </button>
    </div>
  )
}
