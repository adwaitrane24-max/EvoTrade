import { useState, useEffect, useCallback } from 'react'
import { generatePriceData, nextPrice, simulateTrade, generateOrderBook, MODELS } from '../simulation'
import PriceChart from './PriceChart'
import OrderBook from './OrderBook'
import ActivePositions from './ActivePositions'
import TradeLog from './TradeLog'
import ModelPerformance from './ModelPerformance'
import EquityCurve from './EquityCurve'

export default function Dashboard({ profile, models }) {
  const capital = parseFloat(profile?.capital) || 10000
  const [clock, setClock] = useState(new Date())
  const [priceData, setPriceData] = useState(() => generatePriceData(60))
  const [signals, setSignals] = useState([])
  const [trades, setTrades] = useState([])
  const [orderBook, setOrderBook] = useState(() => generateOrderBook(142.5))
  const [equityData, setEquityData] = useState(() => [{ time: new Date().toLocaleTimeString('en-US', { hour12: false }), value: capital }])
  const [portfolioValue, setPortfolioValue] = useState(capital)
  const [totalPnl, setTotalPnl] = useState(0)
  const [modelPnl, setModelPnl] = useState({ 'Momentum-RSI Hybrid': 0, 'Mean Reversion MACD': 0, 'Breakout + Volume Surge': 0 })

  const [positions] = useState(() =>
    MODELS.map((m, i) => ({
      ticker: ['EVOX/USD', 'BTCN/USD', 'ETHX/USD'][i],
      model: m.name,
      modelColor: m.color,
      entry: parseFloat((140 + Math.random() * 5).toFixed(2)),
      side: Math.random() > 0.4 ? 'LONG' : 'SHORT',
    }))
  )

  const currentPrice = priceData[priceData.length - 1]?.price || 142.5

  // Clock
  useEffect(() => {
    const iv = setInterval(() => setClock(new Date()), 1000)
    return () => clearInterval(iv)
  }, [])

  // Price updates (every 2s)
  useEffect(() => {
    const iv = setInterval(() => {
      setPriceData(prev => {
        const last = prev[prev.length - 1]
        const np = nextPrice(last.price)
        const now = new Date()
        const newPoint = {
          time: now.toLocaleTimeString('en-US', { hour12: false }),
          price: np,
          ts: Date.now(),
        }
        const updated = [...prev.slice(-120), newPoint]

        // Random signal
        if (Math.random() < 0.08) {
          setSignals(s => [...s.slice(-30), {
            ...newPoint,
            type: Math.random() > 0.5 ? 'BUY' : 'SELL',
            model: MODELS[Math.floor(Math.random() * 3)].name,
          }])
        }
        return updated
      })
    }, 2000)
    return () => clearInterval(iv)
  }, [])

  // Order book updates (every 2s)
  useEffect(() => {
    const iv = setInterval(() => {
      setPriceData(prev => {
        const cp = prev[prev.length - 1]?.price || 142.5
        setOrderBook(generateOrderBook(cp))
        return prev
      })
    }, 2000)
    return () => clearInterval(iv)
  }, [])

  // Trade events (every 5-8s)
  useEffect(() => {
    const schedule = () => {
      const delay = 5000 + Math.random() * 3000
      return setTimeout(() => {
        setPriceData(prev => {
          const cp = prev[prev.length - 1]?.price || 142.5
          const trade = simulateTrade(cp)
          setTrades(t => [...t.slice(-50), trade])

          // Update model P&L
          setModelPnl(mp => ({
            ...mp,
            [trade.model]: parseFloat((mp[trade.model] + trade.pnl).toFixed(2)),
          }))

          // Update portfolio
          setTotalPnl(p => {
            const newPnl = parseFloat((p + trade.pnl).toFixed(2))
            setPortfolioValue(capital + newPnl)
            return newPnl
          })

          return prev
        })
        timerId = schedule()
      }, delay)
    }
    let timerId = schedule()
    return () => clearTimeout(timerId)
  }, [capital])

  // Equity curve (every 3s)
  useEffect(() => {
    const iv = setInterval(() => {
      setEquityData(prev => {
        const last = prev[prev.length - 1]?.value || capital
        const jitter = (Math.random() - 0.42) * 50
        return [...prev.slice(-80), {
          time: new Date().toLocaleTimeString('en-US', { hour12: false }),
          value: parseFloat((last + jitter).toFixed(2)),
        }]
      })
    }, 3000)
    return () => clearInterval(iv)
  }, [capital])

  const pnlPct = ((portfolioValue - capital) / capital * 100).toFixed(2)
  const pnlPositive = totalPnl >= 0

  return (
    <div className="h-full flex flex-col bg-evo-bg overflow-hidden">
      {/* Top Bar */}
      <div className="px-5 py-3 border-b border-evo-border flex items-center gap-6 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-evo-green animate-pulse-green" />
          <span className="font-mono text-[11px] font-semibold text-evo-green tracking-wider uppercase">
            Paper Trading Active
          </span>
        </div>
        <div className="h-4 w-px bg-evo-border" />
        <Stat label="CAPITAL" value={`$${capital.toLocaleString()}`} />
        <Stat label="PORTFOLIO" value={`$${portfolioValue.toLocaleString()}`} color={pnlPositive ? 'text-evo-green' : 'text-evo-red'} />
        <Stat label="P&L" value={`${pnlPositive ? '+' : ''}$${totalPnl.toFixed(2)} (${pnlPct}%)`} color={pnlPositive ? 'text-evo-green' : 'text-evo-red'} />
        <div className="ml-auto font-mono text-xs text-evo-muted">
          {clock.toLocaleTimeString('en-US', { hour12: false })}
        </div>
      </div>

      {/* Main Grid */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column */}
        <div className="flex-[65] flex flex-col min-w-0 border-r border-evo-border">
          <div className="flex-[3] min-h-0 border-b border-evo-border">
            <PriceChart data={priceData} signals={signals} />
          </div>
          <div className="flex-[2] min-h-0 overflow-hidden">
            <OrderBook data={orderBook} currentPrice={currentPrice} />
          </div>
        </div>

        {/* Right Column */}
        <div className="flex-[35] flex flex-col min-w-0 overflow-hidden">
          <div className="border-b border-evo-border overflow-auto" style={{ flex: '0 0 auto', maxHeight: '30%' }}>
            <ActivePositions positions={positions} currentPrice={currentPrice} />
          </div>
          <div className="flex-1 min-h-0 border-b border-evo-border overflow-hidden">
            <TradeLog trades={trades} />
          </div>
          <div className="border-b border-evo-border" style={{ flex: '0 0 auto', height: '28%' }}>
            <ModelPerformance modelPnl={modelPnl} />
          </div>
        </div>
      </div>

      {/* Bottom Equity Curve */}
      <div className="h-24 shrink-0 border-t border-evo-border">
        <EquityCurve data={equityData} />
      </div>
    </div>
  )
}

function Stat({ label, value, color = 'text-evo-text' }) {
  return (
    <div>
      <div className="font-mono text-[9px] text-evo-muted tracking-wider uppercase">{label}</div>
      <div className={`font-mono text-xs font-medium ${color}`}>{value}</div>
    </div>
  )
}
