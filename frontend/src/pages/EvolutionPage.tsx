import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { GenerationProgress } from '../components/evolution/GenerationProgress'
import { ChromosomeCard } from '../components/evolution/ChromosomeCard'
import { FitnessChart } from '../components/evolution/FitnessChart'
import { Top3Confirmation } from '../components/evolution/Top3Confirmation'
import { useEvolutionStore } from '../stores/evolutionStore'
import { useTradingStore } from '../stores/tradingStore'
import { useChatStore } from '../stores/chatStore'
import { Chromosome } from '../types'
import api from '../lib/api'

const USER_ID = 'evotrade-demo-user'

export function EvolutionPage() {
  const navigate = useNavigate()
  const started = useRef(false)
  const { profileId } = useChatStore()
  const {
    evolutionId, currentGeneration, completedGenerations,
    allChromosomes, top3, isComplete, statusLog, setEvolutionId,
  } = useEvolutionStore()
  const { setAlphaGene, setRunning } = useTradingStore()

  useEffect(() => {
    if (started.current || evolutionId) return
    started.current = true
    ;(async () => {
      try {
        const res = await api.post('/api/evolution/start', {
          user_id: USER_ID,
          profile_id: profileId || 'demo',
        })
        setEvolutionId(res.data.evolution_id)
      } catch (e) {
        console.error('Evolution start failed', e)
      }
    })()
  }, [])

  const top3Ids = new Set(top3.map((c) => c.id))

  const currentGenChroms = allChromosomes.filter((c) => c.generation === currentGeneration)

  const handleConfirm = async (selected: Chromosome) => {
    setAlphaGene(selected)
    try {
      await api.post('/api/trading/store-alpha', {
        alpha_gene_id: selected.alpha_gene_id,
        gene: selected.genes,
        profile: {},
      })
    } catch {}
    try {
      await api.post('/api/trading/start', {
        user_id: USER_ID,
        alpha_gene_id: selected.alpha_gene_id ?? 'default',
      })
      setRunning(true)
    } catch (e) {
      console.error('Trading start failed', e)
    }
    navigate('/dashboard')
  }

  return (
    <div className="h-full overflow-y-auto pr-[240px]">
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Strategy Evolution</h1>
          <p className="text-sm text-text-secondary mt-1">
            Running {5} generations × 10 chromosomes. Watch your AlphaGene emerge.
          </p>
        </div>

        {/* Generation pills */}
        <div className="bg-bg-surface border border-bg-border rounded-xl p-5">
          <GenerationProgress current={currentGeneration} completed={completedGenerations} />
        </div>

        {/* Fitness chart */}
        <div className="bg-bg-surface border border-bg-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Fitness Landscape</h2>
          <FitnessChart chromosomes={allChromosomes} top3Ids={top3Ids} />
        </div>

        {/* Chromosome grid for current generation */}
        {currentGenChroms.length > 0 && (
          <div className="bg-bg-surface border border-bg-border rounded-xl p-5">
            <h2 className="text-sm font-semibold text-text-primary mb-4">
              Generation {currentGeneration} — Chromosomes
            </h2>
            <div className="grid grid-cols-5 gap-3">
              {currentGenChroms.map((c) => (
                <ChromosomeCard key={c.id} chrom={c} isTop={top3Ids.has(c.id)} />
              ))}
            </div>
          </div>
        )}

        {/* Status log */}
        <div className="bg-bg-surface border border-bg-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-3">Activity Log</h2>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {statusLog.length === 0 && (
              <p className="text-xs text-text-muted">Initialising evolution engine...</p>
            )}
            {[...statusLog].reverse().map((log, i) => (
              <p key={i} className="text-xs text-text-secondary font-mono">
                <span className="text-text-muted mr-2">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                {log}
              </p>
            ))}
          </div>
        </div>

        {/* Top 3 confirmation */}
        {isComplete && top3.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-bg-surface border border-accent-primary/20 rounded-xl p-6"
          >
            <Top3Confirmation
              top3={top3}
              onConfirm={handleConfirm}
              onCancel={() => navigate('/')}
            />
          </motion.div>
        )}

        {/* Waiting state */}
        {!isComplete && !evolutionId && (
          <div className="text-center py-8 text-text-muted text-sm">
            Starting evolution engine...
          </div>
        )}
      </div>
    </div>
  )
}
