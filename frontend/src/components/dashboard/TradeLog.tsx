import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Trade } from '../../types'

function fmtTime(ts: string) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function fmtPnl(pnl: number | null): React.ReactNode {
  if (pnl === null) return <span className="text-text-muted font-mono text-xs">—</span>
  const sign = pnl >= 0 ? '+' : ''
  const cls = pnl >= 0 ? 'text-signal-buy' : 'text-signal-sell'
  return <span className={`${cls} font-mono text-xs`}>{sign}₹{Math.abs(pnl).toFixed(2)}</span>
}

export function TradeLog({ trades }: { trades: Trade[] }) {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text-primary">Trade Log</h3>
        <span className="text-xs text-text-muted font-mono">{trades.length} trades</span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-1">
        <AnimatePresence initial={false}>
          {trades.slice(0, 50).map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="flex items-center gap-2 py-1.5 border-b border-bg-border/50 text-xs"
            >
              <span className="text-text-muted font-mono w-16 shrink-0">{fmtTime(t.timestamp)}</span>
              <span className={t.side === 'BUY' ? 'badge-buy' : 'badge-sell'}>{t.side}</span>
              <span className="font-mono text-text-secondary">{t.qty.toFixed(5)}</span>
              <span className="text-text-muted">@</span>
              <span className="font-mono text-text-primary">${t.price.toLocaleString()}</span>
              <span className="ml-auto">{fmtPnl(t.pnl)}</span>
            </motion.div>
          ))}
        </AnimatePresence>
        {trades.length === 0 && (
          <div className="flex items-center justify-center h-24 text-text-muted text-xs">
            Waiting for first trade...
          </div>
        )}
      </div>
    </div>
  )
}
