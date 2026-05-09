import { useEffect } from 'react'
import { wsManager } from '../lib/ws'
import { useWsStore } from '../stores/wsStore'
import { useTradingStore } from '../stores/tradingStore'
import { useEvolutionStore } from '../stores/evolutionStore'
import { WsEvent, Candle, Trade, Portfolio, Chromosome } from '../types'

let initialised = false

export function useWebSocket(userId = 'default') {
  const setConnected = useWsStore((s) => s.setConnected)
  const { appendCandle, addTrade, setPortfolio, setRegime } = useTradingStore()
  const { appendLog, setCurrentGeneration, setCompletedGenerations, addChromosome, setTop3, setComplete: setEvoComplete, setSelectedAlphaGene } = useEvolutionStore()

  useEffect(() => {
    if (!initialised) {
      wsManager.connect(userId)
      initialised = true
    }

    const unsub = wsManager.subscribe((event: WsEvent) => {
      switch (event.type) {
        case 'WS_CONNECTED':
          setConnected(true)
          break
        case 'WS_DISCONNECTED':
          setConnected(false)
          break

        case 'MARKET_TICK':
          appendCandle(event.data as unknown as Candle)
          break

        case 'TRADE_EXECUTED':
          addTrade(event.data as unknown as Trade)
          break

        case 'PORTFOLIO_UPDATE':
          setPortfolio(event.data as unknown as Portfolio)
          break

        case 'REGIME_CHANGED': {
          const d = event.data as { regime?: string; confidence?: number }
          setRegime((d.regime ?? 'SIDEWAYS') as 'BULL' | 'BEAR' | 'SIDEWAYS' | 'CRASH', d.confidence ?? 0.7)
          break
        }

        case 'GEN_STARTED': {
          const d = event.data as { generation: number }
          setCurrentGeneration(d.generation)
          appendLog(`Generation ${d.generation} started`)
          break
        }
        case 'GEN_COMPLETED': {
          const d = event.data as { generation: number }
          setCompletedGenerations(d.generation)
          appendLog(`Generation ${d.generation} complete`)
          break
        }
        case 'CHROMOSOME_CREATED': {
          const d = event.data as unknown as Chromosome & { generation: number; chromosome_id: string }
          addChromosome({ ...d, id: d.chromosome_id })
          break
        }
        case 'TOP_3_SELECTED': {
          const d = event.data as { top3: Chromosome[]; generation: number }
          setTop3(d.top3)
          appendLog(`Top 3 selected for generation ${d.generation}`)
          break
        }
        case 'EVOLUTION_COMPLETE': {
          const d = event.data as { final_top_3: Chromosome[]; best_alpha_gene: Chromosome }
          setTop3(d.final_top_3)
          setSelectedAlphaGene(d.best_alpha_gene)
          setEvoComplete(true)
          appendLog('Evolution complete — AlphaGene ready')
          break
        }
        case 'MONTE_CARLO_STARTED':
          appendLog(`Monte Carlo stress test started (gen ${(event.data as { generation: number }).generation})`)
          break
        case 'AI_COUNCIL_STARTED':
          appendLog(`AI Council evaluating (gen ${(event.data as { generation: number }).generation})`)
          break
        case 'FITNESS_SCORED':
          appendLog(`Fitness scored for generation ${(event.data as { generation: number }).generation}`)
          break
      }
    })

    return () => { unsub() }
  }, [userId])
}
