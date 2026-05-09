import React from 'react'

function useMarketStatus() {
  // Crypto markets are always open 24/7
  // Architecture supports equity market hours (9:15–15:30 IST) for future extension
  const now = new Date()
  const istOffset = 5.5 * 60 * 60 * 1000
  const ist = new Date(now.getTime() + istOffset)
  const h = ist.getUTCHours()
  const m = ist.getUTCMinutes()
  const mins = h * 60 + m
  const equityOpen = mins >= 9 * 60 + 15 && mins <= 15 * 60 + 30

  // For MVP we use Crypto (always open)
  return { isOpen: true, label: 'Crypto Markets — OPEN 24/7', equityOpen }
}

export function MarketStatusBadge() {
  const { isOpen, label } = useMarketStatus()
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg-elevated border border-bg-border">
      <span className={`w-2 h-2 rounded-full ${isOpen ? 'bg-signal-buy animate-pulse' : 'bg-signal-sell'}`} />
      <span className="text-xs text-text-secondary font-mono">{label}</span>
    </div>
  )
}
