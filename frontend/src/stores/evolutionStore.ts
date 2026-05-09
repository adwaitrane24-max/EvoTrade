import { create } from 'zustand'
import { Chromosome, GenerationData } from '../types'

interface EvolutionState {
  evolutionId: string
  currentGeneration: number
  completedGenerations: number
  generations: GenerationData[]
  allChromosomes: Chromosome[]
  top3: Chromosome[]
  selectedAlphaGene: Chromosome | null
  isComplete: boolean
  statusLog: string[]

  setEvolutionId: (id: string) => void
  setCurrentGeneration: (g: number) => void
  setCompletedGenerations: (g: number) => void
  addChromosome: (c: Chromosome) => void
  addGeneration: (g: GenerationData) => void
  setTop3: (top3: Chromosome[]) => void
  setSelectedAlphaGene: (c: Chromosome | null) => void
  setComplete: (v: boolean) => void
  appendLog: (msg: string) => void
  reset: () => void
}

export const useEvolutionStore = create<EvolutionState>((set) => ({
  evolutionId: '',
  currentGeneration: 0,
  completedGenerations: 0,
  generations: [],
  allChromosomes: [],
  top3: [],
  selectedAlphaGene: null,
  isComplete: false,
  statusLog: [],

  setEvolutionId: (id) => set({ evolutionId: id }),
  setCurrentGeneration: (g) => set({ currentGeneration: g }),
  setCompletedGenerations: (g) => set({ completedGenerations: g }),
  addChromosome: (c) => set((s) => ({ allChromosomes: [...s.allChromosomes, c] })),
  addGeneration: (g) => set((s) => ({ generations: [...s.generations, g] })),
  setTop3: (top3) => set({ top3 }),
  setSelectedAlphaGene: (c) => set({ selectedAlphaGene: c }),
  setComplete: (v) => set({ isComplete: v }),
  appendLog: (msg) => set((s) => ({ statusLog: [...s.statusLog.slice(-49), msg] })),
  reset: () => set({
    evolutionId: '', currentGeneration: 0, completedGenerations: 0,
    generations: [], allChromosomes: [], top3: [], selectedAlphaGene: null,
    isComplete: false, statusLog: [],
  }),
}))
