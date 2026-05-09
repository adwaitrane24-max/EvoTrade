export default function ActivePositions({ positions, currentPrice }) {
  return (
    <div className="p-3">
      <div className="flex items-center justify-between mb-3 px-1">
        <span className="font-mono text-[11px] font-semibold text-evo-muted uppercase tracking-wider">
          Active Positions
        </span>
        <span className="font-mono text-[10px] text-evo-muted">{positions.length} open</span>
      </div>
      <div className="space-y-2">
        {positions.map((pos, i) => {
          const priceDiff = currentPrice - pos.entry
          const pnlPct = ((priceDiff / pos.entry) * 100 * (pos.side === 'LONG' ? 1 : -1))
          const isProfit = pnlPct >= 0
          return (
            <div key={i} className="bg-evo-bg rounded-md p-3 border border-evo-border
              hover:border-evo-muted/30 transition-colors duration-200">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-evo-text">{pos.ticker}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold
                    ${pos.side === 'LONG'
                      ? 'bg-evo-green/10 text-evo-green border border-evo-green/20'
                      : 'bg-evo-red/10 text-evo-red border border-evo-red/20'}`}>
                    {pos.side}
                  </span>
                </div>
                <span className={`font-mono text-xs font-bold ${isProfit ? 'text-evo-green' : 'text-evo-red'}`}>
                  {isProfit ? '+' : ''}{pnlPct.toFixed(2)}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-[10px] font-mono text-evo-muted">
                  <span>Entry: <span className="text-evo-text">${pos.entry.toFixed(2)}</span></span>
                  <span>Now: <span className="text-evo-text">${currentPrice.toFixed(2)}</span></span>
                </div>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded"
                  style={{ color: pos.modelColor, backgroundColor: pos.modelColor + '12', border: `1px solid ${pos.modelColor}22` }}>
                  {pos.model.split(' ')[0]}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
