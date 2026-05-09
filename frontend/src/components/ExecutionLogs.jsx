/**
 * ExecutionLogs.jsx — fills + signals + system events in a tabbed view.
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../store'

const ACTION = {
  BUY:  'text-emerald-400 bg-emerald-900/30 border border-emerald-800',
  SELL: 'text-red-400 bg-red-900/30 border border-red-800',
  HOLD: 'text-gray-500 bg-gray-800/30 border border-gray-700',
}

export default function ExecutionLogs() {
  const fills = useStore((s) => s.fills)
  const signals = useStore((s) => s.signals)
  const systemLogs = useStore((s) => s.systemLogs)
  const [tab, setTab] = useState('fills')

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Execution Logs</h2>
        <div className="flex gap-1 text-xs">
          <Tab active={tab === 'fills'} onClick={() => setTab('fills')}>Fills · {fills.length}</Tab>
          <Tab active={tab === 'signals'} onClick={() => setTab('signals')}>Signals · {signals.length}</Tab>
          <Tab active={tab === 'system'} onClick={() => setTab('system')}>System · {systemLogs.length}</Tab>
        </div>
      </div>

      <div className="overflow-auto max-h-56">
        {tab === 'fills'   && <FillsTable fills={fills} />}
        {tab === 'signals' && <SignalsTable signals={signals} />}
        {tab === 'system'  && <SystemTable logs={systemLogs} />}
      </div>
    </div>
  )
}

function Tab({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-2.5 py-1 rounded transition-colors ${
        active
          ? 'bg-indigo-600 text-white'
          : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
      }`}
    >
      {children}
    </button>
  )
}

function FillsTable({ fills }) {
  if (fills.length === 0) return <Empty msg="No fills yet." />
  return (
    <table className="w-full text-left">
      <thead>
        <tr className="text-gray-500 text-[10px] uppercase tracking-wider border-b border-gray-800">
          <th className="px-2 py-1.5 font-medium">Time</th>
          <th className="px-2 py-1.5 font-medium">Action</th>
          <th className="px-2 py-1.5 font-medium text-right">Price</th>
          <th className="px-2 py-1.5 font-medium text-right">Qty</th>
          <th className="px-2 py-1.5 font-medium text-right">Equity</th>
          <th className="px-2 py-1.5 font-medium">Regime</th>
        </tr>
      </thead>
      <tbody>
        <AnimatePresence>
          {fills.map((f, i) => (
            <motion.tr
              key={`${f.ts}-${i}`}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className={`border-b border-gray-800/40 text-xs tabular-nums ${i % 2 === 0 ? 'bg-gray-900/20' : ''}`}
            >
              <td className="px-2 py-1.5 text-gray-500">{new Date(f.ts).toLocaleTimeString()}</td>
              <td className="px-2 py-1.5">
                <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${ACTION[f.side] || ACTION.HOLD}`}>{f.side}</span>
              </td>
              <td className="px-2 py-1.5 text-gray-300 text-right">${Number(f.fill_price ?? 0).toFixed(2)}</td>
              <td className="px-2 py-1.5 text-gray-400 text-right">{Number(f.qty ?? 0).toFixed(6)}</td>
              <td className="px-2 py-1.5 text-emerald-400 text-right">${Number(f.equity_usdt ?? 0).toFixed(2)}</td>
              <td className="px-2 py-1.5 text-gray-500 capitalize">{f.regime || '—'}</td>
            </motion.tr>
          ))}
        </AnimatePresence>
      </tbody>
    </table>
  )
}

function SignalsTable({ signals }) {
  if (signals.length === 0) return <Empty msg="No signals yet." />
  return (
    <table className="w-full text-left">
      <thead>
        <tr className="text-gray-500 text-[10px] uppercase tracking-wider border-b border-gray-800">
          <th className="px-2 py-1.5">Time</th>
          <th className="px-2 py-1.5">Action</th>
          <th className="px-2 py-1.5 text-right">RSI</th>
          <th className="px-2 py-1.5 text-right">MA-S/L</th>
          <th className="px-2 py-1.5 text-right">Price</th>
        </tr>
      </thead>
      <tbody>
        {signals.slice(0, 20).map((s, i) => (
          <tr key={i} className={`border-b border-gray-800/40 text-xs tabular-nums ${i % 2 === 0 ? 'bg-gray-900/20' : ''}`}>
            <td className="px-2 py-1.5 text-gray-500">{new Date(s.ts).toLocaleTimeString()}</td>
            <td className="px-2 py-1.5">
              <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${ACTION[s.action] || ACTION.HOLD}`}>{s.action}</span>
            </td>
            <td className="px-2 py-1.5 text-gray-400 text-right">{s.indicators?.rsi ?? '—'}</td>
            <td className="px-2 py-1.5 text-gray-400 text-right">{s.indicators?.ma_short ?? '—'} / {s.indicators?.ma_long ?? '—'}</td>
            <td className="px-2 py-1.5 text-gray-300 text-right">${s.indicators?.price ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function SystemTable({ logs }) {
  if (logs.length === 0) return <Empty msg="No system events." />
  return (
    <ul className="space-y-1 text-[11px]">
      {logs.slice(0, 30).map((l, i) => (
        <li key={i} className="flex gap-2 text-gray-400 border-b border-gray-800/40 py-1">
          <span className="text-gray-600 tabular-nums w-20">{new Date(l.ts).toLocaleTimeString()}</span>
          <span className={`uppercase tracking-wider text-[9px] w-16 ${
            l.kind === 'error' ? 'text-red-400' : l.kind === 'order_rejected' ? 'text-amber-400' : 'text-gray-500'
          }`}>{l.kind || 'event'}</span>
          <span className="text-gray-300 truncate">
            {l.reason || l.error || l.status || JSON.stringify(l.payload || l).slice(0, 80)}
          </span>
        </li>
      ))}
    </ul>
  )
}

function Empty({ msg }) {
  return <div className="text-center py-6 text-gray-600 text-sm">{msg}</div>
}
