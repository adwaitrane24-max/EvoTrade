import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { MessageSquare, Dna, LayoutDashboard } from 'lucide-react'
import { MarketStatusBadge } from './MarketStatusBadge'
import { useWsStore } from '../../stores/wsStore'

const nav = [
  { to: '/', icon: MessageSquare, label: 'Chat' },
  { to: '/evolution', icon: Dna, label: 'Evolve' },
  { to: '/dashboard', icon: LayoutDashboard, label: 'Trade' },
]

export function Sidebar() {
  const connected = useWsStore((s) => s.connected)

  return (
    <aside className="fixed right-0 top-0 h-full w-[240px] bg-bg-surface border-l border-bg-border flex flex-col z-50">
      {/* Brand */}
      <div className="px-5 py-6 border-b border-bg-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-accent-primary/20 border border-accent-primary/40 flex items-center justify-center">
            <Dna size={14} className="text-accent-primary" />
          </div>
          <span className="font-semibold text-text-primary tracking-tight">EvoTrade</span>
        </div>
        <p className="text-xs text-text-muted mt-1.5">Paper Trading Only</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 ${
                isActive
                  ? 'bg-accent-primary/10 text-accent-primary border border-accent-primary/20'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 pb-5 space-y-3">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg">
          <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-signal-buy' : 'bg-signal-sell'}`} />
          <span className="text-xs text-text-muted font-mono">
            WS {connected ? 'connected' : 'offline'}
          </span>
        </div>
        <MarketStatusBadge />
      </div>
    </aside>
  )
}
