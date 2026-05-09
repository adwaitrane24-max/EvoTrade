/**
 * store/index.js — Zustand store with all PRD §22.2 slices.
 * One slice per domain: session, market, strategy, evolution, risk, logs, ai.
 */

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

import { createSessionSlice }   from './sessionSlice'
import { createMarketSlice }    from './marketSlice'
import { createStrategySlice }  from './strategySlice'
import { createEvolutionSlice } from './evolutionSlice'
import { createRiskSlice }      from './riskSlice'
import { createLogsSlice }      from './logsSlice'
import { createAiSlice }        from './aiSlice'
import { createSystemSlice }    from './systemSlice'

export const useStore = create(
  devtools(
    (set, get) => ({
      ...createSessionSlice(set, get),
      ...createMarketSlice(set, get),
      ...createStrategySlice(set, get),
      ...createEvolutionSlice(set, get),
      ...createRiskSlice(set, get),
      ...createLogsSlice(set, get),
      ...createAiSlice(set, get),
      ...createSystemSlice(set, get),
    }),
    { name: 'evotrade' }
  )
)

// Convenience selectors
export const useRegime    = () => useStore((s) => ({ regime: s.regime, confidence: s.regimeConfidence, posterior: s.regimePosterior, transition: s.transitionMatrix }))
export const useEvolution = () => useStore((s) => ({ generations: s.generations, fitnessHistory: s.fitnessHistory, currentGeneration: s.currentGeneration, alphaGenePerGen: s.alphaGenePerGen, finalAlphaGene: s.finalAlphaGene, running: s.evolutionRunning }))
export const useStrategy  = () => useStore((s) => ({ active: s.activeStrategy, shadow: s.shadowStrategy, all: s.strategies }))
export const useTrades    = () => useStore((s) => s.fills)
export const useSignals   = () => useStore((s) => s.signals)
export const useAiCards   = () => useStore((s) => s.aiCards)
export const useRisk      = () => useStore((s) => ({ killSwitch: s.killSwitchActive, limits: s.riskLimits, events: s.riskEvents }))
