import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { PriceChart } from '../components/dashboard/PriceChart'
import { PortfolioCard } from '../components/dashboard/PortfolioCard'
import { AlphaGenePanel } from '../components/dashboard/AlphaGenePanel'
import { RegimeIndicator } from '../components/dashboard/RegimeIndicator'
import { TradeLog } from '../components/dashboard/TradeLog'
import { PnLCard } from '../components/dashboard/PnLCard'
import { EmergencyStop } from '../components/dashboard/EmergencyStop'
import { useTradingStore } from '../stores/tradingStore'
import { useChatStore } from '../stores/chatStore'
import api from '../lib/api'

const POLL_MS = 5000

export function DashboardPage() {
  const navigate = useNavigate()
  const { candles, trades, portfolio, regime, regimeConfidence, alphaGene, currentPrice } = useTradingStore()
  const { setPortfolio } = useTradingStore()
  const { profile } = useChatStore()
  const initialCapital = profile.capital ?? 50000

  // Poll portfolio every 5s as a fallback for WS gaps
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const res = await api.get('/api/trading/portfolio')
        setPortfolio(res.data)
      } catch {}
    }, POLL_MS)
    return () => clearInterval(id)
  }, [])

  const safePortfolio = portfolio ?? {
    cash: initialCapital,
    position: null,
    trades: [],
    equity_curve: [initialCapital],
    total_pnl: 0,
    daily_pnl: 0,
    win_rate: 0,
    wins: 0,
    total_closed: 0,
  }

  return (
    <div className="h-full overflow-y-auto pr-[240px] pb-4">
      <div className="px-5 py-5 space-y-4 max-w-[1100px]">

        {/* Current price ticker */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-text-primary">Live Paper Trading</h1>
            <p className="text-xs text-text-muted mt-0.5">BTC/USDT · Binance · Paper only — no real money</p>
          </div>
          {currentPrice > 0 && (
            <div className="text-right">
              <div className="text-2xl font-mono font-bold text-text-primary">
                ${currentPrice.toLocaleString()}
              </div>
              <div className="text-xs text-text-muted font-mono">BTC/USDT</div>
            </div>
          )}
        </div>

        {/* Row 1: KPI cards */}
        <PortfolioCard portfolio={safePortfolio} initialCapital={initialCapital} />

        {/* Row 2: Price chart + Alpha gene */}
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-8 bg-bg-surface border border-bg-border rounded-xl p-4" style={{ height: 280 }}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">BTC/USDT — 1m</h3>
              <span className="text-xs text-text-muted font-mono">{candles.length} candles</span>
            </div>
            <div style={{ height: 220 }}>
              {candles.length > 1 ? (
                <PriceChart candles={candles} trades={trades} />
              ) : (
                <div className="flex items-center justify-center h-full text-text-muted text-xs">
                  Waiting for price data from Binance...
                </div>
              )}
            </div>
          </div>

          <div className="col-span-4 bg-bg-surface border border-bg-border rounded-xl p-4" style={{ height: 280 }}>
            {alphaGene ? (
              <AlphaGenePanel gene={alphaGene} />
            ) : (
              <div className="flex items-center justify-center h-full text-text-muted text-xs">
                No alpha gene deployed
              </div>
            )}
          </div>
        </div>

        {/* Row 3: Trade log + Regime + Equity */}
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-5 bg-bg-surface border border-bg-border rounded-xl p-4" style={{ height: 280 }}>
            <TradeLog trades={trades} />
          </div>

          <div className="col-span-3 bg-bg-surface border border-bg-border rounded-xl p-4 flex flex-col items-center justify-center" style={{ height: 280 }}>
            <h3 className="text-sm font-semibold text-text-primary mb-4">Market Regime</h3>
            <RegimeIndicator regime={regime} confidence={regimeConfidence} />
          </div>

          <div className="col-span-4 bg-bg-surface border border-bg-border rounded-xl p-4" style={{ height: 280 }}>
            <PnLCard equityCurve={safePortfolio.equity_curve} initialCapital={initialCapital} />
          </div>
        </div>

        {/* Row 4: Emergency stop */}
        <EmergencyStop onStopped={() => {}} />
      </div>
    </div>
  )
}
