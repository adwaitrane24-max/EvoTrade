/**
 * LiveTradeLog.jsx — Scrollable table of the last 20 real-time trade events.
 */

const ACTION_STYLE = {
  BUY:  'text-emerald-400 bg-emerald-900/30 border border-emerald-800',
  SELL: 'text-red-400 bg-red-900/30 border border-red-800',
  HOLD: 'text-gray-500 bg-gray-800/30 border border-gray-700',
}

function TradeRow({ trade, index }) {
  const style = ACTION_STYLE[trade.action] || ACTION_STYLE.HOLD
  const time = trade.timestamp
    ? new Date(trade.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '—'

  return (
    <tr className={`border-b border-gray-800/50 text-xs tabular-nums ${index % 2 === 0 ? 'bg-gray-900/20' : ''}`}>
      <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{time}</td>
      <td className="px-3 py-2">
        <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${style}`}>
          {trade.action}
        </span>
      </td>
      <td className="px-3 py-2 text-gray-300 text-right">
        ${Number(trade.price ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </td>
      <td className="px-3 py-2 text-gray-400 text-right">
        {Number(trade.quantity ?? 0).toFixed(6)}
      </td>
      <td className="px-3 py-2 text-gray-500 max-w-[160px] truncate" title={trade.reason}>
        {trade.reason || '—'}
      </td>
    </tr>
  )
}

export default function LiveTradeLog({ trades }) {
  const recent = [...(trades || [])].reverse().slice(0, 20)

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Live Trade Log</h2>
        <span className="text-xs text-gray-600">{trades?.length ?? 0} total</span>
      </div>

      <div className="overflow-auto max-h-48">
        {recent.length === 0 ? (
          <p className="text-gray-600 text-sm text-center py-6">No trades yet…</p>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="text-gray-500 text-xs border-b border-gray-800">
                <th className="px-3 py-1.5 font-medium">Time</th>
                <th className="px-3 py-1.5 font-medium">Action</th>
                <th className="px-3 py-1.5 font-medium text-right">Price</th>
                <th className="px-3 py-1.5 font-medium text-right">Qty</th>
                <th className="px-3 py-1.5 font-medium">Reason</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((t, i) => (
                <TradeRow key={`${t.timestamp}-${i}`} trade={t} index={i} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
