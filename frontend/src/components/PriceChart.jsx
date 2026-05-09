import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts'

export default function PriceChart({ data, signals }) {
  if (!data.length) return null
  const entry = data[0]?.price || 142.5
  const current = data[data.length - 1]?.price || 142.5
  const isUp = current >= entry

  // Build signal lookup by time
  const signalMap = {}
  signals.forEach(s => { signalMap[s.time] = s })

  const chartData = data.map(d => ({
    ...d,
    signal: signalMap[d.time]?.type || null,
  }))

  return (
    <div className="h-full w-full p-3 flex flex-col">
      <div className="flex items-center justify-between mb-2 px-1">
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-semibold text-evo-text">EVOX/USD</span>
          <span className={`font-mono text-lg font-bold ${isUp ? 'text-evo-green' : 'text-evo-red'}`}>
            ${current.toFixed(2)}
          </span>
        </div>
        <div className="flex items-center gap-4 text-[10px] font-mono text-evo-muted">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rotate-45 bg-evo-green inline-block" /> BUY
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rotate-45 bg-evo-red inline-block" /> SELL
          </span>
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="priceGradUp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00FF88" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#00FF88" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="priceGradDown" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#FF3B5C" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#FF3B5C" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="time" tick={{ fill: '#555', fontSize: 9, fontFamily: 'JetBrains Mono' }}
              axisLine={{ stroke: '#1E1E1E' }} tickLine={false} interval="preserveStartEnd"
              minTickGap={60} />
            <YAxis domain={['auto', 'auto']} tick={{ fill: '#555', fontSize: 9, fontFamily: 'JetBrains Mono' }}
              axisLine={{ stroke: '#1E1E1E' }} tickLine={false} width={50} />
            <Tooltip
              contentStyle={{ backgroundColor: '#111', border: '1px solid #1E1E1E', borderRadius: '6px', fontFamily: 'JetBrains Mono', fontSize: '11px' }}
              labelStyle={{ color: '#555' }}
              itemStyle={{ color: '#E8E8E8' }}
              formatter={(v) => [`$${v.toFixed(2)}`, 'Price']}
            />
            <Area type="monotone" dataKey="price"
              stroke={isUp ? '#00FF88' : '#FF3B5C'}
              strokeWidth={1.5}
              fill={isUp ? 'url(#priceGradUp)' : 'url(#priceGradDown)'}
            />
            {signals.slice(-20).map((s, i) => (
              <ReferenceDot key={i} x={s.time} y={s.price}
                r={4}
                fill={s.type === 'BUY' ? '#00FF88' : '#FF3B5C'}
                stroke="none"
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
