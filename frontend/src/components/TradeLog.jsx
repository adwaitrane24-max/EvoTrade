import { useRef, useEffect } from 'react'

export default function TradeLog({ trades }) {
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [trades])

  return (
    <div className="h-full flex flex-col p-3">
      <div className="flex items-center justify-between mb-2 px-1">
        <span className="font-mono text-[11px] font-semibold text-evo-muted uppercase tracking-wider">
          Trade Log
        </span>
        <span className="font-mono text-[10px] text-evo-muted">{trades.length} events</span>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-0.5 min-h-0">
        {trades.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <span className="font-mono text-xs text-evo-muted">Waiting for signals...</span>
          </div>
        ) : (
          trades.map((t) => (
            <div key={t.id} className="flex items-center gap-2 py-1 px-1 rounded hover:bg-evo-panel/50
              transition-colors duration-150 animate-fade-in">
              <span className="font-mono text-[9px] text-evo-muted w-16 shrink-0">{t.timestamp}</span>
              <span className="font-mono text-[9px] w-10 shrink-0" style={{ color: t.modelColor }}>
                {t.model.split(' ')[0]}
              </span>
              <span className={`font-mono text-[10px] font-semibold w-8 shrink-0
                ${t.action === 'BUY' ? 'text-evo-green' : 'text-evo-red'}`}>
                {t.action}
              </span>
              <span className="font-mono text-[10px] text-evo-text">${t.price.toFixed(2)}</span>
              <span className="font-mono text-[9px] text-evo-muted">×{t.size}</span>
              <span className={`font-mono text-[9px] ml-auto font-medium
                ${t.pnl >= 0 ? 'text-evo-green' : 'text-evo-red'}`}>
                {t.pnl >= 0 ? '+' : ''}{t.pnl.toFixed(2)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
