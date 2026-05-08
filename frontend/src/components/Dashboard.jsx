/**
 * Dashboard.jsx — Main layout: top bar, evolution graph, gene panel, trade log.
 */

import { useEffect, useReducer, useRef, useState } from 'react'
import { socket, api } from '../api/websocket'
import EvolutionGraph from './EvolutionGraph'
import GeneDisplay from './GeneDisplay'
import LiveTradeLog from './LiveTradeLog'
import RegimeIndicator from './RegimeIndicator'
import SafetyControls from './SafetyControls'

const initialState = {
  connected: false,
  running: false,
  paused: false,
  emergencyStopped: false,
  currentRegime: null,
  currentGene: null,
  currentFitness: undefined,
  fitnessHistory: [],
  generation: 0,
  trades: [],
  statusText: 'Idle',
  portfolioValue: null,
}

function reducer(state, action) {
  switch (action.type) {
    case 'connection':
      return { ...state, connected: action.status === 'connected' }

    case 'started':
      return { ...state, running: true, paused: false, statusText: 'Evolving…' }

    case 'paused':
      return { ...state, paused: true, statusText: 'Paused' }

    case 'resumed':
      return { ...state, paused: false, statusText: 'Running' }

    case 'emergency_stopped':
      return { ...state, emergencyStopped: true, running: false, statusText: 'Emergency Stopped' }

    case 'evolution_started':
      return { ...state, statusText: 'Evolution in progress…', fitnessHistory: [], generation: 0 }

    case 'generation_complete':
      return {
        ...state,
        fitnessHistory: action.fitness_history ?? [...state.fitnessHistory, action.best_fitness],
        generation: action.generation,
        currentGene: action.best_gene ?? state.currentGene,
        currentFitness: action.best_fitness,
        statusText: `Gen ${action.generation} — fitness ${action.best_fitness?.toFixed(4) ?? '…'}`,
      }

    case 'evolution_complete':
    case 're_evolution_complete':
      return {
        ...state,
        currentGene: action.gene ?? action.new_gene ?? state.currentGene,
        currentFitness: action.fitness ?? state.currentFitness,
        statusText: 'Alpha Gene ready — trading live',
      }

    case 'regime_change':
    case 'regime_detected':
      return { ...state, currentRegime: action.current ?? action.regime }

    case 'trade':
      return {
        ...state,
        trades: [...state.trades, action.data].slice(-200),
      }

    case 'converged':
      return { ...state, statusText: `Converged at gen ${action.generation}` }

    case 're_evolution_started':
      return { ...state, statusText: 'Re-evolution triggered…' }

    case 'set_status':
      return { ...state, ...action.payload }

    default:
      return state
  }
}

