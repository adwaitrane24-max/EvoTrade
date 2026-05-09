import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { MODELS } from '../simulation'

export default function ModelPerformance({ modelPnl }) {
  const data = MODELS.map(m => ({
    name: m.id,
    fullName: m.name,
    pnl: modelPnl[m.name] || 0,
    color: m.color,
  }))

  return (
    <div className="h-full flex flex-col p-3">
      <span className="font-mono text-[11px] font-semibold text-evo-muted uppercase tracking-wider mb-2 px-1">
        Model P&L
      </span>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <XAxis dataKey="name" tick={{ fill: '#555', fontSize: 10, fontFamily: 'JetBrains Mono' }}
              axisLine={{ stroke: '#1E1E1E' }} tickLine={false} />
            <YAxis tick={{ fill: '#555', fontSize: 9, fontFamily: 'JetBrains Mono' }}
              axisLine={{ stroke: '#1E1E1E' }} tickLine={false} width={40} />
            <Tooltip
              contentStyle={{ backgroundColor: '#111', border: '1px solid #1E1E1E', borderRadius: '6px',
                fontFamily: 'JetBrains Mono', fontSize: '11px' }}
              formatter={(v, _, props) => [`$${v.toFixed(2)}`, props.payload.fullName]}
              labelFormatter={() => ''}
            />
            <Bar dataKey="pnl" radius={[3, 3, 0, 0]}>
              {data.map((d, i) => (
                <Cell key={i} fill={d.pnl >= 0 ? d.color : '#FF3B5C'} fillOpacity={0.8} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
