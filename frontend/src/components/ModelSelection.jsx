import { useState, useEffect } from 'react'
import { LineChart, Line, ResponsiveContainer } from 'recharts'
import { MODELS, generateSparkline, randomMetrics } from '../simulation'

export default function ModelSelection({ profile, onDeploy }) {
  const [phase, setPhase] = useState('racing') // racing | results | confirm
  const [scores] = useState(() => MODELS.map(() => 55 + Math.random() * 40))
  const [widths, setWidths] = useState([0, 0, 0])
  const [modelData] = useState(() =>
    MODELS.map((m, i) => ({
      ...m,
      score: scores[i],
      metrics: randomMetrics(),
      sparkline: generateSparkline(30),
    }))
  )

  // Animate bars
  useEffect(() => {
    const t = setTimeout(() => setWidths(scores), 100)
    const t2 = setTimeout(() => setPhase('results'), 3500)
    return () => { clearTimeout(t); clearTimeout(t2) }
  }, [scores])

  const capital = profile?.capital || '10,000'

  return (
    <div className="h-full flex flex-col bg-evo-bg overflow-y-auto">
      <div className="flex-1 flex flex-col items-center justify-center px-8 py-10 max-w-4xl mx-auto w-full">

        {/* Header */}
        <div className="w-full mb-10 animate-fade-in">
          <p className="font-mono text-sm text-evo-green mb-1">
            <span className="text-evo-green">[EvoTrade]</span>{' '}
            <span className="text-evo-green/60">&gt;_</span>{' '}
            {phase === 'racing' ? 'Running Evolutionary Optimization...' : 'Evolution Complete — Top 3 Models Selected'}
          </p>
          {phase === 'racing' && (
            <p className="font-mono text-xs text-evo-muted mt-1">
              Evaluating 1,247 strategy combinations across 3 gene pools...
            </p>
          )}
        </div>

        {/* Progress Race */}
        {phase === 'racing' && (
          <div className="w-full space-y-6 animate-fade-in">
            {modelData.map((m, i) => (
              <div key={m.id}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs text-evo-text">
                    Model {m.id}: <span style={{ color: m.color }}>{m.name}</span>
                  </span>
                  <span className="font-mono text-xs text-evo-muted">
                    {widths[i] > 0 ? `${scores[i].toFixed(1)}%` : '—'}
                  </span>
                </div>
                <div className="w-full h-2 bg-evo-border rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-[3000ms] ease-out"
                    style={{ width: `${widths[i]}%`, backgroundColor: m.color }}
                  />
                </div>
              </div>
            ))}
            <div className="flex items-center gap-2 mt-6">
              <div className="w-1.5 h-1.5 rounded-full bg-evo-green animate-pulse" />
              <span className="font-mono text-xs text-evo-muted">Fitness evaluation in progress...</span>
            </div>
          </div>
        )}

        {/* Model Cards */}
        {phase !== 'racing' && (
          <div className="w-full space-y-4 animate-slide-up">
            {modelData.sort((a, b) => b.score - a.score).map((m, i) => (
              <div key={m.id}
                className="bg-evo-panel border border-evo-border rounded-lg p-5 hover:border-evo-muted/30
                  transition-all duration-200 group">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-evo-muted">#{i + 1}</span>
                      <h3 className="font-sans font-semibold text-evo-text">{m.name}</h3>
                    </div>
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-mono font-medium"
                      style={{ backgroundColor: m.color + '15', color: m.color, border: `1px solid ${m.color}33` }}>
                      {m.type}
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-lg font-bold" style={{ color: m.color }}>
                      {m.score.toFixed(1)}%
                    </div>
                    <div className="font-mono text-[10px] text-evo-muted">FITNESS</div>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-4 mb-4">
                  {[
                    ['Win Rate', `${m.metrics.winRate}%`, m.metrics.winRate > 60],
                    ['Avg Return', `${m.metrics.avgReturn}%`, true],
                    ['Max DD', `${m.metrics.maxDrawdown}%`, false],
                    ['Sharpe', m.metrics.sharpe.toFixed(2), m.metrics.sharpe > 1.5],
                  ].map(([label, val, positive]) => (
                    <div key={label}>
                      <div className="font-mono text-[10px] text-evo-muted uppercase mb-0.5">{label}</div>
                      <div className={`font-mono text-sm font-medium ${positive ? 'text-evo-green' : 'text-evo-red'}`}>
                        {val}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="h-12">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={m.sparkline}>
                      <Line type="monotone" dataKey="y" stroke={m.color} strokeWidth={1.5}
                        dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ))}

            {/* Deploy Button */}
            <button
              onClick={() => setPhase('confirm')}
              className="w-full mt-6 py-4 bg-evo-green/10 border border-evo-green/40 rounded-lg
                font-mono text-sm font-semibold text-evo-green
                hover:bg-evo-green/20 hover:border-evo-green/60 hover:shadow-[0_0_20px_#00FF8822]
                transition-all duration-200 active:scale-[0.99]"
            >
              [ DEPLOY TOP 3 MODELS — START PAPER TRADING ]
            </button>
          </div>
        )}

        {/* Confirmation Modal */}
        {phase === 'confirm' && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in">
            <div className="bg-evo-panel border border-evo-border rounded-xl p-8 max-w-md w-full mx-4 animate-slide-up">
              <div className="w-10 h-10 rounded-full bg-evo-green/10 border border-evo-green/30
                flex items-center justify-center mb-5 mx-auto">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00FF88"
                  strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <h3 className="font-sans font-semibold text-lg text-center text-evo-text mb-3">
                Deploy Paper Trading?
              </h3>
              <p className="font-mono text-xs text-evo-muted text-center mb-6 leading-relaxed">
                Are you ready to go live with paper trading?<br />
                Your capital of <span className="text-evo-green">${capital}</span> will be simulated.
              </p>
              <div className="flex gap-3">
                <button onClick={() => setPhase('results')}
                  className="flex-1 py-3 rounded-lg border border-evo-border text-evo-muted font-mono text-sm
                    hover:bg-evo-border/30 transition-all duration-200">
                  CANCEL
                </button>
                <button onClick={() => onDeploy(modelData)}
                  className="flex-1 py-3 rounded-lg bg-evo-green text-evo-bg font-mono text-sm font-semibold
                    hover:shadow-[0_0_20px_#00FF8844] transition-all duration-200 active:scale-[0.98]">
                  YES, DEPLOY
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