export default function Dashboard() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const [starting, setStarting] = useState(false)
  const [showOnboard, setShowOnboard] = useState(false)
  const [onboardForm, setOnboardForm] = useState({ risk_profile: 'medium', symbol: 'BTC/USDT', initial_capital: 10000 })
  const statusPollRef = useRef(null)

  // ── WebSocket subscriptions ──────────────────────────────────────────────
  useEffect(() => {
    socket.connect()
    const unsub = socket.on('*', (event) => dispatch(event))
    return () => {
      unsub()
      socket.disconnect()
    }
  }, [])

  // ── Poll /status on mount to restore state after page reload ─────────────
  useEffect(() => {
    api.status().then((s) => {
      dispatch({
        type: 'set_status',
        payload: {
          running: s.running,
          paused: s.paused,
          emergencyStopped: s.emergency_stopped,
          currentRegime: s.current_regime,
          currentGene: s.current_gene,
          fitnessHistory: s.fitness_history ?? [],
          portfolioValue: s.portfolio_value,
          statusText: s.running ? 'Running' : 'Idle',
        },
      })
    }).catch(() => {})
  }, [])

  async function handleStart() {
    setStarting(true)
    try {
      await api.start()
    } catch (e) {
      console.error(e)
    } finally {
      setStarting(false)
    }
  }

  async function handleOnboard() {
    try {
      await api.onboard(onboardForm)
      setShowOnboard(false)
    } catch (e) {
      console.error(e)
    }
  }

  const pnl = state.portfolioValue != null
    ? ((state.portfolioValue - onboardForm.initial_capital) / onboardForm.initial_capital * 100).toFixed(2)
    : null

  return (
    <div className="min-h-screen flex flex-col bg-gray-950">
      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <header className="border-b border-gray-800 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-2xl select-none">🧬</span>
            <span className="text-lg font-bold tracking-tight text-white">EvoTrade</span>
            <span className="hidden sm:block text-xs text-gray-600 font-mono">v1.0</span>
          </div>

          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${state.connected ? 'bg-emerald-500' : 'bg-gray-600'}`} />
            <span className="text-xs text-gray-500 hidden md:block">
              {state.connected ? 'Live' : 'Connecting…'}
            </span>
          </div>

          {state.currentRegime && <RegimeIndicator regime={state.currentRegime} />}
        </div>

        <div className="flex items-center gap-3">
          {pnl !== null && (
            <span className={`text-sm font-semibold tabular-nums ${Number(pnl) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {Number(pnl) >= 0 ? '+' : ''}{pnl}%
            </span>
          )}

          <span className="text-xs text-gray-600 hidden lg:block font-mono">{state.statusText}</span>

          {!state.running && !state.emergencyStopped && (
            <>
              <button className="btn-ghost text-xs" onClick={() => setShowOnboard((v) => !v)}>
                Configure
              </button>
              <button className="btn-primary text-xs" onClick={handleStart} disabled={starting}>
                {starting ? 'Starting…' : 'Start'}
              </button>
            </>
          )}

          <SafetyControls
            paused={state.paused}
            emergencyStopped={state.emergencyStopped}
            running={state.running}
          />
        </div>
      </header>

      {/* ── Onboard form ─────────────────────────────────────────────────── */}
      {showOnboard && (
        <div className="border-b border-gray-800 bg-gray-900/50 px-6 py-4">
          <div className="max-w-2xl flex flex-wrap gap-4 items-end">
            <Field label="Symbol">
              <select
                className="input"
                value={onboardForm.symbol}
                onChange={(e) => setOnboardForm((f) => ({ ...f, symbol: e.target.value }))}
              >
                {['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT'].map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </Field>
            <Field label="Risk Profile">
              <select
                className="input"
                value={onboardForm.risk_profile}
                onChange={(e) => setOnboardForm((f) => ({ ...f, risk_profile: e.target.value }))}
              >
                {['low', 'medium', 'high'].map((r) => <option key={r}>{r}</option>)}
              </select>
            </Field>
            <Field label="Capital (USDT)">
              <input
                type="number"
                className="input w-32"
                value={onboardForm.initial_capital}
                onChange={(e) => setOnboardForm((f) => ({ ...f, initial_capital: Number(e.target.value) }))}
              />
            </Field>
            <button className="btn-primary text-xs" onClick={handleOnboard}>Save Config</button>
          </div>
        </div>
      )}

      {/* ── Main grid ────────────────────────────────────────────────────── */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 p-4 min-h-0">
        {/* Left — Evolution graph (2/3 width) */}
        <div className="lg:col-span-2 min-h-64 lg:min-h-0">
          <EvolutionGraph
            fitnessHistory={state.fitnessHistory}
            currentGene={state.currentGene}
            generation={state.generation}
          />
        </div>

        {/* Right — Gene display (1/3 width) */}
        <div className="min-h-48 lg:min-h-0">
          <GeneDisplay gene={state.currentGene} fitness={state.currentFitness} />
        </div>
      </main>

      {/* ── Bottom — Trade log ───────────────────────────────────────────── */}
      <div className="px-4 pb-4 shrink-0">
        <LiveTradeLog trades={state.trades} />
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-gray-500">{label}</span>
      {children}
    </label>
  )
}
