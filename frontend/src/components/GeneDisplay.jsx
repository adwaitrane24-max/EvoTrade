/**
 * GeneDisplay.jsx — Panel showing current Alpha Gene parameter values.
 */

const PARAM_META = [
  { key: 'rsi_period',        label: 'RSI Period',      unit: 'bars',  min: 5,    max: 30  },
  { key: 'ma_short',          label: 'MA Short',        unit: 'bars',  min: 5,    max: 50  },
  { key: 'ma_long',           label: 'MA Long',         unit: 'bars',  min: 20,   max: 200 },
  { key: 'stop_loss_pct',     label: 'Stop Loss',       unit: '%',     min: 0.01, max: 0.10, pct: true },
  { key: 'take_profit_pct',   label: 'Take Profit',     unit: '%',     min: 0.01, max: 0.20, pct: true },
  { key: 'position_size_pct', label: 'Position Size',   unit: '%',     min: 0.01, max: 0.50, pct: true },
]

function GeneBar({ meta, value }) {
  const numVal = value ?? 0
  const displayVal = meta.pct ? `${(numVal * 100).toFixed(1)}%` : numVal
  const fillPct = ((numVal - meta.min) / (meta.max - meta.min)) * 100

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-400">{meta.label}</span>
        <span className="text-indigo-300 font-semibold tabular-nums">{displayVal}</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-indigo-600 to-purple-500 rounded-full transition-all duration-700"
          style={{ width: `${Math.max(2, Math.min(100, fillPct))}%` }}
        />
      </div>
    </div>
  )
}

export default function GeneDisplay({ gene, fitness }) {
  if (!gene) {
    return (
      <div className="card h-full flex flex-col items-center justify-center text-gray-600 gap-2">
        <span className="text-3xl">🧬</span>
        <p className="text-sm">Awaiting Alpha Gene…</p>
      </div>
    )
  }

  return (
    <div className="card h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Alpha Gene</h2>
        {fitness !== undefined && (
          <span className="text-xs bg-indigo-900/50 text-indigo-300 border border-indigo-800 rounded px-2 py-0.5 tabular-nums">
            fitness {fitness >= 0 ? '+' : ''}{Number(fitness).toFixed(4)}
          </span>
        )}
      </div>

      <div className="flex flex-col gap-3 flex-1">
        {PARAM_META.map((meta) => (
          <GeneBar key={meta.key} meta={meta} value={gene[meta.key]} />
        ))}
      </div>

      <div className="border-t border-gray-800 pt-3 grid grid-cols-3 gap-2 text-center">
        <Stat label="RSI" value={gene.rsi_period} />
        <Stat label="MA" value={`${gene.ma_short}/${gene.ma_long}`} />
        <Stat label="Size" value={`${((gene.position_size_pct ?? 0) * 100).toFixed(0)}%`} />
      </div>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div>
      <p className="text-gray-500 text-xs">{label}</p>
      <p className="text-gray-200 text-sm font-semibold tabular-nums">{value}</p>
    </div>
  )
}
