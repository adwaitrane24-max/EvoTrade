export default function OrderBook({ data, currentPrice }) {
  const { bids, asks } = data
  const maxBidTotal = Math.max(...bids.map(b => b.total), 1)
  const maxAskTotal = Math.max(...asks.map(a => a.total), 1)

  return (
    <div className="h-full w-full p-3 flex flex-col">
      <div className="flex items-center justify-between mb-2 px-1">
        <span className="font-mono text-[11px] font-semibold text-evo-muted uppercase tracking-wider">Order Book</span>
        <span className="font-mono text-[11px] text-evo-text">
          Spread: <span className="text-evo-yellow">${(asks[0]?.price - bids[0]?.price).toFixed(2)}</span>
        </span>
      </div>
      <div className="flex gap-2 flex-1 min-h-0 overflow-hidden">
        {/* Bids */}
        <div className="flex-1">
          <div className="grid grid-cols-3 gap-1 mb-1">
            {['PRICE', 'SIZE', 'TOTAL'].map(h => (
              <span key={h} className="font-mono text-[8px] text-evo-muted uppercase">{h}</span>
            ))}
          </div>
          {bids.map((b, i) => (
            <div key={i} className="relative grid grid-cols-3 gap-1 py-[2px]">
              <div className="absolute inset-0 bg-evo-green/5 rounded-sm"
                style={{ width: `${(b.total / maxBidTotal) * 100}%` }} />
              <span className="font-mono text-[10px] text-evo-green relative z-10">{b.price.toFixed(2)}</span>
              <span className="font-mono text-[10px] text-evo-text relative z-10">{b.size.toFixed(2)}</span>
              <span className="font-mono text-[10px] text-evo-muted relative z-10">{b.total.toFixed(0)}</span>
            </div>
          ))}
        </div>
        {/* Asks */}
        <div className="flex-1">
          <div className="grid grid-cols-3 gap-1 mb-1">
            {['PRICE', 'SIZE', 'TOTAL'].map(h => (
              <span key={h} className="font-mono text-[8px] text-evo-muted uppercase">{h}</span>
            ))}
          </div>
          {asks.map((a, i) => (
            <div key={i} className="relative grid grid-cols-3 gap-1 py-[2px]">
              <div className="absolute inset-0 bg-evo-red/5 rounded-sm right-0 left-auto"
                style={{ width: `${(a.total / maxAskTotal) * 100}%` }} />
              <span className="font-mono text-[10px] text-evo-red relative z-10">{a.price.toFixed(2)}</span>
              <span className="font-mono text-[10px] text-evo-text relative z-10">{a.size.toFixed(2)}</span>
              <span className="font-mono text-[10px] text-evo-muted relative z-10">{a.total.toFixed(0)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
