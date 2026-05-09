import { AreaChart, Area, ResponsiveContainer, Tooltip, YAxis } from 'recharts'

export default function EquityCurve({ data }) {
  const isUp = data.length >= 2 && data[data.length - 1].value >= data[0].value

  return (
    <div className="h-full w-full flex items-center px-4 gap-4">
      <div className="shrink-0">
        <div className="font-mono text-[9px] text-evo-muted uppercase tracking-wider">Equity Curve</div>
        <div className={`font-mono text-sm font-bold ${isUp ? 'text-evo-green' : 'text-evo-red'}`}>
          ${data[data.length - 1]?.value?.toLocaleString() || '—'}
        </div>
      </div>
      <div className="flex-1 h-full py-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
            <defs>
              <linearGradient id="eqGradUp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00FF88" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#00FF88" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="eqGradDown" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#FF3B5C" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#FF3B5C" stopOpacity={0} />
              </linearGradient>
            </defs>
            <YAxis hide domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ backgroundColor: '#111', border: '1px solid #1E1E1E', borderRadius: '6px',
                fontFamily: 'JetBrains Mono', fontSize: '10px' }}
              formatter={(v) => [`$${v.toFixed(2)}`, 'Value']}
              labelFormatter={() => ''}
            />
            <Area type="monotone" dataKey="value"
              stroke={isUp ? '#00FF88' : '#FF3B5C'}
              strokeWidth={1.5}
              fill={isUp ? 'url(#eqGradUp)' : 'url(#eqGradDown)'}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
