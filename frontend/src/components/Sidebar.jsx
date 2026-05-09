const NAV_ITEMS = [
  { id: 'chat', label: 'Chat',
    icon: <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /> },
  { id: 'dashboard', label: 'Dashboard',
    icon: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></> },
  { id: 'portfolio', label: 'Portfolio',
    icon: <><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></> },
  { id: 'history', label: 'History',
    icon: <><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></> },
  { id: 'settings', label: 'Settings',
    icon: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" /></> },
]

export default function Sidebar({ active, onNavigate, phase }) {
  return (
    <aside className="w-[60px] h-full bg-evo-sidebar border-l border-evo-border flex flex-col items-center py-4 shrink-0">
      {/* Logo */}
      <div className="mb-8 flex flex-col items-center gap-0.5 select-none">
        {['E','V','O'].map((c,i) => (
          <span key={i} className="text-evo-green font-mono font-bold text-sm leading-none">{c}</span>
        ))}
        <div className="w-3 h-px bg-evo-green/40 my-1" />
        {['T','R','D'].map((c,i) => (
          <span key={i} className="text-evo-muted font-mono text-[10px] leading-none">{c}</span>
        ))}
      </div>

      {/* Nav Icons */}
      <nav className="flex flex-col gap-1 flex-1">
        {NAV_ITEMS.map(item => {
          const isActive = active === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              title={item.label}
              className={`
                relative w-10 h-10 flex items-center justify-center rounded-md
                transition-all duration-200 group
                ${isActive
                  ? 'bg-evo-green/10 text-evo-green'
                  : 'text-evo-muted hover:text-evo-text hover:bg-white/5'}
              `}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 bg-evo-green rounded-r shadow-[0_0_8px_#00FF88]" />
              )}
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                {item.icon}
              </svg>
            </button>
          )
        })}
      </nav>

      {/* Phase indicator */}
      <div className="mt-auto flex flex-col items-center gap-1.5 mb-2">
        {[1,2,3].map(p => (
          <div key={p} className={`w-1.5 h-1.5 rounded-full transition-colors duration-300
            ${p === phase ? 'bg-evo-green shadow-[0_0_6px_#00FF88]' :
              p < phase ? 'bg-evo-green/40' : 'bg-evo-border'}`}
          />
        ))}
      </div>
    </aside>
  )
}
